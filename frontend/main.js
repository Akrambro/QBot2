async function api(path, opts){
  const res = await fetch(path, Object.assign({headers:{'Content-Type':'application/json'}}, opts||{}));
  if(!res.ok) throw new Error(await res.text());
  return res.json();
}

function gatherSettings(){
  const payout = parseFloat(document.getElementById('payout').value||'84');
  const assets = document.getElementById('assets').value||'';
  const timeframe = parseInt(document.getElementById('timeframe').value||'60',10);
  const tradePercent = parseFloat(document.getElementById('tradePercent').value||'2');
  const account = document.querySelector('input[name="account"]:checked').value;
  const maxConcurrent = parseInt(document.getElementById('maxConcurrent').value||'1',10);
  const daily_profit_limit = parseFloat(document.getElementById('profitLimit').value||'0');
  const daily_profit_is_percent = document.getElementById('profitIsPercent').value === '1';
  const daily_loss_limit = parseFloat(document.getElementById('lossLimit').value||'0');
  const daily_loss_is_percent = document.getElementById('lossIsPercent').value === '1';
  return {payout, assets, timeframe, trade_percent: tradePercent, account, max_concurrent: maxConcurrent, run_minutes:0, payout_refresh_min:10, daily_profit_limit, daily_profit_is_percent, daily_loss_limit, daily_loss_is_percent};
}

async function refreshStatus(){
  try{
    const s = await api('/api/status');
    document.getElementById('running').textContent = s.running ? 'Yes' : 'No';
    // Placeholder counts
    document.getElementById('dailyTrades').textContent = s.running ? '—' : '0';
    document.getElementById('ongoingList').innerHTML = '';
    const toggle = document.getElementById('toggle');
    if(s.running){ toggle.classList.remove('stop'); toggle.classList.add('run'); toggle.textContent = 'Running'; }
    else { toggle.classList.remove('run'); toggle.classList.add('stop'); toggle.textContent = 'Stopped'; }
  }catch(e){ console.error(e); }
}

async function start(){
  try{
    await api('/api/start', {method:'POST', body: JSON.stringify(gatherSettings())});
    await refreshStatus();
  }catch(e){ alert('Start failed: ' + e.message); }
}

async function stop(){
  try{
    await api('/api/stop', {method:'POST'});
    await refreshStatus();
  }catch(e){ alert('Stop failed: ' + e.message); }
}

document.getElementById('toggle').addEventListener('click', async ()=>{
  const running = (document.getElementById('running').textContent === 'Yes');
  if(running) await stop(); else await start();
});

refreshStatus();
setInterval(refreshStatus, 2000);


