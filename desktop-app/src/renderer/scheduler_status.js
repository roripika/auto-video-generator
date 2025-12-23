(() => {
  const statusSummary = document.getElementById('statusSummary');
  const logList = document.getElementById('logList');
  const regenerateStatus = document.getElementById('regenerateStatus');

  const getScheduler = () => {
    return (
      (window.scheduler && typeof window.scheduler.statusData === 'function' ? window.scheduler : null) ||
      (window.schedulerApi && typeof window.schedulerApi.statusData === 'function' ? window.schedulerApi : null) ||
      (window.schedulerBridge && typeof window.schedulerBridge.statusData === 'function' ? window.schedulerBridge : null) ||
      (window.api && window.api.scheduler && typeof window.api.scheduler.statusData === 'function'
        ? window.api.scheduler
        : null)
    );
  };

  async function regenerateVideo(logPath) {
    const client = getScheduler();
    if (!client || typeof client.regenerateFromLog !== 'function') {
      regenerateStatus.textContent = 'エラー: 再生成APIが利用できません';
      regenerateStatus.style.display = 'block';
      return;
    }
    try {
      regenerateStatus.textContent = '再生成中...';
      regenerateStatus.style.display = 'block';
      regenerateStatus.style.color = '#e0e0e0';
      const result = await client.regenerateFromLog(logPath);
      if (result.success) {
        regenerateStatus.textContent = `✅ 再生成完了: ${result.message || ''}`;
        regenerateStatus.style.color = '#4ade80';
      } else {
        regenerateStatus.textContent = `❌ 再生成失敗: ${result.message || 'Unknown error'}`;
        regenerateStatus.style.color = '#f87171';
      }
    } catch (err) {
      regenerateStatus.textContent = `❌ エラー: ${err.message || String(err)}`;
      regenerateStatus.style.color = '#f87171';
    }
  }

  function renderStatus(data) {
    if (!data) return;
    const running = data.running_tasks || 0;
    const uploading = data.upload_running ? '実行中' : '停止中';
    const maxC = data.max_concurrent || 1;
    const tasks = Array.isArray(data.tasks) ? data.tasks : [];
    statusSummary.innerHTML = `
      <div>実行中タスク: ${running}</div>
      <div>アップロード: ${uploading}</div>
      <div>最大同時実行数: ${maxC}</div>
      <div>登録タスク数: ${tasks.length}</div>
    `;

    logList.innerHTML = '';
    const logs = Array.isArray(data.recent_logs) ? data.recent_logs : [];
    logs.forEach((log) => {
      const card = document.createElement('div');
      card.className = 'log-card';
      const titleRow = document.createElement('div');
      titleRow.style.display = 'flex';
      titleRow.style.justifyContent = 'space-between';
      titleRow.style.alignItems = 'center';
      titleRow.style.marginBottom = '8px';
      const title = document.createElement('div');
      title.className = 'log-title';
      title.textContent = `${log.file} (${new Date(log.mtime).toLocaleString('ja-JP')})`;
      titleRow.appendChild(title);
      const regenerateBtn = document.createElement('button');
      regenerateBtn.textContent = '再生成';
      regenerateBtn.style.padding = '6px 12px';
      regenerateBtn.style.fontSize = '0.85rem';
      regenerateBtn.style.cursor = 'pointer';
      regenerateBtn.addEventListener('click', () => regenerateVideo(log.path));
      titleRow.appendChild(regenerateBtn);
      const pre = document.createElement('pre');
      pre.textContent = log.tail || '';
      pre.style.maxHeight = '220px';
      pre.style.overflow = 'auto';
      card.appendChild(titleRow);
      card.appendChild(pre);
      logList.appendChild(card);
    });
  }

  async function refresh() {
    try {
      const client = getScheduler();
      if (!client) return;
      const data = await client.statusData();
      renderStatus(data);
    } catch (err) {
      console.error(err);
    }
  }

  refresh();
  setInterval(refresh, 5000);
})();
