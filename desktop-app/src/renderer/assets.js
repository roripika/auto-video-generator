(() => {
  const state = { settings: null };
  const keywordInput = document.getElementById('keyword');
  const kindSelect = document.getElementById('kind');
  const allowAICheck = document.getElementById('allowAI');
  const searchBtn = document.getElementById('searchBtn');
  const resultsEl = document.getElementById('results');

  async function loadDefaults() {
    // keep keyword empty; load settings only to ensure APIs ready
    try {
      const settings = await window.assetApi.loadSettings();
      state.settings = settings || {};
    } catch (err) {
      console.error('settings load failed', err);
    }
  }

  function renderResults(list) {
    resultsEl.innerHTML = '';
    if (!list || !list.length) {
      const li = document.createElement('li');
      li.textContent = '検索結果はまだありません。';
      resultsEl.appendChild(li);
      return;
    }
    list.forEach((asset) => {
      const li = document.createElement('li');
      const info = document.createElement('div');
      info.style.flex = '1';
      const title = document.createElement('div');
      title.textContent = `${asset.provider || '??'} / ${asset.kind || ''}`;
      const meta = document.createElement('div');
      meta.className = 'meta';
      const details = [];
      if (asset.path) details.push(asset.path);
      if (asset.duration) details.push(`${Number(asset.duration).toFixed(1)}s`);
      meta.textContent = details.join(' • ');
      info.appendChild(title);
      info.appendChild(meta);

      const previewWrap = document.createElement('div');
      previewWrap.style.display = 'flex';
      previewWrap.style.gap = '8px';
      previewWrap.style.alignItems = 'center';
      previewWrap.style.marginTop = '6px';
      const previewSrc =
        asset.preview_url ||
        (asset.kind === 'image' && asset.path ? (asset.path.startsWith('/') ? `file://${asset.path}` : asset.path) : '');
      if (previewSrc) {
        const img = document.createElement('img');
        img.src = previewSrc;
        img.alt = 'preview';
        img.style.width = '140px';
        img.style.height = '80px';
        img.style.objectFit = 'cover';
        img.loading = 'lazy';
        previewWrap.appendChild(img);
      } else if (asset.kind === 'video' && asset.path) {
        const v = document.createElement('video');
        v.src = asset.path.startsWith('/') ? `file://${asset.path}` : asset.path;
        v.width = 180;
        v.height = 100;
        v.muted = true;
        v.autoplay = true;
        v.loop = true;
        v.playsInline = true;
        previewWrap.appendChild(v);
      }
      if (previewWrap.childElementCount > 0) {
        info.appendChild(previewWrap);
      }

      const actions = document.createElement('div');
      actions.style.display = 'flex';
      actions.style.gap = '8px';
      const applyGlobal = document.createElement('button');
      applyGlobal.textContent = '全体に適用';
      applyGlobal.addEventListener('click', () => {
        window.assetApi.applyBackground({ path: asset.path, target: 'global' });
      });
      const applySection = document.createElement('button');
      applySection.textContent = 'セクションに適用';
      applySection.addEventListener('click', () => {
        window.assetApi.applyBackground({ path: asset.path, target: 'section' });
      });
      actions.appendChild(applyGlobal);
      actions.appendChild(applySection);

      li.appendChild(info);
      li.appendChild(actions);
      resultsEl.appendChild(li);
    });
  }

  async function handleSearch() {
    const keyword = keywordInput.value.trim();
    if (!keyword) {
      resultsEl.innerHTML = '<li>キーワードを入力してください。</li>';
      return;
    }
    searchBtn.disabled = true;
    searchBtn.textContent = '検索中...';
    renderResults([]);
    try {
      const results = await window.assetApi.fetchAssets({
        keyword,
        kind: kindSelect.value || 'video',
        allowAI: allowAICheck.checked,
        providerOrder: state.settings?.assetProviderOrder || 'pexels,pixabay',
        maxResults: state.settings?.assetMaxResults || 5,
      });
      renderResults(Array.isArray(results) ? results : []);
    } catch (err) {
      console.error(err);
      resultsEl.innerHTML = `<li>検索に失敗しました: ${err.message || err}</li>`;
    } finally {
      searchBtn.disabled = false;
      searchBtn.textContent = '検索';
    }
  }

  searchBtn.addEventListener('click', handleSearch);
  keywordInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch();
    }
  });

  loadDefaults();
})();
