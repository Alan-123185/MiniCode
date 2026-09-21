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
        <div class="message-role">
          {{ message.role === 'user' ? '你' : 'AI' }}
          <span v-if="message.status === 'sending'" class="sending-tag">发送中…</span>
        </div>
        <pre v-if="message.role === 'user'" class="message-content">{{ message.content }}</pre>
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
          <div v-if="message.content" class="message-content md-body" v-html="renderMarkdown(message.content)"></div>
          <div v-else class="typing-dots"><span></span><span></span><span></span></div>
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

    <div v-if="store.pendingApproval" class="approval-card">
      <div class="approval-title">
        <span class="approval-icon" aria-hidden="true">⚠</span>
        需要你的确认
      </div>
      <div class="approval-message">{{ store.pendingApproval.message }}</div>
      <div class="approval-actions">
        <button :disabled="store.isStreaming" @click="store.approve('yes')">批准</button>
        <button :disabled="store.isStreaming" class="reject" @click="store.approve('no')">拒绝</button>
      </div>
    </div>
    <MessageInput />
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { marked } from 'marked'
import { useChatStore } from '../stores/chat'
import MessageInput from './MessageInput.vue'

const store = useChatStore()
const messageList = ref(null)

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
