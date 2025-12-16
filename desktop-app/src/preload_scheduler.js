const { contextBridge, ipcRenderer } = require('electron');

const schedulerBridge = {
  list: () => ipcRenderer.invoke('scheduler:list'),
  save: (tasks) => ipcRenderer.invoke('scheduler:save', tasks),
  runNow: (taskId) => ipcRenderer.invoke('scheduler:run-now', taskId),
  remove: (taskId) => ipcRenderer.invoke('scheduler:remove', taskId),
  openLog: (logPath) => ipcRenderer.invoke('scheduler:open-log', logPath),
  openStatus: () => ipcRenderer.invoke('scheduler:status-open'),
  statusData: () => ipcRenderer.invoke('scheduler:status-data'),
};

contextBridge.exposeInMainWorld('schedulerApi', schedulerBridge);
contextBridge.exposeInMainWorld('schedulerBridge', schedulerBridge);
contextBridge.exposeInMainWorld('api', { scheduler: schedulerBridge });
