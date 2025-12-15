(() => {
  const taskList = document.getElementById('taskList');
  const taskAddBtn = document.getElementById('taskAddBtn');
  const taskSaveBtn = document.getElementById('taskSaveBtn');
  const taskStatus = document.getElementById('taskStatus');

  let tasks = [];
  const getScheduler = () => {
    const candidate = window.scheduler;
    if (candidate && typeof candidate.list === 'function') {
      return candidate;
    }
    return (
      window.schedulerApi ||
      window.schedulerBridge ||
      (window.api && window.api.scheduler)
    );
  };

  function uuid() {
    return 't-' + Math.random().toString(36).slice(2, 8);
  }

  function renderTasks() {
    taskList.innerHTML = '';
    tasks.forEach((task) => {
      const li = document.createElement('li');
      li.className = 'task-item';
      const title = document.createElement('div');
      title.className = 'task-title';
      title.textContent = task.name || '無題タスク';
      const row = document.createElement('div');
      row.className = 'task-row';

      const wrapField = (label, node) => {
        const f = document.createElement('label');
        f.className = 'task-field';
        const cap = document.createElement('span');
        cap.className = 'task-label';
        cap.textContent = label;
        f.appendChild(cap);
        f.appendChild(node);
        return f;
      };

      const nameInput = document.createElement('input');
      nameInput.type = 'text';
      nameInput.value = task.name || '';
      nameInput.placeholder = 'タスク名';
      nameInput.addEventListener('input', (e) => {
        task.name = e.target.value;
      });

      const maxKw = document.createElement('input');
      maxKw.type = 'number';
      maxKw.min = '1';
      maxKw.max = '50';
      maxKw.value = task.max_keywords || 10;
      maxKw.addEventListener('input', (e) => {
        task.max_keywords = Number(e.target.value) || 10;
      });

      const interval = document.createElement('input');
      interval.type = 'number';
      interval.min = '1';
      interval.value = task.interval_minutes || 1440;
      interval.addEventListener('input', (e) => {
        task.interval_minutes = Number(e.target.value) || 1440;
      });

      const startOffset = document.createElement('input');
      startOffset.type = 'number';
      startOffset.min = '0';
      startOffset.placeholder = '例: 60';
      startOffset.value =
        typeof task.start_offset_minutes === 'number' ? String(task.start_offset_minutes) : '';
      startOffset.addEventListener('input', (e) => {
        const val = e.target.value;
        task.start_offset_minutes = val === '' ? undefined : Math.max(0, Number(val) || 0);
      });

      const uploadToggle = document.createElement('input');
      uploadToggle.type = 'checkbox';
      uploadToggle.checked = task.auto_upload !== false;
      uploadToggle.addEventListener('change', (e) => {
        task.auto_upload = e.target.checked;
      });

      const clearCacheToggle = document.createElement('input');
      clearCacheToggle.type = 'checkbox';
      clearCacheToggle.checked = task.clear_cache !== false;
      clearCacheToggle.addEventListener('change', (e) => {
        task.clear_cache = e.target.checked;
      });

      const categorySelect = document.createElement('select');
      const categories = [
        '未指定',
        'ライフハック',
        '時事ネタ',
        '統計話題',
        '科学トリビア',
        '健康常識（断定NG）',
        '歴史の豆知識',
        '宇宙・天文',
        '心理学・行動科学',
        'テクノロジー動向',
        'カルチャー・エンタメ',
      ];
      categories.forEach((cat) => {
        const opt = document.createElement('option');
        opt.value = cat === '未指定' ? '' : cat;
        opt.textContent = cat;
        if ((task.category || '') === opt.value) opt.selected = true;
        categorySelect.appendChild(opt);
      });
      categorySelect.addEventListener('change', (e) => {
        task.category = e.target.value || null;
      });

      const enabledToggle = document.createElement('input');
      enabledToggle.type = 'checkbox';
      enabledToggle.checked = task.enabled !== false;
      enabledToggle.addEventListener('change', (e) => {
        task.enabled = e.target.checked;
      });

      const runBtn = document.createElement('button');
      runBtn.textContent = '今すぐ実行';
      runBtn.addEventListener('click', async () => {
        runBtn.disabled = true;
        taskStatus.textContent = '実行中...';
        try {
          const client = getScheduler();
          if (!client?.runNow) throw new Error('scheduler API not available');
          await client.runNow(task.id);
          taskStatus.textContent = '実行完了（ログは logs/scheduler/ を確認）';
          await loadTasks();
        } catch (err) {
          console.error(err);
          taskStatus.textContent = `実行失敗: ${err.message || err}`;
        } finally {
          runBtn.disabled = false;
        }
      });

      const logBtn = document.createElement('button');
      logBtn.textContent = 'ログを開く';
      logBtn.disabled = !task.last_log_path;
      logBtn.addEventListener('click', async () => {
        try {
          const client = getScheduler();
          if (!client?.openLog) throw new Error('scheduler API not available');
          if (!task.last_log_path) throw new Error('ログがありません');
          await client.openLog(task.last_log_path);
        } catch (err) {
          console.error(err);
          taskStatus.textContent = `ログを開けません: ${err.message || err}`;
        }
      });

      const delBtn = document.createElement('button');
      delBtn.textContent = '削除';
      delBtn.className = 'ghost';
      delBtn.addEventListener('click', () => {
        tasks = tasks.filter((t) => t.id !== task.id);
        renderTasks();
      });

      const meta = document.createElement('div');
      meta.className = 'task-meta';
      const lastRunText = task.last_run_at ? new Date(task.last_run_at).toLocaleString('ja-JP') : '未実行';
      meta.innerHTML = `
        <div>max-keywords: ${task.max_keywords || 10}</div>
        <div>間隔(分): ${task.interval_minutes || 1440}</div>
        <div>自動アップロード: ${task.auto_upload !== false ? 'ON' : 'OFF'}</div>
        <div>キャッシュ消去: ${task.clear_cache !== false ? 'ON' : 'OFF'}</div>
        <div>開始まで(分): ${
          typeof task.start_offset_minutes === 'number' ? task.start_offset_minutes : '未指定'
        }</div>
        <div>最終実行: ${lastRunText}</div>
      `;

      row.appendChild(wrapField('タスク名', nameInput));
      row.appendChild(wrapField('max-keywords', maxKw));
      row.appendChild(wrapField('間隔(分)', interval));
      row.appendChild(wrapField('間隔(分)', interval));
      row.appendChild(wrapField('開始まで(分)', startOffset));
      row.appendChild(wrapField('カテゴリ', categorySelect));
      row.appendChild(wrapField('自動アップロード', uploadToggle));
      row.appendChild(wrapField('音声キャッシュ消去', clearCacheToggle));
      row.appendChild(wrapField('有効', enabledToggle));
      row.appendChild(runBtn);
      row.appendChild(logBtn);
      row.appendChild(delBtn);

      li.appendChild(title);
      li.appendChild(row);
      li.appendChild(meta);
      taskList.appendChild(li);
    });
  }

  async function loadTasks() {
    try {
      const client = getScheduler();
      if (!client?.list) throw new Error('scheduler API not available');
      tasks = await client.list();
      if (!Array.isArray(tasks)) tasks = [];
      renderTasks();
    } catch (err) {
      console.error(err);
      taskStatus.textContent = `読み込みに失敗しました: ${err.message || err}`;
    }
  }

  async function saveTasks() {
    try {
      const client = getScheduler();
      if (!client?.save) throw new Error('scheduler API not available');
      await client.save(tasks);
      taskStatus.textContent = 'タスクを保存しました。';
    } catch (err) {
      console.error(err);
      taskStatus.textContent = `保存に失敗しました: ${err.message || err}`;
    }
  }

  if (taskAddBtn) {
    taskAddBtn.addEventListener('click', () => {
      tasks.push({
        id: uuid(),
        name: '新しいタスク',
        max_keywords: 10,
        interval_minutes: 1440,
        start_offset_minutes: 0,
        auto_upload: true,
        clear_cache: true,
        enabled: true,
      });
      renderTasks();
    });
  }
  if (taskSaveBtn) {
    taskSaveBtn.addEventListener('click', saveTasks);
  }

  loadTasks();
})();
