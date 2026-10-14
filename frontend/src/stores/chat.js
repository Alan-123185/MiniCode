import { defineStore } from 'pinia'
import { useToastStore } from './toast'
import { ref, computed, reactive, watch } from 'vue'
import {
  chatStream,
  approveStream,
  continueStream,
  editMessageStream,
  newChat,
  stopChat,
  listSessions,
  getHistory,
  deleteChat,
  addModel,
  setModel,
  updateModel,
  listModels,
  saveSettings as saveSettingsApi,
  getSettings,
  checkGit,
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

/** 旧版「5 组模型配置」的本地存储键 (已废弃, 仅用于启动时一次性迁移到后端数据库) */
const LEGACY_MODEL_PROFILES_KEY = 'minicodex_model_profiles'
/** 当前生效模型在后端库中的 id (本地只记 id, 配置本体一律以后端数据库为准) */
const ACTIVE_MODEL_ID_KEY = 'minicodex_active_model_id'

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
  // 本地单用户: 固定 ID, 不再按 localStorage/origin 生成 (原逻辑会导致
  // dev/打包/file:// 各拿一个 ID, 历史会话"凭空消失")。所有请求统一带这个值。
  const FIXED_USER_ID = 'user_local'
  const userId = ref(FIXED_USER_ID)

  const toast = useToastStore()
  const currentSessionId = ref(null)
  const sessions = ref([])
  /** 每会话消息缓存: 切换会话不丢内容, 后台流式输出始终写入其所属会话 */
  const messageCache = new Map()
  /** 每会话历史加载序号: 丢弃并发加载中迟到的旧响应 */
  const historyTokens = new Map()
  /**
   * 正在流式输出的会话 id 集合 —— 并行生成的唯一事实来源 (single source of truth)。
   * 必须是 reactive Set: 界面(停止按钮/三点动画/状态栏)靠它订阅"哪几条会话在跑"。
   * 同时承担两个职责:
   *  - 防止切回时被尚未落库的后端历史覆盖 (loadHistory 的跳过条件, 见 hasLocalContent)
   *  - 会话级准入闸门: 同一会话同一时刻只允许一路流 (sendMessage / approve / continue /
   *    editMessage / retrySend 都靠它判重, 后端同一 thread_id 也只能跑一条)
   */
  const streamingSessions = reactive(new Set())
  const EMPTY_MESSAGES = []
  /**
   * 是否有任意会话在生成 —— 由 streamingSessions 派生, 不再手工维护。
   * 改成 computed 之前它是手工 set 的 ref, 4 处流各自 finally 里置 false,
   * 并行时先结束的那条会把"还有会话在跑"的事实抹掉, 界面状态直接错乱。
   */
  const isStreaming = computed(() => streamingSessions.size > 0)
  /** 最近启动流式输出的会话 id (仅作提示用途; 并行判定一律看 streamingSessions) */
  const streamingSessionId = ref(null)
  /**
   * 当前会话是否正在流式输出。
   * 界面(停止按钮/输入框占位符/编辑入口)一律以此为准, 不要用全局 isStreaming ——
   * isStreaming 只表示"有某个会话在生成", 切到没有任务在跑的会话时它仍为 true。
   */
  const isCurrentSessionStreaming = computed(() =>
    currentSessionId.value != null && streamingSessions.has(currentSessionId.value)
  )
  /** 当前会话没有任务, 但有别的会话在后台并行生成 */
  const hasBackgroundStreaming = computed(
    () => isStreaming.value && !isCurrentSessionStreaming.value
  )
  /** 正在生成中的会话条数 (状态栏并行提示) */
  const streamingCount = computed(() => streamingSessions.size)
  /** 正在生成的会话标题列表 (状态栏: 并行时全部列出, 避免用户误以为当前会话在跑) */
  const streamingSessionTitles = computed(() =>
    [...streamingSessions].map((id) => sessions.value.find((s) => s.id === id)?.title || '未命名会话')
  )
  /** 状态栏一句话: 只有当前会话在跑 → "生成中…"; 并行/后台 → "N 个会话生成中…" */
  const streamingStatusText = computed(() => {
    const n = streamingSessions.size
    if (!n) return ''
    if (n === 1 && isCurrentSessionStreaming.value) return '生成中…'
    return `${n} 个会话生成中…`
  })
  /** 状态栏 title 提示: 点名是哪几条会话在跑 */
  const streamingStatusTitle = computed(() =>
    streamingSessions.size ? `正在生成: ${streamingSessionTitles.value.join('、')}` : ''
  )
  const pendingApproval = ref(null)
  /**
   * 每会话的一句话状态 (如"正在调用 file_edit 工具…"), 仅作轻提示, 不进消息正文。
   * 并行生成后必须按会话分开存: 单值会让 A 的工具状态串到 B 的界面上。
   */
  const sessionStatus = reactive(new Map())
  /** 当前会话的状态 (界面只展示自己这条会话的) */
  const currentStatus = computed(() =>
    currentSessionId.value ? sessionStatus.get(currentSessionId.value) || '' : ''
  )
  /** 当前生效模型的运行时副本 (model_name/base_url/api_key, 由后端 get_model/set_model 数据回填) */
  const modelConfig = ref({ base_url: '', api_key: '', model: '', extra_params: {} })
  /** 后端模型列表 (GET /MiniCode/get_model → list[ModelGetRequest], 数据源是数据库而非本地存储) */
  const models = ref([])
  /** 当前生效模型在库中的 id: 持久化到本地, 供重启后按 id 调 set_model 恢复后端运行时配置 */
  const activeModelId = ref(Number(localStorage.getItem(ACTIVE_MODEL_ID_KEY)) || null)
  const workspaceCache = loadWorkspaceCache()
  /* 「新建对话」空会话拦截状态: 聚焦输入框信号 (轻提示已统一走 toast store) */
  const inputFocusSignal = ref(0)
  /** 会话搜索聚焦信号: 全局快捷键 Ctrl+K → SessionList 搜索框 (跨组件通信) */
  const searchFocusSignal = ref(0)
  /** 后端连通性 (最近一次会话列表请求结果), 供状态栏指示灯使用 */
  const backendOnline = ref(true)
  /** 已向后端发出停止请求的会话: 区分「用户主动停止」与真实异常 (停止时连接可能被强制取消) */
  const stoppingSessions = new Set()
  /** 上次生成异常中断、可调用 /MiniCode/continue 恢复的会话 (reactive Set 供 UI 响应) */
  const interruptedSessions = reactive(new Set())

  /* ---------- 并行生成: 流式状态的记账助手 ----------
   * 4 条流 (chat / approve / continue / editMessage) 的起止逻辑完全同构,
   * 抽成助手避免各处手写 isStreaming/streamingSessionId 的三行赋值 ——
   * 之前正是这 8 处手写赋值在并行下互相覆盖, 导致状态错乱。 */

  /** 该会话是否已有流在跑 (并行生成下的准入闸门: 只拦同一会话的第二次请求) */
  function isSessionStreaming(sessionId) {
    return !!sessionId && streamingSessions.has(sessionId)
  }

  /** 标记某会话开始流式输出; 顺带清掉它上一轮的残留状态提示 */
  function beginStream(sessionId) {
    streamingSessionId.value = sessionId
    streamingSessions.add(sessionId)
    sessionStatus.delete(sessionId)
  }

  /** 标记某会话流式结束。只有"最近启动的那条"结束时才清 streamingSessionId, 别条并发不受影响 */
  function endStream(sessionId) {
    streamingSessions.delete(sessionId)
    sessionStatus.delete(sessionId)
    if (streamingSessionId.value === sessionId) streamingSessionId.value = null
  }
  /** 生成参数设置 (对应 requestcommon/settingsRequest.py: temperature/theme/think_level), 后端持久化 */
  const DEFAULT_SETTINGS = { temperature: 0.3, theme: true, think_level: 2 }
  const appSettings = ref({ ...DEFAULT_SETTINGS })
  const settingsLoaded = ref(false)
  /** Git 环境检测结果 (GET /MiniCode/checkGit): null=尚未检测完成 */
  const gitReady = ref(null)

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
   * 该会话在前端是否已经有内容 (含正在流式输出的)。
   * 不能用 messageCache.has() 代替: 渲染时 messages 计算属性就会调用 getMessagesOf
   * 顺手建出一个空数组, 于是"缓存已存在"并不代表"已经有内容"。
   */
  function hasLocalContent(sessionId) {
    if (streamingSessions.has(sessionId)) return true
    const list = messageCache.get(sessionId)
    return !!list && list.length > 0
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
    // 必须用 hasLocalContent 而不是 messageCache.has(sessionId):
    // 渲染会在 refreshSessions 选中会话后立刻调 getMessagesOf 建好空缓存, 而 init 的
    // 续行是在渲染之后才执行, 于是旧的判断永远为真 → 打开应用时历史永远不加载,
    // 明明有历史的会话也只显示"开始一个新的对话吧"。
    if (sessionId && !hasLocalContent(sessionId)) {
      await loadHistory(sessionId)
    }
    // 启动时从后端数据库恢复当前生效模型 (后端运行时配置重启即失, 必须重新激活; 失败不阻塞首屏)
    restoreActiveModel()
    // 从后端加载生成参数 (温度/主题/思考等级), 失败时静默保持默认
    loadSettings()
    // 检测后端 Git 环境 (结果仅影响状态栏指示灯, 不阻塞启动)
    checkGitStatus()
  }

  /**
   * 启动时从后端数据库恢复当前生效模型。
   * 优先级: 上次选中的 id (本地缓存) → 库中标记 is_default 的模型 → 列表第一条。
   * 后端 model_config 是纯运行时配置, 重启即失, 因此必须在启动时重新 set_model 激活。
   */
  async function restoreActiveModel() {
    try {
      await refreshModels()
      if (!models.value.length) {
        await migrateLegacyDefaultProfile()
        return
      }
      const pick =
        models.value.find((m) => m.id === activeModelId.value) ||
        models.value.find((m) => m.is_default) ||
        models.value[0]
      if (pick) await activateModel(pick.id)
    } catch (e) {
      console.error('启动恢复模型失败', e)
    }
  }

  /** 一次性迁移: 旧版「5 组本地配置」已废弃, 库为空时把其中「设为默认」的那组写入后端数据库 */
  async function migrateLegacyDefaultProfile() {
    let raw = null
    try {
      raw = JSON.parse(localStorage.getItem(LEGACY_MODEL_PROFILES_KEY) || 'null')
    } catch {
      return
    }
    localStorage.removeItem(LEGACY_MODEL_PROFILES_KEY)
    const idx = raw?.defaultIndex
    const p = raw?.profiles?.[idx]
    if (!Number.isInteger(idx) || !p || (!p.model && !p.base_url && !p.api_key)) return
    try {
      await addNewModel({ model: p.model, base_url: p.base_url, api_key: p.api_key })
    } catch (e) {
      console.error('迁移本地默认模型到后端失败', e)
    }
  }

  /** 确保存在可用会话(首条消息快捷入口时自动创建) */
  async function ensureSession() {
    if (currentSessionId.value) return currentSessionId.value
    await createNewChat()
    return currentSessionId.value
  }

  /**
   * 把后端工具状态事件 (str(toolstatusEvent), 形如
   * `status=1 tool_name='file_edit' args={...} result=... user_prompt=... session_id=...`)
   * 解析成一句简短的「当前在干嘛」提示。解析不出工具名时退化为原文。
   * status: -1 失败 / 0 成功 / 1 尝试调用 / 2 用户拒绝 (对应后端 config/data.py)
   */
  function formatToolStatus(raw) {
    const text = String(raw ?? '')
    const tool = text.match(/tool_name='([^']*)'/)?.[1] || ''
    const status = Number(text.match(/status=(-?\d+)/)?.[1])
    switch (status) {
      case 1:
        return tool ? `正在调用 ${tool} 工具…` : '正在调用工具…'
      case 0:
        return tool ? `${tool} 执行成功` : '工具执行成功'
      case -1:
        return tool ? `${tool} 执行失败` : '工具执行失败'
      case 2:
        return tool ? `已拒绝 ${tool}` : '已拒绝工具调用'
      default:
        return tool ? `正在处理 ${tool}…` : text
    }
  }

  /* ================= 工具调用实时消息 (折叠展示, 不进正文) ================= */

  /**
   * 后端会下发的非工具类系统提示 (service/chatService.py)。
   * 这些是真正的"正文级"信息, 必须进正文、不能被工具面板兜底吞掉。
   */
  function isSystemNotice(text) {
    return (
      text.includes('已停止生成') ||
      text.includes('没有可用的安全检查点') ||
      text.includes('未找到或已被影响') ||
      text.includes('不存在或未初始化') ||
      text.includes('没有可用的快照')
    )
  }

  /**
   * 把后端下发的一条工具状态消息归类。
   * 后端有两种形态:
   *  1) 原始 toolstatusEvent 的 repr (仅"重试超限"分支): 含 `tool_name='...'` 与 `status=N`
   *     status: -1 失败 / 0 成功 / 1 尝试调用 / 2 用户拒绝 (对应后端 config/data.py)
   *  2) manage_toolstatusEvent 转成的中文短句 (绝大多数工具事件走这里), 如
   *     "尝试编辑文件 X" / "读取文件 X (lines 1-10)" / "编辑文件失败: ..." / "拒绝运行 ..."
   *
   * 返回 { tool, phase: 'try'|'result', status, label } 或 null (非工具事件)。
   * phase='try' 用于新增一条 running 记录; phase='result' 用于回填最近一条同工具记录。
   */
  function classifyToolEvent(raw) {
    // 形态 0: 结构化对象 (后端 toolEvent 载荷 {status, message}): 按 status 精确归类, 不猜文案。
    // status: 1 尝试/running, 0 成功, -1 失败, 2 拒绝 (对应后端 config/data.py)。
    if (raw && typeof raw === 'object' && 'status' in raw) {
      const status = Number(raw.status)
      if (![1, 0, -1, 2].includes(status)) return null
      const label = String(raw.message ?? '') || formatToolStatus(String(raw))
      const s = status === 1 ? 'running' : status === 0 ? 'success' : status === -1 ? 'failed' : 'refused'
      return { tool: raw.tool_name || '', phase: status === 1 ? 'try' : 'result', status: s, label }
    }
    const text = String(raw ?? '')
    if (!text) return null

    // 形态 1: 原始 repr (含 tool_name=)
    if (text.includes('tool_name=')) {
      const tool = text.match(/tool_name='([^']*)'/)?.[1] || ''
      const status = Number(text.match(/status=(-?\d+)/)?.[1])
      // 只在状态可识别时当作工具事件, 否则交回上层按原文处理
      if ([1, 0, -1, 2].includes(status)) {
        const phase = status === 1 ? 'try' : 'result'
        const s = status === 1 ? 'running' : status === 0 ? 'success' : status === -1 ? 'failed' : 'refused'
        return { tool, phase, status: s, label: formatToolStatus(text) }
      }
      return null
    }

    // 形态 2: 中文短句。按动词前缀/关键词识别, 尽量覆盖 core/toolStatusEvent.py 的全部文案。
    // 尝试类 (tool_try)
    if (/^尝试(编辑|删除|创建|运行|执行|回滚)/.test(text) || /^try run/i.test(text)) {
      return { tool: '', phase: 'try', status: 'running', label: text }
    }
    // 拒绝类 (tool_refused)
    if (/^拒绝(编辑|删除|创建|运行|执行|回滚)/.test(text) || /refused/i.test(text)) {
      return { tool: '', phase: 'result', status: 'refused', label: text }
    }
    // 失败类 (tool_failed): 统一含"失败"/"failed"
    if (/失败/.test(text) || /failed/i.test(text)) {
      return { tool: '', phase: 'result', status: 'failed', label: text }
    }
    // 成功类 (tool_success): 读取/查看文件夹/删除文件/创建文件/运行...成功/执行/回滚/编辑成功 message
    if (
      /^读取文件/.test(text) ||
      /^查看文件夹/.test(text) ||
      /^删除文件/.test(text) ||
      /^创建文件/.test(text) ||
      /^运行 .*(成功)?$/.test(text) ||
      /成功$/.test(text) ||
      /^执行 /.test(text) ||
      /^回滚/.test(text) ||
      /^run /i.test(text) ||
      /^已(修改|创建|删除|替换)/.test(text) ||
      /已成功替换/.test(text)
    ) {
      return { tool: '', phase: 'result', status: 'success', label: text }
    }
    return null
  }

  /**
   * 把一条工具状态消息并入 assistant 消息的 toolEvents 折叠列表。
   *  - try: 追加一条 running 记录
   *  - result: 回填最近一条同工具且仍 running 的记录 (就地替换"尝试"那行), 找不到则新开一条
   */
  function applyToolEvent(toolEvents, info) {
    if (info.phase === 'try') {
      toolEvents.push({ tool: info.tool, status: 'running', label: info.label })
      return
    }
    // 结果: 优先回填"同工具 + 仍 running"的最近一条
    for (let i = toolEvents.length - 1; i >= 0; i--) {
      const item = toolEvents[i]
      if (item.status === 'running' && (!info.tool || !item.tool || item.tool === info.tool)) {
        item.status = info.status
        item.label = info.label
        return
      }
    }
    toolEvents.push({ tool: info.tool, status: info.status, label: info.label })
  }

  /**
   * 计算单个 SSE 事件对 assistant 消息贡献的文本增量。
   * 后端 Result 结构: { code, message, response }
   *  - 最终结果: response 为 agentResult → 取其 answer/content (交打字机逐字上屏)
   *  - 工具调用实时消息 (尝试/结果): 剥离出正文, 折叠进 message.toolEvents, 不刷屏
   *  - 审批中断 (见 isApprovalMessage) / 系统提示 (如"已停止生成。"): 追加到正文
   *
   * @param sessionId 该流所属会话 —— 进度提示按会话写, 并行时不会串到别的会话上
   */
  function eventTextDelta(event, received, assistantMessage, sessionId) {
    if (!event) return ''
    /** 写"当前在干嘛"的轻提示: 按会话记账, 界面只读自己那条 */
    function setStatus(text) {
      if (sessionId) sessionStatus.set(sessionId, text)
    }
    if (event.response != null) {
      // 最终答案到达: 清掉进度提示, 交给打字机上屏
      setStatus('')
      return formatAgentResult(event.response)
    }
    // 工具状态事件 (后端下发的结构化载荷 {status, message}): 按 status 精确归类进折叠面板,
    // 不靠猜中文文案。status: 1 尝试/running, 0 成功, -1 失败, 2 拒绝 (config/data.py)。
    // 这是"当前会话"工具调用能进折窗的正路 —— 历史会话走 buildHistoryMessages 的结构化
    // tool_calls, 两条路统一, 不再把工具调用漏进正文变成纯文字。
    if (event.toolEvent && assistantMessage) {
      const info = classifyToolEvent(event.toolEvent)
      if (info) {
        if (!assistantMessage.toolEvents) assistantMessage.toolEvents = []
        applyToolEvent(assistantMessage.toolEvents, info)
        setStatus(info.label)
        return ''
      }
    }
    if (event.message) {
      const text = String(event.message)
      // 审批中断: 交审批卡片, 文本仍按原逻辑进正文 (兼容既有行为)
      if (isApprovalMessage(text)) {
        return (received ? '\n\n' : '') + text
      }
      // 工具调用实时消息: 折叠进 toolEvents, 不进正文、不走打字机
      const info = classifyToolEvent(text)
      if (info && assistantMessage) {
        if (!assistantMessage.toolEvents) assistantMessage.toolEvents = []
        applyToolEvent(assistantMessage.toolEvents, info)
        // 同步轻量进度提示 (正文尚未出现时展示"当前在干嘛"), 与折叠列表互不冲突
        setStatus(info.label)
        return ''
      }
      // 兜底: 无法归类、但存在"进行中"的工具记录且不是系统提示时,
      // 视为上一条 running 工具的结果 (如 edit_file 模糊匹配返回的多行 diff),
      // 回填以避免 diff 泄漏进正文、也避免该条永久转圈。
      if (assistantMessage && assistantMessage.toolEvents?.some((ev) => ev.status === 'running') && !isSystemNotice(text)) {
        applyToolEvent(assistantMessage.toolEvents, { tool: '', phase: 'result', status: 'success', label: text })
        setStatus(text)
        return ''
      }
      // 其他纯文本 info (已停止生成 / 异常提示等): 追加到正文
      return (received ? '\n\n' : '') + text
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

  /**
   * 把后端审批中断的 message 解析成人类可读文本。
   * 新契约 (core/InterruptInfo.py manage_InterruptInfo) 下后端下发的已经是人话
   * (如 `我想编辑 calculator.py`), 原样展示即可; 旧契约的
   * `tool_name='file_edit' tool_args={...} message='I want to use file_edit, do you agree?'`
   * 仍然兼容解析。
   */
  function formatInterruptMessage(raw) {
    const text = String(raw ?? '').trim()
    const tool = text.match(/tool_name='([^']*)'/)?.[1] || ''
    const marker = "message='"
    const idx = text.indexOf(marker)
    if (!tool && idx === -1) return text
    let body = text
    if (idx !== -1) {
      body = text.slice(idx + marker.length)
      if (body.endsWith("'")) body = body.slice(0, -1)
    }
    return tool ? `【${tool}】${body}` : body
  }

  /**
   * 后端审批中断文案 (core/InterruptInfo.py manage_InterruptInfo 的 6 个分支):
   * 「我想执行 …」「我想运行脚本 …」「我想编辑 …」「我想创建 …」「我想删除 …」「我将执行回滚操作」。
   * LEGACY 文案用于兼容旧后端 (`... do you agree?`)。
   */
  const APPROVAL_MESSAGE_RE = /^(我想执行|我想运行脚本|我想编辑|我想创建|我想删除|我将执行回滚操作)/
  const LEGACY_APPROVAL_HINT = 'do you agree?'

  /** 该文案是否为工具调用审批中断 (而非停止/失败等纯提示) */
  function isApprovalMessage(raw) {
    const text = String(raw ?? '').trim()
    if (!text) return false
    return APPROVAL_MESSAGE_RE.test(text) || text.includes(LEGACY_APPROVAL_HINT)
  }

  /**
   * 流结束后判断是否为审批中断: 最后一个事件只有 message、没有 response,
   * 且 message 命中审批文案 (见 isApprovalMessage)。
   * 停止/编辑失败/恢复失败等 info 事件同样「只有 message」, 不加内容判定会误弹审批卡片。
   */
  function isApprovalInterrupt(events) {
    const last = events[events.length - 1]
    if (!last || last.response != null || !last.message) return false
    return isApprovalMessage(last.message)
  }

  /**
   * 收尾: 整轮流既没有正文也没有工具记录时, 移除这个"空气泡"。
   * 否则界面会永久停在只有三点动画的空白气泡上 ——
   * 后端 approve 在「当前没有待审批中断」时就是这样: 一个事件都不下发。
   */
  function dropEmptyAssistantMessage(sessionMessages, assistantMessage, hint) {
    if (assistantMessage.content || assistantMessage.toolEvents?.length) return false
    const idx = sessionMessages.indexOf(assistantMessage)
    if (idx !== -1) sessionMessages.splice(idx, 1)
    if (hint) toast.info(hint)
    return true
  }

  /**
   * 收尾时把仍处于「running」的工具记录标记为「stopped」。
   * 流结束后(正常/异常/用户停止)若某条工具的 result 事件始终没到, 不标记就会在
   * 折叠面板里永远转圈 —— 例如用户在工具执行过程中点了停止。
   */
  function finalizeToolEvents(assistantMessage) {
    const list = assistantMessage?.toolEvents
    if (!list) return
    for (const ev of list) {
      if (ev.status === 'running') ev.status = 'stopped'
    }
  }

  async function sendMessage(content) {
    if (!content.trim()) return

    // 无会话时先建会话并等待后端注册完成(保证 chat 请求先于会话注册的契约不破坏);
    // 已有会话时这里不等待任何接口, 消息立即上屏
    if (!currentSessionId.value) await ensureSession()

    // 锁定发送时刻的会话与其消息数组: 后台流式输出不再受会话切换影响
    const sessionId = currentSessionId.value
    // 并行生成的准入闸门: 只拦"这条会话自己"的第二次请求。
    // 别的会话正在并行生成不影响本会话发送 —— 后端 running_tasks/stop_flags 均按
    // session_id 隔离, 检查点按 thread_id 隔离, 天然支持多会话同时跑。
    if (isSessionStreaming(sessionId)) return
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

    beginStream(sessionId)

    // 首句写入本地会话名(后端未命名时兜底)
    const session = sessions.value.find((s) => s.id === sessionId)
    if (session && session.title === '新会话') {
      session.title = localTitle(contentTrimmed)
    }

    // 必须是 reactive: 裸对象 push 进 reactive 数组后, 直接改裸对象会绕过
    // Proxy 的 set 拦截, 界面收不到通知 —— AI 气泡会永远空白
    // toolEvents: 工具调用实时消息的折叠列表 (尝试/结果), 不进正文
    const assistantMessage = reactive({ role: 'assistant', content: '', type: 'stream', toolEvents: [] })
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
        const delta = eventTextDelta(event, received, assistantMessage, sessionId)
        received += delta
        typewriter.push(delta)
      }
      // 流结束: 等缓冲全部打完再落定, 保证逐字效果完整收尾
      await typewriter.finish()
      assistantMessage.type = 'text'
      finalizeToolEvents(assistantMessage)
      // 成功: 流式接口不回显用户消息, 本地原文即真实消息 → 落定状态并去除 pending 标记
      localMessage.status = 'sent'
      interruptedSessions.delete(sessionId)
      if (isApprovalInterrupt(events)) {
        pendingApproval.value = {
          message: formatInterruptMessage(events[events.length - 1].message),
          sessionId,
        }
      }
      dropEmptyAssistantMessage(sessionMessages, assistantMessage, '本次生成没有返回任何内容')
      // 后端会生成会话名,流结束后刷新一次
      await refreshSessions()
    } catch (error) {
      // 失败: 剩余缓冲立即上屏, 错误信息不延迟; 保留消息并标记失败, 由 ChatWindow 展示错误并提供重试入口
      typewriter.flush()
      finalizeToolEvents(assistantMessage)
      if (stoppingSessions.has(sessionId)) {
        // 用户主动停止: 连接被后端强制取消属预期行为, 按正常收尾展示已生成内容
        assistantMessage.type = 'text'
        localMessage.status = 'sent'
        dropEmptyAssistantMessage(sessionMessages, assistantMessage, null)
      } else {
        localMessage.status = 'failed'
        localMessage.error = error.message
        assistantMessage.content += (assistantMessage.content ? '\n\n' : '') + `错误: ${error.message}`
        assistantMessage.type = 'error'
        // 标记会话可恢复: 用户可在 UI 上调用 /MiniCode/continue 从检查点续跑
        interruptedSessions.add(sessionId)
      }
    } finally {
      // 停止标记只服务于"当前这轮流", 必须在这里清掉:
      // 漏清会让该会话之后所有真实异常都被误判成"用户主动停止"(不报错、也不给恢复入口)
      stoppingSessions.delete(sessionId)
      endStream(sessionId)
    }
  }

  /** 重试发送失败的消息: 按原文重发, 并清掉失败气泡与其后本次失败产生的错误提示 */
  async function retrySend(message) {
    if (!message || message.role !== 'user' || message.status !== 'failed') return
    if (!currentSessionId.value) return
    // 并行闸门: 只拦"这条会话自己"正在生成的情况
    if (isSessionStreaming(currentSessionId.value)) return
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
    if (!pendingApproval.value) return

    const approval = pendingApproval.value
    // 并行闸门: 只拦"这条审批所属会话"自己正在生成的情况
    if (isSessionStreaming(approval.sessionId)) return

    // 兜底校验: 审批所属会话必须仍在会话列表里。它可能已被删除(或本地列表
    // 还没同步到它), 此时绝不能发请求 —— 既会打到一个不存在的 session_id,
    // 下面的 getMessagesOf 还会把已删会话的消息缓存凭空重建, 等于复活该会话。
    if (!sessions.value.some((s) => s.id === approval.sessionId)) {
      pendingApproval.value = null
      return
    }
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
    const assistantMessage = reactive({ role: 'assistant', content: '', type: 'stream', toolEvents: [] })
    sessionMessages.push(assistantMessage)
    beginStream(sessionId)

    // 打字机: 与 sendMessage 相同的逐字上屏; received 记录已收到的全部文本(供分隔符判断)
    const typewriter = createTypewriter(assistantMessage)
    let received = ''
    const events = []
    try {
      const stream = approveStream({
        decision,
        session_id: sessionId,
        // decisionRequst.user_id 是必填字段, 漏传会被 FastAPI 判 422 (前端表现为 "SSE 连接失败: 422")
        user_id: userId.value,
      })
      for await (const event of stream) {
        events.push(event)
        // 收到即计算文本增量入缓冲, 由打字机节奏逐字上屏
        const delta = eventTextDelta(event, received, assistantMessage, sessionId)
        received += delta
        typewriter.push(delta)
      }
      // 流结束: 等缓冲全部打完再落定, 保证逐字效果完整收尾
      await typewriter.finish()
      assistantMessage.type = 'text'
      finalizeToolEvents(assistantMessage)
      interruptedSessions.delete(sessionId)
      if (isApprovalInterrupt(events)) {
        pendingApproval.value = {
          message: formatInterruptMessage(events[events.length - 1].message),
          sessionId,
        }
      }
      // 后端 chatService.approve 在没有待审批中断时一个事件都不下发 (has_interrupt 为假),
      // 此时不能留一个永远转圈的空气泡
      dropEmptyAssistantMessage(sessionMessages, assistantMessage, '后端当前没有待审批的中断, 本次操作已忽略')
      await refreshSessions()
    } catch (error) {
      // 失败: 剩余缓冲立即上屏, 错误信息不延迟
      typewriter.flush()
      finalizeToolEvents(assistantMessage)
      if (stoppingSessions.has(sessionId)) {
        // 用户主动停止: 连接被后端取消属预期行为
        assistantMessage.type = 'text'
        dropEmptyAssistantMessage(sessionMessages, assistantMessage, null)
      } else {
        assistantMessage.content += (assistantMessage.content ? '\n\n' : '') + `错误: ${error.message}`
        assistantMessage.type = 'error'
        // 与 sendMessage 一致: 失败后可让用户从检查点续跑, 否则审批中断就再也回不去了
        interruptedSessions.add(sessionId)
      }
    } finally {
      stoppingSessions.delete(sessionId)
      endStream(sessionId)
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
  /** 空会话轻提示: 统一走 toast store, 不再由 chat store 自持 UI 状态 */
  function showEmptySessionToast() {
    toast.info('当前对话尚未开始')
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
  /* ================= 历史消息重建 (后端回传全部 human/ai/tool 消息) ================= */

  /** LangGraph 消息 content 可能是 str 或多模态块数组, 统一转成可渲染文本 */
  function historyText(content) {
    if (content == null) return ''
    if (typeof content === 'string') return content
    if (Array.isArray(content)) {
      return content
        .map((block) => (typeof block === 'string' ? block : block?.text ?? ''))
        .filter(Boolean)
        .join('\n')
    }
    return JSON.stringify(content)
  }

  /** 首行摘要: 工具结果往往多行且带 [system Info] 噪音, 折叠面板里只显示第一行 */
  function firstMeaningfulLine(text, max = 100) {
    const line = String(text ?? '').split('\n').find((l) => l.trim()) || ''
    const trimmed = line.trim()
    return trimmed.length > max ? `${trimmed.slice(0, max)}…` : trimmed
  }

  /**
   * 判断一条 ToolMessage 的内容是否表示失败。
   * toolResult 的 success 标志没有随消息落库 (toolNode 只持久化了 content), ToolMessage.status
   * 也始终是 langchain 的默认值 "success", 只能按内容特征推断 —— 与 classifyToolEvent 的
   * 中文短句识别保持同一套关键词。
   */
  function looksLikeToolFailure(text) {
    const t = String(text ?? '')
    if (!t.trim()) return false
    return (
      /失败/.test(t) ||
      /failed/i.test(t) ||
      /\[system Info\]/i.test(t) ||
      /未找到|不存在/.test(t)
    )
  }

  /** 把一条 ToolMessage 回填进 assistant.toolEvents (优先按 tool_call_id 精确匹配) */
  function applyHistoryToolResult(assistant, toolMsg) {
    const callId = toolMsg?.tool_call_id || null
    const name = toolMsg?.name || ''
    const content = historyText(toolMsg?.content)
    const failed = looksLikeToolFailure(content)

    // 先按 tool_call_id 精确命中"仍在等结果"的那条
    let target = null
    if (callId) {
      for (let i = assistant.toolEvents.length - 1; i >= 0; i--) {
        const ev = assistant.toolEvents[i]
        if (ev.id === callId && ev.status === 'running') {
          target = ev
          break
        }
      }
    }
    // 兜底: 退回 applyToolEvent 的同款策略 —— 最近一条仍 running 的同工具记录
    if (!target) {
      for (let i = assistant.toolEvents.length - 1; i >= 0; i--) {
        const ev = assistant.toolEvents[i]
        if (ev.status === 'running' && (!name || !ev.tool || ev.tool === name)) {
          target = ev
          break
        }
      }
    }

    const tool = target?.tool || name
    const entry = {
      id: callId,
      tool,
      status: failed ? 'failed' : 'success',
      label: failed
        ? `${tool || '工具'} 执行失败${content ? `: ${firstMeaningfulLine(content)}` : ''}`
        : `${tool || '工具'} 执行成功`,
    }
    if (target) Object.assign(target, entry)
    else assistant.toolEvents.push(entry)
  }

  /**
   * 把后端历史消息重建成「assistant 气泡 + toolEvents 折叠面板」结构。
   *
   * 后端 /MiniCode/history 现在回传全部消息 (service/sessionService.get_history 不再过滤),
   * 但 LangGraph state 里它们是平铺的:
   *   Human → AI(tool_calls) → Tool → AI(tool_calls) → Tool → AI(最终答案)
   * 流式期间的展示模式是「一个 assistant 气泡 + 一个折叠工具面板」, 所以这里按轮次归组:
   * 同一轮里的所有工具调用折叠进该轮 assistant 消息的 toolEvents, 最终答案作为气泡正文。
   */
  function buildHistoryMessages(items) {
    const list = Array.isArray(items) ? items : []
    const out = []
    let assistant = null

    /** 当前轮的 assistant 草稿 (历史以工具消息开头时兜底创建一个) */
    const ensureAssistant = () => {
      if (assistant) return assistant
      assistant = { id: null, role: 'assistant', content: '', type: 'text', toolEvents: [] }
      out.push(assistant)
      return assistant
    }

    for (const item of list) {
      const type = item?.type

      // 用户消息: 新一轮开始
      if (type === 'human') {
        assistant = null
        out.push({
          // 后端 LangGraph 消息 id: 编辑重发 (editMessage) 需要它定位检查点
          id: item?.id || null,
          role: 'user',
          content: historyText(item?.content),
          type: 'text',
        })
        continue
      }

      // 工具结果: 回填该轮里对应的那条工具记录
      if (type === 'tool') {
        applyHistoryToolResult(ensureAssistant(), item)
        continue
      }

      // AI 消息: 可能是"发起工具调用"的那条, 也可能是最终答案
      if (type === 'ai') {
        const target = ensureAssistant()
        const calls = Array.isArray(item?.tool_calls) ? item.tool_calls : []
        for (const call of calls) {
          target.toolEvents.push({
            id: call?.id || null,
            tool: call?.name || '',
            status: 'running',
            label: `正在调用 ${call?.name || '工具'} 工具…`,
          })
        }
        const text = historyText(item?.content)
        if (text) target.content = target.content ? `${target.content}\n\n${text}` : text
        if (item?.id && !target.id) target.id = item.id
        continue
      }

      // system 等其他类型: 不属于用户可见对话, 跳过
    }

    // 丢掉没有正文也没有工具记录的空 assistant 气泡 (与 dropEmptyAssistantMessage 同语义)
    const result = out.filter((m) => m.role === 'user' || m.content || m.toolEvents?.length)
    // 历史里不存在"半途而废"的调用: 若某条 try 始终没等到 result, 标记为 stopped,
    // 否则折叠面板里会永远转圈 (与 finalizeToolEvents 同语义)
    for (const m of result) {
      for (const ev of m.toolEvents || []) {
        if (ev.status === 'running') ev.status = 'stopped'
      }
    }
    return result
  }



  async function loadHistory(sessionId) {
    currentSessionId.value = sessionId
    // 审批卡片跟随其所属会话: 切走再切回不丢
    if (pendingApproval.value?.sessionId !== sessionId) pendingApproval.value = null
    // 该会话正在流式输出: 本地实时缓冲是最新的(后端可能尚未落库), 不用历史覆盖
    if (streamingSessions.has(sessionId)) return
    // 本地已有该会话的完整运行时状态时, 同样不能用后端历史覆盖。
    // 后端 /MiniCode/history 只回传 HumanMessage 与「不带 tool_calls 的 AIMessage」
    // (service/sessionService.get_history), 工具调用记录根本不在历史里; 而下面的
    // splice 是整组替换, 替换出来的消息只有 {id, role, content, type} —— 连
    // toolEvents 字段都没有, 于是工具调用折叠面板会整体消失, 且再也回不来。
    // 典型触发路径: 切到别的会话再切回、或点一下侧边栏里「当前正在看的」那个会话项
    // (selectSession 不判断是否已是当前会话, 直接调 loadHistory)。
    // 与 init() 里的 hasLocalContent 判断保持一致: 本地有内容 = 运行时状态更全。
    if (hasLocalContent(sessionId)) return

    // 同一会话可能被并发加载(如 init 自动加载 + 用户点选), 只认最后一次请求的结果
    const token = (historyTokens.get(sessionId) || 0) + 1
    historyTokens.set(sessionId, token)

    let list
    try {
      const res = await getHistory(sessionId)
      // 后端回传全部消息 (human/ai/tool 平铺), 这里按轮次归组成
      // 「assistant 气泡 + toolEvents 折叠面板」, 与流式期间的展示模式一致
      list = buildHistoryMessages(res?.response)
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

    // 该会话的全部运行时残留一并清掉。这些都是「按会话 id 挂载」的状态,
    // 只删 sessions/messageCache 会留下:
    //  - pendingApproval    → 审批卡片继续显示, 点了就对已删除的会话发 approve
    //  - interruptedSessions → 「继续生成」横幅指向不存在的会话
    //  - historyTokens      → 该 id 若被复用, 旧 token 会污染新会话的历史加载
    if (pendingApproval.value?.sessionId === sessionId) pendingApproval.value = null
    interruptedSessions.delete(sessionId)
    historyTokens.delete(sessionId)

    let deleted = true
    try {
      await deleteChat(sessionId)
    } catch (e) {
      // 后端未生效: 下面的 refreshSessions 可能把该会话捞回来,
      // 因此 workspaceCache 只在删除成功后才清, 避免丢掉会话级工作目录绑定
      deleted = false
      console.error('删除会话失败(后端未生效,列表已本地移除)', e)
    }
    if (deleted && workspaceCache[sessionId]) {
      delete workspaceCache[sessionId]
      saveWorkspaceCache(workspaceCache)
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

  /* ================= 模型管理 (数据源: 后端数据库) ================= */

  /** 把后端返回的模型信息同步到本地运行时副本 (modelConfig + 持久化生效 id) */
  function applyModelToLocal(model) {
    if (!model) return
    modelConfig.value = {
      ...modelConfig.value,
      model: model.model_name || '',
      base_url: model.base_url || '',
      api_key: model.api_key || '',
    }
    if (model.id != null) {
      activeModelId.value = model.id
      try {
        localStorage.setItem(ACTIVE_MODEL_ID_KEY, String(model.id))
      } catch (e) {
        console.error('记录当前模型 id 失败', e)
      }
    }
  }

  /** 从后端拉取模型列表 (GET /MiniCode/get_model), 界面数据一律以此为准 */
  async function refreshModels() {
    const res = await listModels()
    models.value = Array.isArray(res?.response) ? res.response : []
    return models.value
  }

  /** 按库中 id 切换生效模型 (POST /MiniCode/set_model?id=xxx) */
  async function activateModel(id) {
    const res = await setModel(id)
    applyModelToLocal({ ...models.value.find((m) => m.id === id), ...(res?.response || {}), id })
    return res
  }

  /** 新增模型 (POST /MiniCode/add_model): 后端落库并立即生效, 成功后回查列表定位新纪录的 id */
  async function addNewModel(config) {
    await addModel({
      model: config.model,
      base_url: config.base_url,
      api_key: config.api_key,
      is_default: config.is_default ?? true,
    })
    await refreshModels()
    const created = models.value.find(
      (m) => m.model_name === config.model && m.base_url === config.base_url && m.api_key === config.api_key
    )
    applyModelToLocal(created || { model_name: config.model, base_url: config.base_url, api_key: config.api_key })
    return created || null
  }

  /** 更新模型配置 (POST /MiniCode/update_model): 后端按 id 局部更新落库字段。
   *  注意: 更新的是「库中记录」, 若改的正是当前生效模型, 需重新激活一次
   *  (set_model) 才能让后端运行时用新配置重建 LLM 客户端 —— 否则界面切了、
   *  库里改了, 但运行时仍用旧的 base_url/api_key 发请求。
   *  is_default 仅在勾选( true )时下发: 后端只在 is_default=true 时把该记录设为库中默认
   *  (先清其他默认), false 不下发以避免与"当前生效模型"概念混淆。 */
  async function updateExistingModel(config) {
    await updateModel({
      id: config.id,
      model_name: config.model,
      base_url: config.base_url,
      api_key: config.api_key,
      ...(config.is_default ? { is_default: true } : {}),
    })
    await refreshModels()
    if (config.id === activeModelId.value) {
      await activateModel(config.id)
    }
    const updated = models.value.find((m) => m.id === config.id)
    return updated || null
  }

  /* ================= 停止生成 (POST /MiniCode/stop) ================= */

  /**
   * 请求后端停止生成。
   *
   * 后端按 session_id 置停 (service/chatService.py stop_chat: 优雅置停 → 3 秒未停则
   * 强制取消任务), SSE 连接可能被后端直接掐断, sendMessage / approve /
   * continueSession / editMessage 的 catch 里依据 stoppingSessions 把这种
   * 「主动停止」当正常收尾, 不标记失败。该标记只对当前这轮流有效, 由各流的 finally 统一清除。
   *
   * 语义严格按会话: 只停「传进来的那个会话」, 且它必须真的在跑。
   *  - 不传参 → 只停当前正在看的会话, 绝不顺手停掉别的会话:
   *    用户在会话 A 生成期间切到空闲的 B, 若这里默认去打 A, 一次误点就把 A 掐了。
   *  - 目标会话没在流式输出 → 直接返回: 不发无效请求 (后端会回 code=500「终止失败」),
   *    也不把它塞进 stoppingSessions —— 否则该会话之后的真实异常会被误判成
   *    「用户主动停止」而不报错、也不给恢复入口。
   */
  async function stopGeneration(sessionId = currentSessionId.value) {
    if (!sessionId) return
    // 与并行闸门同一套判定: 该会话没在跑就什么都不做
    if (!isSessionStreaming(sessionId)) return
    stoppingSessions.add(sessionId)
    try {
      await stopChat(sessionId)
    } catch (e) {
      stoppingSessions.delete(sessionId)
      console.error('停止生成失败', e)
      throw e
    }
  }

  /* ================= 恢复中断的会话 (POST /MiniCode/continue) ================= */

  /**
   * 会话因异常中断后, 从后端最近的安全检查点继续执行图 (SSE 流式返回)。
   * 用于 sendMessage 失败后 (interruptedSessions 标记) 的「继续生成」入口。
   */
  async function continueSession(sessionId = currentSessionId.value) {
    if (!sessionId) return
    // 并行闸门: 只拦"这条会话"自己正在生成的情况
    if (isSessionStreaming(sessionId)) return
    // 与 approve 同样的兜底: 会话已被删除时不能对不存在的 session_id 续跑
    if (!sessions.value.some((s) => s.id === sessionId)) {
      interruptedSessions.delete(sessionId)
      return
    }
    const sessionMessages = getMessagesOf(sessionId)
    pendingApproval.value = null

    const assistantMessage = reactive({ role: 'assistant', content: '', type: 'stream', toolEvents: [] })
    sessionMessages.push(assistantMessage)
    beginStream(sessionId)

    const typewriter = createTypewriter(assistantMessage)
    let received = ''
    const events = []
    try {
      for await (const event of continueStream(sessionId)) {
        events.push(event)
        const delta = eventTextDelta(event, received, assistantMessage, sessionId)
        received += delta
        typewriter.push(delta)
      }
      await typewriter.finish()
      assistantMessage.type = 'text'
      finalizeToolEvents(assistantMessage)
      interruptedSessions.delete(sessionId)
      if (isApprovalInterrupt(events)) {
        pendingApproval.value = {
          message: formatInterruptMessage(events[events.length - 1].message),
          sessionId,
        }
      }
      dropEmptyAssistantMessage(sessionMessages, assistantMessage, '本次恢复没有产生任何内容')
      await refreshSessions()
    } catch (error) {
      typewriter.flush()
      finalizeToolEvents(assistantMessage)
      if (stoppingSessions.has(sessionId)) {
        stoppingSessions.delete(sessionId)
        assistantMessage.type = 'text'
        dropEmptyAssistantMessage(sessionMessages, assistantMessage, null)
      } else {
        assistantMessage.content += (assistantMessage.content ? '\n\n' : '') + `错误: ${error.message}`
        assistantMessage.type = 'error'
        interruptedSessions.add(sessionId)
      }
    } finally {
      stoppingSessions.delete(sessionId)
      endStream(sessionId)
    }
  }
  /* ================= 编辑重发/时间旅行 (POST /MiniCode/editMessage) ================= */

  /**
   * 编辑指定用户消息并让后端从该检查点重新生成 (SSE)。
   * @param message 目标用户消息 (需带后端消息 id; 若无则先拉历史按内容解析)
   * @param newContent 编辑后的新内容
   */
  async function editMessage(message, newContent) {
    if (!currentSessionId.value) return
    // 并行闸门: 只拦"这条会话"自己正在生成的情况 (编辑会覆盖该会话的历史)
    if (isSessionStreaming(currentSessionId.value)) return
    if (!message || message.role !== 'user') return
    const content = (newContent || '').trim()
    if (!content) return

    const sessionId = currentSessionId.value
    const sessionMessages = getMessagesOf(sessionId)

    // 本地乐观消息没有后端 id: 先拉一次历史, 按内容匹配对应的 LangGraph 消息 id
    let messageId = message.id
    if (!messageId) {
      const res = await getHistory(sessionId).catch(() => null)
      const history = Array.isArray(res?.response) ? res.response : []
      // 后端只允许编辑「未造成影响」的消息, 匹配时从后往前找同内容的 human 消息
      const hit = [...history].reverse().find(
        (h) => h.type === 'human' && (typeof h.content === 'string' ? h.content : '') === message.content
      )
      messageId = hit?.id || null
      if (messageId) message.id = messageId
    }
    if (!messageId) {
      throw new Error('未能定位该消息对应的后端记录, 请刷新会话后重试')
    }

    message.content = content
    // 丢弃该消息之后的所有本地消息: 后端会从该检查点重新生成
    const idx = sessionMessages.indexOf(message)
    if (idx !== -1) sessionMessages.splice(idx + 1)

    const assistantMessage = reactive({ role: 'assistant', content: '', type: 'stream', toolEvents: [] })
    sessionMessages.push(assistantMessage)
    beginStream(sessionId)

    const typewriter = createTypewriter(assistantMessage)
    let received = ''
    const events = []
    try {
      for await (const event of editMessageStream({
        session_id: sessionId,
        message_id: messageId,
        new_content: content,
      })) {
        events.push(event)
        const delta = eventTextDelta(event, received, assistantMessage, sessionId)
        received += delta
        typewriter.push(delta)
      }
      await typewriter.finish()
      assistantMessage.type = 'text'
      finalizeToolEvents(assistantMessage)
      interruptedSessions.delete(sessionId)
      if (isApprovalInterrupt(events)) {
        pendingApproval.value = {
          message: formatInterruptMessage(events[events.length - 1].message),
          sessionId,
        }
      }
      dropEmptyAssistantMessage(sessionMessages, assistantMessage, '本次重新生成没有返回任何内容')
      await refreshSessions()
    } catch (error) {
      typewriter.flush()
      finalizeToolEvents(assistantMessage)
      if (stoppingSessions.has(sessionId)) {
        // 用户主动停止: 不算异常, 保留已经生成的内容
        stoppingSessions.delete(sessionId)
        assistantMessage.type = 'text'
        dropEmptyAssistantMessage(sessionMessages, assistantMessage, null)
      } else {
        assistantMessage.content += (assistantMessage.content ? '\n\n' : '') + `错误: ${error.message}`
        assistantMessage.type = 'error'
        interruptedSessions.add(sessionId)
      }
    } finally {
      stoppingSessions.delete(sessionId)
      endStream(sessionId)
    }
  }


  /* ================= 生成参数设置 (POST/GET /MiniCode/settings) ================= */

  /** 从后端拉取生成参数 (temperature/theme/think_level); 首次使用无记录时后端会抛错, 忽略并保持默认 */
  async function loadSettings() {
    try {
      const res = await getSettings(userId.value)
      if (res?.response && typeof res.response === 'object') {
        const { temperature, theme, think_level } = res.response
        appSettings.value = {
          temperature: typeof temperature === 'number' ? temperature : DEFAULT_SETTINGS.temperature,
          theme: typeof theme === 'boolean' ? theme : DEFAULT_SETTINGS.theme,
          think_level: [1, 2, 3].includes(think_level) ? think_level : DEFAULT_SETTINGS.think_level,
        }
        settingsLoaded.value = true
      }
    } catch (e) {
      // 后端 reolad_settings 对无记录的用户会抛错 → 用默认值兜底, 不打断启动
      console.warn('读取生成参数失败, 使用默认值', e)
    }
    return appSettings.value
  }

  /** 保存生成参数到后端 (乐观更新本地; 失败时抛错由 UI 提示) */
  async function saveSettings(patch) {
    const next = { ...appSettings.value, ...(patch || {}) }
    const res = await saveSettingsApi({ user_id: userId.value, settings: next })
    appSettings.value = next
    settingsLoaded.value = true
    return res
  }

  /* ================= Git 环境检测 (GET /MiniCode/checkGit) ================= */

  /** 检测后端运行环境的 Git 可用性; 未安装时后端会尝试 winget 安装, 结果供状态栏展示 */
  async function checkGitStatus() {
    try {
      const res = await checkGit()
      gitReady.value = res?.response === true
    } catch (e) {
      gitReady.value = false
      console.error('Git 环境检测失败', e)
    }
    return gitReady.value
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

  /**
   * 后端契约 (service/workplaceService.py: choose_workplace): 会话级工作目录**只能绑定一次**。
   * 已经绑定的会话再调用 /MiniCode/workplace 会被拒绝
   * (BizException「已经选定目录，无法更改，请创建新对话」), 因此 UI 只在未绑定时给出选择入口,
   * 已绑定时按只读展示, 不再暴露必然失败的"更换/解绑"操作。
   */
  function canBindWorkspace(sessionId = currentSessionId.value) {
    const session = sessions.value.find((s) => s.id === sessionId)
    return !!session && !session.workspacePath
  }

  /** 仅清除当前会话绑定的目录 (后端不接受对已绑定会话的"解绑", 故 UI 不再暴露此入口, 保留供后续后端支持时使用) */
  async function clearSessionWorkspace(sessionId) {
    return setSessionWorkspace(sessionId, '')
  }

  return {
    userId,
    currentSessionId,
    sessions,
    messages,
    isStreaming,
    isCurrentSessionStreaming,
    hasBackgroundStreaming,
    isSessionStreaming,
    streamingCount,
    streamingSessionTitles,
    streamingStatusText,
    streamingStatusTitle,
    streamingSessionId,
    pendingApproval,
    currentStatus,
    modelConfig,
    models,
    activeModelId,
    currentMessages,
    currentTitle,
    currentWorkspacePath,
    inputFocusSignal,
    searchFocusSignal,
    backendOnline,
    gitReady,
    interruptedSessions,
    appSettings,
    settingsLoaded,
    isActiveSessionEmpty,
    requestNewChat,
    focusSessionSearch,
    init,
    sendMessage,
    retrySend,
    approve,
    stopGeneration,
    continueSession,
    editMessage,
    loadSettings,
    saveSettings,
    checkGitStatus,
    createNewChat,
    loadHistory,
    removeSession,
    refreshModels,
    activateModel,
    addNewModel,
    updateExistingModel,
    setSessionWorkspace,
    clearSessionWorkspace,
    canBindWorkspace,
  }
})