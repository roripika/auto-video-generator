(() => {
  const trendList = document.getElementById('trendList');
  const trendFetchBtn = document.getElementById('trendFetchBtn');
  const trendApplySelectedBtn = document.getElementById('trendApplySelectedBtn');
  const trendStatus = document.getElementById('trendStatus');

  const selected = new Set();

  function renderList(items) {
    trendList.innerHTML = '';
    items.forEach((title) => {
      const li = document.createElement('li');
      li.className = 'asset-results__item';
      const label = document.createElement('label');
      label.style.display = 'flex';
      label.style.alignItems = 'center';
      label.style.gap = '8px';
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = selected.has(title);
      cb.addEventListener('change', () => {
        if (cb.checked) selected.add(title);
        else selected.delete(title);
      });
      const span = document.createElement('span');
      span.textContent = title;
      label.appendChild(cb);
      label.appendChild(span);

      const btn = document.createElement('button');
      btn.textContent = 'このトレンドで台本';
      btn.className = 'primary';
      btn.style.marginLeft = '8px';
      btn.addEventListener('click', () => {
        window.trendApi.applyKeyword({ keyword: title });
        window.close();
      });

      li.appendChild(label);
      li.appendChild(btn);
      trendList.appendChild(li);
    });
  }

  async function fetchTrends() {
    trendFetchBtn.disabled = true;
    trendStatus.textContent = '取得中...';
    trendList.innerHTML = '';
    selected.clear();
    try {
      const items = await window.trendApi.fetchTrending({ geo: 'JP', limit: 12 });
      if (!items || !items.length) {
        trendStatus.textContent = 'トレンドが取得できませんでした。APIキーやネットワークをご確認ください。';
        return;
      }
      renderList(items);
      trendStatus.textContent = '';
    } catch (err) {
      console.error(err);
      trendStatus.textContent = `エラー: ${err.message || err}`;
    } finally {
      trendFetchBtn.disabled = false;
    }
  }

  if (trendFetchBtn) {
    trendFetchBtn.addEventListener('click', fetchTrends);
  }
  if (trendApplySelectedBtn) {
    trendApplySelectedBtn.addEventListener('click', () => {
      if (!selected.size) {
        trendStatus.textContent = '少なくとも1件選択してください。';
        return;
      }
      window.trendApi.applyKeyword({ keywords: Array.from(selected) });
      window.close();
    });
  }

  fetchTrends();
})();
