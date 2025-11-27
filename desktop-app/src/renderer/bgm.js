(() => {
  const keywordInput = document.getElementById('bgmKeyword');
  const searchForm = document.getElementById('bgmSearchForm');
  const searchBtn = document.getElementById('bgmSearchBtn');
  const directoryLabel = document.getElementById('bgmDirectoryLabel');
  const resultsEl = document.getElementById('bgmResults');

  let currentItems = [];

  function formatBytes(size) {
    if (!size || size <= 0) return '';
    const units = ['B', 'KB', 'MB', 'GB'];
    let idx = 0;
    let num = size;
    while (num >= 1024 && idx < units.length - 1) {
      num /= 1024;
      idx += 1;
    }
    return `${num.toFixed(idx === 0 ? 0 : 1)}${units[idx]}`;
  }

  function fileUrl(path) {
    if (!path) return '';
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path;
    }
    if (path.startsWith('file://')) return path;
    if (path.startsWith('/')) {
      return `file://${path}`;
    }
    return `file://${path}`;
  }

  function renderResults(items) {
    resultsEl.innerHTML = '';
    if (!items || !items.length) {
      const empty = document.createElement('li');
      empty.textContent = '該当する BGM が見つかりませんでした。設定画面で BGM ディレクトリを確認してください。';
      resultsEl.appendChild(empty);
      return;
    }
    items.forEach((item) => {
      const li = document.createElement('li');
      const title = document.createElement('strong');
      title.textContent = item.relativePath || item.name;
      li.appendChild(title);

      const meta = document.createElement('div');
      meta.className = 'bgm-meta';
      meta.textContent = `${formatBytes(item.size)}`;
      li.appendChild(meta);

      if (item.path) {
        const player = document.createElement('audio');
        player.controls = true;
        player.src = fileUrl(item.path);
        li.appendChild(player);
      }

      const actions = document.createElement('div');
      actions.className = 'bgm-actions';
      const applyBtn = document.createElement('button');
      applyBtn.textContent = 'このBGMを使用';
      applyBtn.addEventListener('click', () => {
        window.bgmApi.applyBgm({
          path: item.path,
          displayName: item.relativePath || item.name,
        });
      });
      actions.appendChild(applyBtn);
      li.appendChild(actions);

      resultsEl.appendChild(li);
    });
  }

  async function performSearch() {
    if (!window.bgmApi || !window.bgmApi.listTracks) return;
    try {
      if (searchBtn) {
        searchBtn.disabled = true;
        searchBtn.textContent = '検索中...';
      }
      const keyword = keywordInput?.value?.trim() || '';
      const result = await window.bgmApi.listTracks({ keyword });
      directoryLabel.textContent = result?.resolvedDirectory
        ? `検索対象ディレクトリ: ${result.resolvedDirectory}`
        : '検索対象ディレクトリが存在しません。設定で BGM ディレクトリを確認してください。';
      currentItems = Array.isArray(result?.items) ? result.items : [];
      renderResults(currentItems);
    } catch (err) {
      console.error('Failed to search BGM files', err);
      resultsEl.innerHTML = '<li>検索中にエラーが発生しました。コンソールを確認してください。</li>';
    } finally {
      if (searchBtn) {
        searchBtn.disabled = false;
        searchBtn.textContent = '検索';
      }
    }
  }

  if (searchForm) {
    searchForm.addEventListener('submit', (event) => {
      event.preventDefault();
      performSearch();
    });
  }

  performSearch();
})();
