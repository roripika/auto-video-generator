(() => {
  const themeSelect = document.getElementById('themeSelect');
  const sectionListEl = document.getElementById('sectionList');
  const sectionFormEl = document.getElementById('sectionForm');
  const yamlPreviewEl = document.getElementById('yamlPreview');
  const summaryPanelEl = document.getElementById('summaryPanel');
  const aiBriefInput = document.getElementById('aiBriefInput');
  const aiSectionsInput = document.getElementById('aiSectionsInput');
  const aiGenerateBtn = document.getElementById('aiGenerateBtn');
  const bgPathInput = document.getElementById('bgPathInput');
  const bgBrowseBtn = document.getElementById('bgBrowseBtn');
  const assetKeywordInput = document.getElementById('assetKeywordInput');
  const assetKindSelect = document.getElementById('assetKindSelect');
  const assetAllowAICheck = document.getElementById('assetAllowAICheck');
  const assetFetchBtn = document.getElementById('assetFetchBtn');
  const assetOpenWindowBtn = document.getElementById('assetOpenWindowBtn');
  const assetResultList = document.getElementById('assetResultList');
  const textFontInput = document.getElementById('textFontInput');
  const textFontSizeInput = document.getElementById('textFontSizeInput');
  const textFillInput = document.getElementById('textFillInput');
  const textStrokeColorInput = document.getElementById('textStrokeColorInput');
  const textStrokeWidthInput = document.getElementById('textStrokeWidthInput');
  const textPosXInput = document.getElementById('textPosXInput');
  const textPosYInput = document.getElementById('textPosYInput');
  const textAnimationInput = document.getElementById('textAnimationInput');
  const audioGenerateBtn = document.getElementById('audioGenerateBtn');
  const timelineRefreshBtn = document.getElementById('timelineRefreshBtn');
  const timelineSummaryEl = document.getElementById('timelineSummary');
  const videoGenerateBtn = document.getElementById('videoGenerateBtn');
  const videoOpenBtn = document.getElementById('videoOpenBtn');
  const videoLogEl = document.getElementById('videoLog');
  const statusBadge = document.createElement('span');
  statusBadge.className = 'status';
  document.querySelector('.app-header').appendChild(statusBadge);

  const settingsModal = document.getElementById('settingsModal');
  const settingsProviderSelect = document.getElementById('settingsProvider');
  const settingsApiKeyInput = document.getElementById('settingsApiKey');
  const settingsBaseUrlInput = document.getElementById('settingsBaseUrl');
  const settingsModelInput = document.getElementById('settingsModel');
  const settingsProviderOrder = document.getElementById('settingsProviderOrder');
  const providerHintEl = document.getElementById('providerHint');
  const settingsBtn = document.getElementById('settingsBtn');
  const settingsCancelBtn = document.getElementById('settingsCancelBtn');
  const settingsCloseBtn = document.getElementById('settingsCloseBtn');
  const settingsSaveBtn = document.getElementById('settingsSaveBtn');
  const settingsPexelsKeyInput = document.getElementById('settingsPexelsKey');
  const settingsPixabayKeyInput = document.getElementById('settingsPixabayKey');
  const settingsStabilityKeyInput = document.getElementById('settingsStabilityKey');
  const settingsMaxResults = document.getElementById('settingsMaxResults');

  const PROVIDER_PRESETS = {
    openai: {
      label: 'OpenAI',
      baseUrl: 'https://api.openai.com/v1',
      model: 'gpt-4o-mini',
      env: 'OPENAI_API_KEY',
    },
    anthropic: {
      label: 'Anthropic Claude',
      baseUrl: 'https://api.anthropic.com/v1/messages',
      model: 'claude-3-haiku-20240307',
      env: 'ANTHROPIC_API_KEY',
    },
    gemini: {
      label: 'Google Gemini',
      baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
      model: 'gemini-2.5-flash',
      env: 'GEMINI_API_KEY / GOOGLE_API_KEY',
    },
  };

  const state = {
    themes: [],
    script: null,
    filePath: null,
    selectedIndex: 0,
    settings: null,
    generating: false,
    assetLoading: false,
    assetResults: [],
    audioGenerating: false,
    timelineLoading: false,
    timeline: null,
    videoGenerating: false,
    videoLog: '',
    lastVideoPath: '',
  };

  async function init() {
    await loadSettings();
    state.themes = await window.api.listThemes();
    populateThemeSelect();
    if (state.themes.length) {
      themeSelect.value = state.themes[0].id;
      await createScriptFromTheme();
    }
  }

  function populateThemeSelect() {
    themeSelect.innerHTML = '';
    state.themes.forEach((theme) => {
      const option = document.createElement('option');
      option.value = theme.id;
      option.textContent = `${theme.label} (${theme.genre})`;
      themeSelect.appendChild(option);
    });
  }

  async function createScriptFromTheme() {
    const themeId = themeSelect.value;
    const script = await window.api.newScriptFromTheme(themeId);
    state.script = script;
    state.filePath = null;
    state.selectedIndex = 0;
    state.timeline = null;
    render();
    setStatus(`テーマ「${themeId}」から新規作成しました。`);
  }

  async function handleOpenScript() {
    const result = await window.api.openScript();
    if (result.canceled) return;
    state.script = result.script;
    state.filePath = result.path;
    state.selectedIndex = 0;
    state.timeline = null;
    render();
    setStatus(`${result.path} を読み込みました。`);
  }

  async function handleSaveScript() {
    if (!state.script) return;
    const result = await window.api.saveScript({ path: state.filePath, script: state.script });
    if (result.canceled) return;
    state.filePath = result.path;
    setStatus(`${result.path} に保存しました。`);
  }

  async function handleAIGenerate() {
    if (!aiBriefInput || !aiSectionsInput || !aiGenerateBtn) {
      return;
    }
    const brief = aiBriefInput.value.trim();
    if (!brief) {
      setStatus('ブリーフを入力してください。');
      return;
    }
    if (!state.themes.length) {
      setStatus('テーマが読み込まれていません。');
      return;
    }
    if (state.generating) return;
    state.generating = true;
    aiGenerateBtn.disabled = true;
    const originalLabel = aiGenerateBtn.textContent;
    aiGenerateBtn.textContent = '生成中...';
    const sections = Number(aiSectionsInput.value) || 5;
    const themeId = themeSelect.value || state.themes[0].id;

    try {
      const script = await window.api.generateScriptFromBrief({
        brief,
        sections,
        themeId,
      });
      state.script = script;
      state.filePath = null;
      state.selectedIndex = 0;
      state.timeline = null;
      render();
      setStatus('AI生成した台本を読み込みました。');
    } catch (err) {
      console.error(err);
      setStatus(`AI生成に失敗しました: ${err.message || err}`);
    } finally {
      state.generating = false;
      aiGenerateBtn.disabled = false;
      aiGenerateBtn.textContent = originalLabel;
    }
  }

  async function handleGenerateAudio() {
    if (!audioGenerateBtn) return;
    if (!state.script) {
      setStatus('スクリプトを読み込んでから音声を生成してください。');
      return;
    }
    if (state.audioGenerating) return;
    state.audioGenerating = true;
    const original = audioGenerateBtn.textContent;
    audioGenerateBtn.disabled = true;
    audioGenerateBtn.textContent = '音声生成中...';
    try {
      await window.api.generateAudio({ script: state.script });
      setStatus('VOICEVOX 音声の生成が完了しました。');
    } catch (err) {
      console.error(err);
      setStatus(`音声生成に失敗しました: ${err.message || err}`);
    } finally {
      state.audioGenerating = false;
      audioGenerateBtn.disabled = false;
      audioGenerateBtn.textContent = original;
    }
  }

  async function handleTimelineRefresh() {
    if (!timelineRefreshBtn) return;
    if (!state.script) {
      setStatus('スクリプトを読み込んでからタイムラインを更新してください。');
      return;
    }
    if (state.timelineLoading) return;
    state.timelineLoading = true;
    timelineRefreshBtn.disabled = true;
    const original = timelineRefreshBtn.textContent;
    timelineRefreshBtn.textContent = '計算中...';
    renderTimelineSummary();
    try {
      const result = await window.api.describeTimeline({ script: state.script });
      state.timeline = result;
      setStatus('タイムラインを更新しました。');
    } catch (err) {
      console.error(err);
      state.timeline = null;
      setStatus(`タイムラインの計算に失敗しました: ${err.message || err}`);
    } finally {
      state.timelineLoading = false;
      timelineRefreshBtn.disabled = false;
      timelineRefreshBtn.textContent = original;
      renderTimelineSummary();
    }
  }

  async function handleVideoGenerate() {
    if (!videoGenerateBtn) return;
    if (!state.script) {
      setStatus('スクリプトを読み込んでから動画生成を行ってください。');
      return;
    }
    if (state.videoGenerating) return;
    state.videoGenerating = true;
    const original = videoGenerateBtn.textContent;
    videoGenerateBtn.disabled = true;
    videoGenerateBtn.textContent = '動画生成中...';
    videoLogEl.value = '';
    try {
      const result = await window.api.generateVideo({ script: state.script });
      state.videoLog = result.stdout || '';
      videoLogEl.value = state.videoLog;
      state.lastVideoPath = result.outputPath;
      if (videoOpenBtn) {
        videoOpenBtn.disabled = !state.lastVideoPath;
      }
      setStatus('動画生成が完了しました。');
    } catch (err) {
      console.error(err);
      state.videoLog = err.message || '';
      videoLogEl.value = state.videoLog;
      setStatus(`動画生成に失敗しました: ${err.message || err}`);
    } finally {
      state.videoGenerating = false;
      videoGenerateBtn.disabled = false;
      videoGenerateBtn.textContent = original;
    }
  }

  async function handleOpenVideo() {
    if (!state.lastVideoPath) {
      setStatus('動画ファイルがまだありません。');
      return;
    }
    try {
      await window.api.openOutputPath({ path: state.lastVideoPath });
    } catch (err) {
      console.error(err);
      setStatus(`動画のオープンに失敗しました: ${err.message || err}`);
    }
  }

  function render() {
    renderSectionList();
    renderSectionForm();
    renderSummary();
    renderYaml();
    updateBackgroundField();
    renderAssetResults();
    syncTextStyleForm();
    renderTimelineSummary();
  }

  function renderSectionList() {
    sectionListEl.innerHTML = '';
    if (!state.script) return;
    state.script.sections.forEach((section, index) => {
      const li = document.createElement('li');
      li.textContent = `${index + 1}. ${section.on_screen_text || section.id}`;
      if (index === state.selectedIndex) {
        li.classList.add('active');
      }
      li.addEventListener('click', () => {
        state.selectedIndex = index;
        renderSectionForm();
        renderSectionList();
      });
      sectionListEl.appendChild(li);
    });
  }

  function renderSectionForm() {
    sectionFormEl.innerHTML = '';
    if (!state.script) {
      sectionFormEl.textContent = 'テーマを選択して新しいスクリプトを作成してください。';
      return;
    }
    const section = state.script.sections[state.selectedIndex];
    if (!section) {
      sectionFormEl.textContent = 'セクションがありません。';
      return;
    }

    const fields = [
      { key: 'on_screen_text', label: 'テロップ' },
      { key: 'narration', label: 'ナレーション' },
      { key: 'hook', label: 'フック' },
      { key: 'evidence', label: '根拠' },
      { key: 'demo', label: '実演/メリット' },
      { key: 'bridge', label: 'ブリッジ' },
      { key: 'cta', label: 'CTA' },
    ];

    fields.forEach(({ key, label }) => {
      const wrapper = document.createElement('div');
      const fieldLabel = document.createElement('label');
      fieldLabel.textContent = label;
      const textarea = document.createElement('textarea');
      textarea.value = section[key] || '';
      textarea.addEventListener('input', (event) => {
        section[key] = event.target.value;
        renderSectionList();
        renderSummary();
        renderYaml();
      });
      wrapper.appendChild(fieldLabel);
      wrapper.appendChild(textarea);
      sectionFormEl.appendChild(wrapper);
    });

    // Section background input & preview
    const bgWrapper = document.createElement('div');
    const bgLabel = document.createElement('label');
    bgLabel.textContent = 'セクション背景 (未指定なら全体背景を使用)';
    const bgInput = document.createElement('input');
    bgInput.type = 'text';
    bgInput.placeholder = 'assets/cache/...';
    bgInput.value = section.bg || '';
    bgInput.addEventListener('input', (e) => {
      section.bg = e.target.value || null;
      renderYaml();
      renderSummary();
    });
    const clearBtn = document.createElement('button');
    clearBtn.textContent = 'クリア';
    clearBtn.className = 'ghost';
    clearBtn.addEventListener('click', () => {
      section.bg = null;
      bgInput.value = '';
      renderYaml();
      renderSummary();
      renderSectionForm();
    });
    const preview = document.createElement('div');
    preview.style.marginTop = '6px';
    preview.style.display = 'flex';
    preview.style.gap = '8px';
    const bgSrc = section.bg || '';
    if (bgSrc) {
      if (bgSrc.match(/\\.(png|jpg|jpeg|bmp)$/i)) {
        const img = document.createElement('img');
        img.src = bgSrc.startsWith('/') ? `file://${bgSrc}` : bgSrc;
        img.alt = 'bg-preview';
        img.style.width = '160px';
        img.style.height = '90px';
        img.style.objectFit = 'cover';
        img.loading = 'lazy';
        preview.appendChild(img);
      } else {
        const v = document.createElement('video');
        v.src = bgSrc.startsWith('/') ? `file://${bgSrc}` : bgSrc;
        v.width = 180;
        v.height = 100;
        v.muted = true;
        v.autoplay = true;
        v.loop = true;
        v.playsInline = true;
        preview.appendChild(v);
      }
    }
    bgWrapper.appendChild(bgLabel);
    bgWrapper.appendChild(bgInput);
    bgWrapper.appendChild(clearBtn);
    bgWrapper.appendChild(preview);
    sectionFormEl.appendChild(bgWrapper);
  }

  function renderSummary() {
    if (!state.script) {
      summaryPanelEl.textContent = 'スクリプト未読込。';
      return;
    }
    const sectionCount = state.script.sections.length;
    summaryPanelEl.innerHTML = `
      <div><strong>タイトル:</strong> ${state.script.title}</div>
      <div><strong>ファイル:</strong> ${state.filePath || '未保存'}</div>
      <div><strong>セクション数:</strong> ${sectionCount}</div>
      <div><strong>CTA:</strong> ${state.script.sections[0]?.cta || ''}</div>
    `;
  }

  function renderYaml() {
    if (!state.script) {
      yamlPreviewEl.value = '';
      return;
    }
    yamlPreviewEl.value = window.yaml.stringify(state.script);
  }

  function addSection() {
    if (!state.script) return;
    const index = state.script.sections.length + 1;
    state.script.sections.push({
      id: `rank-${index}`,
      on_screen_text: `第${index}位：新しい項目`,
      narration: '',
      hook: '',
      evidence: '',
      demo: '',
      bridge: '',
      cta: '',
    });
    state.selectedIndex = state.script.sections.length - 1;
    render();
  }

  function renderAssetResults() {
    // メインウインドウでは検索リストを表示しない（別ウインドウへ移行）
    if (!assetResultList) return;
    assetResultList.innerHTML = '';
  }

  function renderTimelineSummary() {
    if (!timelineSummaryEl) return;
    if (state.timelineLoading) {
      timelineSummaryEl.textContent = 'タイムライン計算中...';
      return;
    }
    if (!state.timeline) {
      timelineSummaryEl.textContent = '未計算。音声生成後にタイムラインを更新してください。';
      return;
    }
    const lines = [`合計: ${state.timeline.total_duration.toFixed(2)}s / セクション ${state.timeline.sections.length}件`];
    state.timeline.sections.forEach((item) => {
      const audioLabel = item.has_audio ? '🎧' : '—';
      lines.push(`#${item.index} ${item.id} : ${item.duration.toFixed(2)}s ${audioLabel}`);
    });
    timelineSummaryEl.textContent = lines.join('\n');
  }

  async function handleFetchAssets() {
    if (!assetFetchBtn) return;
    const keywordInput = assetKeywordInput?.value?.trim();
    const fallbackKeyword = state.script?.title || '';
    const keyword = keywordInput || fallbackKeyword;
    if (!keyword) {
      setStatus('素材検索のキーワードを入力してください。');
      return;
    }
    if (state.assetLoading) return;
    state.assetLoading = true;
    assetFetchBtn.disabled = true;
    assetFetchBtn.textContent = '検索中...';
    renderAssetResults();
    try {
      const results = await window.api.fetchAssets({
        keyword,
        kind: assetKindSelect?.value || 'video',
        allowAI: assetAllowAICheck ? assetAllowAICheck.checked : true,
        providerOrder: state.settings?.assetProviderOrder || 'pexels,pixabay',
        maxResults: 5,
      });
      state.assetResults = Array.isArray(results) ? results : [];
      setStatus(
        state.assetResults.length
          ? '素材を取得しました。リストから適用できます。'
          : '素材が見つかりませんでした。'
      );
    } catch (err) {
      console.error(err);
      setStatus(`素材取得に失敗しました: ${err.message || err}`);
    } finally {
      state.assetLoading = false;
      assetFetchBtn.disabled = false;
      assetFetchBtn.textContent = '素材を検索';
      renderAssetResults();
    }
  }

  function setStatus(message) {
    statusBadge.textContent = message;
    if (!message) return;
    setTimeout(() => {
      statusBadge.textContent = '';
    }, 4000);
  }

  function ensureTextStyle() {
    if (!state.script) return null;
    if (!state.script.text_style) {
      state.script.text_style = {
        font: 'Noto Sans JP',
        fontsize: 60,
        fill: '#FFFFFF',
        stroke: { color: '#000000', width: 4 },
        position: { x: 'center', y: 'bottom-180' },
        max_chars_per_line: 22,
        lines: 3,
      };
    }
    if (!state.script.text_style.stroke) {
      state.script.text_style.stroke = { color: '#000000', width: 4 };
    }
    if (!state.script.text_style.position) {
      state.script.text_style.position = { x: 'center', y: 'bottom-180' };
    }
    return state.script.text_style;
  }

  function syncTextStyleForm() {
    if (!textFontInput) return;
    const style = state.script?.text_style;
    if (!style) {
      textFontInput.value = '';
      if (textFontSizeInput) textFontSizeInput.value = '';
      if (textFillInput) textFillInput.value = '#ffffff';
      if (textStrokeColorInput) textStrokeColorInput.value = '#000000';
      if (textStrokeWidthInput) textStrokeWidthInput.value = '0';
      if (textPosXInput) textPosXInput.value = '';
      if (textPosYInput) textPosYInput.value = '';
      if (textAnimationInput) textAnimationInput.value = '';
      return;
    }
    textFontInput.value = style.font || '';
    if (textFontSizeInput) textFontSizeInput.value = style.fontsize ?? '';
    if (textFillInput && style.fill) textFillInput.value = style.fill;
    if (textStrokeColorInput && style.stroke?.color) textStrokeColorInput.value = style.stroke.color;
    if (textStrokeWidthInput && typeof style.stroke?.width === 'number') {
      textStrokeWidthInput.value = style.stroke.width;
    }
    if (textPosXInput) textPosXInput.value = style.position?.x ?? '';
    if (textPosYInput) textPosYInput.value = style.position?.y ?? '';
    if (textAnimationInput) textAnimationInput.value = style.animation || '';
  }

  function applyTextStyleChange(mutator) {
    const style = ensureTextStyle();
    if (!style) return;
    mutator(style);
    renderYaml();
    setStatus('テキストスタイルを更新しました。');
  }

  function handleTextFontChange(event) {
    applyTextStyleChange((style) => {
      style.font = event.target.value;
    });
  }

  function handleFontSizeChange(event) {
    const value = parseInt(event.target.value, 10);
    if (Number.isNaN(value)) return;
    applyTextStyleChange((style) => {
      style.fontsize = value;
    });
  }

  function handleFillChange(event) {
    applyTextStyleChange((style) => {
      style.fill = event.target.value;
    });
  }

  function handleStrokeColorChange(event) {
    applyTextStyleChange((style) => {
      style.stroke.color = event.target.value;
    });
  }

  function handleStrokeWidthChange(event) {
    const value = parseInt(event.target.value, 10);
    if (Number.isNaN(value)) return;
    applyTextStyleChange((style) => {
      style.stroke.width = value;
    });
  }

  function handlePositionChange(axis, value) {
    applyTextStyleChange((style) => {
      style.position[axis] = value;
    });
  }

  function handleAnimationChange(event) {
    applyTextStyleChange((style) => {
      style.animation = event.target.value;
    });
  }

  function updateBackgroundField() {
    if (!bgPathInput) return;
    const current = state.script?.video?.bg || '';
    if (bgPathInput.value !== current) {
      bgPathInput.value = current;
    }
  }

  function setVideoBackground(value) {
    if (!state.script || !state.script.video) {
      setStatus('スクリプトが読み込まれていません。');
      return;
    }
    state.script.video.bg = value || '';
    updateBackgroundField();
    renderSummary();
    renderYaml();
    setStatus(value ? `背景を ${value} に設定しました。` : '背景を未設定にしました。');
  }

  function setSectionBackground(value) {
    if (!state.script) return;
    const section = state.script.sections[state.selectedIndex];
    if (!section) return;
    section.bg = value || null;
    renderSectionForm();
    renderSummary();
    renderYaml();
    setStatus(value ? `セクション背景を ${value} に設定しました。` : 'セクション背景を未設定にしました。');
  }

  function handleBackgroundInput(event) {
    setVideoBackground(event.target.value);
  }

  async function handleBrowseBackground() {
    try {
      const result = await window.api.chooseBackgroundFile();
      if (result && !result.canceled && result.path) {
        setVideoBackground(result.path);
      }
    } catch (err) {
      console.error(err);
      setStatus('背景ファイルの選択に失敗しました。');
    }
  }

  async function handleFetchAssets() {
    if (!assetFetchBtn) return;
    const keywordInput = assetKeywordInput?.value?.trim();
    const fallbackKeyword = state.script?.title || '';
    const keyword = keywordInput || fallbackKeyword;
    if (!keyword) {
      setStatus('素材検索のキーワードを入力してください。');
      return;
    }
    if (state.assetLoading) return;
    state.assetLoading = true;
    assetFetchBtn.disabled = true;
    assetFetchBtn.textContent = '検索中...';
    renderAssetResults();
    try {
      const results = await window.api.fetchAssets({
        keyword,
        kind: assetKindSelect?.value || 'video',
        allowAI: assetAllowAICheck ? assetAllowAICheck.checked : true,
        maxResults: 5,
      });
      state.assetResults = Array.isArray(results) ? results : [];
      setStatus(
        state.assetResults.length
          ? '素材を取得しました。リストから適用できます。'
          : '素材が見つかりませんでした。'
      );
    } catch (err) {
      console.error(err);
      setStatus(`素材取得に失敗しました: ${err.message || err}`);
    } finally {
      state.assetLoading = false;
      assetFetchBtn.disabled = false;
      assetFetchBtn.textContent = '素材を検索';
      renderAssetResults();
    }
  }

  async function loadSettings() {
    try {
      state.settings = await window.api.loadSettings();
    } catch (err) {
      console.error('Failed to load settings', err);
      state.settings = null;
    }
  }

  function populateProviderOptions() {
    settingsProviderSelect.innerHTML = '';
    Object.entries(PROVIDER_PRESETS).forEach(([value, meta]) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = meta.label;
      settingsProviderSelect.appendChild(option);
    });
  }

  function openSettingsModal() {
    populateProviderOptions();
    const settings = state.settings || {
      provider: 'openai',
      apiKey: '',
      baseUrl: PROVIDER_PRESETS.openai.baseUrl,
      model: PROVIDER_PRESETS.openai.model,
      pexelsApiKey: '',
      pixabayApiKey: '',
      stabilityApiKey: '',
      assetProviderOrder: 'pexels,pixabay',
      assetMaxResults: 5,
    };
    settingsProviderSelect.value = settings.provider in PROVIDER_PRESETS ? settings.provider : 'openai';
    settingsApiKeyInput.value = settings.apiKey || '';
    settingsBaseUrlInput.value = settings.baseUrl || PROVIDER_PRESETS[settingsProviderSelect.value].baseUrl;
    settingsModelInput.value = settings.model || PROVIDER_PRESETS[settingsProviderSelect.value].model;
    if (settingsProviderOrder) settingsProviderOrder.value = settings.assetProviderOrder || 'pexels,pixabay';
    if (settingsMaxResults) settingsMaxResults.value = settings.assetMaxResults || 5;
    if (settingsPexelsKeyInput) settingsPexelsKeyInput.value = settings.pexelsApiKey || '';
    if (settingsPixabayKeyInput) settingsPixabayKeyInput.value = settings.pixabayApiKey || '';
    if (settingsStabilityKeyInput) settingsStabilityKeyInput.value = settings.stabilityApiKey || '';
    settingsBaseUrlInput.dataset.dirty = 'false';
    settingsModelInput.dataset.dirty = 'false';
    updateProviderHint();
    settingsModal.classList.remove('hidden');
  }

  function closeSettingsModal() {
    settingsModal.classList.add('hidden');
  }

  function handleProviderChanged() {
    const preset = PROVIDER_PRESETS[settingsProviderSelect.value];
    if (!preset) {
      return;
    }
    if (settingsBaseUrlInput.dataset.dirty !== 'true') {
      settingsBaseUrlInput.value = preset.baseUrl;
    }
    if (settingsModelInput.dataset.dirty !== 'true') {
      settingsModelInput.value = preset.model;
    }
    updateProviderHint();
  }

  function markDirty(event) {
    event.target.dataset.dirty = 'true';
  }

  async function handleSettingsSave() {
    const payload = {
      provider: settingsProviderSelect.value,
      apiKey: settingsApiKeyInput.value.trim(),
      baseUrl: settingsBaseUrlInput.value.trim(),
      model: settingsModelInput.value.trim(),
      assetProviderOrder: settingsProviderOrder?.value || 'pexels,pixabay',
      assetMaxResults: Number(settingsMaxResults?.value) || 5,
      pexelsApiKey: settingsPexelsKeyInput?.value?.trim() || '',
      pixabayApiKey: settingsPixabayKeyInput?.value?.trim() || '',
      stabilityApiKey: settingsStabilityKeyInput?.value?.trim() || '',
    };
    try {
      const saved = await window.api.saveSettings(payload);
      state.settings = saved;
      setStatus('AI 設定を保存しました。');
    } catch (err) {
      console.error('Failed to save settings', err);
      setStatus('AI 設定の保存に失敗しました。');
    } finally {
      closeSettingsModal();
    }
  }

  function handleModalClick(event) {
    if (event.target === settingsModal) {
      closeSettingsModal();
    }
  }

  function updateProviderHint() {
    if (!providerHintEl) return;
    const preset = PROVIDER_PRESETS[settingsProviderSelect.value];
    if (!preset) {
      providerHintEl.textContent = '';
      return;
    }
    providerHintEl.textContent = `プロバイダ: ${preset.label}（APIキー: ${preset.env}）`;
  }

  document.getElementById('newScriptBtn').addEventListener('click', createScriptFromTheme);
  document.getElementById('openScriptBtn').addEventListener('click', handleOpenScript);
  document.getElementById('saveScriptBtn').addEventListener('click', handleSaveScript);
  document.getElementById('addSectionBtn').addEventListener('click', addSection);
  themeSelect.addEventListener('change', () => setStatus(`選択テーマ: ${themeSelect.value}`));
  if (aiGenerateBtn) {
    aiGenerateBtn.addEventListener('click', handleAIGenerate);
  }
  if (bgPathInput) {
    bgPathInput.addEventListener('input', handleBackgroundInput);
  }
  if (bgBrowseBtn) {
    bgBrowseBtn.addEventListener('click', handleBrowseBackground);
  }
  if (assetFetchBtn) {
    assetFetchBtn.addEventListener('click', handleFetchAssets);
  }
  if (assetOpenWindowBtn && window.api.openAssetWindow) {
    assetOpenWindowBtn.addEventListener('click', () => {
      window.api.openAssetWindow();
    });
  }
  if (audioGenerateBtn) {
    audioGenerateBtn.addEventListener('click', handleGenerateAudio);
  }
  if (timelineRefreshBtn) {
    timelineRefreshBtn.addEventListener('click', handleTimelineRefresh);
  }
  if (videoGenerateBtn) {
    videoGenerateBtn.addEventListener('click', handleVideoGenerate);
  }
  if (videoOpenBtn) {
    videoOpenBtn.addEventListener('click', handleOpenVideo);
  }
  if (textFontInput) textFontInput.addEventListener('input', handleTextFontChange);
  if (textFontSizeInput) textFontSizeInput.addEventListener('input', handleFontSizeChange);
  if (textFillInput) textFillInput.addEventListener('input', handleFillChange);
  if (textStrokeColorInput) textStrokeColorInput.addEventListener('input', handleStrokeColorChange);
  if (textStrokeWidthInput) textStrokeWidthInput.addEventListener('input', handleStrokeWidthChange);
  if (textPosXInput) textPosXInput.addEventListener('input', (e) => handlePositionChange('x', e.target.value));
  if (textPosYInput) textPosYInput.addEventListener('input', (e) => handlePositionChange('y', e.target.value));
  if (textAnimationInput) textAnimationInput.addEventListener('input', handleAnimationChange);
  if (settingsBtn) settingsBtn.addEventListener('click', openSettingsModal);
  if (settingsCancelBtn) settingsCancelBtn.addEventListener('click', closeSettingsModal);
  if (settingsCloseBtn) settingsCloseBtn.addEventListener('click', closeSettingsModal);
  if (settingsSaveBtn) settingsSaveBtn.addEventListener('click', handleSettingsSave);
  if (settingsModal) settingsModal.addEventListener('click', handleModalClick);
  if (settingsProviderSelect) settingsProviderSelect.addEventListener('change', handleProviderChanged);
  if (settingsBaseUrlInput) settingsBaseUrlInput.addEventListener('input', markDirty);
  if (settingsModelInput) settingsModelInput.addEventListener('input', markDirty);

  renderAssetResults();
  renderTimelineSummary();
  init();

  if (window.api.onAssetSelected) {
    window.api.onAssetSelected((payload) => {
      if (!payload || !payload.path) return;
      if (payload.target === 'section') {
        setSectionBackground(payload.path);
      } else {
        setVideoBackground(payload.path);
      }
    });
  }
})();
