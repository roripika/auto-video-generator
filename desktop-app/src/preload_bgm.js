const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('bgmApi', {
  listTracks: (payload) => ipcRenderer.invoke('bgm:list', payload || {}),
  loadSettings: () => ipcRenderer.invoke('settings:load'),
  applyBgm: (payload) => ipcRenderer.send('bgm-window:apply', payload),
});
