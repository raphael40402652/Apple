"""Flask backend for the Elliott Wave stock analyzer."""

from __future__ import annotations

import logging

import yfinance as yf
from flask import Flask, jsonify, render_template, request

from elliott_wave import analyze

app = Flask(__name__)
log = logging.getLogger(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    payload = request.get_json(silent=True) or {}
    ticker = (payload.get('ticker') or '').strip().upper()
    period = payload.get('period') or '1y'
    interval = payload.get('interval') or '1d'
    try:
        threshold_pct = float(payload.get('threshold', 5))
    except (TypeError, ValueError):
        return jsonify({'error': 'ZigZag 민감도는 숫자여야 합니다.'}), 400
    threshold = max(0.005, min(threshold_pct / 100.0, 0.5))

    if not ticker:
        return jsonify({'error': '티커를 입력하세요.'}), 400

    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )
    except Exception as e:
        log.exception('yfinance download failed')
        return jsonify({'error': f'데이터 수집 실패: {e}'}), 502

    if df is None or df.empty:
        return jsonify({'error': f"'{ticker}'의 데이터를 찾을 수 없습니다. 티커/기간/간격 조합을 확인하세요."}), 404

    df = df.reset_index()
    result = analyze(df, threshold=threshold)
    result['ticker'] = ticker
    result['period'] = period
    result['interval'] = interval
    result['threshold'] = threshold
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
