<template>
  <div class="chat-window">
    <div class="message-list" ref="messageList" @scroll="onScroll" @click="onMessageListClick">
      <div v-if="store.currentMessages.length === 0" class="empty-state">
        <div class="empty-icon">
          <div class="morph-rotate">
            <span class="icon-four">✦</span>
            <div class="icon-three"></div>
          </div>
        </div>
        <p class="empty-title">开始一个新的对话吧</p>
        <p class="empty-sub">点击下方建议快速开始，或按 <kbd>Ctrl</kbd>+<kbd>N</kbd> 新建会话</p>
        <div class="suggestions">
          <button v-for="s in suggestions" :key="s" class="chip" @click="quickAsk(s)">{{ s }}</button>
        </div>
      </div>

      <div
        v-for="(message, index) in store.currentMessages"
        :key="index"
        :class="[
          'message',
          message.role === 'user' ? 'user' : 'assistant',
          { streaming: message.type === 'stream', failed: message.type === 'error' },
        ]"
      >
        <button
          class="msg-copy"
          :title="`复制${message.role === 'user' ? '你的' : '这条'}消息`"
          @click="copyMessage(message, $event)"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
        </button>
        <!-- 用户消息: 编辑重发 (时间旅行, POST /MiniCode/editMessage) -->
        <button
          v-if="message.role === 'user' && !store.isStreaming && editingIndex !== index"
          class="msg-edit"
          title="编辑并重新生成"
          @click="startEdit(message, index)"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>
          </svg>
        </button>
        <div class="message-role">
          {{ message.role === 'user' ? '你' : 'AI' }}
          <span v-if="message.status === 'sending'" class="sending-tag">发送中…</span>
        </div>
        <!-- 编辑态: textarea 内联编辑, 保存后从该消息重新生成 -->
        <div v-if="message.role === 'user' && editingIndex === index" class="msg-editor">
          <textarea
            ref="editorTa"
            v-model="editingText"
            class="msg-editor-input"
            rows="3"
            aria-label="编辑消息内容"
            @keydown.escape.prevent="cancelEdit"
            @keydown.enter.exact.meta.prevent="saveEdit(message)"
            @keydown.enter.exact.ctrl.prevent="saveEdit(message)"
          ></textarea>
          <div class="msg-editor-actions">
            <button
              class="msg-editor-save"
              :disabled="!editingText.trim() || editing"
              :title="'保存修改并从这条消息重新生成 (Ctrl+Enter)'"
              @click="saveEdit(message)"
            >
              {{ editing ? '重新生成中…' : '保存并重新生成' }}
            </button>
            <button class="msg-editor-cancel" title="取消编辑 (Esc)" @click="cancelEdit">取消</button>
            <span class="msg-editor-hint">修改会从这条消息开始覆盖其后的对话</span>
          </div>
        </div>
        <pre v-else-if="message.role === 'user'" class="message-content">{{ message.content }}</pre>
        <div v-if="message.role === 'user' && message.status === 'failed'" class="send-failed">
          <span class="send-failed-text">发送失败{{ message.error ? `: ${message.error}` : '' }}</span>
          <button
            class="retry-btn"
            :disabled="store.isStreaming"
            title="重新发送这条消息"
            @click="store.retrySend(message)"
          >重试</button>
        </div>
        <template v-else-if="message.role !== 'user'">
          <!-- 工具调用实时消息: 默认折叠成一行摘要, 点击展开查看每次调用的实时状态/结果 -->
          <div v-if="message.toolEvents && message.toolEvents.length" class="tool-trace">
            <button
              class="tool-trace-toggle"
              type="button"
              :aria-expanded="isToolTraceOpen(index) ? 'true' : 'false'"
              @click="toggleToolTrace(index)"
            >
              <span class="tool-trace-caret" :class="{ open: isToolTraceOpen(index) }" aria-hidden="true">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
              </span>
              <span v-if="hasRunningTool(message)" class="mini-spinner" aria-hidden="true"></span>
              <span v-else class="tool-trace-done" aria-hidden="true">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
              </span>
              <span class="tool-trace-summary">{{ toolTraceSummary(message) }}</span>
            </button>
            <transition name="fade">
              <ol v-if="isToolTraceOpen(index)" class="tool-trace-list">
                <li v-for="(ev, i) in message.toolEvents" :key="i" class="tool-trace-item" :class="ev.status">
                  <span class="tool-trace-icon" aria-hidden="true">
                    <span v-if="ev.status === 'running'" class="mini-spinner"></span>
                    <svg v-else-if="ev.status === 'success'" xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    <svg v-else-if="ev.status === 'failed'" xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    <svg v-else xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="4.9" y1="4.9" x2="19.1" y2="19.1"></line></svg>
                  </span>
                  <span class="tool-trace-label">{{ ev.label }}</span>
                </li>
              </ol>
            </transition>
          </div>
          <div v-if="message.content" class="message-content md-body" v-html="renderMarkdown(message.content)"></div>
          <!-- 正在生成且尚无正文: 展示「当前在干嘛」的轻提示 (非流式), 无状态时退回三点动画 -->
          <div v-else-if="message.type === 'stream' && store.currentStatus && !message.toolEvents?.length" class="stream-status">
            <span class="mini-spinner" aria-hidden="true"></span>
            <span class="stream-status-text">{{ store.currentStatus }}</span>
          </div>
          <!-- 三点动画只在"正在生成"时出现: 否则流结束后留下的空气泡会一直转圈 -->
          <div v-else-if="message.type === 'stream' && !message.toolEvents?.length" class="typing-dots"><span></span><span></span><span></span></div>
        </template>
      </div>
    </div>

    <!-- 回到底部: 用户向上翻阅历史时出现 -->
    <transition name="fade">
      <button
        v-if="showScrollButton"
        class="scroll-bottom-btn"
        title="回到底部"
        @click="scrollToBottom(true); stickToBottom = true"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>
    </transition>

    <!-- 中断恢复横幅: 该会话上次生成异常中断时出现, 调用 /MiniCode/continue 从检查点续跑 -->
    <transition name="fade">
      <div v-if="showResumeBanner" class="resume-card">
        <span class="resume-icon" aria-hidden="true">⟲</span>
        <span class="resume-text">上次生成因异常中断, 可从最近的检查点继续</span>
        <button
          class="resume-btn"
          :disabled="store.isStreaming"
          title="从后端最近的安全检查点继续执行"
          @click="store.continueSession()"
        >继续生成</button>
        <button class="resume-dismiss" title="忽略" @click="dismissResume">×</button>
      </div>
    </transition>

    <div v-if="activeApproval" class="approval-card">
      <div class="approval-title">
        <span class="approval-icon" aria-hidden="true">⚠</span>
        需要你的确认
      </div>
      <div class="approval-message">{{ activeApproval.message }}</div>
      <div class="approval-actions">
        <button :disabled="store.isStreaming" @click="store.approve('yes')">批准</button>
        <button :disabled="store.isStreaming" class="reject" @click="store.approve('no')">拒绝</button>
      </div>
    </div>
    <MessageInput />
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { marked } from 'marked'
import { useChatStore } from '../stores/chat'
import MessageInput from './MessageInput.vue'

const store = useChatStore()
const messageList = ref(null)

/* ---------- 工具调用折叠面板 ----------
 * 每个 assistant 消息的 toolEvents (来自 store) 折叠展示: 默认只占一行摘要。
 * 流式进行中自动展开 (让用户看到实时进度), 结束后沿用用户最后一次的手动选择;
 * 未手动操作过的消息在流结束后自动收起, 保持界面清爽。 */
const toolTraceManual = ref({}) // index -> boolean (用户手动展开/收起的选择)
const toolTraceAutoOpen = ref(true) // 流式期间默认展开

function isToolTraceOpen(index) {
  if (index in toolTraceManual.value) return toolTraceManual.value[index]
  // 尚未手动操作: 流式输出期间展开, 结束后收起
  return store.isStreaming && toolTraceAutoOpen.value
}

function toggleToolTrace(index) {
  toolTraceManual.value = { ...toolTraceManual.value, [index]: !isToolTraceOpen(index) }
}

// 该消息是否仍有"进行中"的工具调用
function hasRunningTool(message) {
  return (message.toolEvents || []).some((ev) => ev.status === 'running')
}

// 折叠面板的一行摘要: 进行中显示最新动作, 结束后显示成功/失败计数
function toolTraceSummary(message) {
  const list = message.toolEvents || []
  const running = list.filter((ev) => ev.status === 'running').length
  if (running > 0) {
    const last = [...list].reverse().find((ev) => ev.status === 'running')
    return last ? last.label : `正在调用工具… (${running})`
  }
  const failed = list.filter((ev) => ev.status === 'failed' || ev.status === 'refused' || ev.status === 'stopped').length
  const total = list.length
  if (failed > 0) return `已调用 ${total} 个工具 · ${failed} 个未成功`
  return `已调用 ${total} 个工具`
}

const suggestions = [
  '你都能帮我做什么？',
  '帮我创建一个 hello.py',
  '介绍一下你的工具能力',
]

marked.setOptions({ breaks: true, gfm: true })

/** 轻量 sanitize: 无依赖, 移除危险标签与内联事件 (marked 原样输出 HTML) */
function sanitizeHtml(html) {
  const doc = new DOMParser().parseFromString(html, 'text/html')
  doc.querySelectorAll('script, style, iframe, object, embed, link, meta').forEach((el) => el.remove())
  doc.querySelectorAll('*').forEach((el) => {
    for (const attr of Array.from(el.attributes)) {
      const name = attr.name.toLowerCase()
      if (name.startsWith('on')) {
        el.removeAttribute(attr.name)
      } else if (name === 'href' || name === 'src') {
        const value = attr.value.trim().toLowerCase()
        if (value.startsWith('javascript:') || value.startsWith('data:text/html')) {
          el.removeAttribute(attr.name)
        }
      }
    }
  })
  return doc.body.innerHTML
}

/** Markdown 渲染: sanitize 后包装代码块, 注入桌面端复制按钮 */
function renderMarkdown(content) {
  if (!content) return ''
  const html = sanitizeHtml(marked.parse(content))
  return html
    .replace(/<pre>/g, '<div class="md-code"><button type="button" class="md-copy-btn">复制</button><pre>')
    .replace(/<\/pre>/g, '</pre></div>')
}

/** 消息列表事件委托: 代码块「复制」按钮 → 复制代码文本 */
async function onMessageListClick(e) {
  const btn = e.target.closest('.md-copy-btn')
  if (!btn) return
  const code = btn.parentElement?.querySelector('pre')?.innerText || ''
  await copyText(code)
  btn.textContent = '已复制'
  setTimeout(() => (btn.textContent = '复制'), 1200)
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    console.error('写入剪贴板失败')
  }
}

async function copyMessage(message, e) {
  await copyText(message.content || '')
  const btn = e.currentTarget
  const original = btn.title
  btn.title = '已复制'
  btn.classList.add('copied')
  setTimeout(() => {
    btn.title = original
    btn.classList.remove('copied')
  }, 1200)
}

function quickAsk(text) {
  store.sendMessage(text)
}

/* ---------- 编辑重发 (时间旅行, POST /MiniCode/editMessage) ---------- */
const editingIndex = ref(-1)
const editingText = ref('')
const editing = ref(false)
const editorTa = ref(null)

function startEdit(message, index) {
  if (store.isStreaming) return
  editingIndex.value = index
  editingText.value = message.content
  nextTick(() => {
    const ta = Array.isArray(editorTa.value) ? editorTa.value[0] : editorTa.value
    ta?.focus()
  })
}

function cancelEdit() {
  editingIndex.value = -1
  editingText.value = ''
}

async function saveEdit(message) {
  if (editing.value || !editingText.value.trim()) return
  editing.value = true
  try {
    await store.editMessage(message, editingText.value)
    cancelEdit()
  } catch (e) {
    // 定位后端消息失败等: 保留编辑态让用户可重试, 错误进气泡
    console.error('编辑重发失败', e)
    const list = store.currentMessages
    list.push({
      role: 'assistant',
      content: `编辑重发失败: ${e.message}`,
      type: 'error',
    })
  } finally {
    editing.value = false
  }
}

/* ---------- 中断恢复横幅 ---------- */
const dismissedResume = ref(false)

/**
 * 只展示属于当前会话的审批卡片。
 * pendingApproval 是全局单值, 直接 v-if 它会让别的会话(含已删除会话)遗留的
 * 审批显示在当前界面上; store.loadHistory 切换时会清, 但删除会话等路径
 * 不一定经过它, 所以这里按 sessionId 再兜一层。
 */
const activeApproval = computed(
  () =>
    store.pendingApproval?.sessionId === store.currentSessionId ? store.pendingApproval : null
)

const showResumeBanner = computed(
  () =>
    !store.isStreaming &&
    !dismissedResume.value &&
    store.currentSessionId != null &&
    store.interruptedSessions.has(store.currentSessionId)
)

function dismissResume() {
  dismissedResume.value = true
}

// 切换会话时重置「忽略」状态, 每个会话各自决定是否再提示
watch(
  () => store.currentSessionId,
  () => {
    dismissedResume.value = false
    cancelEdit()
    // 折叠面板的手动选择是按消息 index 记录的, 换会话后 index 语义变了, 需清空
    toolTraceManual.value = {}
  }
)

/* ---------- 滚动: 底部跟随 + 回到底部按钮 ---------- */
const stickToBottom = ref(true)
const showScrollButton = ref(false)

function scrollToBottom(smooth) {
  if (!messageList.value) return
  messageList.value.scrollTo({
    top: messageList.value.scrollHeight,
    behavior: smooth ? 'smooth' : 'auto',
  })
}

/** 用户滚动位置: 距底 > 80px 视为离开底部 (暂停自动跟随), > 240px 显示回到底部按钮 */
function onScroll() {
  const el = messageList.value
  if (!el) return
  const distance = el.scrollHeight - el.scrollTop - el.clientHeight
  stickToBottom.value = distance < 80
  showScrollButton.value = distance > 240
}

// 新消息出现时平滑滚动 (尊重用户是否停留在底部)
watch(() => store.messages.length, async () => {
  await nextTick()
  if (stickToBottom.value) scrollToBottom(true)
})

// 自己刚发出的消息 (乐观插入): 立即强制滚到底部, 让用户马上看到
watch(
  () => {
    const list = store.currentMessages
    const last = list[list.length - 1]
    return last && last.role === 'user' ? list.length : -1
  },
  async () => {
    await nextTick()
    stickToBottom.value = true
    scrollToBottom(true)
  }
)

// 流式内容更新时即时跟随
watch(
  () => {
    const last = store.messages[store.messages.length - 1]
    return last ? last.content : ''
  },
  async () => {
    await nextTick()
    if (stickToBottom.value) scrollToBottom(false)
  }
)
</script>

<style scoped>
.chat-window {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-primary);
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-5) var(--space-5) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* ---------- 消息气泡 ---------- */
.message {
  position: relative;
  max-width: 76%;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  line-height: 1.6;
  word-break: break-word;
  box-shadow: var(--shadow-xs);
  animation: fadeUp 0.3s var(--ease-out) both;
}

.message.user {
  align-self: flex-end;
  background: var(--accent);
  color: #fff;
  border-bottom-right-radius: var(--radius-xs);
}

.message.user .message-role {
  color: rgba(255, 255, 255, 0.75);
}

.message.assistant {
  align-self: flex-start;
  background: var(--bg-tertiary);
  border-bottom-left-radius: var(--radius-xs);
}

/* 出错的消息: 语义错误色 */
.message.failed {
  background: var(--error-light);
  border: 1px solid var(--error);
}

.message.failed .message-role {
  color: var(--error);
}

.message-role {
  font-size: 11px;
  margin-bottom: 4px;
  opacity: 0.7;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 600;
}

.message-content {
  margin: 0;
  font-family: inherit;
  white-space: pre-wrap;
}

.message.assistant .message-content.md-body {
  white-space: normal;
}

/* 流式打字机光标: 生成中的 AI 气泡尾部闪烁竖线 (内容为空时仍显示 typing-dots, 不受影响) */
.message.assistant.streaming .message-content::after {
  content: '';
  display: inline-block;
  width: 2px;
  height: 1em;
  margin-left: 2px;
  vertical-align: text-bottom;
  background: var(--accent);
  animation: caret-blink 0.9s step-end infinite;
}

@keyframes caret-blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}

/* 消息复制按钮: hover 浮现于气泡外侧 (桌面鼠标交互) */
.msg-copy {
  position: absolute;
  top: -2px;
  padding: 3px 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs);
  box-shadow: var(--shadow-xs);
  opacity: 0;
  pointer-events: none;
  z-index: 2;
  transition: opacity var(--dur-fast) ease, background var(--dur-fast) ease,
    color var(--dur-fast) ease, transform var(--dur-base) ease-in-out;
}

.message.user .msg-copy {
  left: -30px;
}

.message.assistant .msg-copy {
  right: -30px;
}

.message:hover .msg-copy,
.msg-copy:focus-visible {
  opacity: 1;
  pointer-events: auto;
}

.msg-copy:hover:not(:disabled) {
  color: var(--accent);
  background: var(--accent-light);
  border-color: var(--accent-border);
  box-shadow: none;
  transform: none;
}

.msg-copy.copied {
  color: var(--success);
  border-color: var(--success);
  opacity: 1;
  pointer-events: auto;
}

/* 编辑按钮: 与复制按钮同款, 排在其下方 */
.msg-edit {
  position: absolute;
  top: 30px;
  padding: 3px 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs);
  box-shadow: var(--shadow-xs);
  opacity: 0;
  pointer-events: none;
  z-index: 2;
  transition: opacity var(--dur-fast) ease, background var(--dur-fast) ease,
    color var(--dur-fast) ease;
}

.message.user .msg-edit {
  left: -30px;
}

.message:hover .msg-edit,
.msg-edit:focus-visible {
  opacity: 1;
  pointer-events: auto;
}

.msg-edit:hover:not(:disabled) {
  color: var(--accent);
  background: var(--accent-light);
  border-color: var(--accent-border);
  box-shadow: none;
}

/* ---------- 内联编辑器 (时间旅行) ---------- */
.msg-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 280px;
}

.msg-editor-input {
  width: 100%;
  padding: 8px 10px;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--bg-primary);
  border: 1px solid var(--accent-border);
  border-radius: var(--radius-xs);
  resize: vertical;
}

.msg-editor-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-ring);
}

.msg-editor-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.msg-editor-save {
  padding: 5px 12px;
  font-size: 12.5px;
  font-weight: 500;
  color: #fff;
  background: var(--accent);
  border-radius: var(--radius-xs);
}

.msg-editor-save:hover:not(:disabled) {
  background: var(--accent-hover);
}

.msg-editor-save:disabled {
  cursor: not-allowed;
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
}

.msg-editor-cancel {
  padding: 5px 12px;
  font-size: 12.5px;
  color: var(--text-secondary);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs);
}

.msg-editor-cancel:hover:not(:disabled) {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.msg-editor-hint {
  font-size: 11.5px;
  color: var(--text-tertiary);
}

/* ---------- 中断恢复横幅 ---------- */
.resume-card {
  margin: 0 var(--space-5) var(--space-3);
  padding: var(--space-2) var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
  color: var(--warning);
  background: var(--warning-light, var(--bg-secondary));
  border: 1px solid var(--warning, var(--border-color));
  border-radius: var(--radius-md);
  animation: fadeUp 0.3s var(--ease-out) both;
}

.resume-icon {
  font-size: 15px;
}

.resume-text {
  flex: 1;
  color: var(--text-primary);
}

.resume-btn {
  padding: 4px 12px;
  font-size: 12.5px;
  font-weight: 500;
  color: #fff;
  background: var(--accent);
  border-radius: var(--radius-xs);
}

.resume-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.resume-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.resume-dismiss {
  padding: 0 6px;
  font-size: 16px;
  line-height: 1;
  color: var(--text-tertiary);
  background: transparent;
  border: none;
}

.resume-dismiss:hover {
  color: var(--text-primary);
}

/* 流式输出时的闪烁光标 */
.message.streaming .md-body::after {
  content: '▍';
  color: var(--accent);
  animation: blink 1s steps(1) infinite;
  margin-left: 2px;
}

/* 等待首个 token 的打字点 */
.typing-dots {
  display: flex;
  gap: 5px;
  padding: 4px 0;
}

.typing-dots span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-secondary);
  animation: typingBounce 1.2s infinite;
}

.typing-dots span:nth-child(2) { animation-delay: 0.15s; }
.typing-dots span:nth-child(3) { animation-delay: 0.3s; }

/* ---------- 生成中「当前在干嘛」轻提示 (非流式) ---------- */
.stream-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 4px 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.stream-status-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 旋转小 spinner: 与顶栏「生成中…」一致的低调风格 */
.mini-spinner {
  width: 12px;
  height: 12px;
  flex: none;
  border: 2px solid var(--accent-border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ---------- 乐观发送状态标记 ---------- */
/* 发送中: 角色行尾部的小标记 */
.sending-tag {
  margin-left: 4px;
  font-size: 10px;
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
  opacity: 0.85;
}

/* 发送失败: 气泡内错误提示 + 重试入口 (消息不静默消失) */
.send-failed {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  font-size: 12px;
  color: #ffe0e0;
}

.retry-btn {
  padding: 2px 10px;
  font-size: 11px;
  color: #fff;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: var(--radius-xs);
}

.retry-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.22);
}

.retry-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ---------- 空状态 ---------- */
.empty-state {
  margin: auto;
  text-align: center;
  color: var(--text-secondary);
  animation: fadeUp 0.4s var(--ease-out) both;
}

.empty-icon {
  font-size: 40px;
  color: var(--accent);
  margin-top: -60px;
  margin-bottom: var(--space-2);
  animation: blink 2.5s infinite;
}

.morph-rotate {
  display: inline-block;
  position: relative;
  transform-origin: 50% 200%;
  animation: slowRotate 8s linear infinite;
}

.icon-four, .icon-three {
  display: block;
  width: 40px;
  height: 40px;
}

.icon-three {
  position: absolute;
  top: 0;
  left: 0;
  background: var(--accent);
  clip-path: polygon(
    50% 5%, 58% 45%, 89% 72%,
    50% 60%, 11% 72%, 42% 45%
  );
  animation: fadeSwap 4s ease-in-out infinite;
}

.icon-four {
  animation: fadeSwapReverse 4s ease-in-out infinite;
}

@keyframes slowRotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes fadeSwap {
  0%, 35% { opacity: 0; }
  50%, 85% { opacity: 1; }
  100% { opacity: 0; }
}

@keyframes fadeSwapReverse {
  0%, 35% { opacity: 1; }
  50%, 85% { opacity: 0; }
  100% { opacity: 1; }
}

.empty-title {
  margin: 0 0 var(--space-1);
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.empty-sub {
  margin: 0 0 var(--space-5);
  font-size: 13px;
}

.empty-sub kbd {
  font-size: 10px;
}

.suggestions {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  justify-content: center;
  max-width: 460px;
}

.chip {
  background: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  padding: 8px 14px;
  font-size: 13px;
  box-shadow: var(--shadow-xs);
  border-radius: var(--radius-pill);
}

.chip:hover:not(:disabled) {
  background: var(--accent-light);
  color: var(--accent);
  border-color: var(--accent-border);
}

/* 回到底部按钮: 悬浮于消息列表右下 */
.scroll-bottom-btn {
  position: absolute;
  right: 24px;
  bottom: 132px;
  width: 32px;
  height: 32px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 50%;
  box-shadow: var(--shadow-md);
  z-index: 5;
}

.scroll-bottom-btn:hover:not(:disabled) {
  color: var(--accent);
  background: var(--accent-light);
  border-color: var(--accent-border);
}

/* ---------- 工具调用折叠窗 (独立卡片容器 + 等宽字体, 与正文 sans 形成层次) ---------- */
.tool-trace {
  margin: 0 0 var(--space-2);
  max-width: 100%;
  font-family: var(--font-mono);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  overflow: hidden;
}

.tool-trace-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  max-width: 100%;
  padding: 6px 10px;
  font-family: inherit;
  font-size: 12px;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  border-radius: 0;
  text-align: left;
  transition: color var(--dur-fast) ease, background var(--dur-fast) ease;
}

.tool-trace-toggle:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.tool-trace-caret {
  display: inline-flex;
  flex: none;
  color: var(--text-tertiary);
  transition: transform var(--dur-fast) var(--ease-out);
}

.tool-trace-caret.open {
  transform: rotate(90deg);
}

.tool-trace-toggle .mini-spinner {
  width: 11px;
  height: 11px;
  border-width: 1.5px;
}

.tool-trace-done {
  display: inline-flex;
  flex: none;
  color: var(--success);
}

.tool-trace-summary {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 展开后的工具调用列表: 与标题栏用分隔线隔开, 保持等宽字体 */
.tool-trace-list {
  margin: 0;
  padding: var(--space-2) 10px var(--space-2) 10px;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-primary);
}

.tool-trace-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  font-family: inherit;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
}

.tool-trace-icon {
  display: inline-flex;
  flex: none;
  align-items: center;
  height: 18px;
}

.tool-trace-item .mini-spinner {
  width: 11px;
  height: 11px;
  border-width: 1.5px;
}

.tool-trace-item.success .tool-trace-icon {
  color: var(--success);
}

.tool-trace-item.failed .tool-trace-icon {
  color: var(--error);
}

.tool-trace-item.refused .tool-trace-icon {
  color: var(--warning, var(--text-tertiary));
}

.tool-trace-item.stopped .tool-trace-icon {
  color: var(--text-tertiary);
}

.tool-trace-label {
  min-width: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ---------- 审批卡片 ---------- */
.approval-card {
  margin: 0 var(--space-5) var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--accent-border);
  border-radius: var(--radius-md);
  background: var(--accent-light);
  box-shadow: var(--shadow-md);
  animation: fadeUp 0.3s var(--ease-out) both;
}

.approval-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.03em;
  color: var(--accent);
  margin-bottom: var(--space-2);
}

.approval-icon {
  font-size: 13px;
}

.approval-message {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13.5px;
  line-height: 1.6;
  margin-bottom: var(--space-3);
}

.approval-actions {
  display: flex;
  gap: var(--space-3);
}

.approval-actions button {
  background: var(--accent);
  color: #fff;
  font-weight: 500;
  border-radius: var(--radius-xs);
}

.approval-actions button:hover:not(:disabled) {
  background: var(--accent-hover);
}

.approval-actions button:active:not(:disabled) {
  background: var(--accent-active);
}

.approval-actions .reject {
  background: var(--error);
}

.approval-actions .reject:hover:not(:disabled) {
  background: var(--error-hover);
}

/* 过渡 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--dur-base) ease, transform var(--dur-base) var(--ease-out);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
