import { defineStore } from 'pinia'
import { ref } from 'vue'

/** 提示类型 → 决定 ToastHost 的配色与图标 */
export const TOAST_TYPES = {
  success: 'success',
  error: 'error',
  info: 'info',
}

/** 同一文案在该时间窗内的重复提示会被合并 (毫秒), 避免连点按钮刷屏 */
const DEDUPE_WINDOW = 1200
/** 队列上限: 超出的旧提示直接丢弃, 防止异常循环调用堆满屏幕 */
const MAX_VISIBLE = 4

export const useToastStore = defineStore('toast', () => {
  /** toast 数组, 每条 = { id, message, type, duration } */
  const toasts = ref([])
  /** 最近一次提示的文案 → 时间戳, 用于 DEDUPE_WINDOW 内的去重 */
  const recent = new Map()
  /** 每条 toast 的定时器句柄, 供 dismiss 时取消 */
  const timers = new Map()

  let seq = 0

  /**
   * 弹出一条全局提示。
   * @param {string} message 提示文案
   * @param {{type?: 'success'|'error'|'info', duration?: number}} [options]
   *   type: 默认 info; duration: 停留毫秒, 传 0 表示不自动消失
   * @returns {number|null} toast id; 被去重/拦截时返回 null
   */
  function show(message, options = {}) {
    if (!message) return null

    const now = Date.now()
    const last = recent.get(message)
    // 去重窗口内已有同样文案 → 忽略本次, 不新增气泡
    if (last && now - last < DEDUPE_WINDOW) return null
    recent.set(message, now)

    const type = TOAST_TYPES[options.type] ? options.type : TOAST_TYPES.info
    const id = ++seq
    const duration = Number.isFinite(options.duration) ? options.duration : 3000

    // 超出上限时丢掉最早的一条, 保证屏幕上的提示数量受控
    while (toasts.value.length >= MAX_VISIBLE) dismiss(toasts.value[0].id)

    toasts.value.push({ id, message: String(message), type, duration })

    if (duration > 0) timers.set(id, setTimeout(() => dismiss(id), duration))
    return id
  }

  const success = (message, duration) => show(message, { type: 'success', duration })
  const error = (message, duration) => show(message, { type: 'error', duration })
  const info = (message, duration) => show(message, { type: 'info', duration })

  /** 手动关闭一条提示 (自动消失超时到达时也走这里) */
  function dismiss(id) {
    const idx = toasts.value.findIndex((t) => t.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
    const timer = timers.get(id)
    if (timer) {
      clearTimeout(timer)
      timers.delete(id)
    }
  }

  /** 清空全部提示 (如切换会话/关闭弹窗时避免上一条上下文残留) */
  function clear() {
    timers.forEach((t) => clearTimeout(t))
    timers.clear()
    toasts.value = []
  }

  return { toasts, show, success, error, info, dismiss, clear }
})