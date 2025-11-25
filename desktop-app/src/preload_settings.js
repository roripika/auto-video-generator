const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('aiSettings', {
  load: () => ipcRenderer.invoke('settings:load'),
  save: (payload) => ipcRenderer.invoke('settings:save', payload),
});

contextBridge.exposeInMainWorld('externalLinks', {
  open: (url) => ipcRenderer.invoke('external:open', url),
});
