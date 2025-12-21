// Preview window script
(() => {
  const yamlPreview = document.getElementById('yamlPreview');
  const yamlEditBtn = document.getElementById('yamlEditBtn');
  const yamlApplyBtn = document.getElementById('yamlApplyBtn');
  const yamlCopyBtn = document.getElementById('yamlCopyBtn');
  const yamlRefreshBtn = document.getElementById('yamlRefreshBtn');
  const summaryPanel = document.getElementById('summaryPanel');
  const sectionPreviewBg = document.getElementById('sectionPreviewBg');
  const sectionPreviewTexts = document.getElementById('sectionPreviewTexts');

  let editMode = false;
  let currentScript = null;
  let selectedSectionIndex = 0;

  const PREVIEW_BASE_W = 1080;
  const PREVIEW_BASE_H = 1920;

  // Listen for script updates from main window
  window.api.onPreviewUpdate((data) => {
    currentScript = data.script;
    selectedSectionIndex = data.selectedIndex || 0;
    updatePreview();
    updateSectionPreview();
  });

  function updatePreview() {
    if (!currentScript) {
      yamlPreview.value = '# スクリプトが読み込まれていません';
      summaryPanel.innerHTML = '<span style="color: #999;">スクリプトを読み込んでください</span>';
      return;
    }

    try {
      const yamlText = window.yaml.stringify(currentScript);
      yamlPreview.value = yamlText;
      updateSummary();
    } catch (err) {
      console.error('YAML stringify error:', err);
      yamlPreview.value = '# エラー: YAML生成に失敗しました\n' + err.message;
    }
  }

  function updateSummary() {
    if (!currentScript) return;

    const sections = currentScript.sections?.length || 0;
    const duration = currentScript.sections?.reduce((sum, s) => {
      const d = s.duration_hint_sec || 0;
      return sum + d;
    }, 0) || 0;

    summaryPanel.innerHTML = `
      <strong>${currentScript.title || '無題'}</strong><br>
      セクション数: ${sections} / 
      推定時間: ${duration > 0 ? duration.toFixed(1) + '秒' : '未計算'}
    `;
  }

  function updateSectionPreview() {
    if (!currentScript || !currentScript.sections || currentScript.sections.length === 0) {
      sectionPreviewBg.style.backgroundImage = 'none';
      sectionPreviewTexts.innerHTML = '<div style="color: #666; text-align: center; padding: 20px;">セクションがありません</div>';
      return;
    }

    const section = currentScript.sections[selectedSectionIndex];
    if (!section) return;

    // Background
    const bg = section.bg || currentScript.video?.bg || '';
    if (bg) {
      const bgUrl = bg.startsWith('/') ? `file://${bg}` : bg;
      sectionPreviewBg.style.backgroundImage = `url("${bgUrl}")`;
    } else {
      sectionPreviewBg.style.backgroundImage = 'none';
    }

    // Text
    sectionPreviewTexts.innerHTML = '';
    
    if (section.on_screen_segments && section.on_screen_segments.length > 0) {
      // Multi-segment layout
      const baseStyle = currentScript.text_style || {};
      let yOffset = 0;
      
      section.on_screen_segments.forEach((seg, idx) => {
        const style = { ...baseStyle, ...(seg.style || {}) };
        const fontSize = style.fontsize || 64;
        const fill = style.fill || '#FFFFFF';
        const text = seg.text || '';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'section-preview__text';
        textDiv.textContent = text;
        textDiv.style.fontSize = fontSize + 'px';
        textDiv.style.color = fill;
        textDiv.style.left = '50%';
        textDiv.style.top = `${PREVIEW_BASE_H / 2 - 120 + yOffset}px`;
        textDiv.style.transform = 'translateX(-50%)';
        textDiv.style.width = '90%';
        
        sectionPreviewTexts.appendChild(textDiv);
        yOffset += fontSize + 24;
      });
    } else if (section.on_screen_text) {
      // Single text
      const style = currentScript.text_style || {};
      const fontSize = style.fontsize || 64;
      const fill = style.fill || '#FFFFFF';
      
      const textDiv = document.createElement('div');
      textDiv.className = 'section-preview__text';
      textDiv.textContent = section.on_screen_text;
      textDiv.style.fontSize = fontSize + 'px';
      textDiv.style.color = fill;
      textDiv.style.left = '50%';
      textDiv.style.top = `${PREVIEW_BASE_H / 2 - 120}px`;
      textDiv.style.transform = 'translateX(-50%)';
      textDiv.style.width = '90%';
      
      sectionPreviewTexts.appendChild(textDiv);
    }
  }

  yamlEditBtn.addEventListener('click', () => {
    editMode = !editMode;
    yamlPreview.readOnly = !editMode;
    yamlApplyBtn.disabled = !editMode;
    yamlEditBtn.textContent = editMode ? 'キャンセル' : '編集';

    if (!editMode) {
      // Cancel edit - revert to original
      updatePreview();
    }
  });

  yamlApplyBtn.addEventListener('click', async () => {
    try {
      const edited = window.yaml.parse(yamlPreview.value);
      
      // Send updated script back to main window
      await window.api.updateScriptFromPreview(edited);
      
      currentScript = edited;
      editMode = false;
      yamlPreview.readOnly = true;
      yamlApplyBtn.disabled = true;
      yamlEditBtn.textContent = '編集';
      
      alert('YAMLを適用しました');
    } catch (err) {
      alert('YAML パースエラー: ' + err.message);
    }
  });

  yamlCopyBtn.addEventListener('click', () => {
    yamlPreview.select();
    document.execCommand('copy');
    const originalText = yamlCopyBtn.textContent;
    yamlCopyBtn.textContent = 'コピー済み!';
    setTimeout(() => {
      yamlCopyBtn.textContent = originalText;
    }, 2000);
  });

  if (yamlRefreshBtn) {
    yamlRefreshBtn.addEventListener('click', () => {
      window.api.requestPreviewData();
    });
  }

  // Request initial data
  window.api.requestPreviewData();
})();
