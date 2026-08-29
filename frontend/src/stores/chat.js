import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
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

/** 后端 DB 列名为 id/name/user_id/created_at，前端兼容两种命名风格 */
function normalizeSession(row) {
  return {
    id: row.id || row.session_id,
    title: row.name || row.session_name || '新会话',
    workplace: row.workplace || '',
    createTime: row.created_at || row.create_time || 0,
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
  const messages = ref([])
  const isStreaming = ref(false)
  const pendingApproval = ref(null)
  const modelConfig = ref({ base_url: '', api_key: '', model: '', extra_params: {} })
  const workplace = ref('')

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
      const remote = rows.map(normalizeSession)
      for (const s of remote) {
        if (s.title === '新会话') {
          const local = sessions.value.find((ls) => ls.id === s.id)
          if (local && local.title !== '新会话') {
            s.title = local.title
          }
        }
      }
      remote.sort((a, b) => b.createTime - a.createTime)
      sessions.value = remote

      if (!currentSessionId.value && remote.length > 0) {
        currentSessionId.value = remote[0].id
      }
    } catch (e) {
      console.error('拉取会话列表失败', e)
    }
  }

  /** 应用启动时: 只从后端拉取会话列表, 为空则等待用户点 "+" 创建 */
  async function init() {
    await refreshSessions()
    if (sessions.value.length > 0) {
      currentSessionId.value = sessions.value[0].id
      await loadHistory(currentSessionId.value)
    }
  }

  /** 确保存在可用会话(首条消息快捷入口时自动创建) */
  async function ensureSession() {
    if (currentSessionId.value) return currentSessionId.value
    await createNewChat()
    return currentSessionId.value
  }

  /**
   * 解析单个 SSE 事件并追加到 assistant 消息。
   * 后端 Result 结构: { code, message, response }
   *  - 最终结果: response 为 agentResult, message 为答案摘要
   *  - 审批中断 / 中间事件: 仅 message
   */
  function appendEventToMessage(message, event) {
    if (!event) return
    if (event.response != null) {
      message.content += formatAgentResult(event.response)
    } else if (event.message) {
      message.content += (message.content ? '\n\n' : '') + event.message
    }
  }

  /** 流结束后判断是否为审批中断: 最后一个事件只有 message、没有 response */
  function isApprovalInterrupt(events) {
    const last = events[events.length - 1]
    return !!last && last.response == null && !!last.message
  }

  async function sendMessage(content) {
    if (!content.trim() || isStreaming.value) return

    await ensureSession()

    const contentTrimmed = content.trim()
    messages.value.push({ role: 'user', content: contentTrimmed, type: 'text' })
    isStreaming.value = true

    // 首句写入本地会话名(后端未命名时兜底)
    const session = sessions.value.find((s) => s.id === currentSessionId.value)
    if (session && session.title === '新会话') {
      session.title = localTitle(contentTrimmed)
    }

    const assistantMessage = { role: 'assistant', content: '', type: 'stream' }
    messages.value.push(assistantMessage)

    const events = []
    try {
      const stream = chatStream({
        message: contentTrimmed,
        user_id: userId.value,
        session_id: currentSessionId.value,
      })
      for await (const event of stream) {
        events.push(event)
        appendEventToMessage(assistantMessage, event)
      }
      assistantMessage.type = 'text'
      if (isApprovalInterrupt(events)) {
        pendingApproval.value = {
          message: events[events.length - 1].message,
          sessionId: currentSessionId.value,
        }
      }
      // 后端会生成会话名,流结束后刷新一次
      await refreshSessions()
    } catch (error) {
      assistantMessage.content += (assistantMessage.content ? '\n\n' : '') + `错误: ${error.message}`
      assistantMessage.type = 'error'
    } finally {
      isStreaming.value = false
    }
  }

  /** 用户批准/拒绝工具调用，从暂停处恢复 agent */
  async function approve(decision) {
    if (!pendingApproval.value || isStreaming.value) return

    const approval = pendingApproval.value
    pendingApproval.value = null

    messages.value.push({
      role: 'assistant',
      content: `[操作${decision === 'yes' ? '已批准' : '已拒绝'}] ${approval.message}`,
      type: 'approval',
    })

    const assistantMessage = { role: 'assistant', content: '', type: 'stream' }
    messages.value.push(assistantMessage)
    isStreaming.value = true

    const events = []
    try {
      const stream = approveStream({
        decision,
        session_id: approval.sessionId,
      })
      for await (const event of stream) {
        events.push(event)
        appendEventToMessage(assistantMessage, event)
      }
      assistantMessage.type = 'text'
      if (isApprovalInterrupt(events)) {
        pendingApproval.value = {
          message: events[events.length - 1].message,
          sessionId: approval.sessionId,
        }
      }
      await refreshSessions()
    } catch (error) {
      assistantMessage.content += (assistantMessage.content ? '\n\n' : '') + `错误: ${error.message}`
      assistantMessage.type = 'error'
    } finally {
      isStreaming.value = false
    }
  }

  async function createNewChat() {
    const sessionId = genSessionId()
    currentSessionId.value = sessionId
    messages.value = []
    pendingApproval.value = null
    sessions.value.unshift({ id: sessionId, title: '新会话', workplace: '', createTime: Date.now() })
    try {
      await newChat({ message: '', user_id: userId.value, session_id: sessionId })
      await refreshSessions()
    } catch (e) {
      console.error('创建会话失败', e)
    }
  }

  async function loadHistory(sessionId) {
    currentSessionId.value = sessionId
    pendingApproval.value = null
    try {
      const res = await getHistory(sessionId)
      if (res?.response) {
        messages.value = res.response.map((item) => ({
          role: item.type === 'human' ? 'user' : 'assistant',
          content: typeof item.content === 'string' ? item.content : JSON.stringify(item.content),
          type: 'text',
        }))
      } else {
        messages.value = []
      }
    } catch (e) {
      console.error('加载历史失败', e)
      messages.value = []
    }
  }

  async function removeSession(sessionId) {
    // 乐观更新: 先从本地列表移除, 保证 UI 立即响应
    sessions.value = sessions.value.filter((s) => s.id !== sessionId)

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

  async function setWorkplace(path) {
    try {
      const res = await chooseWorkplace({
        workplace: path,
        user_id: userId.value,
        session_id: currentSessionId.value,
      })
      workplace.value = path
      return res
    } catch (e) {
      console.error('设置工作目录失败', e)
      throw e
    }
  }

  return {
    userId,
    currentSessionId,
    sessions,
    messages,
    isStreaming,
    pendingApproval,
    modelConfig,
    workplace,
    currentMessages,
    currentTitle,
    init,
    sendMessage,
    approve,
    createNewChat,
    loadHistory,
    removeSession,
    switchModel,
    restoreModel,
    setWorkplace,
  }
})