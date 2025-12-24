const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('aiSettings', {
  load: () => ipcRenderer.invoke('settings:load'),
  save: (payload) => ipcRenderer.invoke('settings:save', payload),
});

contextBridge.exposeInMainWorld('fileDialog', {
  chooseYoutubeClientSecrets: () => ipcRenderer.invoke('file:choose-json'),
  chooseYoutubeCredentials: () => ipcRenderer.invoke('file:choose-any'),
});

contextBridge.exposeInMainWorld('externalLinks', {
  open: (url) => ipcRenderer.invoke('external:open', url),
});

contextBridge.exposeInMainWorld('youtubeAuth', {
  runAuthTest: () => ipcRenderer.invoke('youtube:auth-test'),
  deleteCredentials: () => ipcRenderer.invoke('youtube:delete-creds'),
});
