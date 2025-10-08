async function api(path, opts) {
    const res = await fetch(path, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts || {}));
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

function gatherSettings() {
    const payout = parseFloat(document.getElementById('payout').value || '84');
    const timeframe = parseInt(document.getElementById('timeframe').value || '60', 10);
    const tradePercent = parseFloat(document.getElementById('tradePercent').value || '2');
    const account = document.querySelector('input[name="account"]:checked').value;
    const maxConcurrent = parseInt(document.getElementById('maxConcurrent').value || '1', 10);
    // Daily limits are not part of the new UI, so they are removed from here.
    return { payout, timeframe, trade_percent: tradePercent, account, max_concurrent: maxConcurrent, run_minutes: 0, payout_refresh_min: 10 };
}

async function refreshStatus() {
    try {
        const s = await api('/api/status');
        const toggle = document.getElementById('toggle');
        if (s.running) {
            toggle.classList.remove('stop');
            toggle.classList.add('run');
            toggle.textContent = 'Stop Bot';
        } else {
            toggle.classList.remove('run');
            toggle.classList.add('stop');
            toggle.textContent = 'Start Bot';
        }
    } catch (e) { console.error(e); }
}

async function refreshTradeLogs() {
    try {
        const logs = await api('/api/trade_logs');
        const activeBody = document.querySelector('#activeTrades tbody');
        const historyBody = document.querySelector('#tradeHistory tbody');
        activeBody.innerHTML = '';
        historyBody.innerHTML = '';

        logs.active_trades.forEach(t => {
            const expiresIn = Math.round((new Date(t.timestamp).getTime() / 1000 + t.duration) - (Date.now() / 1000));
            activeBody.innerHTML += `<tr>
                <td>${t.id}</td>
                <td>${t.asset}</td>
                <td>${t.amount}</td>
                <td>${t.direction}</td>
                <td>${new Date(t.timestamp).toLocaleTimeString()}</td>
                <td>${expiresIn > 0 ? expiresIn + 's' : 'Expired'}</td>
                <td>${t.live_pnl}</td>
            </tr>`;
        });

        logs.trade_history.forEach(t => {
            historyBody.innerHTML += `<tr>
                <td>${new Date(t.timestamp).toLocaleString()}</td>
                <td>${t.asset}</td>
                <td>${t.amount}</td>
                <td>${t.direction}</td>
                <td>${t.pnl}</td>
                <td>${t.balance_after}</td>
            </tr>`;
        });
    } catch (e) {
        console.error("Failed to refresh trade logs:", e);
    }
}


async function start() {
    try {
        await api('/api/start', { method: 'POST', body: JSON.stringify(gatherSettings()) });
        await refreshStatus();
    } catch (e) { alert('Start failed: ' + e.message); }
}

async function stop() {
    try {
        await api('/api/stop', { method: 'POST' });
        await refreshStatus();
    } catch (e) { alert('Stop failed: ' + e.message); }
}

document.getElementById('toggle').addEventListener('click', async () => {
    const isRunning = document.getElementById('toggle').classList.contains('run');
    if (isRunning) {
        await stop();
    } else {
        await start();
    }
});

async function init() {
    try {
        const data = await api('/api/initial_data');
        document.getElementById('practiceBalance').textContent = `$${data.balances.practice.toFixed(2)}`;
        document.getElementById('realBalance').textContent = `$${data.balances.real.toFixed(2)}`;
        const assetsList = document.getElementById('assetsList');
        assetsList.innerHTML = data.assets.join(', ');
    } catch (e) {
        console.error("Failed to load initial data", e);
        alert("Failed to load initial data: " + e.message);
    }
    await refreshStatus();
    await refreshTradeLogs();
}

init();
setInterval(refreshStatus, 2000);
setInterval(refreshTradeLogs, 5000);
