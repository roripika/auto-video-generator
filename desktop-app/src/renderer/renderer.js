(() => {
  const themeSelect = document.getElementById('themeSelect');
  const sectionListEl = document.getElementById('sectionList');
  const sectionFormEl = document.getElementById('sectionForm');
  const yamlPreviewEl = document.getElementById('yamlPreview');
  const yamlEditBtn = document.getElementById('yamlEditBtn');
  const yamlApplyBtn = document.getElementById('yamlApplyBtn');
  const summaryPanelEl = document.getElementById('summaryPanel');
  const aiBriefInput = document.getElementById('aiBriefInput');
  const aiSectionsInput = document.getElementById('aiSectionsInput');
  const aiGenerateBtn = document.getElementById('aiGenerateBtn');
  const trendBriefBtn = document.getElementById('trendBriefBtn');
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
  const bgmFileInput = document.getElementById('bgmFileInput');
  const bgmBrowseBtn = document.getElementById('bgmBrowseBtn');
  const bgmOpenWindowBtn = document.getElementById('bgmOpenWindowBtn');
  const bgmClearBtn = document.getElementById('bgmClearBtn');
  const bgmVolumeInput = document.getElementById('bgmVolumeInput');
  const bgmDuckingInput = document.getElementById('bgmDuckingInput');
  const bgmLicenseInput = document.getElementById('bgmLicenseInput');
  const settingsYoutubeForceInput = document.getElementById('settingsYoutubeForce');
  const audioGenerateBtn = document.getElementById('audioGenerateBtn');
  const audioClearBtn = document.getElementById('audioClearBtn');
  const timelineRefreshBtn = document.getElementById('timelineRefreshBtn');
  const timelineSummaryEl = document.getElementById('timelineSummary');
  const videoGenerateBtn = document.getElementById('videoGenerateBtn');
  const videoOpenBtn = document.getElementById('videoOpenBtn');
  const videoUploadBtn = document.getElementById('videoUploadBtn');
  const videoLogEl = document.getElementById('videoLog');
  const schedulerBtn = document.getElementById('schedulerBtn');
  const clearAudioOnVideo = document.getElementById('clearAudioOnVideo');
  const voiceSpeakerSelect = document.getElementById('voiceSpeakerSelect');
  const voiceSpeakerLabel = document.getElementById('voiceSpeakerLabel');
  const infoButtons = document.querySelectorAll('.info-btn');
  const statusBadge = document.createElement('span');
  statusBadge.className = 'status';
  document.querySelector('.app-header').appendChild(statusBadge);
  const sectionPreviewEl = document.getElementById('sectionPreview');
  const sectionPreviewBgEl = document.getElementById('sectionPreviewBg');
  const sectionPreviewTextsEl = document.getElementById('sectionPreviewTexts');

  const settingsBtn = document.getElementById('settingsBtn');
  let modalProviderConfigs = {};
  let modalActiveProvider = 'openai';
  const saveScriptAsBtn = document.getElementById('saveScriptAsBtn');

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
    yamlEditMode: false,
    voicevoxSpeakers: [
      { id: 88, name: '青山龍星' },
      { id: 3, name: 'ずんだもん(ノーマル)' },
      { id: 1, name: '四国めたん(ノーマル)' },
    ],
  };

  const normalizeLinebreaks = (value = '') =>
    value.replace(/\r\n/g, '\n').replace(/\r/g, '\n').replace(/\\n/g, '\n');

  const summarizeOnScreenText = (value = '') =>
    normalizeLinebreaks(value)
      .split('\n')
      .map((part) => part.trim())
      .filter(Boolean)
      .join(' / ');

  const VOICEVOX_SPEAKERS = [
    { id: 13, name: '青山龍星 (ノーマル)' },
    { id: 3, name: 'ずんだもん(ノーマル)' },
    { id: 1, name: '四国めたん(ノーマル)' },
  ];

  const PREVIEW_BASE_W = 1920;
  const PREVIEW_BASE_H = 1080;
  const TEXT_LAYOUTS = {
    hero_center: {
      id: 'hero_center',
      base_position: { x: 'center', y: 'center-120' },
      line_gap: 28,
      rank_offset: { x: 0, y: 0 },
      body_offset: { x: 0, y: 72 },
      align: 'center',
    },
    hero_middle: {
      id: 'hero_middle',
      base_position: { x: 'center', y: 'center' },
      line_gap: 30,
      rank_offset: { x: 0, y: -20 },
      body_offset: { x: 0, y: 50 },
      align: 'center',
    },
    lower_third: {
      id: 'lower_third',
      base_position: { x: 'center', y: 'bottom-220' },
      line_gap: 24,
      rank_offset: { x: 0, y: 0 },
      body_offset: { x: 0, y: 64 },
      align: 'center',
    },
    side_left: {
      id: 'side_left',
      base_position: { x: 'left+120', y: 'center-40' },
      line_gap: 26,
      rank_offset: { x: 0, y: 0 },
      body_offset: { x: 0, y: 72 },
      align: 'left',
    },
    side_right: {
      id: 'side_right',
      base_position: { x: 'right-120', y: 'center-40' },
      line_gap: 26,
      rank_offset: { x: 0, y: 0 },
      body_offset: { x: 0, y: 72 },
      align: 'right',
    },
  };

  const baseTextStyle = () => {
    const base = state.script?.text_style || {};
    return {
      font: base.font || 'Noto Sans JP',
      fontsize: base.fontsize || 64,
      fill: base.fill || '#FFFFFF',
      strokeColor: base.stroke?.color || '#000000',
      strokeWidth: base.stroke?.width ?? 4,
    };
  };

  const mergeSegmentStylePreview = (base, segStyle = {}) => {
    const merged = { ...base };
    if (segStyle.font) merged.font = segStyle.font;
    if (segStyle.fontsize) merged.fontsize = segStyle.fontsize;
    if (segStyle.fill) merged.fill = segStyle.fill;
    if (segStyle.stroke?.color) merged.strokeColor = segStyle.stroke.color;
    if (segStyle.stroke?.width !== undefined) merged.strokeWidth = segStyle.stroke.width;
    return merged;
  };

  const applyTierPreviewStyle = (style, tier) => {
    const applied = { ...style };
    if (tier === 'emphasis') {
      applied.fontsize = Math.max(applied.fontsize || 0, 96);
      applied.fill = '#FFE65A';
      applied.strokeColor = '#000000';
      applied.strokeWidth = Math.max(applied.strokeWidth || 0, 6);
    } else if (tier === 'connector') {
      applied.fontsize = Math.max(applied.fontsize || 0, 72);
      applied.fill = '#FFFFFF';
      applied.strokeColor = '#000000';
      applied.strokeWidth = Math.max(applied.strokeWidth || 0, 4);
    } else {
      applied.fontsize = Math.max(applied.fontsize || 0, 64);
      applied.fill = '#FFFFFF';
      applied.strokeColor = '#000000';
      applied.strokeWidth = Math.max(applied.strokeWidth || 0, 4);
    }
    return applied;
  };

  const resolvePositionValue = (raw, axis) => {
    if (typeof raw === 'number') return raw;
    const token = String(raw || '').trim().toLowerCase();
    if (!token) return axis === 'x' ? PREVIEW_BASE_W / 2 : PREVIEW_BASE_H / 2;
    const num = Number(token);
    if (!Number.isNaN(num)) return num;
    const anchorMatch = token.match(/^(left|right|top|bottom|center)([+-]\d+)?$/);
    if (anchorMatch) {
      const [, anchor, deltaRaw] = anchorMatch;
      const delta = Number(deltaRaw || 0) || 0;
      const baseMap = {
        left: 0,
        right: axis === 'x' ? PREVIEW_BASE_W : 0,
        top: 0,
        bottom: axis === 'y' ? PREVIEW_BASE_H : 0,
        center: axis === 'x' ? PREVIEW_BASE_W / 2 : PREVIEW_BASE_H / 2,
      };
      return (baseMap[anchor] ?? 0) + delta;
    }
    return axis === 'x' ? PREVIEW_BASE_W / 2 : PREVIEW_BASE_H / 2;
  };

  const approximateTextWidth = (text, fontSize) => {
    const chars = Math.max(1, (text || '').length);
    return chars * fontSize * 0.55;
  };

  const previewBackgroundUrl = (path) => {
    if (!path) return '';
    return path.startsWith('/') ? `file://${path}` : path;
  };

  const fetchYoutubeTrendingTitles = async (apiKey, geo = 'JP', limit = 8) => {
    if (!apiKey) return [];
    const url = `https://www.googleapis.com/youtube/v3/videos?part=snippet&chart=mostPopular&regionCode=${encodeURIComponent(
      geo
    )}&maxResults=${limit}&key=${encodeURIComponent(apiKey)}`;
    try {
      const resp = await fetch(url, { cache: 'no-cache' });
      if (!resp.ok) throw new Error(`status ${resp.status}`);
      const data = await resp.json();
      const seen = new Set();
      const titles = [];
      (data.items || []).forEach((item) => {
        const title = item?.snippet?.title;
        if (title && !seen.has(title)) {
          seen.add(title);
          titles.push(title);
        }
      });
      return titles.slice(0, limit);
    } catch (err) {
      console.warn('Failed to fetch YouTube trending', err);
      return [];
    }
  };

  async function handleTrendBriefGenerate() {
    if (!aiBriefInput) return;
    setStatus('トレンド候補を取得中... (YouTube)');
    const ytKey = state.settings?.youtubeApiKey || '';
    if (!ytKey) {
      setStatus('YouTube API Key を設定してください。');
      return;
    }
    const keywords = await fetchYoutubeTrendingTitles(ytKey, 'JP', 8);
    if (!keywords.length) {
      setStatus('YouTubeのトレンド取得に失敗しました。APIキーやネットワークをご確認ください。');
      return;
    }
    const briefText = [
      '最新のトレンド候補です。伸びそうなテーマを選んで台本を作ってください。',
      `候補: ${keywords.join(' / ')}`,
      'この中から最も視聴者が惹かれるテーマを選び、ランキング形式で構成してください。',
    ].join('\n');
    aiBriefInput.value = briefText;
    setStatus('トレンド候補をブリーフ欄に反映しました。');
  }

  function ensureSegmentStyle(segment) {
    if (!segment.style) segment.style = {};
    return segment.style;
  }

  function cleanupSegmentStyle(segment) {
    if (!segment.style) return;
    if (segment.style.stroke && Object.keys(segment.style.stroke).length === 0) {
      delete segment.style.stroke;
    }
    if (segment.style.position && Object.keys(segment.style.position).length === 0) {
      delete segment.style.position;
    }
    if (Object.keys(segment.style).length === 0) {
      delete segment.style;
    }
  }

  function updateSegmentStyleField(segment, key, rawValue, parser) {
    const value = rawValue === '' ? undefined : parser ? parser(rawValue) : rawValue;
    if (value === undefined || value === null || value === '' || Number.isNaN(value)) {
      if (segment.style) {
        delete segment.style[key];
        cleanupSegmentStyle(segment);
      }
      return;
    }
    ensureSegmentStyle(segment)[key] = value;
  }

  function updateSegmentStrokeField(segment, key, rawValue, parser) {
    const value = rawValue === '' ? undefined : parser ? parser(rawValue) : rawValue;
    if (value === undefined || value === null || value === '' || Number.isNaN(value)) {
      if (segment.style?.stroke) {
        delete segment.style.stroke[key];
        if (Object.keys(segment.style.stroke).length === 0) {
          delete segment.style.stroke;
          cleanupSegmentStyle(segment);
        }
      }
      return;
    }
    const style = ensureSegmentStyle(segment);
    if (!style.stroke) style.stroke = {};
    style.stroke[key] = value;
  }

  function updateSegmentPositionField(segment, axis, rawValue) {
    const trimmed = rawValue.trim();
    if (!trimmed) {
      if (segment.style?.position) {
        delete segment.style.position[axis];
        if (Object.keys(segment.style.position).length === 0) {
          delete segment.style.position;
          cleanupSegmentStyle(segment);
        }
      }
      return;
    }
    const style = ensureSegmentStyle(segment);
    if (!style.position) style.position = {};
    const num = Number(trimmed);
    style.position[axis] = Number.isNaN(num) ? trimmed : num;
  }

  function createLabeledInput(label, type, value, onChange, options = {}) {
    const field = document.createElement('label');
    field.className = 'form-field-inline';
    const title = document.createElement('span');
    title.textContent = label;
    const input = document.createElement('input');
    input.type = type;
    if (options.placeholder) input.placeholder = options.placeholder;
    if (options.step) input.step = options.step;
    if (options.min !== undefined) input.min = options.min;
    if (options.max !== undefined) input.max = options.max;
    if (options.fullWidth) input.style.width = '100%';
    input.value = value ?? '';
    input.addEventListener('input', (event) => onChange(event.target.value));
    field.appendChild(title);
    field.appendChild(input);
    return field;
  }

  function ensureBgmConfig() {
    if (!state.script) return null;
    const defaults = { file: '', volume_db: -10, ducking_db: 0 };
    if (!state.script.bgm) {
      state.script.bgm = { ...defaults, license: '' };
    } else {
      if (typeof state.script.bgm.volume_db !== 'number') {
        state.script.bgm.volume_db = defaults.volume_db;
      }
      if (typeof state.script.bgm.ducking_db !== 'number') {
        state.script.bgm.ducking_db = defaults.ducking_db;
      }
    }
    return state.script.bgm;
  }

  function renderBgmForm() {
    const bgm = state.script?.bgm || null;
    if (bgmFileInput) {
      bgmFileInput.value = bgm?.file || '';
    }
    if (bgmVolumeInput) {
      bgmVolumeInput.value = bgm?.volume_db ?? '';
    }
    if (bgmDuckingInput) {
      bgmDuckingInput.value = bgm?.ducking_db ?? '';
    }
    if (bgmLicenseInput) {
      bgmLicenseInput.value = bgm?.license || '';
    }
    if (bgmClearBtn) {
      bgmClearBtn.disabled = !bgm;
    }
  }

  function handleBgmFileInput(event) {
    if (!state.script) return;
    const value = event.target.value.trim();
    const bgm = ensureBgmConfig();
    if (!bgm) return;
    bgm.file = value;
    renderYaml();
  }

  async function handleBrowseBgm() {
    if (!window.api.chooseBgmFile) return;
    try {
      const result = await window.api.chooseBgmFile();
      if (result && result.path && !result.canceled) {
        const bgm = ensureBgmConfig();
        if (bgm) {
          bgm.file = result.path;
          renderBgmForm();
          renderYaml();
          setStatus(`BGMを ${result.path} に設定しました。`);
        }
      }
    } catch (err) {
      console.error(err);
      setStatus('BGMファイルの選択に失敗しました。');
    }
  }

  function handleClearBgm() {
    if (!state.script) return;
    state.script.bgm = null;
    renderBgmForm();
    renderYaml();
    setStatus('BGM設定をクリアしました。');
  }

  function handleBgmVolumeInput(event) {
    if (!state.script) return;
    const bgm = ensureBgmConfig();
    if (!bgm) return;
    const value = Number(event.target.value);
    bgm.volume_db = Number.isNaN(value) ? -10 : value;
    renderYaml();
  }

  function handleBgmDuckingInput(event) {
    if (!state.script) return;
    const bgm = ensureBgmConfig();
    if (!bgm) return;
    const value = Number(event.target.value);
    bgm.ducking_db = Number.isNaN(value) ? 0 : value;
    renderYaml();
  }

  function handleBgmLicenseInput(event) {
    if (!state.script) return;
    const bgm = ensureBgmConfig();
    if (!bgm) return;
    const value = event.target.value.trim();
    bgm.license = value || null;
    renderYaml();
  }

  function estimateDurationFromText(script) {
    if (!script || !Array.isArray(script.sections)) return 0;
    const pauseSec = (script.voice?.pause_msec || 0) / 1000;
    const sections = script.sections;
    let total = 0;
    sections.forEach((sec, idx) => {
      const text = (sec.narration || sec.on_screen_text || '').trim();
      const length = Math.max(text.length, 1);
      const est = Math.max(5, length / 9);
      total += est;
      if (idx < sections.length - 1) {
        total += pauseSec;
      }
    });
    return total;
  }

  async function init() {
    try {
      await loadSettings();
      await loadVoicevoxSpeakers();
      await loadLatestVideo();
      state.themes = await window.api.listThemes();
      populateThemeSelect();
      if (state.themes.length) {
        themeSelect.value = state.themes[0].id;
        await createScriptFromTheme();
      }
    } catch (err) {
      console.error('Init failed', err);
      setStatus(`初期化に失敗しました: ${err.message || err}`);
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

  async function handleSaveScriptAs() {
    if (!state.script) return;
    const result = await window.api.saveScript({ path: null, script: state.script });
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
      await handleTimelineRefresh();
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
      const result = await window.api.generateVideo({
        script: state.script,
        clearAudio: clearAudioOnVideo?.checked !== false,
      });
      state.videoLog = result.stdout || '';
      videoLogEl.value = state.videoLog;
      state.lastVideoPath = result.outputPath;
      if (videoOpenBtn) {
        videoOpenBtn.disabled = !state.lastVideoPath;
      }
      if (videoUploadBtn) {
        videoUploadBtn.disabled = !state.lastVideoPath;
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
    renderBgmForm();
    renderVoiceSpeaker();
    renderTimelineSummary();
    renderSectionPreview();
    updateVideoButtons();
  }

  function enterYamlEditMode() {
    state.yamlEditMode = true;
    yamlPreviewEl.readOnly = false;
    if (yamlApplyBtn) yamlApplyBtn.disabled = false;
    if (yamlEditBtn) yamlEditBtn.disabled = true;
    yamlPreviewEl.focus();
  }

  function exitYamlEditMode() {
    state.yamlEditMode = false;
    yamlPreviewEl.readOnly = true;
    if (yamlApplyBtn) yamlApplyBtn.disabled = true;
    if (yamlEditBtn) yamlEditBtn.disabled = false;
  }

  function handleYamlApply() {
    try {
      const parsed = window.yaml.parse(yamlPreviewEl.value || '');
      if (parsed && parsed.__error) {
        setStatus(`YAML解析に失敗しました: ${parsed.__error}`);
        return;
      }
      state.script = parsed;
      state.filePath = state.filePath || null;
      state.selectedIndex = 0;
      exitYamlEditMode();
      setStatus('YAMLを適用しました。');
      render();
    } catch (err) {
      console.error(err);
      setStatus(`YAMLの適用に失敗しました: ${err.message || err}`);
    }
  }

  function renderSectionList() {
    sectionListEl.innerHTML = '';
    if (!state.script) return;
    state.script.sections.forEach((section, index) => {
      const li = document.createElement('li');
      const display = summarizeOnScreenText(section.on_screen_text || section.id || '');
      li.textContent = `${index + 1}. ${display || section.id}`;
      if (index === state.selectedIndex) {
        li.classList.add('active');
      }
      li.addEventListener('click', () => {
        state.selectedIndex = index;
        renderSectionForm();
        renderSectionList();
        renderSectionPreview();
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
      const normalizedValue = normalizeLinebreaks(section[key] || '');
      textarea.value = normalizedValue;
      if (section[key] !== normalizedValue) {
        section[key] = normalizedValue;
      }
      textarea.addEventListener('input', (event) => {
        section[key] = normalizeLinebreaks(event.target.value || '');
        renderSectionList();
        renderSummary();
        renderYaml();
        renderSectionPreview();
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
      renderSectionPreview();
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
      renderSectionPreview();
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

    // Segment editor
    if (!Array.isArray(section.on_screen_segments)) {
      section.on_screen_segments = [];
    }
    const segmentsPanel = document.createElement('div');
    segmentsPanel.className = 'segment-list';
    const segmentsHeader = document.createElement('div');
    segmentsHeader.className = 'panel-subtitle';
    segmentsHeader.textContent = 'テロップセグメント（行ごとにフォントや色を調整）';
    const segmentsHint = document.createElement('p');
    segmentsHint.className = 'field-hint';
    segmentsHint.textContent = '空の場合は上記「テロップ」欄の文字がそのまま使われます。';
    segmentsPanel.appendChild(segmentsHeader);
    segmentsPanel.appendChild(segmentsHint);

    section.on_screen_segments.forEach((seg, segIndex) => {
      if (!seg || typeof seg !== 'object') {
        section.on_screen_segments[segIndex] = { text: '', style: {} };
      }
      const segWrapper = document.createElement('div');
      segWrapper.className = 'segment-item';
      const segTitle = document.createElement('div');
      segTitle.textContent = `セグメント ${segIndex + 1}`;
      segTitle.style.fontWeight = '600';
      segWrapper.appendChild(segTitle);

      const segTextarea = document.createElement('textarea');
      segTextarea.value = seg.text || '';
      segTextarea.placeholder = '例: 第1位：\n驚きの○○';
      segTextarea.addEventListener('input', (e) => {
        seg.text = e.target.value;
        renderSectionList();
        renderYaml();
        renderSectionPreview();
      });
      segWrapper.appendChild(segTextarea);

      const styleRow = document.createElement('div');
      styleRow.className = 'segment-style-row';
      styleRow.appendChild(
        createLabeledInput(
          'フォントサイズ',
          'number',
          seg.style?.fontsize ?? '',
          (val) => {
            updateSegmentStyleField(seg, 'fontsize', val, (v) => Number(v));
            renderYaml();
            renderSectionPreview();
          },
          { min: 20, step: 2 }
        )
      );
      styleRow.appendChild(
        createLabeledInput(
          '文字色',
          'text',
          seg.style?.fill ?? '',
          (val) => {
            updateSegmentStyleField(seg, 'fill', val.trim());
            renderYaml();
            renderSectionPreview();
          },
          { placeholder: '#RRGGBB' }
        )
      );
      styleRow.appendChild(
        createLabeledInput(
          '枠線色',
          'text',
          seg.style?.stroke?.color ?? '',
          (val) => {
            updateSegmentStrokeField(seg, 'color', val.trim());
            renderYaml();
            renderSectionPreview();
          },
          { placeholder: '#000000' }
        )
      );
      styleRow.appendChild(
        createLabeledInput(
          '枠線幅',
          'number',
          seg.style?.stroke?.width ?? '',
          (val) => {
            updateSegmentStrokeField(seg, 'width', val, (v) => Number(v));
            renderYaml();
            renderSectionPreview();
          },
          { min: 0, step: 1 }
        )
      );
      styleRow.appendChild(
        createLabeledInput(
          'X 位置',
          'text',
          seg.style?.position?.x ?? '',
          (val) => {
            updateSegmentPositionField(seg, 'x', val);
            renderYaml();
            renderSectionPreview();
          },
          { placeholder: 'center / left+80 / 320' }
        )
      );
      styleRow.appendChild(
        createLabeledInput(
          'Y 位置',
          'text',
          seg.style?.position?.y ?? '',
          (val) => {
            updateSegmentPositionField(seg, 'y', val);
            renderYaml();
            renderSectionPreview();
          },
          { placeholder: 'center / top+120 / 400' }
        )
      );
      segWrapper.appendChild(styleRow);

      const segActions = document.createElement('div');
      segActions.style.display = 'flex';
      segActions.style.justifyContent = 'space-between';
      segActions.style.marginTop = '8px';
      const removeSegBtn = document.createElement('button');
      removeSegBtn.className = 'ghost';
      removeSegBtn.textContent = 'このセグメントを削除';
      removeSegBtn.addEventListener('click', () => {
        section.on_screen_segments.splice(segIndex, 1);
        renderSectionForm();
        renderYaml();
        renderSectionPreview();
      });
      segActions.appendChild(removeSegBtn);
      segWrapper.appendChild(segActions);
      segmentsPanel.appendChild(segWrapper);
    });

    const addSegmentBtn = document.createElement('button');
    addSegmentBtn.className = 'ghost';
    addSegmentBtn.textContent = 'セグメントを追加';
    addSegmentBtn.addEventListener('click', () => {
      const base = state.script?.text_style || {};
      section.on_screen_segments.push({
        text: '',
        style: {
          fontsize: base.fontsize || 60,
          fill: base.fill || '#FFFFFF',
          stroke: { color: base.stroke?.color || '#000000', width: base.stroke?.width ?? 4 },
          position: { ...(base.position || { x: 'center', y: 'center' }) },
        },
      });
      renderSectionForm();
      renderYaml();
      renderSectionPreview();
    });
    segmentsPanel.appendChild(addSegmentBtn);
    sectionFormEl.appendChild(segmentsPanel);

    // Overlay editor
    if (!Array.isArray(section.overlays)) {
      section.overlays = [];
    }
    const overlayPanel = document.createElement('div');
    overlayPanel.className = 'overlay-list';
    const overlayHeader = document.createElement('div');
    overlayHeader.className = 'panel-subtitle';
    overlayHeader.textContent = '前景オーバーレイ（商品写真やアイコンなど）';
    const overlayHint = document.createElement('p');
    overlayHint.className = 'field-hint';
    overlayHint.textContent = '画像ファイルやURLを指定すると背景上に重ねられます。';
    overlayPanel.appendChild(overlayHeader);
    overlayPanel.appendChild(overlayHint);

    section.overlays.forEach((overlay, overlayIndex) => {
      const overlayWrapper = document.createElement('div');
      overlayWrapper.className = 'overlay-item';
      const overlayTitle = document.createElement('div');
      overlayTitle.textContent = `オーバーレイ ${overlayIndex + 1}`;
      overlayTitle.style.fontWeight = '600';
      overlayWrapper.appendChild(overlayTitle);

      const fileField = createLabeledInput(
        'ファイル/URL',
        'text',
        overlay.file || '',
        (val) => {
          overlay.file = val.trim();
          renderYaml();
        },
        { fullWidth: true, placeholder: 'assets/overlay.png または https://...' }
      );
      overlayWrapper.appendChild(fileField);

      const overlayRow = document.createElement('div');
      overlayRow.className = 'overlay-row';
      overlayRow.appendChild(
        createLabeledInput(
          'X 位置',
          'text',
          overlay.position?.x ?? '',
          (val) => {
            const trimmed = val.trim();
            if (!trimmed) {
              if (overlay.position) {
                delete overlay.position.x;
                if (!overlay.position.x && !overlay.position.y) {
                  delete overlay.position;
                }
              }
            } else {
              const num = Number(trimmed);
              if (!overlay.position) overlay.position = {};
              overlay.position.x = Number.isNaN(num) ? trimmed : num;
            }
            renderYaml();
          },
          { placeholder: 'center / right-120 / 400' }
        )
      );
      overlayRow.appendChild(
        createLabeledInput(
          'Y 位置',
          'text',
          overlay.position?.y ?? '',
          (val) => {
            const trimmed = val.trim();
            if (!trimmed) {
              if (overlay.position) {
                delete overlay.position.y;
                if (!overlay.position.x && !overlay.position.y) {
                  delete overlay.position;
                }
              }
            } else {
              const num = Number(trimmed);
              if (!overlay.position) overlay.position = {};
              overlay.position.y = Number.isNaN(num) ? trimmed : num;
            }
            renderYaml();
          },
          { placeholder: 'center / top+80 / 420' }
        )
      );
      overlayRow.appendChild(
        createLabeledInput(
          '縮尺',
          'number',
          overlay.scale ?? '',
          (val) => {
            const num = Number(val);
            if (!val) {
              delete overlay.scale;
            } else if (!Number.isNaN(num)) {
              overlay.scale = num;
            }
            renderYaml();
          },
          { step: 0.1, min: 0.1 }
        )
      );
      overlayRow.appendChild(
        createLabeledInput(
          '不透明度(0-1)',
          'number',
          overlay.opacity ?? '',
          (val) => {
            const num = Number(val);
            if (!val) {
              delete overlay.opacity;
            } else if (!Number.isNaN(num)) {
              overlay.opacity = Math.min(1, Math.max(0, num));
            }
            renderYaml();
          },
          { step: 0.05, min: 0, max: 1 }
        )
      );
      overlayWrapper.appendChild(overlayRow);

      const overlayActions = document.createElement('div');
      overlayActions.style.display = 'flex';
      overlayActions.style.justifyContent = 'space-between';
      overlayActions.style.marginTop = '8px';
      const removeOverlayBtn = document.createElement('button');
      removeOverlayBtn.className = 'ghost';
      removeOverlayBtn.textContent = 'このオーバーレイを削除';
      removeOverlayBtn.addEventListener('click', () => {
        section.overlays.splice(overlayIndex, 1);
        renderSectionForm();
        renderYaml();
      });
      overlayActions.appendChild(removeOverlayBtn);
      overlayWrapper.appendChild(overlayActions);
      overlayPanel.appendChild(overlayWrapper);
    });

    const addOverlayBtn = document.createElement('button');
    addOverlayBtn.className = 'ghost';
    addOverlayBtn.textContent = 'オーバーレイを追加';
    addOverlayBtn.addEventListener('click', () => {
      section.overlays.push({
        file: '',
        position: { x: 'right-120', y: 'center' },
        scale: 0.6,
        opacity: 1,
      });
      renderSectionForm();
      renderYaml();
    });
    overlayPanel.appendChild(addOverlayBtn);
    sectionFormEl.appendChild(overlayPanel);
    renderSectionPreview();
  }

  function renderSectionPreview() {
    if (!sectionPreviewEl || !sectionPreviewTextsEl || !sectionPreviewBgEl) return;
    sectionPreviewTextsEl.innerHTML = '';

    if (!state.script || !state.script.sections.length) {
      sectionPreviewBgEl.style.backgroundImage = 'linear-gradient(135deg, #1c1c24, #0f0f14)';
      return;
    }

    const section = state.script.sections[state.selectedIndex] || state.script.sections[0];
    const layout = TEXT_LAYOUTS[section.text_layout] || TEXT_LAYOUTS.hero_center;
    const basePos = layout.base_position || { x: 'center', y: 'center-120' };
    const rankOffset = layout.rank_offset || { x: 0, y: 0 };
    const bodyOffset = layout.body_offset || { x: 0, y: 0 };
    const lineGap = layout.line_gap ?? 24;
    const align = layout.align || 'center';
    const rect = sectionPreviewEl.getBoundingClientRect();
    const scale = rect.width ? rect.width / PREVIEW_BASE_W : 0.5;

    const bgPath = section.bg || state.script.video?.bg || '';
    if (bgPath) {
      sectionPreviewBgEl.style.backgroundImage = `url('${previewBackgroundUrl(bgPath)}')`;
      sectionPreviewBgEl.style.opacity = 0.85;
    } else {
      sectionPreviewBgEl.style.backgroundImage = 'linear-gradient(135deg, #1c1c24, #0f0f14)';
      sectionPreviewBgEl.style.opacity = 1;
    }

    const baseStyleVal = baseTextStyle();
    const lines = [];

    if (Array.isArray(section.on_screen_segments) && section.on_screen_segments.length) {
      section.on_screen_segments.forEach((seg, segIdx) => {
        const tier = segIdx === 0 ? 'emphasis' : 'body';
        const merged = applyTierPreviewStyle(mergeSegmentStylePreview(baseStyleVal, seg.style), tier);
        const offset = segIdx === 0 ? rankOffset : bodyOffset;
        normalizeLinebreaks(seg.text || '')
          .split('\n')
          .filter((l) => l.trim())
          .forEach((textLine) => {
            lines.push({ text: textLine, style: merged, offset, tier });
          });
      });
    } else {
      const merged = applyTierPreviewStyle(baseStyleVal, 'body');
      normalizeLinebreaks(section.on_screen_text || '')
        .split('\n')
        .filter((l) => l.trim())
        .forEach((textLine, idx) => {
          const tier = idx === 0 ? 'emphasis' : 'body';
          const offset = idx === 0 ? rankOffset : bodyOffset;
          lines.push({ text: textLine, style: applyTierPreviewStyle(merged, tier), offset, tier });
        });
    }

    let yCursor = 0;
    const baseX = resolvePositionValue(basePos.x, 'x');
    const baseY = resolvePositionValue(basePos.y, 'y');

    lines.forEach((line, idx) => {
      const fontSize = line.style.fontsize || 64;
      const textWidth = approximateTextWidth(line.text, fontSize);
      const offX = Number(line.offset?.x || 0);
      const offY = Number(line.offset?.y || 0);
      let xPos = baseX + offX;
      if (align === 'left') {
        xPos = 60 + offX;
      } else if (align === 'right') {
        xPos = PREVIEW_BASE_W - textWidth - 60 - offX;
      } else {
        xPos = baseX + offX - textWidth / 2;
      }
      const yPos = baseY + offY + yCursor;

      const el = document.createElement('div');
      el.className = `section-preview__textline section-preview__textline--${line.tier || 'body'}`;
      el.textContent = line.text;
      el.style.left = `${xPos * scale}px`;
      el.style.top = `${yPos * scale}px`;
      el.style.fontSize = `${fontSize * scale}px`;
      el.style.color = line.style.fill || '#FFFFFF';
      el.style.webkitTextStroke = `${(line.style.strokeWidth || 0) * scale}px ${line.style.strokeColor || '#000000'}`;
      sectionPreviewTextsEl.appendChild(el);

      yCursor += fontSize + lineGap;
    });
  }

  function renderSummary() {
    if (!state.script) {
      summaryPanelEl.textContent = 'スクリプト未読込。';
      return;
    }
    const sectionCount = state.script.sections.length;
    const estimatedDuration = estimateDurationFromText(state.script);
    summaryPanelEl.innerHTML = `
      <div><strong>タイトル:</strong> ${state.script.title}</div>
      <div><strong>ファイル:</strong> ${state.filePath || '未保存'}</div>
      <div><strong>セクション数:</strong> ${sectionCount}</div>
      <div><strong>推定尺(文字ベース):</strong> 約 ${estimatedDuration.toFixed(1)} 秒</div>
      <div><strong>CTA:</strong> ${state.script.sections[0]?.cta || ''}</div>
    `;
  }

  function renderYaml() {
    if (!state.script) {
      yamlPreviewEl.value = '';
      return;
    }
    yamlPreviewEl.value = window.yaml.stringify(state.script);
    yamlPreviewEl.readOnly = !state.yamlEditMode;
    if (yamlApplyBtn) yamlApplyBtn.disabled = !state.yamlEditMode;
    if (yamlEditBtn) yamlEditBtn.disabled = state.yamlEditMode;
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
      on_screen_segments: [],
      overlays: [],
    });
    state.selectedIndex = state.script.sections.length - 1;
    render();
  }

  function renderAssetResults() {
    // メインウインドウでは検索リストを表示しない（別ウインドウへ移行）
    if (!assetResultList) return;
    assetResultList.innerHTML = '';
  }

  function renderVoiceSpeaker() {
    if (!voiceSpeakerSelect) return;
    voiceSpeakerSelect.innerHTML = '';
    state.voicevoxSpeakers.forEach((sp) => {
      const opt = document.createElement('option');
      opt.value = String(sp.id);
      opt.textContent = `${sp.name} (id:${sp.id})`;
      voiceSpeakerSelect.appendChild(opt);
    });
    const speakerId = state.script?.voice?.speaker_id ?? '';
    voiceSpeakerSelect.value = String(speakerId);
    const found = state.voicevoxSpeakers.find((s) => String(s.id) === String(speakerId));
    if (voiceSpeakerLabel) {
      voiceSpeakerLabel.textContent = found ? `現在: ${found.name} (id:${found.id})` : `id: ${speakerId || '未設定'}`;
    }
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
    bindExternalLinks();
  }

  async function loadVoicevoxSpeakers() {
    const endpoint = 'http://localhost:50021';
    try {
      const res = await fetch(`${endpoint.replace(/\/$/, '')}/speakers`);
      const data = await res.json();
      const flattened = [];
      data.forEach((sp) => {
        (sp.styles || []).forEach((style) => {
          flattened.push({ id: style.id, name: `${sp.name} (${style.name})` });
        });
      });
      if (flattened.length) {
        state.voicevoxSpeakers = flattened;
        renderVoiceSpeaker();
        setStatus('VOICEVOX 話者リストを更新しました。');
      }
    } catch (err) {
      console.warn('Failed to fetch VOICEVOX speakers; using defaults.', err);
    }
  }

  async function loadLatestVideo() {
    try {
      const result = await window.api.getLatestVideo();
      if (result && result.path) {
        state.lastVideoPath = result.path;
        if (videoOpenBtn) {
          videoOpenBtn.disabled = false;
        }
      }
    } catch (err) {
      console.error('Failed to load latest video', err);
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

  function cloneProviderConfigs(source) {
    return JSON.parse(JSON.stringify(source || {}));
  }

  function ensureModalProviderConfig(providerKey) {
    if (!modalProviderConfigs[providerKey]) {
      modalProviderConfigs[providerKey] = {
        apiKey: '',
        baseUrl: PROVIDER_PRESETS[providerKey]?.baseUrl || '',
        model: PROVIDER_PRESETS[providerKey]?.model || '',
      };
    }
    return modalProviderConfigs[providerKey];
  }

  function applyProviderFields(providerKey) {
    const config = ensureModalProviderConfig(providerKey);
    settingsApiKeyInput.value = config.apiKey || '';
    settingsBaseUrlInput.value = config.baseUrl || PROVIDER_PRESETS[providerKey]?.baseUrl || '';
    settingsModelInput.value = config.model || PROVIDER_PRESETS[providerKey]?.model || '';
  }

  function persistCurrentProviderFields() {
    const config = ensureModalProviderConfig(modalActiveProvider);
    config.apiKey = settingsApiKeyInput.value.trim();
    config.baseUrl = settingsBaseUrlInput.value.trim() || config.baseUrl;
    config.model = settingsModelInput.value.trim() || config.model;
  }

  function openSettingsModal() {
    populateProviderOptions();
    const settings = state.settings || {};
    modalProviderConfigs = cloneProviderConfigs(settings.providers);
    modalActiveProvider =
      settings.activeProvider && PROVIDER_PRESETS[settings.activeProvider]
        ? settings.activeProvider
        : 'openai';
    settingsProviderSelect.value = modalActiveProvider;
    applyProviderFields(modalActiveProvider);
    if (settingsProviderOrder) settingsProviderOrder.value = settings.assetProviderOrder || 'pexels,pixabay';
    if (settingsMaxResults) settingsMaxResults.value = settings.assetMaxResults || 5;
    if (settingsPexelsKeyInput) settingsPexelsKeyInput.value = settings.pexelsApiKey || '';
    if (settingsPixabayKeyInput) settingsPixabayKeyInput.value = settings.pixabayApiKey || '';
    if (settingsStabilityKeyInput) settingsStabilityKeyInput.value = settings.stabilityApiKey || '';
    if (settingsYoutubeKeyInput) settingsYoutubeKeyInput.value = settings.youtubeApiKey || '';
    if (settingsBgmDirInput) settingsBgmDirInput.value = settings.bgmDirectory || 'assets/bgm';
    if (settingsYoutubeForceInput) settingsYoutubeForceInput.value = settings.youtubeForceVideo || '';
    updateProviderHint();
    settingsModal.classList.remove('hidden');
  }

  function closeSettingsModal() {
    settingsModal.classList.add('hidden');
  }

  function handleProviderChanged() {
    persistCurrentProviderFields();
    const nextKey = settingsProviderSelect.value;
    if (!PROVIDER_PRESETS[nextKey]) {
      return;
    }
    modalActiveProvider = nextKey;
    applyProviderFields(modalActiveProvider);
    updateProviderHint();
  }

  async function handleSettingsSave() {
    persistCurrentProviderFields();
    const payload = {
      activeProvider: modalActiveProvider,
      providers: modalProviderConfigs,
      assetProviderOrder: settingsProviderOrder?.value || 'pexels,pixabay',
      assetMaxResults: Number(settingsMaxResults?.value) || 5,
      pexelsApiKey: settingsPexelsKeyInput?.value?.trim() || '',
      pixabayApiKey: settingsPixabayKeyInput?.value?.trim() || '',
      stabilityApiKey: settingsStabilityKeyInput?.value?.trim() || '',
      youtubeApiKey: settingsYoutubeKeyInput?.value?.trim() || '',
      bgmDirectory: settingsBgmDirInput?.value?.trim() || '',
      youtubeForceVideo: settingsYoutubeForceInput?.value?.trim() || '',
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
  if (saveScriptAsBtn) {
    saveScriptAsBtn.addEventListener('click', handleSaveScriptAs);
  }
  document.getElementById('addSectionBtn').addEventListener('click', addSection);
  themeSelect.addEventListener('change', () => setStatus(`選択テーマ: ${themeSelect.value}`));
  if (aiGenerateBtn) {
    aiGenerateBtn.addEventListener('click', handleAIGenerate);
  }
  if (trendBriefBtn) {
    trendBriefBtn.addEventListener('click', () => {
      window.api.openTrendWindow();
    });
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
  if (audioClearBtn && window.api.clearAudioCache) {
    audioClearBtn.addEventListener('click', async () => {
      try {
        audioClearBtn.disabled = true;
        audioClearBtn.textContent = '削除中...';
        await window.api.clearAudioCache();
        setStatus('音声キャッシュを削除しました。');
        renderTimelineSummary();
      } catch (err) {
        console.error(err);
        setStatus('音声キャッシュの削除に失敗しました。');
      } finally {
        audioClearBtn.disabled = false;
        audioClearBtn.textContent = '音声キャッシュ削除';
      }
    });
  }
  if (voiceSpeakerSelect) {
    voiceSpeakerSelect.addEventListener('change', (e) => {
      if (!state.script) return;
      const val = Number(e.target.value);
      if (!state.script.voice) {
        state.script.voice = { engine: 'voicevox', speaker_id: val };
      } else {
        state.script.voice.engine = 'voicevox';
        state.script.voice.speaker_id = val;
      }
      renderVoiceSpeaker();
      renderYaml();
      setStatus(`話者を id:${val} に変更しました。`);
    });
  }
  if (window.api?.onTrendSelected) {
    window.api.onTrendSelected((payload) => {
      const kws = payload?.keywords || (payload?.keyword ? [payload.keyword] : []);
      if (!kws.length || !aiBriefInput) return;
      // テーマをフリーテーマに自動切り替え（存在する場合）
      if (themeSelect && state.themes?.length) {
        const free = state.themes.find((t) => t.id === 'freeform_prompt');
        if (free) {
          themeSelect.value = free.id;
          createScriptFromTheme();
        }
      }
      const lines = [
        `キーワード候補: ${kws.join(' / ')}`,
        'これらの中で重複・類似をまとめ、最も良い切り口を選んで構成してください。',
        '形式はランキング/解説/暴露など最適なものをAIが判断してください。',
        'イントロでフック→本編複数セクション→アウトロ/CTAの流れで。中間セクション数は内容に合わせて決めてください。',
        '視聴者が惹きつけられる切り口と、信頼性のある根拠を入れてください。',
      ];
      aiBriefInput.value = lines.join('\n');
      setStatus(`トレンド候補をブリーフに反映しました (${kws.length}件)。`);
    });
  }
  function updateVideoButtons() {
    if (videoUploadBtn) {
      videoUploadBtn.disabled = !state.lastVideoPath;
    }
    if (videoOpenBtn) {
      videoOpenBtn.disabled = !state.lastVideoPath;
    }
  }

  async function handleVideoUpload() {
    if (!state.lastVideoPath) {
      setStatus('先に動画を生成してください。');
      return;
    }
    videoUploadBtn.disabled = true;
    setStatus('YouTubeにアップロード中...');
    try {
      const uploadPrep = state.script?.upload_prep || {};
      const title =
        (typeof uploadPrep.title === 'string' && uploadPrep.title.trim()) ||
        state.script?.title ||
        '自動生成動画';
      const desc =
        (typeof uploadPrep.desc === 'string' && uploadPrep.desc.trim()) ||
        state.script?.output?.description ||
        '';
      const tags =
        Array.isArray(uploadPrep.tags) && uploadPrep.tags.length
          ? uploadPrep.tags
          : state.script?.output?.tags || [];
      const resp = await window.api.uploadVideo({
        path: state.lastVideoPath,
        title,
        description: desc,
        tags,
      });
      setStatus('YouTubeへのアップロードを開始しました。ターミナル出力を確認してください。');
      if (resp?.stdout && videoLogEl) {
        videoLogEl.value = `${resp.stdout}\n${videoLogEl.value || ''}`;
      }
    } catch (err) {
      console.error(err);
      setStatus(`アップロードに失敗しました: ${err.message || err}`);
    } finally {
      videoUploadBtn.disabled = false;
    }
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
  if (videoUploadBtn) {
    videoUploadBtn.addEventListener('click', handleVideoUpload);
  }
  if (schedulerBtn) {
    schedulerBtn.addEventListener('click', () => window.api.openSchedulerWindow());
  }
  if (textFontInput) textFontInput.addEventListener('input', handleTextFontChange);
  if (textFontSizeInput) textFontSizeInput.addEventListener('input', handleFontSizeChange);
  if (textFillInput) textFillInput.addEventListener('input', handleFillChange);
  if (textStrokeColorInput) textStrokeColorInput.addEventListener('input', handleStrokeColorChange);
  if (textStrokeWidthInput) textStrokeWidthInput.addEventListener('input', handleStrokeWidthChange);
  if (textPosXInput) textPosXInput.addEventListener('input', (e) => handlePositionChange('x', e.target.value));
  if (textPosYInput) textPosYInput.addEventListener('input', (e) => handlePositionChange('y', e.target.value));
  if (textAnimationInput) textAnimationInput.addEventListener('input', handleAnimationChange);
  if (bgmFileInput) bgmFileInput.addEventListener('input', handleBgmFileInput);
  if (bgmBrowseBtn) bgmBrowseBtn.addEventListener('click', handleBrowseBgm);
  if (bgmOpenWindowBtn && window.api.openBgmWindow) {
    bgmOpenWindowBtn.addEventListener('click', async () => {
      try {
        await window.api.openBgmWindow();
      } catch (err) {
        console.error('Failed to open BGM library window', err);
        setStatus('BGMライブラリを開けませんでした。');
      }
    });
  }
  if (bgmClearBtn) bgmClearBtn.addEventListener('click', handleClearBgm);
  if (bgmVolumeInput) bgmVolumeInput.addEventListener('input', handleBgmVolumeInput);
  if (bgmDuckingInput) bgmDuckingInput.addEventListener('input', handleBgmDuckingInput);
  if (bgmLicenseInput) bgmLicenseInput.addEventListener('input', handleBgmLicenseInput);
  if (settingsBtn && window.api.openSettingsWindow) {
    settingsBtn.addEventListener('click', async () => {
      try {
        await window.api.openSettingsWindow();
      } catch (err) {
        console.error('Failed to open settings window', err);
        setStatus('設定ウインドウの起動に失敗しました。');
      }
    });
  }
  if (yamlEditBtn) yamlEditBtn.addEventListener('click', enterYamlEditMode);
  if (yamlApplyBtn) yamlApplyBtn.addEventListener('click', handleYamlApply);
  if (infoButtons && infoButtons.length) {
    infoButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const key = btn.dataset.info;
        const messages = {
          brief: 'AI台本生成: ブリーフとセクション数を入力し、テーマを選んで「AIで生成」を押すと YAML 台本を生成します。生成後は必要に応じて編集してから保存してください。',
          assets: '背景素材: 背景ファイルを指定するか、「別ウインドウで検索」で Pexels/Pixabay/AI から素材を取得できます。結果から全体またはセクションごとに適用可能です。',
          textstyle: 'テキストスタイル: フォント、サイズ、色、縁取り、位置、アニメーションを設定し、テロップ表示に反映します。YAMLにも保存されます。',
          bgm: 'BGM設定: ローカル音源やURLを指定し、音量(dB)とナレーション時のducking量、ライセンス表記メモを入力すると、生成される動画に自動で合成されます。',
        };
        const msg = messages[key] || 'この機能の説明は準備中です。';
        setStatus(msg);
        alert(msg);
      });
    });
  }

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
  if (window.api.onBgmSelected) {
    window.api.onBgmSelected((payload) => {
      if (!payload || !payload.path) return;
      const bgm = ensureBgmConfig();
      if (!bgm) return;
      bgm.file = payload.path;
      renderBgmForm();
      renderYaml();
      setStatus(`BGMを ${payload.displayName || payload.path} に設定しました。`);
    });
  }
})();
  function bindExternalLinks(root = document) {
    root.querySelectorAll('[data-external-link="true"]').forEach((link) => {
      if (link.dataset.boundExternal === 'true') return;
      link.dataset.boundExternal = 'true';
      link.addEventListener('click', (event) => {
        event.preventDefault();
        const href = link.getAttribute('href');
        if (href && window.api?.openExternalLink) {
          window.api.openExternalLink(href);
        }
      });
    });
  }
