import { fetchEventSource } from '@microsoft/fetch-event-source'

const DEFAULT_BASE = 'http://127.0.0.1:8000'

/** 非桌面端可用的基地址: 开发态走 Vite 代理 (/api → 127.0.0.1:8000), 其余直连后端 */
function getFallbackBase() {
  return import.meta.env.DEV ? '/api' : DEFAULT_BASE
}

let baseUrlPromise = null

/** 获取 API 基地址: Electron IPC > 开发代理 > 生产默认值。
 *  供 api 层内部与状态栏展示复用。
 *  注意: IPC 失败(主进程未注册 handler / 预加载脚本未生效)时必须回退默认地址 ——
 *  旧实现把失败的 Promise 永久缓存, 会让整个应用再也拿不到 base, 所有接口全挂;
 *  这里失败即丢弃缓存, 后续调用可以重新尝试。 */
export async function getBase() {
  const ipc = window.electronAPI?.getApiBaseUrl
  if (!ipc) return getFallbackBase()

  if (!baseUrlPromise) {
    baseUrlPromise = Promise.resolve()
      .then(() => ipc())
      .then((base) =>
        typeof base === 'string' && base.trim() ? base.trim().replace(/\/+$/, '') : getFallbackBase()
      )
      .catch((e) => {
        console.warn('获取桌面端 API 地址失败, 已回退到默认地址', e)
        baseUrlPromise = null // 不缓存失败结果, 下次调用可以重试
        return getFallbackBase()
      })
  }
  return baseUrlPromise
}

async function request(path, options = {}) {
  const base = await getBase()
  const url = `${base}${path}`
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  let response
  try {
    response = await fetch(url, { ...options, headers })
  } catch (e) {
    // fetch 只在网络层失败时 reject (后端没启动 / 连接被中断), 给出可读的提示
    throw new Error(`无法连接后端 ${base}（${e?.message || e}）`)
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok || data.code !== 200) {
    throw new Error(data.error || data.message || `请求失败: ${response.status}`)
  }
  return data
}

/**
 * 以 async generator 形式消费后端 SSE。
 *
 * body 可省略 (如 /MiniCode/continue、/MiniCode/stop 这类纯 query 参数接口)。
 *
 * 用「队列 + 唤醒器」而非单个 resolveNext: 事件随时可能到达, 消费者可能
 * 正在 yield、正在处理上一个事件、或尚未开始等待, 单个 resolveNext 槽位会
 * 在这些时机里丢事件或永久挂起。
 *
 * 结束条件由 onclose / onerror 统一驱动, 二者都保证唤醒消费者:
 *  - 正常关闭 → finish(), 队列排空后 generator 正常 return
 *  - 出错 → finish(err) 并在 onerror 中抛出, 让 fetch-event-source 停止
 *    默认的每秒无限重试; 消费者排空队列后抛出该错误
 *
 * openWhenHidden 必须显式开启: fetch-event-source 默认会在页面隐藏(切标签/最小化)时
 * abort 请求 —— 而它 abort 后既不会回调 onclose 也不会回调 onerror, 本 generator 会
 * 永久停在等待上(界面卡在"生成中", 直到刷新页面), 重新可见时还会重新 POST 一次
 * 造成重复生成。开启后连接在后台保持, 与"生成不应被切标签打断"的预期一致。
 */
export async function* stream(endpoint, body) {
  const base = await getBase()
  const url = `${base}${endpoint}`

  const queue = []
  let wake = null
  let finished = false
  let failure = null

  function enqueue(payload) {
    queue.push(payload)
    if (wake) {
      wake()
      wake = null
    }
  }

  function finish(err) {
    if (finished) return
    finished = true
    if (err) failure = err
    if (wake) {
      wake()
      wake = null
    }
  }

  fetchEventSource(url, {
    method: 'POST',
    openWhenHidden: true,
    headers: { 'Content-Type': 'application/json' },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    async onopen(response) {
      if (!response.ok) {
        throw new Error(`SSE 连接失败: ${response.status}`)
      }
    },
    onmessage(ev) {
      try {
        enqueue(JSON.parse(ev.data))
      } catch (e) {
        console.error('解析 SSE 消息失败', e)
      }
    },
    onclose() {
      finish()
    },
    onerror(err) {
      finish(err instanceof Error ? err : new Error(String(err)))
      // 抛出: fetch-event-source 会 dispose 连接并 reject, 不再重试
      throw err
    },
  }).then(
    () => finish(),
    (err) => finish(err instanceof Error ? err : new Error(String(err)))
  )

  while (true) {
    if (queue.length > 0) {
      yield queue.shift()
      continue
    }
    if (finished) break
    await new Promise((resolve) => {
      wake = resolve
    })
  }

  if (failure) throw failure
}

export function chatStream(body) {
  return stream('/MiniCode/chat', body)
}

export function approveStream(body) {
  return stream('/MiniCode/approve', body)
}

/** 会话异常中断恢复: POST /MiniCode/continue?session_id=xxx, SSE 返回 (query 参数, routers/chatRouter.py) */
export function continueStream(sessionId) {
  return stream(`/MiniCode/continue?session_id=${encodeURIComponent(sessionId)}`)
}

/** 时间旅行: 编辑某条历史消息并重新生成, SSE 返回 (routers/chatRouter.py /MiniCode/editMessage) */
export function editMessageStream(body) {
  return stream('/MiniCode/editMessage', body)
}

export function newChat(body) {
  return request('/MiniCode/new_chat', { method: 'POST', body: JSON.stringify(body) })
}

/** 停止生成: POST /MiniCode/stop?session_id=xxx (query 参数, 返回普通 Result 非 SSE) */
export function stopChat(sessionId) {
  return request(`/MiniCode/stop?session_id=${encodeURIComponent(sessionId)}`, { method: 'POST' })
}

/**
 * 切换会话工作模式: POST /MiniCode/mode?session_id=xxx&mode=xxx (query 参数, 无 body)。
 * 后端: routers/chatRouter.py update_mode + service/chatService.py update_mode,
 *  mode 取值对应 mode/modeRegistry.py 注册表: 'work' | 'plan' | 'free_fly'。
 * 成功返回 Result(code=200, message="已切换模式为 xxx")。
 * 注意:
 *  - 模式持久化在 LangGraph checkpointer (按 thread_id/会话隔离), 覆盖该会话后续所有对话;
 *  - 后端没有读取当前模式的接口, 每会话模式由前端自行缓存 (stores/chat.js sessionModes);
 *  - 新会话尚未产生检查点时后端抛 BizException「会话 xxx 不存在或未初始化」,
 *    由 store 转成本地暂存 + 首轮流式结束后补同步 (setSessionMode → endStream)。
 */
export function updateMode(sessionId, mode) {
  return request(
    `/MiniCode/mode?session_id=${encodeURIComponent(sessionId)}&mode=${encodeURIComponent(mode)}`,
    { method: 'POST' }
  )
}

export function listSessions(userId) {
  // 后端: GET /MiniCode/sessions?user_id=xxx (query 参数, routers/sessionRouter.py)
  return request(`/MiniCode/sessions?user_id=${encodeURIComponent(userId)}`)
}

export function getHistory(sessionId) {
  // 后端: GET /MiniCode/history?session_id=xxx (query 参数, routers/sessionRouter.py)
  return request(`/MiniCode/history?session_id=${encodeURIComponent(sessionId)}`)
}

export function deleteChat(sessionId) {
  // 后端: POST /MiniCode/deleteChat?session_id=xxx (query 参数, routers/sessionRouter.py)
  return request(`/MiniCode/deleteChat?session_id=${encodeURIComponent(sessionId)}`, { method: 'POST' })
}

/**
 * 新增模型配置 (POST /MiniCode/add_model, routers/modelRouter.py)。
 * body 对应后端 ModelSetRequest: { base_url, api_key, model_name, is_default }。
 * 注意:
 *  - mapper/modelMapper.add_model 里 is_default=False 不会落库, 因此固定补 true;
 *  - 后端 add_model 会同时把该配置设为运行时生效模型 (service/modelService.py);
 *  - 返回值不含新纪录的 id, 需要 id 时再调 listModels() 按字段匹配。
 */
export function addModel(body) {
  const { model, is_default = true, ...rest } = body || {}
  return request('/MiniCode/add_model', {
    method: 'POST',
    body: JSON.stringify({ ...rest, model_name: model, is_default }),
  })
}

/** 更新模型配置 (POST /MiniCode/update_model, routers/modelRouter.py)。
 *  body 对应后端 ModelUpdateRequest: { id, base_url, api_key, model_name, is_default };
 *  除 id 外均为可选, 传哪个字段就更新哪个字段 (mapper/modelMapper.update_model 逐字段判空)。 */
export function updateModel(body) {
  return request('/MiniCode/update_model', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

/** 按库中 id 切换当前生效模型 (POST /MiniCode/set_model?id=xxx, id 是 query 参数, response 为 ModelSetRequest) */
export function setModel(id) {
  return request(`/MiniCode/set_model?id=${encodeURIComponent(id)}`, { method: 'POST' })
}

/** 已保存的模型列表 (GET /MiniCode/get_model): response 为 list[ModelGetRequest], 含 id/base_url/api_key/model_name/is_default */
export function listModels() {
  return request('/MiniCode/get_model')
}

/** 保存生成参数设置 (POST /MiniCode/settings, body: { user_id, settings }) */
export function saveSettings(body) {
  return request('/MiniCode/settings', { method: 'POST', body: JSON.stringify(body) })
}

/** 读取生成参数设置 (GET /MiniCode/get_settings/{user_id}) */
export function getSettings(userId) {
  return request(`/MiniCode/get_settings/${encodeURIComponent(userId)}`)
}

/** Git 环境检测 (GET /MiniCode/checkGit, main.py): 未安装时后端会尝试 winget 安装 */
export function checkGit() {
  return request('/MiniCode/checkGit')
}

export function chooseWorkplace(body) {
  return request('/MiniCode/workplace', { method: 'POST', body: JSON.stringify(body) })
}