/**
 * 会话级工作目录选择器。
 * 桌面端: 通过 Electron IPC 唤起系统原生目录选择器 (dialog.showOpenDialog openDirectory)
 * 浏览器端: 降级为 prompt 输入（便于纯 Web 调试），并明确提示非原生行为
 */
export function useWorkspacePicker() {
  const isElectron = typeof window !== 'undefined' && !!window.electronAPI?.selectDirectory

  /** @returns {Promise<string|null>} 选中的绝对路径；用户取消返回 null */
  async function pickDirectory() {
    if (isElectron) {
      try {
        return await window.electronAPI.selectDirectory()
      } catch (e) {
        console.error('唤起系统目录选择器失败', e)
        return null
      }
    }
    // 浏览器降级路径（仅调试用）
    const input = window.prompt('浏览器模式: 请输入工作目录的绝对路径（桌面端将唤起系统资源管理器）:')
    return input && input.trim() ? input.trim() : null
  }

  return { isElectron, pickDirectory }
}