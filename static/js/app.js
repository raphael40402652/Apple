const form = document.getElementById('analyzeForm');
const btn = document.getElementById('analyzeBtn');
const statusEl = document.getElementById('status');

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    await runAnalysis();
});

async function runAnalysis() {
    const ticker = document.getElementById('ticker').value.trim();
    const period = document.getElementById('period').value;
    const interval = document.getElementById('interval').value;
    const threshold = parseFloat(document.getElementById('threshold').value);

    if (!ticker) {
        showError('티커를 입력하세요.');
        return;
    }

    btn.disabled = true;
    statusEl.className = 'status loading';
    statusEl.textContent = `${ticker} 데이터 수집 및 엘리엇 파동 분석 중...`;

    try {
        const res = await fetch('/api/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ticker, period, interval, threshold}),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '분석 실패');

        statusEl.style.display = 'none';
        renderChart(data);
        renderAnalysis(data);
    } catch (err) {
        showError(err.message);
    } finally {
        btn.disabled = false;
    }
}

function showError(msg) {
    statusEl.className = 'status error';
    statusEl.textContent = msg;
}

function renderChart(data) {
    const candle = {
        x: data.dates,
        open: data.open,
        high: data.high,
        low: data.low,
        close: data.close,
        type: 'candlestick',
        name: data.ticker,
        increasing: {line: {color: '#3fb950'}, fillcolor: '#3fb950'},
        decreasing: {line: {color: '#f85149'}, fillcolor: '#f85149'},
        showlegend: false,
    };

    const traces = [candle];

    if (data.pivots && data.pivots.length > 0) {
        traces.push({
            x: data.pivots.map(p => p.date),
            y: data.pivots.map(p => p.price),
            mode: 'lines+markers',
            name: 'ZigZag',
            line: {color: '#79c0ff', width: 1.5, dash: 'dot'},
            marker: {size: 7, color: '#79c0ff'},
            hoverinfo: 'skip',
            showlegend: false,
        });
    }

    const annotations = [];
    if (data.wave_data && data.wave_data.waves) {
        const waves = data.wave_data.waves;
        const isBull = data.wave_data.direction === 'bullish';
        for (let i = 0; i < waves.length; i++) {
            const w = waves[i];
            if (w.label === '0') continue;
            const isHigh = (i % 2 === 1) === isBull;
            annotations.push({
                x: data.dates[w.index],
                y: w.price,
                text: `<b>${w.label}</b>`,
                showarrow: true,
                arrowhead: 2,
                arrowsize: 1.2,
                arrowwidth: 1.5,
                arrowcolor: '#f0b400',
                ax: 0,
                ay: isHigh ? -32 : 32,
                font: {color: '#f0b400', size: 14},
                bgcolor: 'rgba(13, 17, 23, 0.92)',
                bordercolor: '#f0b400',
                borderwidth: 1,
                borderpad: 5,
            });
        }
    }

    if (data.targets && data.targets.levels) {
        for (const lvl of data.targets.levels) {
            annotations.push({
                xref: 'paper', x: 1.0, xanchor: 'right',
                y: lvl.price,
                text: `${lvl.name}: ${formatPrice(lvl.price)}`,
                showarrow: false,
                font: {color: '#a371f7', size: 11},
                bgcolor: 'rgba(13, 17, 23, 0.85)',
                bordercolor: '#a371f7',
                borderwidth: 1,
                borderpad: 3,
            });
        }
    }

    const shapes = (data.targets && data.targets.levels) ? data.targets.levels.map(lvl => ({
        type: 'line',
        xref: 'paper', x0: 0, x1: 1,
        y0: lvl.price, y1: lvl.price,
        line: {color: 'rgba(163, 113, 247, 0.45)', width: 1, dash: 'dash'},
    })) : [];

    const title = `${data.ticker} (${data.period}, ${data.interval}, ZZ ${(data.threshold * 100).toFixed(1)}%)`;

    const layout = {
        title: {text: title, font: {color: '#e6edf3', size: 15}},
        paper_bgcolor: '#161b22',
        plot_bgcolor: '#0d1117',
        font: {color: '#c9d1d9', family: 'inherit'},
        xaxis: {
            gridcolor: '#21262d',
            rangeslider: {visible: false},
            type: 'category',
            tickangle: -30,
            nticks: 12,
        },
        yaxis: {gridcolor: '#21262d', title: '가격'},
        margin: {l: 64, r: 180, t: 50, b: 60},
        height: 600,
        showlegend: false,
        annotations,
        shapes,
        hovermode: 'x unified',
    };

    Plotly.newPlot('chart', traces, layout, {responsive: true, displayModeBar: false});
}

function renderAnalysis(data) {
    const summary = document.getElementById('summary');
    const details = document.getElementById('details');
    const targets = document.getElementById('targets');

    summary.textContent = data.analysis.summary;
    summary.className = data.wave_data
        ? (data.wave_data.direction === 'bullish' ? 'bullish' : 'bearish')
        : '';

    details.innerHTML = '';
    if (data.analysis.details && data.analysis.details.length > 0) {
        for (const d of data.analysis.details) {
            const li = document.createElement('li');
            li.textContent = d;
            details.appendChild(li);
        }
    } else {
        details.innerHTML = '<li>표시할 내용이 없습니다.</li>';
    }

    targets.innerHTML = '';
    if (data.targets && data.targets.levels) {
        for (const lvl of data.targets.levels) {
            const li = document.createElement('li');
            li.innerHTML = `${lvl.name}: <b>${formatPrice(lvl.price)}</b>`;
            targets.appendChild(li);
        }
    } else {
        targets.innerHTML = '<li>유효한 임펄스 패턴이 감지되지 않아 목표가를 산출할 수 없습니다.</li>';
    }
    if (data.current_price != null) {
        const li = document.createElement('li');
        li.style.marginTop = '8px';
        li.style.color = '#58a6ff';
        li.innerHTML = `현재가: <b>${formatPrice(data.current_price)}</b>`;
        targets.appendChild(li);
    }
}

function formatPrice(p) {
    if (p == null || isNaN(p)) return '-';
    if (Math.abs(p) >= 100) return p.toFixed(2);
    if (Math.abs(p) >= 1) return p.toFixed(3);
    return p.toFixed(5);
}

window.addEventListener('load', () => {
    runAnalysis();
});
