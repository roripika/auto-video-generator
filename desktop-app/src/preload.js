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
  generateAudio: (payload) => ipcRenderer.invoke('audio:generate', payload),
  describeTimeline: (payload) => ipcRenderer.invoke('timeline:describe', payload),
  generateVideo: (payload) => ipcRenderer.invoke('video:generate', payload),
  openOutputPath: (payload) => ipcRenderer.invoke('video:open-output', payload),
});

contextBridge.exposeInMainWorld('yaml', {
  stringify: (data) => ipcRenderer.sendSync('yaml:stringify', data),
});
