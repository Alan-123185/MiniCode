const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getApiBaseUrl: () => ipcRenderer.invoke('get-api-base-url'),
  // 唤起系统原生目录选择器（dialog.showOpenDialog properties: ['openDirectory']）
  selectDirectory: () => ipcRenderer.invoke('select-workspace-directory'),
  // 订阅原生菜单命令 (new-chat / focus-search / open-settings / toggle-theme)
  // 返回取消订阅函数
  onMenuCommand: (callback) => {
    const handler = (_event, action) => callback(action)
    ipcRenderer.on('menu-command', handler)
    return () => ipcRenderer.removeListener('menu-command', handler)
  },
})
