const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')

const isDev = !app.isPackaged

function createWindow () {
  const mainWindow = new BrowserWindow({
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
