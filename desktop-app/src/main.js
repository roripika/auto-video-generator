const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron');
const path = require('path');
const os = require('os');
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

const DEFAULT_YT_CREDENTIALS_PATH = path.join(os.homedir(), '.config', 'auto-video-generator', 'youtube_credentials.pickle');

const YOUTUBE_PRIVACY_OPTIONS = new Set(['private', 'unlisted', 'public']);

const DEFAULT_AI_SETTINGS = {
  activeProvider: 'openai',
  providers: cloneProviderDefaults(),
  pexelsApiKey: '',
  pixabayApiKey: '',
  stabilityApiKey: '',
  youtubeApiKey: '',
  youtubeClientSecretsPath: '',
  youtubeCredentialsPath: DEFAULT_YT_CREDENTIALS_PATH,
  youtubePrivacyStatus: 'private',
  bgmDirectory: 'assets/bgm',
  assetProviderOrder: 'pexels,pixabay',
  assetMaxResults: 5,
};
const VENV_PY = path.join(PROJECT_ROOT, '.venv', 'bin', 'python3');
const VENV_BIN_DIR = path.join(PROJECT_ROOT, '.venv', 'bin');
const PYTHON_BIN = process.env.PYTHON_BIN || (fs.existsSync(VENV_PY) ? VENV_PY : 'python3');
const FETCH_ASSETS_SCRIPT = path.join(PROJECT_ROOT, 'scripts', 'fetch_assets.py');
const GENERATE_AUDIO_SCRIPT = path.join(PROJECT_ROOT, 'scripts', 'generate_audio.py');
const DESCRIBE_TIMELINE_SCRIPT = path.join(PROJECT_ROOT, 'scripts', 'describe_timeline.py');
const GENERATE_VIDEO_SCRIPT = path.join(PROJECT_ROOT, 'scripts', 'generate_video.py');
const YOUTUBE_AUTH_TEST_SCRIPT = path.join(PROJECT_ROOT, 'scripts', 'youtube_auth_test.py');
const TRENDS_FETCH_SCRIPT = path.join(PROJECT_ROOT, 'scripts', 'fetch_trend_ideas_llm.py');
const YOUTUBE_UPLOAD_SCRIPT = path.join(PROJECT_ROOT, 'scripts', 'youtube_upload.py');
const SCHEDULE_FILE = path.join(SETTINGS_DIR, 'schedule.json');
const DEFAULT_MAX_CONCURRENT = 1;
const SCHEDULER_LOG_DIR = path.join(PROJECT_ROOT, 'logs', 'scheduler');
const TMP_DIR = path.join(PROJECT_ROOT, 'tmp');
const UI_SCRIPT_PATH = path.join(TMP_DIR, 'ui_script.yaml');
const AUDIO_CACHE_DIR = path.join(PROJECT_ROOT, 'work', 'audio');
const OUTPUTS_DIR = path.join(PROJECT_ROOT, 'outputs', 'rendered');
const AUDIO_EXTENSIONS = new Set(['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.aiff', '.aif', '.wma']);

let currentSettings = loadAISettings();
let mainWindowRef = null;
let assetWindow = null;
let bgmWindow = null;
let settingsWindow = null;
let trendWindow = null;
let schedulerWindow = null;
let schedulerTimers = {};
let schedulerQueue = Promise.resolve();
let uploadQueue = Promise.resolve();
let schedulerMaxConcurrent = DEFAULT_MAX_CONCURRENT;

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
  ipcMain.handle('scheduler:open', () => {
    if (schedulerWindow && !schedulerWindow.isDestroyed()) {
      schedulerWindow.focus();
      return { ok: true };
    }
    schedulerWindow = new BrowserWindow({
      width: 860,
      height: 720,
      title: '定期実行タスク',
      parent: mainWindowRef || undefined,
      webPreferences: {
        preload: path.join(__dirname, 'preload_scheduler.js'),
        contextIsolation: true,
        nodeIntegration: false,
      },
    });
    schedulerWindow.on('closed', () => {
      schedulerWindow = null;
    });
    schedulerWindow.loadFile(path.join(__dirname, 'renderer', 'scheduler.html'));
    return { ok: true };
  });
  ipcMain.handle('trend-window:open', () => {
    if (trendWindow && !trendWindow.isDestroyed()) {
      trendWindow.focus();
      return { ok: true };
    }
    trendWindow = new BrowserWindow({
      width: 720,
      height: 640,
      title: 'トレンド候補',
      parent: mainWindowRef || undefined,
      webPreferences: {
        preload: path.join(__dirname, 'preload_trends.js'),
        contextIsolation: true,
        nodeIntegration: false,
      },
    });
    trendWindow.on('closed', () => {
      trendWindow = null;
    });
    trendWindow.loadFile(path.join(__dirname, 'renderer', 'trends.html'));
    return { ok: true };
  });
  ipcMain.on('trend-window:apply', (_event, payload) => {
    if (mainWindowRef && !mainWindowRef.isDestroyed()) {
      mainWindowRef.webContents.send('trend:selected', payload);
    }
  });
  ipcMain.handle('bgm-window:open', () => {
    if (bgmWindow && !bgmWindow.isDestroyed()) {
      bgmWindow.focus();
      return { ok: true };
    }
    bgmWindow = new BrowserWindow({
      width: 760,
      height: 640,
      title: 'BGM ライブラリ',
      parent: mainWindowRef || undefined,
      webPreferences: {
        preload: path.join(__dirname, 'preload_bgm.js'),
        contextIsolation: true,
        nodeIntegration: false,
      },
    });
    bgmWindow.on('closed', () => {
      bgmWindow = null;
    });
    bgmWindow.loadFile(path.join(__dirname, 'renderer', 'bgm.html'));
    return { ok: true };
  });
  ipcMain.on('bgm-window:apply', (_event, payload) => {
    if (mainWindowRef && !mainWindowRef.isDestroyed()) {
      mainWindowRef.webContents.send('bgm:selected', payload);
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
  ipcMain.handle('bgm:list', (_event, payload) => {
    const keyword = (payload?.keyword || '').trim().toLowerCase();
    const directory =
      (payload?.directory && payload.directory.trim()) ||
      currentSettings.bgmDirectory ||
      DEFAULT_AI_SETTINGS.bgmDirectory;
    const { resolvedDirectory, items } = collectBgmFiles(directory);
    const filtered = !keyword
      ? items
      : items.filter((item) => {
          const target = (item.relativePath || item.name || '').toLowerCase();
          return target.includes(keyword);
        });
    filtered.sort((a, b) => {
      const left = (a.relativePath || a.name || '').toLowerCase();
      const right = (b.relativePath || b.name || '').toLowerCase();
      if (left < right) return -1;
      if (left > right) return 1;
      return 0;
    });
    return {
      directory,
      resolvedDirectory,
      items: filtered,
    };
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
  ipcMain.handle('file:choose-json', async () => {
    const result = await dialog.showOpenDialog({
      title: 'client_secrets.json を選択',
      properties: ['openFile'],
      filters: [{ name: 'JSON', extensions: ['json'] }, { name: 'All files', extensions: ['*'] }],
    });
    if (result.canceled || !result.filePaths.length) {
      return { canceled: true };
    }
    return { canceled: false, path: result.filePaths[0] };
  });
  ipcMain.handle('file:choose-any', async () => {
    const result = await dialog.showOpenDialog({
      title: '保存先ファイルを選択（既存ファイルを指定可）',
      properties: ['openFile', 'createDirectory'],
      filters: [{ name: 'All files', extensions: ['*'] }],
    });
    if (result.canceled || !result.filePaths.length) {
      return { canceled: true };
    }
    return { canceled: false, path: result.filePaths[0] };
  });
  ipcMain.handle('youtube:auth-test', async () => {
    const settings = currentSettings || DEFAULT_AI_SETTINGS;
    const clientPath = settings.youtubeClientSecretsPath;
    const credPath = settings.youtubeCredentialsPath || DEFAULT_YT_CREDENTIALS_PATH;
    if (!clientPath || !fs.existsSync(clientPath)) {
      throw new Error('client_secrets.json のパスが設定されていません。');
    }
    const args = [
      YOUTUBE_AUTH_TEST_SCRIPT,
      '--client-secrets',
      clientPath,
      '--credentials',
      credPath,
    ];
    return new Promise((resolve, reject) => {
      const proc = spawn(PYTHON_BIN, args, { cwd: PROJECT_ROOT, env: buildEnv() });
      let stderr = '';
      proc.stderr.on('data', (data) => {
        stderr += data.toString();
      });
      proc.on('error', (err) => reject(err));
      proc.on('close', (code) => {
        if (code === 0) {
          resolve({ ok: true, credentials: credPath });
        } else {
          reject(new Error(stderr || `auth test failed (exit ${code})`));
        }
      });
    });
  });
  ipcMain.handle('trends:fetch', async (event, payload) => {
    const geo = (payload?.geo || 'JP').toUpperCase();
    const limit = Math.max(1, Math.min(Number(payload?.limit) || 10, 50));
    const ytKey = currentSettings.youtubeApiKey || process.env.YOUTUBE_API_KEY;
    if (!ytKey) {
      throw new Error('YouTube API Keyが設定されていません。');
    }
    const url = `https://www.googleapis.com/youtube/v3/videos?part=snippet&chart=mostPopular&regionCode=${geo}&maxResults=${limit}&key=${ytKey}`;
    const resp = await fetch(url);
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`YouTube trending fetch failed: status ${resp.status} ${text}`);
    }
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
    return titles;
  });
  ipcMain.handle('trends:fetch-llm', async (_event, payload) => {
    const limit = clampNumber(payload?.limit, 1, 20, 8);
    const args = [
      path.join(PROJECT_ROOT, 'scripts', 'fetch_trend_ideas_llm.py'),
      '--max-ideas',
      String(limit),
      '--stdout',
    ];
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
      proc.on('error', (err) => reject(err));
      proc.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(stderr || `fetch_trend_ideas_llm failed (exit ${code})`));
          return;
        }
        try {
          const parsed = JSON.parse(stdout || '{}');
          resolve({
            keywords: Array.isArray(parsed.keywords) ? parsed.keywords : [],
            briefs: Array.isArray(parsed.briefs) ? parsed.briefs : [],
          });
        } catch (err) {
          reject(new Error(`LLM JSON parse error: ${err.message || err}`));
        }
      });
    });
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
    const result = await runPythonText(args, '音声生成に失敗しました。');
    return result;
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
    if (payload?.clearAudio) args.push('--clear-audio-cache');
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
  ipcMain.handle('video:upload', async (event, payload) => {
    const videoPath = payload?.path;
    if (!videoPath) throw new Error('動画パスが指定されていません。');
    const settings = currentSettings || DEFAULT_AI_SETTINGS;
    const clientSecrets = settings.youtubeClientSecretsPath;
    const credsPath = settings.youtubeCredentialsPath || DEFAULT_YT_CREDENTIALS_PATH;
    const privacyStatus = normalizeYoutubePrivacyStatus(settings.youtubePrivacyStatus);
    if (!clientSecrets || !fs.existsSync(clientSecrets)) {
      throw new Error('client_secrets.json のパスが設定されていません。設定画面で指定してください。');
    }
    const args = [
      YOUTUBE_UPLOAD_SCRIPT,
      '--video',
      videoPath,
      '--title',
      payload?.title || path.basename(videoPath),
      '--description',
      payload?.description || '',
      '--client-secrets',
      clientSecrets,
      '--credentials',
      credsPath,
      '--privacy-status',
      privacyStatus,
    ];
    if (payload?.tags && Array.isArray(payload.tags) && payload.tags.length) {
      args.push('--tags', ...payload.tags);
    }
    // Uploads are serialized to avoid concurrent API errors.
    uploadQueue = uploadQueue
      .then(
        () =>
          new Promise((resolve, reject) => {
            const proc = spawn(PYTHON_BIN, args, { cwd: PROJECT_ROOT, env: buildEnv() });
            let stdout = '';
            let stderr = '';
            proc.stdout.on('data', (d) => (stdout += d.toString()));
            proc.stderr.on('data', (d) => (stderr += d.toString()));
            proc.on('error', (err) => reject(err));
            proc.on('close', (code) => {
              if (code === 0) {
                resolve({ ok: true, stdout });
              } else {
                reject(new Error(stderr || `YouTube upload failed (exit ${code})`));
              }
            });
          })
      )
      .catch((err) => {
        // keep queue alive
        console.error('upload failed', err);
        throw err;
      });
    return uploadQueue;
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
  const clampNumber = (value, min, max, fallback) => {
    const num = Number(value);
    if (Number.isFinite(num)) {
      return Math.min(max, Math.max(min, num));
    }
    return fallback;
  };

  const sanitizeSchedulerTask = (task = {}) => {
    const id =
      typeof task.id === 'string' && task.id.trim()
        ? task.id.trim()
        : `t-${Math.random().toString(36).slice(2, 8)}`;
    return {
      id,
      name: typeof task.name === 'string' ? task.name : '',
      max_keywords: clampNumber(task.max_keywords, 1, 50, 10),
      interval_minutes: clampNumber(task.interval_minutes, 1, 10080, 1440),
      start_offset_minutes:
        task.start_offset_minutes === undefined || task.start_offset_minutes === null
          ? undefined
          : Math.max(0, Number(task.start_offset_minutes) || 0),
      auto_upload: task.auto_upload !== false,
      clear_cache: task.clear_cache !== false,
      enabled: task.enabled !== false,
    };
  };

  const sanitizeSchedulerTasks = (tasks) => (Array.isArray(tasks) ? tasks : []).map(sanitizeSchedulerTask);

  const loadSchedulerData = () => {
    let tasks = [];
    let maxConcurrent = DEFAULT_MAX_CONCURRENT;
    try {
      if (fs.existsSync(SCHEDULE_FILE)) {
        const data = JSON.parse(fs.readFileSync(SCHEDULE_FILE, 'utf-8'));
        if (Array.isArray(data)) {
          tasks = data;
        } else if (data && typeof data === 'object') {
          tasks = data.tasks || [];
          if (data.max_concurrent !== undefined) {
            maxConcurrent = clampNumber(data.max_concurrent, 1, 4, DEFAULT_MAX_CONCURRENT);
          }
        }
      }
    } catch (err) {
      console.error('Failed to load scheduler file', err);
    }
    return {
      tasks: sanitizeSchedulerTasks(tasks),
      max_concurrent: maxConcurrent,
    };
  };

  const getSavedSchedulerTasks = () => {
    const data = loadSchedulerData();
    schedulerMaxConcurrent = data.max_concurrent || DEFAULT_MAX_CONCURRENT;
    return data.tasks || [];
  };

  const getLatestLogInfo = (taskId) => {
    try {
      if (!taskId || !fs.existsSync(SCHEDULER_LOG_DIR)) return null;
      const files = fs
        .readdirSync(SCHEDULER_LOG_DIR)
        .filter((file) => file.startsWith(`${taskId}-`) && file.endsWith('.log'));
      if (!files.length) return null;
      files.sort(
        (a, b) =>
          fs.statSync(path.join(SCHEDULER_LOG_DIR, b)).mtimeMs -
          fs.statSync(path.join(SCHEDULER_LOG_DIR, a)).mtimeMs
      );
      const logPath = path.join(SCHEDULER_LOG_DIR, files[0]);
      return {
        logPath,
        runAt: new Date(fs.statSync(logPath).mtimeMs).toISOString(),
      };
    } catch (err) {
      console.error('Failed to inspect scheduler logs', err);
      return null;
    }
  };

  const decorateSchedulerTasks = (tasks) =>
    (tasks || []).map((task) => {
      if (!task.id) return task;
      const meta = getLatestLogInfo(task.id);
      return {
        ...task,
        last_log_path: meta?.logPath || null,
        last_run_at: meta?.runAt || null,
      };
    });

  ipcMain.handle('scheduler:list', async () => {
    const data = loadSchedulerData();
    schedulerMaxConcurrent = data.max_concurrent || DEFAULT_MAX_CONCURRENT;
    return {
      tasks: decorateSchedulerTasks(data.tasks || []),
      max_concurrent: schedulerMaxConcurrent,
    };
  });

  const saveSchedulerData = (tasks, maxConcurrent) => {
    const sanitized = sanitizeSchedulerTasks(tasks);
    schedulerMaxConcurrent = clampNumber(maxConcurrent, 1, 4, DEFAULT_MAX_CONCURRENT);
    fs.mkdirSync(SETTINGS_DIR, { recursive: true });
    fs.writeFileSync(
      SCHEDULE_FILE,
      JSON.stringify({ tasks: sanitized, max_concurrent: schedulerMaxConcurrent }, null, 2),
      'utf-8'
    );
    return { tasks: sanitized, max_concurrent: schedulerMaxConcurrent };
  };

  const clearSchedulerTimers = () => {
    Object.values(schedulerTimers).forEach((timer) => {
      if (timer?.interval) clearInterval(timer.interval);
      if (timer?.timeout) clearTimeout(timer.timeout);
    });
    schedulerTimers = {};
  };

  const autoTrendArgs = (task) => {
    const args = [
      path.join(PROJECT_ROOT, 'scripts', 'auto_trend_pipeline.py'),
      '--max-keywords',
      String(task.max_keywords || 10),
      '--theme-id',
      'freeform_prompt',
    ];
    if (task.category) {
      args.push('--llm-category', task.category);
    }
    const wantUpload = task.auto_upload !== false;
    if (wantUpload && currentSettings.youtubeClientSecretsPath) {
      args.push('--youtube-client-secrets', currentSettings.youtubeClientSecretsPath);
    }
    if (wantUpload && currentSettings.youtubeCredentialsPath) {
      args.push('--youtube-credentials', currentSettings.youtubeCredentialsPath);
    }
    if (wantUpload && currentSettings.youtubePrivacyStatus) {
      args.push('--youtube-privacy', normalizeYoutubePrivacyStatus(currentSettings.youtubePrivacyStatus));
    }
    if (task.clear_cache !== false) {
      args.push('--clear-cache');
    }
    return args;
  };

  const runTaskNow = (task) =>
    new Promise((resolve, reject) => {
      fs.mkdirSync(SCHEDULER_LOG_DIR, { recursive: true });
      const ts = new Date().toISOString().replace(/[:.]/g, '-');
      const logPath = path.join(SCHEDULER_LOG_DIR, `${task.id || 'task'}-${ts}.log`);
      const args = autoTrendArgs(task);
      const proc = spawn(PYTHON_BIN, args, { cwd: PROJECT_ROOT, env: buildEnv() });
      const logStream = fs.createWriteStream(logPath);
      proc.stdout.on('data', (d) => logStream.write(d));
      proc.stderr.on('data', (d) => logStream.write(d));
      proc.on('error', (err) => {
        logStream.end();
        reject(err);
      });
      proc.on('close', (code) => {
        logStream.end();
        if (code === 0) resolve({ ok: true, logPath });
        else reject(new Error(`exit ${code}, log: ${logPath}`));
      });
    });

  const enqueueTask = (task, { swallowErrors = true } = {}) => {
    schedulerQueue = schedulerQueue
      .then(() => runTaskNow(task))
      .catch((err) => {
        if (swallowErrors) {
          console.error('Scheduled task failed', err);
          return null;
        }
        throw err;
      });
    return schedulerQueue;
  };

  const scheduleTasks = (tasks) => {
    clearSchedulerTimers();
    (tasks || [])
      .filter((t) => t.enabled !== false)
      .forEach((task) => {
        const intervalMin = Math.max(1, Number(task.interval_minutes || 1440));
        const intervalMs = intervalMin * 60 * 1000;
        const startOffsetMin =
          task.start_offset_minutes !== undefined && task.start_offset_minutes !== null
            ? Math.max(0, Number(task.start_offset_minutes) || 0)
            : intervalMin;
        const firstDelayMs = startOffsetMin * 60 * 1000;
        const runner = () => enqueueTask(task, { swallowErrors: true });
        const handleIntervalStart = () => {
          const interval = setInterval(runner, intervalMs);
          schedulerTimers[task.id] = { ...(schedulerTimers[task.id] || {}), interval };
        };
        if (firstDelayMs > 0) {
          const timeout = setTimeout(() => {
            runner();
            handleIntervalStart();
          }, firstDelayMs);
          schedulerTimers[task.id] = { timeout };
        } else {
          runner();
          handleIntervalStart();
        }
      });
  };

  ipcMain.handle('scheduler:save', async (_event, payload) => {
    const incomingTasks = (payload && payload.tasks) || payload || [];
    const maxConcurrent =
      (payload && payload.max_concurrent !== undefined) ? payload.max_concurrent : schedulerMaxConcurrent;
    const saved = saveSchedulerData(incomingTasks || [], maxConcurrent);
    scheduleTasks(saved.tasks);
    return { ok: true };
  });

  ipcMain.handle('scheduler:run-now', async (_event, taskId) => {
    if (!taskId) throw new Error('taskId is required');
    const tasks = getSavedSchedulerTasks();
    const task = (tasks || []).find((t) => t.id === taskId);
    if (!task) throw new Error('task not found');
    return enqueueTask(task, { swallowErrors: false });
  });

  ipcMain.handle('scheduler:remove', async (_event, taskId) => {
    const tasks = getSavedSchedulerTasks();
    const next = (tasks || []).filter((t) => t.id !== taskId);
    const sanitized = saveSchedulerTasks(next);
    scheduleTasks(sanitized);
    return { ok: true };
  });

  ipcMain.handle('scheduler:open-log', async (_event, logPath) => {
    if (!logPath) throw new Error('logPath is required');
    if (!fs.existsSync(logPath)) {
      throw new Error('指定されたログファイルが見つかりません。');
    }
    const result = await shell.openPath(logPath);
    if (result) {
      throw new Error(result);
    }
    return { ok: true };
  });

  // 初期ロード時にスケジュールをセット
  scheduleTasks(getSavedSchedulerTasks());

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

function normalizeYoutubePrivacyStatus(value) {
  const raw = typeof value === 'string' ? value.trim().toLowerCase() : '';
  if (YOUTUBE_PRIVACY_OPTIONS.has(raw)) {
    return raw;
  }
  return DEFAULT_AI_SETTINGS.youtubePrivacyStatus;
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
    youtubeClientSecretsPath:
      typeof payload.youtubeClientSecretsPath === 'string' ? payload.youtubeClientSecretsPath : '',
    youtubeCredentialsPath:
      typeof payload.youtubeCredentialsPath === 'string' && payload.youtubeCredentialsPath.trim()
        ? payload.youtubeCredentialsPath.trim()
        : DEFAULT_AI_SETTINGS.youtubeCredentialsPath,
    youtubeForceVideo:
      typeof payload.youtubeForceVideo === 'string' && payload.youtubeForceVideo.trim()
        ? payload.youtubeForceVideo.trim()
        : '',
    youtubePrivacyStatus: normalizeYoutubePrivacyStatus(payload.youtubePrivacyStatus),
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
  const baseEnv = {
    ...process.env,
    PEXELS_API_KEY: currentSettings.pexelsApiKey || process.env.PEXELS_API_KEY,
    PIXABAY_API_KEY: currentSettings.pixabayApiKey || process.env.PIXABAY_API_KEY,
    STABILITY_API_KEY: currentSettings.stabilityApiKey || process.env.STABILITY_API_KEY,
    YOUTUBE_API_KEY: currentSettings.youtubeApiKey || process.env.YOUTUBE_API_KEY,
    BGM_DIRECTORY: currentSettings.bgmDirectory || process.env.BGM_DIRECTORY,
    PYTHONUNBUFFERED: '1',
  };
  // Prefer venv's bin in PATH so spawned processes find the same Python/pip
  const sep = path.delimiter || ':';
  const venvPath = fs.existsSync(VENV_BIN_DIR) ? `${VENV_BIN_DIR}${sep}${process.env.PATH || ''}` : process.env.PATH;
  return { ...baseEnv, PATH: venvPath };
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

function resolveBgmDirectory(dir) {
  if (dir && path.isAbsolute(dir)) {
    return dir;
  }
  if (dir && dir.trim()) {
    return path.join(PROJECT_ROOT, dir.trim());
  }
  return path.join(PROJECT_ROOT, DEFAULT_AI_SETTINGS.bgmDirectory);
}

function collectBgmFiles(directory) {
  const resolvedDirectory = resolveBgmDirectory(directory);
  const items = [];
  if (!fs.existsSync(resolvedDirectory)) {
    return { resolvedDirectory, items };
  }
  const walk = (target) => {
    let entries;
    try {
      entries = fs.readdirSync(target, { withFileTypes: true });
    } catch (err) {
      console.warn('Failed to read BGM directory entry', target, err);
      return;
    }
    entries.forEach((entry) => {
      const entryPath = path.join(target, entry.name);
      if (entry.isDirectory()) {
        walk(entryPath);
        return;
      }
      if (!entry.isFile()) {
        return;
      }
      const ext = path.extname(entry.name).toLowerCase();
      if (!AUDIO_EXTENSIONS.has(ext)) {
        return;
      }
      let size = 0;
      try {
        size = fs.statSync(entryPath).size;
      } catch (err) {
        console.warn('Failed to stat BGM file', entryPath, err);
      }
      items.push({
        name: entry.name,
        path: entryPath,
        relativePath: path.relative(PROJECT_ROOT, entryPath),
        size,
      });
    });
  };
  walk(resolvedDirectory);
  return { resolvedDirectory, items };
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
