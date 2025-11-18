const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('assetApi', {
  fetchAssets: (payload) => ipcRenderer.invoke('assets:fetch', payload),
  loadSettings: () => ipcRenderer.invoke('settings:load'),
  applyBackground: (payload) => ipcRenderer.send('asset-window:apply-bg', payload),
});

