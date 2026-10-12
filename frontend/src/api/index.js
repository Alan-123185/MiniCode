import { fetchEventSource } from '@microsoft/fetch-event-source'

const DEFAULT_BASE = 'http://127.0.0.1:8000'

function getBaseUrl() {
  if (window.electronAPI?.getApiBaseUrl) {
    return window.electronAPI.getApiBaseUrl()
  }
  return import.meta.env.DEV ? '/api' : DEFAULT_BASE
}

let baseUrlPromise = null

/** 获取 API 基地址: Electron IPC > 开发代理 > 生产默认值。
 *  供 api 层内部与状态栏展示复用。 */
export async function getBase() {
  if (window.electronAPI?.getApiBaseUrl) {
    if (!baseUrlPromise) {
      baseUrlPromise = window.electronAPI.getApiBaseUrl()
    }
    return baseUrlPromise
  }
  return getBaseUrl()
}

async function request(path, options = {}) {
  const base = await getBase()
  const url = `${base}${path}`
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  const response = await fetch(url, { ...options, headers })
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

export function chooseModel(body) {
  // 后端 ModelChooseRequest 字段为 model_name (requestcommon/ModelRequest.py), 前端内部叫 model;
  // 注意: mapper/modelMapper.add_model 只有 is_default=True 才会落库, 启动恢复依赖它, 因此默认补 true
  const { model, is_default = true, ...rest } = body || {}
  return request('/MiniCode/model', {
    method: 'POST',
    body: JSON.stringify({ ...rest, model_name: model, is_default }),
  })
}

/** 已保存的模型列表 (GET /MiniCode/get_model, routers/modelRouter.py) */
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