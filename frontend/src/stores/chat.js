import { defineStore } from 'pinia'
import { ref, computed, reactive } from 'vue'
import {
  chatStream,
  approveStream,
  newChat,
  listSessions,
  getHistory,
  deleteChat,
  chooseModel,
  oldModel,
  chooseWorkplace,
} from '../api'

function genId() {
  return crypto.randomUUID()
}

function formatAgentResult(result) {
  if (result == null) return ''
  if (typeof result === 'string') return result
  if (result.answer) return result.answer
  if (result.content) return result.content
  return JSON.stringify(result)
}

function localTitle(content) {
  return content.replace(/\s+/g, ' ').trim().slice(0, 20)
}

/** 后端 DB 列名为 id/name/user_id/created_at，前端兼容两种命名风格。
 *  workspacePath 为「会话级」工作目录：以后端 workplace 列为准，本地缓存兜底 */
function normalizeSession(row, workspaceCache = {}) {
  const id = row.id || row.session_id
  return {
    id,
    title: row.name || row.session_name || '新会话',
    workspacePath: row.workplace || row.workspace_path || workspaceCache[id] || '',
    createTime: row.created_at || row.create_time || 0,
  }
}

/** 会话级工作目录的本地缓存（仅前端持久化，后端字段缺失时兜底） */
const SESSION_WORKSPACE_KEY = 'minicodex_session_workspaces'

/** 5 组模型配置的本地持久化键（SettingsModal 与启动默认模型共用） */
export const MODEL_PROFILES_KEY = 'minicodex_model_profiles'

function loadWorkspaceCache() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_WORKSPACE_KEY) || '{}')
  } catch {
    return {}
  }
}

function saveWorkspaceCache(cache) {
  try {
    localStorage.setItem(SESSION_WORKSPACE_KEY, JSON.stringify(cache))
  } catch (e) {
    console.error('保存工作目录缓存失败', e)
  }
}

export const useChatStore = defineStore('chat', () => {
  const userKey = 'minicodex_user_id'

  function getUserId() {
    let id = localStorage.getItem(userKey)
    if (!id) {
      id = `user_${genId()}`
      localStorage.setItem(userKey, id)
    }
    return id
  }

  const userId = ref(getUserId())
  const currentSessionId = ref(null)
  const sessions = ref([])
  /** 每会话消息缓存: 切换会话不丢内容, 后台流式输出始终写入其所属会话 */
  const messageCache = new Map()
  /** 每会话历史加载序号: 丢弃并发加载中迟到的旧响应 */
  const historyTokens = new Map()
  /** 正在流式输出的会话 id 集合 (防止切回时被尚未落库的后端历史覆盖) */
  const streamingSessions = new Set()
  const EMPTY_MESSAGES = []
  const isStreaming = ref(false)
  /** 当前正在流式输出的会话 id (供会话列表在对应会话项旁显示"生成中"三点动画) */
  const streamingSessionId = ref(null)
  const pendingApproval = ref(null)
  const modelConfig = ref({ base_url: '', api_key: '', model: '', extra_params: {} })
  const workspaceCache = loadWorkspaceCache()
  /* 「新建对话」空会话拦截状态: 聚焦输入框信号 + 轻提示显隐 */
  const inputFocusSignal = ref(0)
  const emptySessionToast = ref(false)
  let emptyToastTimer = null
  /** 会话搜索聚焦信号: 全局快捷键 Ctrl+K → SessionList 搜索框 (跨组件通信) */
  const searchFocusSignal = ref(0)
  /** 后端连通性 (最近一次会话列表请求结果), 供状态栏指示灯使用 */
  const backendOnline = ref(true)

  function getMessagesOf(sessionId) {
    let list = messageCache.get(sessionId)
    if (!list) {
      // 必须是 reactive 数组: 否则 sendMessage push 消息不会触发界面更新
      list = reactive([])
      messageCache.set(sessionId, list)
    }
    return list
  }

  /**
   * 当前会话消息 (可写 computed):
   * 读 → 返回当前会话的缓存数组; 写 → 原地整组替换该数组的内容。
   * 流式回调持有缓存数组/消息对象的引用, 因此会话切换时输出不中断、切回即恢复。
   */
  const messages = computed({
    get: () => (currentSessionId.value ? getMessagesOf(currentSessionId.value) : EMPTY_MESSAGES),
    set: (next) => {
      if (!currentSessionId.value) return
      // 原地替换而不是换一个新数组: 数组引用可能正被流式回调持有,
      // 换掉它会让后续输出写进已废弃的数组, 界面上再也看不到
      const target = getMessagesOf(currentSessionId.value)
      target.splice(0, target.length, ...next)
    },
  })

  const currentMessages = computed(() => messages.value)
  const currentTitle = computed(() => {
    const session = sessions.value.find((s) => s.id === currentSessionId.value)
    return session?.title || '新会话'
  })

  function genSessionId() {
    return genId()
  }

  /** 从后端拉取会话列表,名字以后端为准;后端仍返回"新会话"时才用本地首句兜底 */
  async function refreshSessions() {
    try {
      const res = await listSessions(userId.value)
      const rows = res?.response || []
      const remote = rows.map((row) => normalizeSession(row, workspaceCache))
      for (const s of remote) {
        if (s.title === '新会话') {
          const local = sessions.value.find((ls) => ls.id === s.id)
          if (local && local.title !== '新会话') {
            s.title = local.title
          }
        }
      }
      // 后端还没登记、但本地已乐观创建的会话先留着, 否则刚发出的会话会
      // 从列表里瞬间消失(后端登记后由远端数据接管)
      const known = new Set(remote.map((s) => s.id))
      for (const s of sessions.value) {
        if (s.local && !known.has(s.id)) remote.push(s)
      }
      remote.sort((a, b) => b.createTime - a.createTime)
      sessions.value = remote
      backendOnline.value = true

      if (!currentSessionId.value && remote.length > 0) {
        currentSessionId.value = remote[0].id
      }
    } catch (e) {
      backendOnline.value = false
      console.error('拉取会话列表失败', e)
    }
  }

  /** 聚焦会话搜索框 (Ctrl+K / 原生菜单「搜索会话」) */
  function focusSessionSearch() {
    searchFocusSignal.value++
  }

  /** 应用启动时: 只从后端拉取会话列表, 为空则等待用户点 "+" 创建 */
  async function init() {
    // 注意: 这里绝不能无条件 currentSessionId = 列表第一条。
    // 首次刷新可能很慢, 期间用户完全可能已经发了消息(自动建了新会话),
    // 旧写法会把 currentSessionId 顶到列表里那条旧会话上, 于是:
    // 刚发出的消息落到新会话缓存里 → 当前显示的却是旧会话 → 界面退回待机页。
    // refreshSessions 自己只在 currentSessionId 仍为空时才自动选最近会话。
    await refreshSessions()
    const sessionId = currentSessionId.value
    // 消息缓存已存在 → 该会话已被用户使用过(或正在流式输出), 不要用历史覆盖
    if (sessionId && !messageCache.has(sessionId)) {
      await loadHistory(sessionId)
    }
    // 启动时把用户在设置里「设为默认」的模型配置应用到后端 (未设置/为空则跳过, 不阻塞首屏)
    applyStartupDefaultModel()
  }

  /** 读取「设为默认」的模型配置并提交后端, 让最终用户重启后无需重新选模型 */
  async function applyStartupDefaultModel() {
    try {
      const raw = JSON.parse(localStorage.getItem(MODEL_PROFILES_KEY) || 'null')
      const idx = raw?.defaultIndex
      if (!Number.isInteger(idx) || idx < 0 || idx >= (raw?.profiles?.length || 0)) return
      const p = raw.profiles[idx]
      if (!p || (!p.model && !p.base_url && !p.api_key)) return
      await switchModel({ model: p.model, base_url: p.base_url, api_key: p.api_key })
    } catch (e) {
      console.error('启动应用默认模型失败', e)
    }
  }

  /** 确保存在可用会话(首条消息快捷入口时自动创建) */
  async function ensureSession() {
    if (currentSessionId.value) return currentSessionId.value
    await createNewChat()
    return currentSessionId.value
  }

  /**
   * 计算单个 SSE 事件对 assistant 消息贡献的文本增量。
   * 后端 Result 结构: { code, message, response }
   *  - 最终结果: response 为 agentResult → 取其 answer/content
   *  - 审批中断 / 中间事件(工具状态): 仅 message → 取 message, 与已有内容间以空行分隔
   * 拼装规则与旧版 appendEventToMessage 完全一致, 区别仅在于增量交给打字机按节奏上屏。
   */
  function eventTextDelta(event, received) {
    if (!event) return ''
    if (event.response != null) {
      return formatAgentResult(event.response)
    }
    if (event.message) {
      return (received ? '\n\n' : '') + event.message
    }
    return ''
  }

  /**
   * 打字机渲染器: 把收到的文本按节奏逐字"打"到消息 content 上。
   * 后端答案全文随最后一个 SSE 事件一次性到达(不逐 token 下发), 逐字效果由本层实现。
   *
   *  - push(text): 流式期间持续喂入增量文本, 定时器匀速上屏
   *  - finish(): 流结束后自适应提速清空缓冲(长文约 40 tick 内打完), 打完才 resolve
   *  - flush(): 立即倾倒剩余文本(错误路径用, 保证错误提示不延迟)
   */
  function createTypewriter(message, { interval = 20, baseChars = 3 } = {}) {
    let buffer = ''
    let timer = null
    let ended = false
    let onDone = null

    function ensureTimer() {
      if (!timer) timer = setInterval(tick, interval)
    }

    function stopTimer() {
      if (timer) {
        clearInterval(timer)
        timer = null
      }
    }

    function tick() {
      if (!buffer.length) {
        // 缓冲已空且流已结束: 停表并唤醒 finish() 的等待方
        if (ended) {
          stopTimer()
          const cb = onDone
          onDone = null
          cb?.()
        }
        return
      }
      // 流结束后自适应提速: 至少按 缓冲/40 的速度打, 保证长文尾部 ~1s 内收尾
      const speed = ended ? Math.max(baseChars, Math.ceil(buffer.length / 40)) : baseChars
      message.content += buffer.slice(0, speed)
      buffer = buffer.slice(speed)
    }

    return {
      push(text) {
        if (!text) return
        buffer += text
        if (!ended) ensureTimer()
      },
      async finish() {
        ended = true
        if (buffer.length) ensureTimer()
        if (timer) {
          await new Promise((resolve) => {
            onDone = resolve
          })
        }
      },
      flush() {
        if (buffer.length) {
          message.content += buffer
          buffer = ''
        }
        ended = true
        stopTimer()
        const cb = onDone
        onDone = null
        cb?.()
      },
    }
  }

  /** 流结束后判断是否为审批中断: 最后一个事件只有 message、没有 response */
  function isApprovalInterrupt(events) {
    const last = events[events.length - 1]
    return !!last && last.response == null && !!last.message
  }

  async function sendMessage(content) {
    if (!content.trim() || isStreaming.value) return

    // 无会话时先建会话并等待后端注册完成(保证 chat 请求先于会话注册的契约不破坏);
    // 已有会话时这里不等待任何接口, 消息立即上屏
    if (!currentSessionId.value) await ensureSession()

    // 锁定发送时刻的会话与其消息数组: 后台流式输出不再受会话切换影响
    const sessionId = currentSessionId.value
    const sessionMessages = getMessagesOf(sessionId)
    const contentTrimmed = content.trim()

    // 乐观插入: 本地临时消息(唯一 id + pending 状态)不等接口返回立刻显示,
    // 成功后仅落定状态, 不重复插入, 避免重复渲染
    const localMessage = reactive({
      id: `local-${Date.now()}`,
      role: 'user',
      content: contentTrimmed,
      type: 'text',
      status: 'sending',
    })
    sessionMessages.push(localMessage)

    isStreaming.value = true
    streamingSessionId.value = sessionId
    streamingSessions.add(sessionId)

    // 首句写入本地会话名(后端未命名时兜底)
    const session = sessions.value.find((s) => s.id === sessionId)
    if (session && session.title === '新会话') {
      session.title = localTitle(contentTrimmed)
    }

    // 必须是 reactive: 裸对象 push 进 reactive 数组后, 直接改裸对象会绕过
    // Proxy 的 set 拦截, 界面收不到通知 —— AI 气泡会永远空白
    const assistantMessage = reactive({ role: 'assistant', content: '', type: 'stream' })
    sessionMessages.push(assistantMessage)

    // 打字机: 事件文本先进缓冲再逐字上屏; received 记录已收到的全部文本(供分隔符判断)
    const typewriter = createTypewriter(assistantMessage)
    let received = ''
    const events = []
    try {
      const stream = chatStream({
        message: contentTrimmed,
        user_id: userId.value,
        session_id: sessionId,
      })
      for await (const event of stream) {
        events.push(event)
        // 收到即计算文本增量入缓冲, 由打字机节奏逐字上屏
        const delta = eventTextDelta(event, received)
        received += delta
        typewriter.push(delta)
      }
      // 流结束: 等缓冲全部打完再落定, 保证逐字效果完整收尾
      await typewriter.finish()
      assistantMessage.type = 'text'
      // 成功: 流式接口不回显用户消息, 本地原文即真实消息 → 落定状态并去除 pending 标记
      localMessage.status = 'sent'
      if (isApprovalInterrupt(events)) {
        pendingApproval.value = {
          message: events[events.length - 1].message,
          sessionId,
        }
      }
      // 后端会生成会话名,流结束后刷新一次
      await refreshSessions()
    } catch (error) {
      // 失败: 剩余缓冲立即上屏, 错误信息不延迟; 保留消息并标记失败, 由 ChatWindow 展示错误并提供重试入口
      typewriter.flush()
      localMessage.status = 'failed'
      localMessage.error = error.message
      assistantMessage.content += (assistantMessage.content ? '\n\n' : '') + `错误: ${error.message}`
      assistantMessage.type = 'error'
    } finally {
      isStreaming.value = false
      streamingSessionId.value = null
      streamingSessions.delete(sessionId)
    }
  }

  /** 重试发送失败的消息: 按原文重发, 并清掉失败气泡与其后本次失败产生的错误提示 */
  async function retrySend(message) {
    if (!message || message.role !== 'user' || message.status !== 'failed') return
    if (isStreaming.value || !currentSessionId.value) return
    const list = getMessagesOf(currentSessionId.value)
    const idx = list.indexOf(message)
    if (idx === -1) return
    // 仅移除该失败消息及其后连续的 assistant 气泡(本次失败产生的错误提示)
    let end = idx + 1
    while (end < list.length && list[end].role === 'assistant') end++
    list.splice(idx, end - idx)
    await sendMessage(message.content)
  }

  /** 用户批准/拒绝工具调用，从暂停处恢复 agent */
  async function approve(decision) {
    if (!pendingApproval.value || isStreaming.value) return

    const approval = pendingApproval.value
    pendingApproval.value = null

    // 恢复流写入其所属会话的缓存, 与 sendMessage 相同的切换保护
    const sessionId = approval.sessionId
    const sessionMessages = getMessagesOf(sessionId)

    sessionMessages.push(reactive({
      role: 'assistant',
      content: `[操作${decision === 'yes' ? '已批准' : '已拒绝'}] ${approval.message}`,
      type: 'approval',
    }))

    // 同 sendMessage: 流式写入的气泡必须是 reactive 对象
    const assistantMessage = reactive({ role: 'assistant', content: '', type: 'stream' })
    sessionMessages.push(assistantMessage)
    isStreaming.value = true
    streamingSessionId.value = sessionId
    streamingSessions.add(sessionId)

    // 打字机: 与 sendMessage 相同的逐字上屏; received 记录已收到的全部文本(供分隔符判断)
    const typewriter = createTypewriter(assistantMessage)
    let received = ''
    const events = []
    try {
      const stream = approveStream({
        decision,
        session_id: sessionId,
      })
      for await (const event of stream) {
        events.push(event)
        // 收到即计算文本增量入缓冲, 由打字机节奏逐字上屏
        const delta = eventTextDelta(event, received)
        received += delta
        typewriter.push(delta)
      }
      // 流结束: 等缓冲全部打完再落定, 保证逐字效果完整收尾
      await typewriter.finish()
      assistantMessage.type = 'text'
      if (isApprovalInterrupt(events)) {
        pendingApproval.value = {
          message: events[events.length - 1].message,
          sessionId,
        }
      }
      await refreshSessions()
    } catch (error) {
      // 失败: 剩余缓冲立即上屏, 错误信息不延迟
      typewriter.flush()
      assistantMessage.content += (assistantMessage.content ? '\n\n' : '') + `错误: ${error.message}`
      assistantMessage.type = 'error'
    } finally {
      isStreaming.value = false
      streamingSessionId.value = null
      streamingSessions.delete(sessionId)
    }
  }

  /**
   * 独立判断函数: 当前活跃会话是否为"空会话"
   * (已创建会话但尚未发送任何消息, 即 messages 数组为空)
   * @returns {boolean}
   */
  function isActiveSessionEmpty() {
    return currentSessionId.value != null && messages.value.length === 0
  }

  /** 通过自增信号通知 MessageInput 组件聚焦输入框 (跨组件通信) */
  function focusMessageInput() {
    inputFocusSignal.value++
  }

  /** 在输入框上方弹出轻提示, 2 秒后自动消失 */
  function showEmptySessionToast() {
    emptySessionToast.value = true
    clearTimeout(emptyToastTimer)
    emptyToastTimer = setTimeout(() => {
      emptySessionToast.value = false
    }, 2000)
  }

  /**
   * 「新建对话」统一入口 (供 UI 按钮 / Ctrl+N / 原生菜单调用):
   * 当前会话已存在但还没发过消息时 → 不重复建会话, 聚焦输入框并轻提示,
   * 否则创建并切换到新会话, 创建后自动聚焦输入框。
   * 注: 旧版在此处做了「当前会话为空则不新建」的拦截, 但历史未加载完 /
   * 加载失败时会被误判为空会话, 导致 + 按钮看起来完全无效, 已移除。
   * @returns {Promise<boolean>} 是否创建了新会话
   */
  async function requestNewChat() {
    if (isActiveSessionEmpty()) {
      showEmptySessionToast()
      focusMessageInput()
      return false
    }
    await createNewChat()
    focusMessageInput()
    return true
  }

  async function createNewChat() {
    const sessionId = genSessionId()
    currentSessionId.value = sessionId
    messages.value = []
    pendingApproval.value = null
    sessions.value.unshift({
      id: sessionId,
      title: '新会话',
      workspacePath: '',
      createTime: Date.now(),
      local: true, // 后端登记前先留在列表里, 见 refreshSessions
    })
    try {
      await newChat({ message: '', user_id: userId.value, session_id: sessionId })
      await refreshSessions()
    } catch (e) {
      console.error('创建会话失败', e)
    }
  }

  async function loadHistory(sessionId) {
    currentSessionId.value = sessionId
    // 审批卡片跟随其所属会话: 切走再切回不丢
    if (pendingApproval.value?.sessionId !== sessionId) pendingApproval.value = null
    // 该会话正在流式输出: 本地实时缓冲是最新的(后端可能尚未落库), 不用历史覆盖
    if (streamingSessions.has(sessionId)) return

    // 同一会话可能被并发加载(如 init 自动加载 + 用户点选), 只认最后一次请求的结果
    const token = (historyTokens.get(sessionId) || 0) + 1
    historyTokens.set(sessionId, token)

    let list
    try {
      const res = await getHistory(sessionId)
      list = Array.isArray(res?.response)
        ? res.response.map((item) => ({
            role: item.type === 'human' ? 'user' : 'assistant',
            content: typeof item.content === 'string' ? item.content : JSON.stringify(item.content),
            type: 'text',
          }))
        : []
    } catch (e) {
      // 拉取失败: 保留已有内容(可能是刚发出的消息), 绝不能清空 ——
      // 旧实现在这里 messages.value = [] 会把用户刚发的消息抹掉, 界面退回待机页
      console.error('加载历史失败', e)
      return
    }

    // 等待期间该会话已开始流式输出, 或又发起了更新的加载: 本次结果已过期, 丢弃
    if (streamingSessions.has(sessionId)) return
    if (historyTokens.get(sessionId) !== token) return

    // 原地替换而非 messages.value = 新数组: 流式回调持有的是数组引用,
    // 换掉数组会让它的写入落在被丢弃的旧数组上, 永远显示不出来
    const target = getMessagesOf(sessionId)
    target.splice(0, target.length, ...list)
  }

  async function removeSession(sessionId) {
    // 乐观更新: 先从本地列表移除, 保证 UI 立即响应
    sessions.value = sessions.value.filter((s) => s.id !== sessionId)
    messageCache.delete(sessionId)

    try {
      await deleteChat(sessionId)
    } catch (e) {
      console.error('删除会话失败(后端未生效,列表已本地移除)', e)
    }

    if (currentSessionId.value === sessionId) {
      if (sessions.value.length > 0) {
        await loadHistory(sessions.value[0].id)
      } else {
        // 删空了就留空, 不再自动新建
        currentSessionId.value = null
        messages.value = []
        pendingApproval.value = null
      }
    } else {
      // 刷新成功则以后端为准; 刷新失败则保留本地乐观结果
      await refreshSessions().catch(() => {})
    }
  }

  async function switchModel(config) {
    try {
      const res = await chooseModel({ ...modelConfig.value, ...config })
      Object.assign(modelConfig.value, config)
      return res
    } catch (e) {
      console.error('切换模型失败', e)
      throw e
    }
  }

  async function restoreModel() {
    try {
      return await oldModel()
    } catch (e) {
      console.error('恢复模型失败', e)
      throw e
    }
  }

  /** 当前会话绑定的会话级工作目录（切换会话时自动跟随） */
  const currentWorkspacePath = computed(() => {
    const session = sessions.value.find((s) => s.id === currentSessionId.value)
    return session?.workspacePath || ''
  })

  /**
   * 为指定会话绑定工作目录（会话级，非全局）。
   * 乐观更新 UI -> 同步后端 -> 本地缓存兜底；失败时回滚并抛错。
   */
  async function setSessionWorkspace(sessionId, path) {
    if (!sessionId) throw new Error('当前没有可用的会话')
    const session = sessions.value.find((s) => s.id === sessionId)
    const prevPath = session?.workspacePath || ''

    // 乐观更新: 先让 UI 立即响应
    if (session) session.workspacePath = path
    workspaceCache[sessionId] = path
    saveWorkspaceCache(workspaceCache)

    try {
      const res = await chooseWorkplace({
        workplace: path,
        user_id: userId.value,
        session_id: sessionId,
      })
      return res
    } catch (e) {
      // 后端失败: 回滚 UI 与缓存，保证状态一致
      if (session) session.workspacePath = prevPath
      if (prevPath) {
        workspaceCache[sessionId] = prevPath
      } else {
        delete workspaceCache[sessionId]
      }
      saveWorkspaceCache(workspaceCache)
      console.error('设置工作目录失败', e)
      throw e
    }
  }

  /** 仅清除当前会话绑定的目录（用于徽章上的"取消绑定"操作） */
  async function clearSessionWorkspace(sessionId) {
    return setSessionWorkspace(sessionId, '')
  }

  return {
    userId,
    currentSessionId,
    sessions,
    messages,
    isStreaming,
    streamingSessionId,
    pendingApproval,
    modelConfig,
    currentMessages,
    currentTitle,
    currentWorkspacePath,
    inputFocusSignal,
    emptySessionToast,
    searchFocusSignal,
    backendOnline,
    isActiveSessionEmpty,
    requestNewChat,
    focusSessionSearch,
    init,
    sendMessage,
    retrySend,
    approve,
    createNewChat,
    loadHistory,
    removeSession,
    switchModel,
    restoreModel,
    setSessionWorkspace,
    clearSessionWorkspace,
  }
})