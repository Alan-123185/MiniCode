import { fetchEventSource } from '@microsoft/fetch-event-source'

const DEFAULT_BASE = 'http://127.0.0.1:8000'

function getBaseUrl() {
  if (window.electronAPI?.getApiBaseUrl) {
    return window.electronAPI.getApiBaseUrl()
  }
  return import.meta.env.DEV ? '/api' : DEFAULT_BASE
}

let baseUrlPromise = null

async function getBase() {
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

export async function* stream(endpoint, body) {
  const base = await getBase()
  const url = `${base}${endpoint}`

  const events = []
  let resolveNext = null
  let ended = false
  let error = null

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
        const payload = JSON.parse(ev.data)
        if (resolveNext) {
          resolveNext(payload)
          resolveNext = null
        } else {
          events.push(payload)
        }
      } catch (e) {
        console.error('解析 SSE 消息失败', e)
      }
    },
    onclose() {
      ended = true
      if (resolveNext) resolveNext(null)
    },
    onerror(err) {
      error = err
      ended = true
      if (resolveNext) resolveNext(null)
    },
  })

  while (!ended || events.length > 0) {
    if (events.length > 0) {
      yield events.shift()
    } else {
      const value = await new Promise((resolve) => {
        resolveNext = resolve
      })
      if (value === null) break
      yield value
    }
  }

  if (error) {
    throw error
  }
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
  return request(`/MiniCode/sessions/${encodeURIComponent(userId)}`)
}

export function getHistory(sessionId) {
  return request(`/MiniCode/history/${encodeURIComponent(sessionId)}`, { method: 'POST' })
}

export function deleteChat(sessionId) {
  return request(`/MiniCode/deleteChat/${encodeURIComponent(sessionId)}`, { method: 'POST' })
}

export function chooseModel(body) {
  return request('/MiniCode/model', { method: 'POST', body: JSON.stringify(body) })
}

export function oldModel() {
  return request('/MiniCode/old_model')
}

export function chooseWorkplace(body) {
  return request('/MiniCode/workplace', { method: 'POST', body: JSON.stringify(body) })
}