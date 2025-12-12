const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  listThemes: () => ipcRenderer.invoke('themes:list'),
  newScriptFromTheme: (themeId) => ipcRenderer.invoke('scripts:new', { themeId }),
  openScript: () => ipcRenderer.invoke('scripts:open'),
  saveScript: (payload) => ipcRenderer.invoke('scripts:save', payload),
  loadSettings: () => ipcRenderer.invoke('settings:load'),
  saveSettings: (payload) => ipcRenderer.invoke('settings:save', payload),
  generateScriptFromBrief: (payload) => ipcRenderer.invoke('scripts:generate-from-brief', payload),
  fetchAssets: (payload) => ipcRenderer.invoke('assets:fetch', payload),
  openAssetWindow: () => ipcRenderer.invoke('asset-window:open'),
  onAssetSelected: (callback) => ipcRenderer.on('asset:selected', (_event, payload) => callback(payload)),
  chooseBackgroundFile: () => ipcRenderer.invoke('background:choose-file'),
  chooseBgmFile: () => ipcRenderer.invoke('bgm:choose-file'),
  chooseYoutubeClientSecrets: () => ipcRenderer.invoke('file:choose-json'),
  chooseYoutubeCredentials: () => ipcRenderer.invoke('file:choose-any'),
  openBgmWindow: () => ipcRenderer.invoke('bgm-window:open'),
  openTrendWindow: () => ipcRenderer.invoke('trend-window:open'),
  openSchedulerWindow: () => ipcRenderer.invoke('scheduler:open'),
  onBgmSelected: (callback) => ipcRenderer.on('bgm:selected', (_event, payload) => callback(payload)),
  onTrendSelected: (callback) => ipcRenderer.on('trend:selected', (_event, payload) => callback(payload)),
  openSettingsWindow: () => ipcRenderer.invoke('settings:open-window'),
  generateAudio: (payload) => ipcRenderer.invoke('audio:generate', payload),
  clearAudioCache: () => ipcRenderer.invoke('audio:clear'),
  describeTimeline: (payload) => ipcRenderer.invoke('timeline:describe', payload),
  generateVideo: (payload) => ipcRenderer.invoke('video:generate', payload),
  uploadVideo: (payload) => ipcRenderer.invoke('video:upload', payload),
  openOutputPath: (payload) => ipcRenderer.invoke('video:open-output', payload),
  getLatestVideo: () => ipcRenderer.invoke('video:get-latest'),
  scheduler: {
    list: () => ipcRenderer.invoke('scheduler:list'),
    save: (tasks) => ipcRenderer.invoke('scheduler:save', tasks),
    runNow: (taskId) => ipcRenderer.invoke('scheduler:run-now', taskId),
    remove: (taskId) => ipcRenderer.invoke('scheduler:remove', taskId),
    openLog: (logPath) => ipcRenderer.invoke('scheduler:open-log', logPath),
  },
  openExternalLink: (url) => ipcRenderer.invoke('external:open', url),
});

contextBridge.exposeInMainWorld('yaml', {
  stringify: (data) => ipcRenderer.sendSync('yaml:stringify', data),
  parse: (text) => ipcRenderer.sendSync('yaml:parse', text),
});
