const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getApiBaseUrl: () => ipcRenderer.invoke('get-api-base-url'),
  // 唤起系统原生目录选择器（dialog.showOpenDialog properties: ['openDirectory']）
  selectDirectory: () => ipcRenderer.invoke('select-workspace-directory'),
})
