const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const YAML = require('yaml');
const { spawn } = require('child_process');

const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const THEMES_DIR = path.join(PROJECT_ROOT, 'configs', 'themes');
const SETTINGS_DIR = path.join(PROJECT_ROOT, 'settings');
const SETTINGS_FILE = path.join(SETTINGS_DIR, 'ai_settings.json');
const PROVIDER_PRESETS = {
  openai: {
    label: 'OpenAI',
    baseUrl: 'https://api.openai.com/v1',
    model: 'gpt-4o-mini',
  },
  anthropic: {
    label: 'Anthropic Claude',
    baseUrl: 'https://api.anthropic.com/v1/messages',
    model: 'claude-3-sonnet-20240229',
  },
  gemini: {
    label: 'Google Gemini',
    baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
    model: 'gemini-2.5-flash',
  },
};
const PROVIDER_KEYS = Object.keys(PROVIDER_PRESETS);

function cloneProviderDefaults() {
  const defaults = {};
  PROVIDER_KEYS.forEach((key) => {
    defaults[key] = {
      apiKey: '',
      baseUrl: PROVIDER_PRESETS[key].baseUrl,
      model: PROVIDER_PRESETS[key].model,
    };
  });
  return defaults;
}

const DEFAULT_AI_SETTINGS = {
  activeProvider: 'openai',
  providers: cloneProviderDefaults(),
  pexelsApiKey: '',
  pixabayApiKey: '',
  stabilityApiKey: '',
  youtubeApiKey: '',
  bgmDirectory: 'assets/bgm',
  assetProviderOrder: 'pexels,pixabay',
  assetMaxResults: 5,
};
const PYTHON_BIN = process.env.PYTHON_BIN || 'python3';
const FETCH_ASSETS_SCRIPT = path.join(PROJECT_ROOT, 'scripts', 'fetch_assets.py');
const GENERATE_AUDIO_SCRIPT = path.join(PROJECT_ROOT, 'scripts', 'generate_audio.py');
const DESCRIBE_TIMELINE_SCRIPT = path.join(PROJECT_ROOT, 'scripts', 'describe_timeline.py');
const GENERATE_VIDEO_SCRIPT = path.join(PROJECT_ROOT, 'scripts', 'generate_video.py');
const TMP_DIR = path.join(PROJECT_ROOT, 'tmp');
const UI_SCRIPT_PATH = path.join(TMP_DIR, 'ui_script.yaml');
const AUDIO_CACHE_DIR = path.join(PROJECT_ROOT, 'work', 'audio');
const OUTPUTS_DIR = path.join(PROJECT_ROOT, 'outputs', 'rendered');

let currentSettings = loadAISettings();
let mainWindowRef = null;
let assetWindow = null;
let settingsWindow = null;

function suggestScriptFilename(script) {
  const raw =
    (script && typeof script.title === 'string' && script.title) ||
    (script && typeof script.project === 'string' && script.project) ||
    'script';
  const sanitized = raw
    .trim()
    .replace(/\s+/g, '_')
    .replace(/[\\/:*?"<>|]/g, '_')
    .slice(0, 80);
  return sanitized || 'script';
}

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 1100,
    minHeight: 720,
    title: 'Auto Video Script Editor',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindowRef = mainWindow;

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
}

app.whenReady().then(() => {
  registerHandlers();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

function registerHandlers() {
  ipcMain.handle('asset-window:open', () => {
    if (assetWindow && !assetWindow.isDestroyed()) {
      assetWindow.focus();
      return { ok: true };
    }
    assetWindow = new BrowserWindow({
      width: 900,
      height: 700,
      title: '背景素材検索',
      parent: mainWindowRef || undefined,
      webPreferences: {
        preload: path.join(__dirname, 'preload_assets.js'),
        contextIsolation: true,
        nodeIntegration: false,
      },
    });
    assetWindow.on('closed', () => {
      assetWindow = null;
    });
    assetWindow.loadFile(path.join(__dirname, 'renderer', 'assets.html'));
    return { ok: true };
  });

  ipcMain.on('asset-window:apply-bg', (_event, payload) => {
    if (mainWindowRef && !mainWindowRef.isDestroyed()) {
      mainWindowRef.webContents.send('asset:selected', payload);
    }
  });

  ipcMain.handle('themes:list', () => listThemes());
  ipcMain.handle('scripts:new', (event, args) => {
    const theme = listThemes().find((t) => t.id === args?.themeId);
    return buildDefaultScript(theme);
  });

  ipcMain.handle('scripts:open', async () => {
    const result = await dialog.showOpenDialog({
      title: 'スクリプト YAML を開く',
      filters: [{ name: 'YAML', extensions: ['yaml', 'yml'] }],
      properties: ['openFile'],
    });
    if (result.canceled || !result.filePaths.length) {
      return { canceled: true };
    }
    const filePath = result.filePaths[0];
    const raw = fs.readFileSync(filePath, 'utf-8');
    const script = YAML.parse(raw);
    return { canceled: false, path: filePath, script };
  });

  ipcMain.handle('scripts:save', async (event, payload) => {
    let targetPath = payload?.path;
    if (!targetPath) {
      const result = await dialog.showSaveDialog({
        title: 'スクリプト YAML を保存',
        filters: [{ name: 'YAML', extensions: ['yaml'] }],
        defaultPath: path.join(
          PROJECT_ROOT,
          'scripts',
          `${suggestScriptFilename(payload?.script)}.yaml`
        ),
      });
      if (result.canceled || !result.filePath) {
        return { canceled: true };
      }
      targetPath = result.filePath;
    }
    const yamlText = YAML.stringify(payload.script);
    fs.writeFileSync(targetPath, yamlText, 'utf-8');
    return { canceled: false, path: targetPath };
  });

  ipcMain.handle('themes:get-default', (event, args) => {
    const theme = listThemes().find((t) => t.id === args?.themeId);
    return buildDefaultScript(theme);
  });

  ipcMain.handle('settings:load', () => loadAISettings());
  ipcMain.handle('settings:save', (event, payload) => {
    const sanitized = sanitizeSettings(payload);
    currentSettings = saveAISettings(sanitized);
    return currentSettings;
  });
  ipcMain.handle('scripts:generate-from-brief', async (event, payload) => {
    const { brief, themeId, sections } = payload || {};
    if (!brief || !brief.trim()) {
      throw new Error('ブリーフが入力されていません。');
    }
    const normalizedSections = Number(sections) || 5;
    const script = await generateScriptFromBrief({
      brief,
      themeId,
      sections: normalizedSections,
    });
    return script;
  });
  ipcMain.handle('assets:fetch', async (event, payload) => {
    const { keyword, kind, maxResults, allowAI } = payload || {};
    if (!keyword || !keyword.trim()) {
      throw new Error('キーワードを入力してください。');
    }
    const providerOrder =
      (payload && payload.providerOrder) ||
      currentSettings.assetProviderOrder ||
      DEFAULT_AI_SETTINGS.assetProviderOrder;
    const maxFetch =
      (payload && payload.maxResults) ||
      currentSettings.assetMaxResults ||
      DEFAULT_AI_SETTINGS.assetMaxResults;
    const args = [
      FETCH_ASSETS_SCRIPT,
      '--keyword',
      keyword,
      '--kind',
      kind || 'video',
      '--max-results',
      String(maxFetch),
      '--json',
      '--log-level',
      'WARNING',
    ];
    if (providerOrder) {
      args.push('--provider-order', providerOrder);
    }
    if (allowAI === false) {
      args.push('--disable-ai');
    }
    return runPythonJson(args, '背景素材の取得に失敗しました。');
  });
  ipcMain.handle('background:choose-file', async () => {
    const result = await dialog.showOpenDialog({
      title: '背景素材を選択',
      properties: ['openFile'],
      filters: [
        { name: 'Video', extensions: ['mp4', 'mov', 'm4v'] },
        { name: 'Image', extensions: ['jpg', 'jpeg', 'png', 'bmp'] },
        { name: 'All files', extensions: ['*'] },
      ],
    });
    if (result.canceled || !result.filePaths.length) {
      return { canceled: true };
    }
    return { canceled: false, path: result.filePaths[0] };
  });
  ipcMain.handle('bgm:choose-file', async () => {
    const result = await dialog.showOpenDialog({
      title: 'BGM ファイルを選択',
      properties: ['openFile'],
      filters: [
        { name: 'Audio', extensions: ['mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg'] },
        { name: 'All files', extensions: ['*'] },
      ],
    });
    if (result.canceled || !result.filePaths.length) {
      return { canceled: true };
    }
    return { canceled: false, path: result.filePaths[0] };
  });
  ipcMain.handle('audio:generate', async (event, payload) => {
    const script = payload?.script;
    if (!script) {
      throw new Error('Script data is required for audio generation.');
    }
    const scriptPath = saveTempScript(script);
    const args = [GENERATE_AUDIO_SCRIPT, '--script', scriptPath];
    if (payload?.configPath) {
      args.push('--config', payload.configPath);
    }
    return runPythonText(args, '音声生成に失敗しました。');
  });
  ipcMain.handle('timeline:describe', async (event, payload) => {
    const script = payload?.script;
    if (!script) {
      throw new Error('Script data is required for timeline.');
    }
    const scriptPath = saveTempScript(script);
    const args = [DESCRIBE_TIMELINE_SCRIPT, '--script', scriptPath, '--json'];
    if (payload?.configPath) {
      args.push('--config', payload.configPath);
    }
    return runPythonJson(args, 'タイムライン計算に失敗しました。');
  });
  ipcMain.handle('video:generate', async (event, payload) => {
    const script = payload?.script;
    if (!script) {
      throw new Error('Script data is required for video generation.');
    }
    const scriptPath = saveTempScript(script);
    const args = [GENERATE_VIDEO_SCRIPT, '--script', scriptPath];
    if (payload?.configPath) {
      args.push('--config', payload.configPath);
    }
    if (payload?.skipAudio) args.push('--skip-audio');
    if (payload?.forceAudio) args.push('--force-audio');
    const result = await runPythonText(args, '動画生成に失敗しました。');
    const outputDir = payload?.outputDir || OUTPUTS_DIR;
    const filename = script?.output?.filename || 'output.mp4';
    return { ...result, outputPath: path.join(outputDir, filename) };
  });

  ipcMain.handle('audio:clear', async () => {
    try {
      fs.rmSync(AUDIO_CACHE_DIR, { recursive: true, force: true });
      fs.mkdirSync(AUDIO_CACHE_DIR, { recursive: true });
      return { ok: true };
    } catch (err) {
      console.error('Failed to clear audio cache', err);
      throw new Error('音声キャッシュの削除に失敗しました。');
    }
  });

  ipcMain.handle('video:get-latest', async () => {
    try {
      if (!fs.existsSync(OUTPUTS_DIR)) {
        return { path: null };
      }
      const files = fs
        .readdirSync(OUTPUTS_DIR)
        .filter((f) => f.toLowerCase().endsWith('.mp4'))
        .map((f) => path.join(OUTPUTS_DIR, f));
      if (!files.length) return { path: null };
      files.sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
      return { path: files[0] };
    } catch (err) {
      console.error('Failed to get latest video', err);
      return { path: null };
    }
  });
  ipcMain.handle('video:open-output', async (event, payload) => {
    const target = payload?.path;
    if (!target) throw new Error('path is required');
    await shell.openPath(target);
    return { ok: true };
  });
  ipcMain.handle('external:open', async (_event, url) => {
    if (typeof url !== 'string' || !url.trim()) {
      return { ok: false };
    }
    await shell.openExternal(url);
    return { ok: true };
  });

  ipcMain.on('yaml:stringify', (event, payload) => {
    try {
      event.returnValue = YAML.stringify(payload || {});
    } catch (err) {
      console.error('Failed to stringify YAML', err);
      event.returnValue = '';
    }
  });

  ipcMain.on('yaml:parse', (event, payload) => {
    try {
      const parsed = YAML.parse(payload || '');
      event.returnValue = parsed;
    } catch (err) {
      console.error('Failed to parse YAML', err);
      event.returnValue = { __error: err.message || String(err) };
    }
  });
}

function listThemes() {
  if (!fs.existsSync(THEMES_DIR)) {
    return [];
  }
  const files = fs.readdirSync(THEMES_DIR).filter((file) => file.endsWith('.yaml'));
  return files
    .map((file) => {
      try {
        const data = YAML.parse(fs.readFileSync(path.join(THEMES_DIR, file), 'utf-8'));
        return {
          id: data.id,
          label: data.label,
          genre: data.genre,
          thumbnail_keywords: data.thumbnail_keywords || [],
          ranking: data.ranking || {},
          cta: data.cta || {},
          raw: data,
        };
      } catch (error) {
        console.error('Failed to load theme', file, error);
        return null;
      }
    })
    .filter(Boolean);
}

function buildDefaultScript(theme) {
  const now = new Date();
  const fallbackTheme =
    theme || {
      id: 'generic',
      label: '汎用スクリプト',
      genre: 'general',
      thumbnail_keywords: [],
      ranking: { default_items: 5 },
      cta: { primary: '感想はコメントへ！', secondary: '' },
    };

  const sectionCount = fallbackTheme.ranking?.default_items || 5;
  const sections = Array.from({ length: sectionCount }, (_, index) => {
    const rank = index + 1;
    return {
      id: `rank-${rank}`,
      on_screen_text: `第${rank}位：ここにタイトル`,
      narration: `第${rank}位の詳細ナレーションを入力してください。`,
      hook: fallbackTheme.thumbnail_keywords?.[0] || '驚きポイント',
      evidence: '根拠となるデータや引用を記述',
      demo: '実践方法や具体例を記述',
      bridge: '次の順位へのブリッジ文',
      cta: fallbackTheme.cta?.primary,
    };
  });

  return {
    project: `${fallbackTheme.id}-${now.getTime()}`,
    title: `${fallbackTheme.label} ${now.toLocaleDateString('ja-JP')}`,
    locale: 'ja-JP',
    video: { width: 1920, height: 1080, fps: 30, bg: 'assets/cache/default.mp4', bg_fit: 'cover' },
    voice: {
      engine: 'voicevox',
      speaker_id: 13, // 青山龍星ノーマル
      speedScale: 1.02,
      pitchScale: 0.0,
      intonationScale: 1.1,
      volumeScale: 1.0,
      pause_msec: 150,
    },
    text_style: {
      font: 'Noto Sans JP',
      fontsize: 60,
      fill: '#FFFFFF',
      stroke: { color: '#000000', width: 4 },
      position: { x: 'center', y: 'bottom-180' },
      max_chars_per_line: 22,
      lines: 3,
    },
    sections,
    output: {
      filename: `${fallbackTheme.id}.mp4`,
      srt: true,
      thumbnail_time_sec: 1.2,
    },
    upload_prep: {
      title: `${fallbackTheme.label} ベスト${sectionCount}`,
      tags: [fallbackTheme.genre, 'ランキング', 'ライフハック'],
      desc: `作成日: ${now.toLocaleDateString('ja-JP')}\n${fallbackTheme.cta?.primary || ''}`,
    },
  };
}

function sanitizeProviderConfigs(rawProviders, legacy = {}) {
  const configs = cloneProviderDefaults();
  PROVIDER_KEYS.forEach((key) => {
    const source = rawProviders && rawProviders[key];
    if (source) {
      if (typeof source.apiKey === 'string') {
        configs[key].apiKey = source.apiKey;
      }
      if (typeof source.baseUrl === 'string' && source.baseUrl.trim()) {
        configs[key].baseUrl = source.baseUrl.trim();
      }
      if (typeof source.model === 'string' && source.model.trim()) {
        configs[key].model = source.model.trim();
      }
    }
  });
  if (legacy && legacy.provider && PROVIDER_KEYS.includes(legacy.provider)) {
    const target = configs[legacy.provider];
    if (typeof legacy.apiKey === 'string' && legacy.apiKey) {
      target.apiKey = legacy.apiKey;
    }
    if (typeof legacy.baseUrl === 'string' && legacy.baseUrl.trim()) {
      target.baseUrl = legacy.baseUrl.trim();
    }
    if (typeof legacy.model === 'string' && legacy.model.trim()) {
      target.model = legacy.model.trim();
    }
  }
  return configs;
}

function sanitizeSettings(payload = {}) {
  const legacyProvider = typeof payload.provider === 'string' ? payload.provider : undefined;
  const activeRaw =
    typeof payload.activeProvider === 'string'
      ? payload.activeProvider
      : legacyProvider || DEFAULT_AI_SETTINGS.activeProvider;
  const activeProvider = PROVIDER_KEYS.includes(activeRaw) ? activeRaw : DEFAULT_AI_SETTINGS.activeProvider;

  return {
    activeProvider,
    providers: sanitizeProviderConfigs(payload.providers, {
      provider: legacyProvider,
      apiKey: payload.apiKey,
      baseUrl: payload.baseUrl,
      model: payload.model,
    }),
    pexelsApiKey: typeof payload.pexelsApiKey === 'string' ? payload.pexelsApiKey : '',
    pixabayApiKey: typeof payload.pixabayApiKey === 'string' ? payload.pixabayApiKey : '',
    stabilityApiKey: typeof payload.stabilityApiKey === 'string' ? payload.stabilityApiKey : '',
    youtubeApiKey: typeof payload.youtubeApiKey === 'string' ? payload.youtubeApiKey : '',
    bgmDirectory:
      typeof payload.bgmDirectory === 'string' && payload.bgmDirectory.trim()
        ? payload.bgmDirectory.trim()
        : DEFAULT_AI_SETTINGS.bgmDirectory,
    assetProviderOrder:
      typeof payload.assetProviderOrder === 'string'
        ? payload.assetProviderOrder
        : DEFAULT_AI_SETTINGS.assetProviderOrder,
    assetMaxResults:
      typeof payload.assetMaxResults === 'number' && Number.isFinite(payload.assetMaxResults)
        ? payload.assetMaxResults
        : DEFAULT_AI_SETTINGS.assetMaxResults,
  };
}

function loadAISettings() {
  try {
    if (fs.existsSync(SETTINGS_FILE)) {
      const data = JSON.parse(fs.readFileSync(SETTINGS_FILE, 'utf-8'));
      return sanitizeSettings(data);
    }
  } catch (err) {
    console.error('Failed to load AI settings, fallback to defaults.', err);
  }
  return sanitizeSettings({});
}

function saveAISettings(payload) {
  const mergedInput = {
    ...currentSettings,
    ...payload,
    providers: {
      ...(currentSettings?.providers || {}),
      ...(payload.providers || {}),
    },
  };
  const sanitized = sanitizeSettings(mergedInput);
  fs.mkdirSync(SETTINGS_DIR, { recursive: true });
  fs.writeFileSync(SETTINGS_FILE, JSON.stringify(sanitized, null, 2), 'utf-8');
  return sanitized;
}

function generateScriptFromBrief({ brief, themeId, sections }) {
  const args = [
    path.join(PROJECT_ROOT, 'scripts', 'generate_script_from_brief.py'),
    '--brief',
    brief,
    '--theme-id',
    themeId || 'lifehack_surprise',
    '--sections',
    String(sections || 5),
    '--stdout',
  ];
  return new Promise((resolve, reject) => {
    const proc = spawn(PYTHON_BIN, args, { cwd: PROJECT_ROOT });
    let stdout = '';
    let stderr = '';
    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });
    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    proc.on('error', (err) => {
      reject(new Error(`LLM プロセス起動に失敗しました: ${err.message}`));
    });
    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(stderr.trim() || `スクリプト生成に失敗しました (exit ${code}).`));
        return;
      }
      try {
        const script = YAML.parse(stdout);
        resolve(script);
      } catch (err) {
        reject(new Error(`生成結果の解析に失敗しました: ${err.message}`));
      }
    });
  });
}

function buildEnv() {
  return {
    ...process.env,
    PEXELS_API_KEY: currentSettings.pexelsApiKey || process.env.PEXELS_API_KEY,
    PIXABAY_API_KEY: currentSettings.pixabayApiKey || process.env.PIXABAY_API_KEY,
    STABILITY_API_KEY: currentSettings.stabilityApiKey || process.env.STABILITY_API_KEY,
    YOUTUBE_API_KEY: currentSettings.youtubeApiKey || process.env.YOUTUBE_API_KEY,
    BGM_DIRECTORY: currentSettings.bgmDirectory || process.env.BGM_DIRECTORY,
  };
}

function runPythonJson(args, friendlyError) {
  return new Promise((resolve, reject) => {
    const proc = spawn(PYTHON_BIN, args, { cwd: PROJECT_ROOT, env: buildEnv() });
    let stdout = '';
    let stderr = '';
    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });
    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    proc.on('error', (err) => {
      reject(new Error(`${friendlyError || 'コマンド実行に失敗しました。'}\n${err.message}`));
    });
    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`${friendlyError || 'コマンド実行に失敗しました。'}\n${stderr.trim()}`));
        return;
      }
      try {
        resolve(JSON.parse(stdout || '[]'));
      } catch (err) {
        reject(new Error(`${friendlyError || '応答の解析に失敗しました。'}\n${err.message}`));
      }
    });
  });
}

function runPythonText(args, friendlyError) {
  return new Promise((resolve, reject) => {
    const proc = spawn(PYTHON_BIN, args, { cwd: PROJECT_ROOT, env: buildEnv() });
    let stderr = '';
    let stdout = '';
    proc.stdout.on('data', (data) => {
      const text = data.toString();
      stdout += text;
      process.stdout.write(text);
    });
    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    proc.on('error', (err) => {
      reject(new Error(`${friendlyError || 'コマンド実行に失敗しました。'}\n${err.message}`));
    });
    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`${friendlyError || 'コマンド実行に失敗しました。'}\n${stderr.trim()}`));
        return;
      }
      resolve({ ok: true, stdout: stdout.trim(), stderr: stderr.trim() });
    });
  });
}

function saveTempScript(script) {
  fs.mkdirSync(TMP_DIR, { recursive: true });
  const yamlText = YAML.stringify(script || {});
  fs.writeFileSync(UI_SCRIPT_PATH, yamlText, 'utf-8');
  return UI_SCRIPT_PATH;
}
  ipcMain.handle('settings:open-window', () => {
    if (settingsWindow && !settingsWindow.isDestroyed()) {
      settingsWindow.focus();
      return { ok: true };
    }
    settingsWindow = new BrowserWindow({
      width: 640,
      height: 760,
      title: 'AI 設定',
      parent: mainWindowRef || undefined,
      webPreferences: {
        preload: path.join(__dirname, 'preload_settings.js'),
        contextIsolation: true,
        nodeIntegration: false,
      },
    });
    settingsWindow.on('closed', () => {
      settingsWindow = null;
    });
    settingsWindow.loadFile(path.join(__dirname, 'renderer', 'settings.html'));
    return { ok: true };
  });
