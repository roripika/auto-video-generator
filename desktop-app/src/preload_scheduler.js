const { contextBridge, ipcRenderer } = require('electron');

const schedulerBridge = {
  list: () => ipcRenderer.invoke('scheduler:list'),
  save: (tasks) => ipcRenderer.invoke('scheduler:save', tasks),
  runNow: (taskId) => ipcRenderer.invoke('scheduler:run-now', taskId),
  remove: (taskId) => ipcRenderer.invoke('scheduler:remove', taskId),
};

const safeExpose = (key, value) => {
  try {
    contextBridge.exposeInMainWorld(key, value);
  } catch (err) {
    console.warn(`[scheduler-preload] expose ${key} failed: ${err.message}`);
  }
};

safeExpose('scheduler', schedulerBridge);
safeExpose('schedulerApi', schedulerBridge);
safeExpose('schedulerBridge', schedulerBridge);
safeExpose('api', { scheduler: schedulerBridge });
