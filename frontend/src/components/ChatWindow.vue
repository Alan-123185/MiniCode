<template>
  <div class="chat-window">
    <div class="chat-header">
      <span class="session-title">{{ store.currentTitle }}</span>
      <span v-if="store.isStreaming" class="streaming-indicator">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        AI 正在思考
      </span>
    </div>
    <div class="message-list" ref="messageList">
      <div v-if="store.currentMessages.length === 0" class="empty-state">
        <div class="empty-icon">
          <div class="morph-rotate">
            <span class="icon-four">✦</span>
            <div class="icon-three"></div>
          </div>
        </div>
        <p>开始一个新的对话吧，点击下方建议，或左上角点 + 新建会话</p>
        <div class="suggestions">
          <button v-for="s in suggestions" :key="s" class="chip" @click="quickAsk(s)">{{ s }}</button>
        </div>
      </div>
      <div
        v-for="(message, index) in store.currentMessages"
        :key="index"
        :class="['message', message.role === 'user' ? 'user' : 'assistant', { streaming: message.type === 'stream' }]"
      >
        <div class="message-role">{{ message.role === 'user' ? '你' : 'AI' }}</div>
        <pre v-if="message.role === 'user'" class="message-content">{{ message.content }}</pre>
        <template v-else>
          <div v-if="message.content" class="message-content md-body" v-html="renderMarkdown(message.content)"></div>
          <div v-else class="typing-dots"><span></span><span></span><span></span></div>
        </template>
      </div>
    </div>
    <div v-if="store.pendingApproval" class="approval-card">
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

function renderMarkdown(content) {
  if (!content) return ''
  return marked.parse(content)
}

function quickAsk(text) {
  store.sendMessage(text)
}

function scrollToBottom(smooth) {
  if (!messageList.value) return
  messageList.value.scrollTo({
    top: messageList.value.scrollHeight,
    behavior: smooth ? 'smooth' : 'auto',
  })
}

// 新消息出现时平滑滚动
watch(() => store.messages.length, async () => {
  await nextTick()
  scrollToBottom(true)
})

// 流式内容更新时即时跟随
watch(
  () => {
    const last = store.messages[store.messages.length - 1]
    return last ? last.content : ''
  },
  async () => {
    await nextTick()
    scrollToBottom(false)
  }
)
</script>

<style scoped>
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-primary);
}

.chat-header {
  height: 52px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.session-title {
  font-weight: 600;
  color: var(--text-primary);
}

.streaming-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--accent);
}

.streaming-indicator .dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
  animation: typingBounce 1.2s infinite;
}

.streaming-indicator .dot:nth-child(2) { animation-delay: 0.15s; }
.streaming-indicator .dot:nth-child(3) { animation-delay: 0.3s; }

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.message {
  max-width: 78%;
  padding: 12px 16px;
  border-radius: 18px;
  line-height: 1.6;
  word-break: break-word;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  animation: fadeUp 0.3s var(--ease-out) both;
}

.message.user {
  align-self: flex-end;
  background: var(--accent);
  color: #fff;
  border-bottom-right-radius: 6px;
}

.message.user .message-role {
  color: rgba(255, 255, 255, 0.75);
}

.message.assistant {
  align-self: flex-start;
  background: var(--bg-tertiary);
  border-bottom-left-radius: 6px;
}

.message-role {
  font-size: 12px;
  margin-bottom: 4px;
  opacity: 0.7;
}

.message-content {
  margin: 0;
  font-family: inherit;
  white-space: pre-wrap;
}

.message.assistant .message-content.md-body {
  white-space: normal;
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

/* 空状态 */
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
  margin-bottom: 8px;
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

.empty-state p {
  margin: 0 0 18px;
  font-size: 15px;
}

.suggestions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
  max-width: 420px;
}

.chip {
  background: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  padding: 8px 14px;
  font-size: 13px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.chip:hover {
  background: var(--accent-light);
  color: var(--accent);
  border-color: var(--accent);
}

/* 审批卡片 */
.approval-card {
  margin: 0 20px 14px;
  padding: 14px 16px;
  border: 1px solid var(--accent);
  border-radius: 16px;
  background: var(--accent-light);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.12);
  animation: fadeUp 0.3s var(--ease-out) both;
}

.approval-message {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 10px;
}

.approval-actions {
  display: flex;
  gap: 10px;
}

.approval-actions .reject {
  background: var(--error);
}

.approval-actions .reject:hover {
  background: #d93636;
}
</style>