async function api(path, opts = {}) {
    const defaultHeaders = { 'Content-Type': 'application/json' };
    const headers = Object.assign(defaultHeaders, opts.headers || {});
    const config = Object.assign({ headers }, opts);
    
    const res = await fetch(path, config);
    if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText || `HTTP ${res.status}`);
    }
    return res.json();
}

function gatherSettings() {
    const payout = parseFloat(document.getElementById('payout').value || '84');
    const tradePercent = parseFloat(document.getElementById('tradePercent').value || '2');
    const account = document.querySelector('input[name="account"]:checked').value;
    const maxConcurrent = parseInt(document.getElementById('maxConcurrent').value || '1', 10);
    const daily_profit_limit = parseFloat(document.getElementById('profitLimit').value || '0');
    const daily_profit_is_percent = document.getElementById('profitIsPercent').value === '1';
    const daily_loss_limit = parseFloat(document.getElementById('lossLimit').value || '0');
    const daily_loss_is_percent = document.getElementById('lossIsPercent').value === '1';
    
    // Strategy configurations
    const breakout_strategy = {
        enabled: document.getElementById('breakoutEnabled').checked,
        analysis_timeframe: parseInt(document.getElementById('breakoutAnalysisTf').value || '60', 10),
        trade_timeframe: parseInt(document.getElementById('breakoutTradeTf').value || '60', 10)
    };
    
    const engulfing_strategy = {
        enabled: document.getElementById('engulfingEnabled').checked,
        analysis_timeframe: parseInt(document.getElementById('engulfingAnalysisTf').value || '60', 10),
        trade_timeframe: parseInt(document.getElementById('engulfingTradeTf').value || '60', 10)
    };
    
    const bollinger_strategy = {
        enabled: document.getElementById('bollingerEnabled').checked,
        analysis_timeframe: parseInt(document.getElementById('bollingerAnalysisTf').value || '60', 10),
        trade_timeframe: parseInt(document.getElementById('bollingerTradeTf').value || '60', 10)
    };
    
    const bollinger_period = parseInt(document.getElementById('bollingerPeriod').value || '14', 10);
    const bollinger_deviation = parseFloat(document.getElementById('bollingerDeviation').value || '1.0');
    
    return { 
        payout, 
        trade_percent: tradePercent, 
        account, 
        max_concurrent: maxConcurrent, 
        run_minutes: 0, 
        payout_refresh_min: 10, 
        daily_profit_limit, 
        daily_profit_is_percent, 
        daily_loss_limit, 
        daily_loss_is_percent,
        breakout_strategy,
        engulfing_strategy,
        bollinger_strategy,
        bollinger_period,
        bollinger_deviation
    };
}

async function refreshStatus() {
    try {
        const s = await api('/api/status');
        const toggle = document.getElementById('toggle');
        if (s.running) {
            toggle.classList.remove('stop');
            toggle.classList.add('run');
            toggle.textContent = 'Stop Bot';
            
            // Update current balance if available
            if (s.current_balance && s.current_balance > 0) {
                const account = s.settings?.account || 'PRACTICE';
                if (account === 'PRACTICE') {
                    document.getElementById('practiceBalance').textContent = `$${s.current_balance.toFixed(2)}`;
                } else {
                    document.getElementById('realBalance').textContent = `$${s.current_balance.toFixed(2)}`;
                }
            }
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
            const tradeTime = new Date(t.timestamp).getTime() / 1000;
            const currentTime = Date.now() / 1000;
            const expiresIn = Math.round(tradeTime + t.duration - currentTime);
            
            // Only show if not expired (with 5 second buffer)
            if (expiresIn > -5) {
                const expiryDisplay = expiresIn > 0 ? `${expiresIn}s` : 'Closing...';
                const rowClass = expiresIn <= 5 ? 'expiring-soon' : '';
                
                activeBody.innerHTML += `<tr class="${rowClass}">
                    <td>${t.id}</td>
                    <td>${t.strategy || 'N/A'}</td>
                    <td>${t.asset}</td>
                    <td>${t.amount}</td>
                    <td>${t.direction}</td>
                    <td>${new Date(t.timestamp).toLocaleTimeString()}</td>
                    <td>${expiryDisplay}</td>
                    <td>${t.live_pnl}</td>
                </tr>`;
            }
        });
        
        // Show message if no active trades
        if (logs.active_trades.length === 0 || activeBody.innerHTML === '') {
            activeBody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: #888;">No active trades</td></tr>';
        }

        logs.trade_history.forEach(t => {
            const pnl = parseFloat(t.pnl) || 0;
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${new Date(t.timestamp).toLocaleString()}</td>
                <td>${t.strategy || 'N/A'}</td>
                <td>${t.asset}</td>
                <td>${t.amount}</td>
                <td>${t.direction}</td>
                <td class="pnl-cell">${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}</td>
                <td>${t.balance_after}</td>
            `;
            const pnlCell = row.querySelector('.pnl-cell');
            pnlCell.style.color = pnl >= 0 ? '#22c55e' : '#ef4444';
            pnlCell.style.fontWeight = 'bold';
            historyBody.appendChild(row);
        });
        
        // Update progress tubes and daily P&L display
        const dailyPnl = logs.daily_pnl || 0;
        updateProgressTubes(dailyPnl);
        
        // Update daily P&L display with null check
        const dailyPnlElement = document.getElementById('dailyPnl');
        if (dailyPnlElement) {
            dailyPnlElement.textContent = `$${dailyPnl.toFixed(2)}`;
            // Remove all color classes first
            dailyPnlElement.classList.remove('daily-pnl-neutral', 'daily-pnl-positive', 'daily-pnl-negative');
            // Add appropriate class based on P&L
            if (dailyPnl > 0) {
                dailyPnlElement.classList.add('daily-pnl-positive');
            } else if (dailyPnl < 0) {
                dailyPnlElement.classList.add('daily-pnl-negative');
            } else {
                dailyPnlElement.classList.add('daily-pnl-neutral');
            }
        }
    } catch (e) {
        console.error("Failed to refresh trade logs:", e);
    }
}

function updateProgressTubes(dailyPnl = 0) {
    const profitLimit = parseFloat(document.getElementById('profitLimit').value || '0');
    const lossLimit = parseFloat(document.getElementById('lossLimit').value || '0');
    const profitIsPercent = document.getElementById('profitIsPercent').value === '1';
    const lossIsPercent = document.getElementById('lossIsPercent').value === '1';
    
    // Get current balance from the appropriate account
    const practiceBalance = parseFloat(document.getElementById('practiceBalance').textContent.replace('$', '')) || 1000;
    const realBalance = parseFloat(document.getElementById('realBalance').textContent.replace('$', '')) || 1000;
    const currentBalance = document.querySelector('input[name="account"]:checked')?.value === 'REAL' ? realBalance : practiceBalance;
    
    // Calculate actual limits based on current balance
    const actualProfitLimit = profitIsPercent ? (currentBalance * profitLimit / 100) : profitLimit;
    const actualLossLimit = lossIsPercent ? (currentBalance * lossLimit / 100) : lossLimit;
    
    // Update profit tube
    if (actualProfitLimit > 0) {
        const profitProgress = Math.min(Math.max(dailyPnl / actualProfitLimit * 100, 0), 100);
        document.getElementById('profitTube').style.width = profitProgress + '%';
        document.getElementById('profitLabel').textContent = `$${dailyPnl.toFixed(2)} / $${actualProfitLimit.toFixed(2)}`;
    } else {
        document.getElementById('profitTube').style.width = '0%';
        document.getElementById('profitLabel').textContent = `$${dailyPnl.toFixed(2)}`;
    }
    
    // Update loss tube
    if (actualLossLimit > 0) {
        const lossProgress = Math.min(Math.max(Math.abs(Math.min(dailyPnl, 0)) / actualLossLimit * 100, 0), 100);
        document.getElementById('lossTube').style.width = lossProgress + '%';
        document.getElementById('lossLabel').textContent = `$${Math.abs(Math.min(dailyPnl, 0)).toFixed(2)} / $${actualLossLimit.toFixed(2)}`;
    } else {
        document.getElementById('lossTube').style.width = '0%';
        document.getElementById('lossLabel').textContent = `$${Math.abs(Math.min(dailyPnl, 0)).toFixed(2)}`;
    }
}


async function start() {
    try {
        const settings = gatherSettings();
        console.log('Sending settings:', settings);
        await api('/api/start', { 
            method: 'POST', 
            body: JSON.stringify(settings),
            headers: { 'Content-Type': 'application/json' }
        });
        await refreshStatus();
    } catch (e) { 
        console.error('Start error:', e);
        alert('Start failed: ' + e.message); 
    }
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
        if (data.error) {
            console.warn('Connection issue:', data.error);
            assetsList.innerHTML = `<span style="color: #ef4444;">Connection failed: ${data.error}</span>`;
        } else if (data.assets && data.assets.length > 0) {
            assetsList.innerHTML = `<span style="color: #22c55e;">${data.assets.length} assets:</span> ${data.assets.join(', ')}`;
            console.log('Loaded assets:', data.assets);
        } else {
            assetsList.innerHTML = '<span style="color: #f59e0b;">No tradable assets found - check payout threshold</span>';
        }
        
        const profileDetails = document.getElementById('profileDetails');
        if (data.email) {
            profileDetails.textContent = data.email;
        }

    } catch (e) {
        console.error("Failed to load initial data", e);
        document.getElementById('assetsList').innerHTML = `<span style="color: #ef4444;">Failed to load assets: ${e.message}</span>`;
    }
    await refreshStatus();
    await refreshTradeLogs();
}

async function refreshAssets() {
    const assetsList = document.getElementById('assetsList');
    const payout = parseFloat(document.getElementById('payout').value || '84');
    
    try {
        assetsList.innerHTML = 'Refreshing assets...';
        const data = await api(`/api/refresh_assets?payout=${payout}`);
        
        if (data.assets && data.assets.length > 0) {
            assetsList.innerHTML = `<span style="color: #22c55e;">${data.assets.length} assets:</span> ${data.assets.join(', ')}`;
            console.log('Refreshed assets:', data.assets);
        } else {
            assetsList.innerHTML = '<span style="color: #f59e0b;">No tradable assets found</span>';
        }
    } catch (e) {
        console.error('Failed to refresh assets:', e);
        assetsList.innerHTML = `<span style="color: #ef4444;">Refresh failed: ${e.message}</span>`;
    }
}

document.getElementById('refreshAssets')?.addEventListener('click', refreshAssets);
document.getElementById('payout')?.addEventListener('change', refreshAssets);

// Update tubes when limits change
document.getElementById('profitLimit')?.addEventListener('input', () => {
    const currentPnl = parseFloat(document.getElementById('dailyPnl')?.textContent?.replace('$', '') || '0');
    updateProgressTubes(currentPnl);
});
document.getElementById('lossLimit')?.addEventListener('input', () => {
    const currentPnl = parseFloat(document.getElementById('dailyPnl')?.textContent?.replace('$', '') || '0');
    updateProgressTubes(currentPnl);
});
document.getElementById('profitIsPercent')?.addEventListener('change', () => {
    const currentPnl = parseFloat(document.getElementById('dailyPnl')?.textContent?.replace('$', '') || '0');
    updateProgressTubes(currentPnl);
});
document.getElementById('lossIsPercent')?.addEventListener('change', () => {
    const currentPnl = parseFloat(document.getElementById('dailyPnl')?.textContent?.replace('$', '') || '0');
    updateProgressTubes(currentPnl);
});

init();
setInterval(refreshStatus, 2000);  // Update every 2 seconds for balance
setInterval(refreshTradeLogs, 2000);  // Update every 2 seconds for active/closed trades
