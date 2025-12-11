const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('trendApi', {
  loadSettings: () => ipcRenderer.invoke('settings:load'),
  fetchTrending: (payload) => ipcRenderer.invoke('trends:fetch', payload),
  applyKeyword: (payload) => ipcRenderer.send('trend-window:apply', payload),
});
