const { app, BrowserWindow, ipcMain, dialog } = require('electron')
const path = require('path')

const isDev = !app.isPackaged

let mainWindow = null

function createWindow () {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  const devServerUrl = process.env.VITE_DEV_SERVER_URL

  if (isDev && devServerUrl) {
    // 热更新模式: 先启动 vite dev server, 再通过 VITE_DEV_SERVER_URL 指向它
    mainWindow.loadURL(devServerUrl)
  } else {
    // 默认: 加载构建产物 (npm run build 后)
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

ipcMain.handle('get-api-base-url', () => {
  // 生产模式下后端地址在这里调整
  return 'http://127.0.0.1:8000'
})

// 唤起操作系统原生目录选择器，返回所选绝对路径；用户取消时返回 null
ipcMain.handle('select-workspace-directory', async () => {
  if (!mainWindow) return null
  const { canceled, filePaths } = await dialog.showOpenDialog(mainWindow, {
    title: '选择工作目录',
    buttonLabel: '选择此目录',
    properties: ['openDirectory', 'createDirectory'],
  })
  if (canceled || !filePaths || filePaths.length === 0) return null
  return filePaths[0]
})
