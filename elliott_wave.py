"""Elliott Wave detection on OHLC data.

Approach:
  1. Detect ZigZag pivots from highs/lows using a percentage deviation.
  2. Try to fit the most recent pivots to a 5-wave impulse (and optional ABC).
  3. Validate Elliott's three cardinal rules.
  4. Compute Fibonacci ratios and project simple targets.

The result is a JSON-serialisable dict consumed by the Flask front end.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def zigzag(highs: np.ndarray, lows: np.ndarray, deviation: float = 0.05) -> list[tuple[int, float, str]]:
    """ZigZag pivot detection.

    A new pivot is confirmed when price retraces by `deviation` (fraction)
    from the most recent extreme. Returns a list of (index, price, 'H'|'L').
    """
    n = len(highs)
    pivots: list[tuple[int, float, str]] = []
    if n < 2:
        return pivots

    last_high = float(highs[0])
    last_high_idx = 0
    last_low = float(lows[0])
    last_low_idx = 0
    direction: str | None = None

    for i in range(1, n):
        hi = float(highs[i])
        lo = float(lows[i])

        if direction is None:
            if hi >= last_low * (1 + deviation):
                pivots.append((last_low_idx, last_low, 'L'))
                last_high, last_high_idx = hi, i
                direction = 'up'
            elif lo <= last_high * (1 - deviation):
                pivots.append((last_high_idx, last_high, 'H'))
                last_low, last_low_idx = lo, i
                direction = 'down'
            else:
                if hi > last_high:
                    last_high, last_high_idx = hi, i
                if lo < last_low:
                    last_low, last_low_idx = lo, i
        elif direction == 'up':
            if hi > last_high:
                last_high, last_high_idx = hi, i
            elif lo <= last_high * (1 - deviation):
                pivots.append((last_high_idx, last_high, 'H'))
                last_low, last_low_idx = lo, i
                direction = 'down'
        else:  # down
            if lo < last_low:
                last_low, last_low_idx = lo, i
            elif hi >= last_low * (1 + deviation):
                pivots.append((last_low_idx, last_low, 'L'))
                last_high, last_high_idx = hi, i
                direction = 'up'

    if direction == 'up':
        pivots.append((last_high_idx, last_high, 'H'))
    elif direction == 'down':
        pivots.append((last_low_idx, last_low, 'L'))

    return pivots


def _validate_pattern(seq: list[tuple[int, float, str]]) -> dict[str, Any] | None:
    """Validate an Elliott impulse (and optional ABC) on a pivot sequence.

    Bullish impulse expects pivots typed as L H L H L H, bearish as H L H L H L.
    """
    if len(seq) < 6:
        return None

    types = [p[2] for p in seq]
    for i in range(1, len(seq)):
        if types[i] == types[i - 1]:
            return None  # pivots must alternate

    if types[0] == 'L':
        direction = 'bullish'
    elif types[0] == 'H':
        direction = 'bearish'
    else:
        return None

    p = seq[:6]
    if direction == 'bullish':
        wave1 = p[1][1] - p[0][1]
        wave3 = p[3][1] - p[2][1]
        wave5 = p[5][1] - p[4][1]
        if wave1 <= 0 or wave3 <= 0 or wave5 <= 0:
            return None
        if p[2][1] <= p[0][1]:
            return None  # Wave 2 retraced past origin
        if wave3 < wave1 and wave3 < wave5:
            return None  # Wave 3 cannot be the shortest
        if p[4][1] <= p[1][1]:
            return None  # Wave 4 cannot overlap Wave 1
        wave2_retrace = (p[1][1] - p[2][1]) / wave1
        wave4_retrace = (p[3][1] - p[4][1]) / wave3
    else:
        wave1 = p[0][1] - p[1][1]
        wave3 = p[2][1] - p[3][1]
        wave5 = p[4][1] - p[5][1]
        if wave1 <= 0 or wave3 <= 0 or wave5 <= 0:
            return None
        if p[2][1] >= p[0][1]:
            return None
        if wave3 < wave1 and wave3 < wave5:
            return None
        if p[4][1] >= p[1][1]:
            return None
        wave2_retrace = (p[2][1] - p[1][1]) / wave1
        wave4_retrace = (p[4][1] - p[3][1]) / wave3

    labels = ['0', '1', '2', '3', '4', '5']
    waves = [
        {'label': labels[i], 'index': int(p[i][0]), 'price': float(p[i][1])}
        for i in range(6)
    ]

    has_correction = False
    if len(seq) >= 9:
        a, b, c = seq[6], seq[7], seq[8]
        if direction == 'bullish' and types[6] == 'L' and types[7] == 'H' and types[8] == 'L':
            if a[1] < p[5][1] and b[1] > a[1] and b[1] < p[5][1] and c[1] < a[1]:
                has_correction = True
        elif direction == 'bearish' and types[6] == 'H' and types[7] == 'L' and types[8] == 'H':
            if a[1] > p[5][1] and b[1] < a[1] and b[1] > p[5][1] and c[1] > a[1]:
                has_correction = True
        if has_correction:
            for i, lbl in zip((6, 7, 8), ('A', 'B', 'C')):
                waves.append({'label': lbl, 'index': int(seq[i][0]), 'price': float(seq[i][1])})

    return {
        'direction': direction,
        'waves': waves,
        'wave2_retrace': float(wave2_retrace),
        'wave4_retrace': float(wave4_retrace),
        'wave3_extension': float(wave3 / wave1),
        'wave5_vs_wave1': float(wave5 / wave1),
        'has_correction': has_correction,
    }


def find_impulse_waves(pivots: list[tuple[int, float, str]]) -> dict[str, Any] | None:
    """Search recent pivots for a valid impulse pattern.

    Tries longer (9 pivots, with ABC) before shorter (6, impulse only),
    and slides backward a few positions to tolerate an unfinished new wave
    forming on the right edge.
    """
    n = len(pivots)
    if n < 6:
        return None

    for end_offset in range(0, min(n - 5, 4)):
        end = n - end_offset
        for length in (9, 6):
            if end >= length:
                result = _validate_pattern(pivots[end - length:end])
                if result:
                    return result
    return None


def project_targets(wave_data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Project simple Fibonacci targets for the next probable move."""
    if not wave_data:
        return None

    waves = wave_data['waves']
    direction = wave_data['direction']
    targets: dict[str, Any] = {}

    if len(waves) == 6:
        wave5_price = waves[5]['price']
        wave0_price = waves[0]['price']
        impulse_range = abs(wave5_price - wave0_price)
        sign = -1 if direction == 'bullish' else 1
        targets['phase'] = 'expecting_correction'
        targets['next_label'] = 'A'
        targets['levels'] = [
            {'name': 'A 38.2% 되돌림', 'price': float(wave5_price + sign * impulse_range * 0.382)},
            {'name': 'A 50.0% 되돌림', 'price': float(wave5_price + sign * impulse_range * 0.500)},
            {'name': 'A 61.8% 되돌림', 'price': float(wave5_price + sign * impulse_range * 0.618)},
        ]
    elif len(waves) == 9:
        c_price = waves[8]['price']
        a_price = waves[6]['price']
        leg = abs(a_price - c_price)
        sign = 1 if direction == 'bullish' else -1
        targets['phase'] = 'expecting_new_impulse'
        targets['next_label'] = '1'
        targets['levels'] = [
            {'name': '신규 1파 38.2% 확장', 'price': float(c_price + sign * leg * 0.382)},
            {'name': '신규 1파 61.8% 확장', 'price': float(c_price + sign * leg * 0.618)},
            {'name': '신규 1파 100% 확장', 'price': float(c_price + sign * leg * 1.000)},
        ]
    else:
        return None
    return targets


def generate_analysis(wave_data: dict[str, Any] | None) -> dict[str, Any]:
    """Build a human-readable analysis summary in Korean."""
    if not wave_data:
        return {
            'summary': '명확한 엘리엇 파동 패턴을 감지하지 못했습니다. ZigZag 민감도를 조정해 보세요.',
            'details': [],
        }

    direction = wave_data['direction']
    waves = wave_data['waves']
    n = len(waves)
    direction_kr = '상승' if direction == 'bullish' else '하락'
    opposite_kr = '하락' if direction == 'bullish' else '상승'

    details = [
        f'추세 방향: {direction_kr}',
        f"2파 되돌림: {wave_data['wave2_retrace']*100:.1f}% (전형값 50~61.8%)",
        f"3파 / 1파 비율: {wave_data['wave3_extension']*100:.1f}% (161.8% 이상이면 강한 임펄스)",
        f"4파 되돌림: {wave_data['wave4_retrace']*100:.1f}% (전형값 23.6~38.2%)",
        f"5파 / 1파 비율: {wave_data['wave5_vs_wave1']*100:.1f}%",
    ]

    if n == 6:
        summary = f'{direction_kr} 임펄스 5파 완성으로 추정됩니다. {opposite_kr} 방향 ABC 조정 진입이 예상됩니다.'
    elif n == 9:
        summary = f'{direction_kr} 5파 + ABC 조정 사이클이 완성된 것으로 보입니다. 신규 {direction_kr} 임펄스 시작 가능성이 있습니다.'
    else:
        summary = f'{direction_kr} 추세 진행 중'

    return {'summary': summary, 'details': details}


def analyze(df: pd.DataFrame, threshold: float = 0.05) -> dict[str, Any]:
    """Top-level entry point used by the Flask route."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    if 'Date' in df.columns:
        date_col = 'Date'
    elif 'Datetime' in df.columns:
        date_col = 'Datetime'
    else:
        df = df.reset_index()
        date_col = 'Date' if 'Date' in df.columns else 'Datetime'

    try:
        dates = pd.to_datetime(df[date_col]).dt.strftime('%Y-%m-%d').tolist()
    except Exception:
        dates = [str(x) for x in df[date_col].tolist()]

    highs = df['High'].to_numpy(dtype=float)
    lows = df['Low'].to_numpy(dtype=float)
    closes = df['Close'].to_numpy(dtype=float)
    opens = df['Open'].to_numpy(dtype=float)
    volumes = df['Volume'].fillna(0).to_numpy(dtype=float) if 'Volume' in df.columns else np.zeros(len(df))

    pivots = zigzag(highs, lows, deviation=threshold)
    wave_data = find_impulse_waves(pivots)
    targets = project_targets(wave_data)
    analysis = generate_analysis(wave_data)

    pivot_data = [
        {'index': int(p[0]), 'date': dates[p[0]], 'price': float(p[1]), 'type': p[2]}
        for p in pivots
    ]

    return {
        'dates': dates,
        'open': opens.tolist(),
        'high': highs.tolist(),
        'low': lows.tolist(),
        'close': closes.tolist(),
        'volume': volumes.tolist(),
        'pivots': pivot_data,
        'wave_data': wave_data,
        'targets': targets,
        'analysis': analysis,
        'current_price': float(closes[-1]) if len(closes) else None,
    }
