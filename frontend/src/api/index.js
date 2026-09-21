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
    body: JSON.stringify(body),
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

export function newChat(body) {
  return request('/MiniCode/new_chat', { method: 'POST', body: JSON.stringify(body) })
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
  // 后端 ModelChooseRequest 字段为 model_name (requestcommon/ModelRequest.py), 前端内部叫 model
  const { model, ...rest } = body || {}
  return request('/MiniCode/model', {
    method: 'POST',
    body: JSON.stringify({ ...rest, model_name: model }),
  })
}

export function oldModel() {
  // 后端实际提供的是 GET /MiniCode/get_model (routers/modelRouter.py), 不存在 /old_model
  return request('/MiniCode/get_model')
}

export function chooseWorkplace(body) {
  return request('/MiniCode/workplace', { method: 'POST', body: JSON.stringify(body) })
}