(() => {
  const statusSummary = document.getElementById('statusSummary');
  const logList = document.getElementById('logList');

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
      const title = document.createElement('div');
      title.className = 'log-title';
      title.textContent = `${log.file} (${new Date(log.mtime).toLocaleString('ja-JP')})`;
      const pre = document.createElement('pre');
      pre.textContent = log.tail || '';
      pre.style.maxHeight = '220px';
      pre.style.overflow = 'auto';
      card.appendChild(title);
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
