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
          <button v-for="s in suggestions" :key="s" class="chip btn-secondary" @click="quickAsk(s)">{{ s }}</button>
        </div>
      </div>

      <div
        v-for="(message, index) in store.currentMessages"
        :key="index"
        :class="[
          'message',
          message.role === 'user' ? 'user' : 'assistant',
          {
            streaming: message.type === 'stream',
            failed: message.type === 'error',
            editing: editingIndex === index,
          },
        ]"
      >
        <div class="message-role">
          <span class="role-name">{{ message.role === 'user' ? '你' : 'AI' }}</span>
          <span v-if="message.status === 'sending'" class="sending-tag">发送中…</span>
          <!-- 行内操作: 与角色标注同处一行, 不脱离内容通道 (旧实现绝对定位到框外, 窄屏会溢出) -->
          <span class="msg-actions">
            <button
              class="msg-copy icon-btn"
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
              v-if="message.role === 'user' && !store.isCurrentSessionStreaming && editingIndex !== index"
              class="msg-edit icon-btn"
              title="编辑并重新生成"
              @click="startEdit(message, index)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>
              </svg>
            </button>
          </span>
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
              class="msg-editor-save btn-primary"
              :disabled="!editingText.trim() || editing"
              :title="'保存修改并从这条消息重新生成 (Ctrl+Enter)'"
              @click="saveEdit(message)"
            >
              {{ editing ? '重新生成中…' : '保存并重新生成' }}
            </button>
            <button class="msg-editor-cancel btn-secondary" title="取消编辑 (Esc)" @click="cancelEdit">取消</button>
            <span class="msg-editor-hint">修改会从这条消息开始覆盖其后的对话</span>
          </div>
        </div>
        <pre v-else-if="message.role === 'user'" class="message-content">{{ message.content }}</pre>
        <div v-if="message.role === 'user' && message.status === 'failed'" class="send-failed">
          <span class="send-failed-text">发送失败{{ message.error ? `: ${message.error}` : '' }}</span>
          <button
            class="retry-btn btn-secondary"
            :disabled="store.isCurrentSessionStreaming"
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
                    <svg v-else-if="ev.status === 'approved'" xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    <svg v-else-if="ev.status === 'pending'" xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
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
          class="resume-btn btn-primary"
          :disabled="store.isCurrentSessionStreaming"
          title="从后端最近的安全检查点继续执行"
          @click="store.continueSession()"
        >继续生成</button>
        <button class="resume-dismiss icon-btn" title="忽略" @click="dismissResume">×</button>
      </div>
    </transition>

    <div v-if="activeApproval" class="approval-card">
      <div class="approval-title">
        <span class="approval-icon" aria-hidden="true">⚠</span>
        需要你的确认
      </div>
      <div class="approval-message">
        <template v-if="approvalCodeBlock">
          <span>{{ approvalCodeBlock.prefix }}</span>
          <pre class="approval-code">{{ approvalCodeBlock.code }}</pre>
        </template>
        <template v-else>{{ activeApproval.message }}</template>
      </div>
      <div class="approval-actions">
        <button class="btn-primary" :disabled="store.isCurrentSessionStreaming" @click="store.approve('yes')">批准</button>
        <button class="reject btn-secondary" :disabled="store.isCurrentSessionStreaming" @click="store.approve('no')">拒绝</button>
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

/* ---------- 工具调用折叠面板 (统一折窗) ----------
 * 每个 assistant 消息的 toolEvents (来自 store) 一律折叠成一行摘要, 点击展开看明细。
 * 统一成折窗, 让"当前会话"与"历史会话"观感一致, 不再把一长串工具调用摊成列表:
 *  - 流式进行中 (message.type === 'stream'): 自动展开, 让用户看到实时进度;
 *  - 流结束后 / 历史消息 (message.type === 'text'): 一律折叠成折窗, 只占一行摘要;
 *  - 用户手动展开/收起的选择 (toolTraceManual) 始终优先。
 * 折叠≠丢失: toolEvents 数据始终留在消息对象里 (v-if 只控制列表显隐), 点开即可查看;
 * 刷新后历史会话由 store.buildHistoryMessages 从后端全量消息重建, 与折叠状态无关。 */
const toolTraceManual = ref({}) // index -> boolean (用户手动展开/收起的选择)

function isToolTraceOpen(index) {
  if (index in toolTraceManual.value) return toolTraceManual.value[index]
  // 尚未手动操作: 只有"正在流式生成"的那条自动展开, 其余(含历史)一律折叠成折窗
  const message = store.currentMessages[index]
  return message?.type === 'stream' && !!message.toolEvents?.length
}

function toggleToolTrace(index) {
  toolTraceManual.value = { ...toolTraceManual.value, [index]: !isToolTraceOpen(index) }
}

// 该消息是否仍有"进行中"的工具调用
function hasRunningTool(message) {
  return (message.toolEvents || []).some((ev) => ev.status === 'running')
}

// 折叠面板的一行摘要: 待批准 > 进行中 > 成功/失败计数
function toolTraceSummary(message) {
  const list = message.toolEvents || []
  // 有待批准项时优先提示, 让用户一眼看到"卡在等确认"这一步
  const pending = list.filter((ev) => ev.status === 'pending').length
  if (pending > 0) return `等待批准… (${pending})`
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
  // 只拦"这条会话自己"正在生成的情况; 别的会话并行生成不影响本会话编辑
  if (store.isCurrentSessionStreaming) return
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
 * 当前会话的审批卡片 (批准/拒绝按钮所在的卡片)。
 * store.pendingApproval 已改为「按会话挂载」的 computed (pendingApprovals Map 按
 * sessionId 存), 只会返回属于当前会话的审批 —— 切走再切回不丢, 也不会把别的
 * 会话(含已删除会话)的审批显示到当前界面上; 这里按 sessionId 再兜一层防御。
 */
const activeApproval = computed(() =>
  store.pendingApproval?.sessionId === store.currentSessionId ? store.pendingApproval : null
)

/**
 * execute_command / run_code 的审批文案形如「我想执行 <命令>」「我想运行脚本 <代码>」
 * (后端 core/InterruptInfo.py manage_InterruptInfo, 这两类已完整下发不再截断)。
 * 拆出命令/代码部分, 用等宽字体的代码块渲染, 与说明文字区分 —— 用户批准前能
 * 看清到底要执行什么; 其它工具的审批文案保持原来的纯文本渲染, 不受影响。
 * 后端 else 兜底分支会给没有专属文案的工具发「我想执行 <tool_name>」(如 file_edit),
 * 这种单词不是真实命令, 不进代码块。
 */
const APPROVAL_CODE_RE = /^(我想执行|我想运行脚本)\s+([\s\S]+)$/
const TOOL_NAME_FALLBACK_RE = /^[A-Za-z_][A-Za-z0-9_]*$/
const approvalCodeBlock = computed(() => {
  const msg = activeApproval.value?.message ?? ''
  const m = msg.match(APPROVAL_CODE_RE)
  if (!m || TOOL_NAME_FALLBACK_RE.test(m[2].trim())) return null
  return { prefix: m[1], code: m[2] }
})

const showResumeBanner = computed(
  () =>
    !store.isCurrentSessionStreaming &&
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
  /* 内容通道居中: 与输入框共用 --content-max, 左右边缘严格对齐, 视线不左右扫射 */
  padding: var(--space-5) max(var(--space-5), calc((100% - var(--content-max)) / 2)) var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* ---------- 消息: AI 回复融入背景, 用户消息为轻量浅底块 ----------
   所有消息与输入框共用同一条内容通道 (--content-max), 左边缘严格对齐:
   AI 回复占满通道宽度, 用户消息靠右但右边缘与通道右边缘重合。 */
.message {
  position: relative;
  width: 100%;
  max-width: var(--content-max);
  padding: 0;
  border-radius: 0;
  line-height: var(--lh-relaxed);
  word-break: break-word;
  animation: fadeUp 0.25s var(--ease-out) both;
}

.message.user {
  align-self: flex-end;
  /* 用户消息: 次级底色轻块, 无边框无阴影, 与 AI 纯文本形成克制的区分 */
  width: auto;
  max-width: min(560px, 88%);
  padding: 8px 13px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: none;
  border-radius: var(--radius-md);
  border-bottom-right-radius: var(--radius-xs);
}

.message.user .message-role {
  color: var(--text-tertiary);
}

/* 编辑态: 用户气泡从「贴合内容」放宽到整条通道, 否则内联编辑器 (min-width 280px)
   会被 88% 的窄气泡挤到溢出。编辑是临时态, 放宽不影响常态阅读节奏 */
.message.user.editing {
  width: 100%;
  max-width: var(--content-max);
}

.message.assistant {
  /* AI 回复融入主背景: 去除气泡底色/边框/圆角/内边距, 与输入框同宽同左边缘 */
  align-self: flex-start;
  background: transparent;
  border: none;
  border-radius: 0;
  box-shadow: none;
  padding: 0;
}

/* 出错的消息: 语义错误底色, 轻描边而非红框 */
.message.failed {
  padding: 8px 13px;
  border-radius: var(--radius-md);
  background: var(--error-light);
  border: 1px solid color-mix(in srgb, var(--error) 35%, transparent);
}

.message.failed .message-role {
  color: var(--error);
}

/* 角色标注行: 标注 + 行内操作按钮同处一行, 高度固定避免 hover 时内容跳动 */
.message-role {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  height: 20px;
  margin-bottom: 4px;
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-weight: 600;
  letter-spacing: 0.02em;
}

/* 行内操作: 默认隐形, hover 消息或键盘聚焦时才浮现 (不占视觉重量) */
.msg-actions {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  opacity: 0;
  transition: opacity var(--dur-fast) ease;
}

.message:hover .msg-actions,
.message:focus-within .msg-actions {
  opacity: 1;
}

/* 复制/编辑: 复用全局 .icon-btn, 收窄到 20px 以贴合标注行高度 */
.msg-copy,
.msg-edit {
  width: 20px;
  height: 20px;
  color: var(--text-tertiary);
}

.msg-copy.copied {
  color: var(--success);
  opacity: 1;
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

.msg-edit:hover:not(:disabled) {
  color: var(--text-primary);
  background: var(--bg-hover);
}

/* ---------- 内联编辑器 (时间旅行) ---------- */
.msg-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  /* 期望宽度 280px, 但允许被压缩: 极窄窗口下宁可窄一点, 也不撑破气泡横向溢出 */
  width: 280px;
  max-width: 100%;
}

.msg-editor-input {
  width: 100%;
  padding: 8px 10px;
  font-family: inherit;
  font-size: var(--fs-md);
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
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
  flex-wrap: wrap;
  gap: var(--space-2);
}

/* 保存/取消: 复用全局 .btn-primary / .btn-secondary, 仅收窄内边距适配行内编辑器 */
.msg-editor-save,
.msg-editor-cancel {
  padding: 5px 12px;
  flex: none;
}

.msg-editor-hint {
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
  /* 说明文字可换行, 不参与挤压按钮 */
  min-width: 0;
}

/* ---------- 中断恢复横幅: 轻量提示条, 非重框卡片 ---------- */
.resume-card {
  margin: 0 var(--space-5) var(--space-3);
  padding: var(--space-2) var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--fs-base);
  color: var(--text-secondary);
  background: var(--warning-light);
  border: 1px solid color-mix(in srgb, var(--warning) 30%, transparent);
  border-radius: var(--radius-sm);
  animation: fadeUp 0.25s var(--ease-out) both;
}

.resume-icon {
  font-size: var(--fs-md);
  color: var(--warning);
}

.resume-text {
  flex: 1;
  color: var(--text-primary);
}

.resume-btn {
  padding: 4px 12px;
  font-size: var(--fs-sm);
}

.resume-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* 忽略按钮: 复用全局 .icon-btn, 收窄命中区以贴合横幅高度 */
.resume-dismiss {
  width: 22px;
  height: 22px;
  font-size: var(--fs-lg);
  line-height: 1;
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
  background: var(--text-tertiary);
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
  font-size: var(--fs-base);
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
/* 乐观发送状态标记 */
.sending-tag {
  margin-left: 4px;
  font-size: var(--fs-xs);
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
  color: var(--text-tertiary);
}

/* 发送失败: 气泡内错误提示 + 重试入口 (消息不静默消失) */
.send-failed {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  font-size: var(--fs-sm);
  color: var(--error);
}

.retry-btn {
  padding: 2px 10px;
  font-size: var(--fs-xs);
  color: var(--error);
  border-color: color-mix(in srgb, var(--error) 45%, transparent);
}

.retry-btn:hover:not(:disabled) {
  color: var(--error);
  background: var(--error-light);
  border-color: var(--error);
}

.retry-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ---------- 空状态: 静态简洁图标, 不做装饰动画 ---------- */
.empty-state {
  margin: auto;
  text-align: center;
  color: var(--text-secondary);
  animation: fadeUp 0.3s var(--ease-out) both;
}

.empty-icon {
  /* 装饰性字形 (✦), 不属于排版字号阶, 单独取值 */
  font-size: 30px;
  color: var(--text-tertiary);
  margin-top: -48px;
  margin-bottom: var(--space-3);
}

.morph-rotate {
  display: inline-block;
  position: relative;
  transform-origin: 50% 200%;
}

.icon-four,
.icon-three {
  display: block;
  width: 40px;
  height: 40px;
}

/* 三叉形态叠层只在动画时有意义, 静态下隐藏, 仅保留 ✦ */
.icon-three {
  display: none;
}

.empty-title {
  margin: 0 0 var(--space-1);
  font-size: var(--fs-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.empty-sub {
  margin: 0 0 var(--space-5);
  font-size: var(--fs-base);
}

.empty-sub kbd {
  font-size: var(--fs-xs);
}

.suggestions {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  justify-content: center;
  max-width: 480px;
}

/* 建议入口: 复用全局 .btn-secondary 的描边文字按钮形态, 仅放宽内边距 */
.chip {
  padding: 7px 13px;
  font-size: var(--fs-base);
}

/* 回到底部: 悬浮于消息列表右下, 轻投影的圆形图标钮 */
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
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: 50%;
  box-shadow: var(--shadow-sm);
  z-index: 5;
}

.scroll-bottom-btn:hover:not(:disabled) {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

/* ---------- 工具调用折窗: 左侧细竖线做层次, 不包卡片 ---------- */
.tool-trace {
  margin: 2px 0 var(--space-2);
  max-width: 100%;
  font-family: var(--font-mono);
  padding-left: 10px;
  border-left: 2px solid var(--border-color);
  background: transparent;
  border-top: none;
  border-right: none;
  border-bottom: none;
  border-radius: 0;
}

.tool-trace-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  max-width: 100%;
  padding: 4px 6px;
  font-family: inherit;
  font-size: var(--fs-sm);
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
  padding: var(--space-2) 0 var(--space-2) 18px;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: transparent;
}

.tool-trace-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  font-family: inherit;
  font-size: var(--fs-sm);
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

.tool-trace-item.pending .tool-trace-icon {
  color: var(--warning, var(--text-tertiary));
}

.tool-trace-item.approved .tool-trace-icon {
  color: var(--success);
}

.tool-trace-label {
  min-width: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ---------- 审批卡片: 中性底 + 左侧警示竖线, 不用大面积强调色底 ---------- */
.approval-card {
  margin: 0 var(--space-5) var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--warning);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  animation: fadeUp 0.25s var(--ease-out) both;
}

.approval-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--warning);
  margin-bottom: var(--space-2);
}

.approval-icon {
  font-size: var(--fs-base);
}

.approval-message {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: var(--fs-base);
  line-height: 1.6;
  color: var(--text-primary);
  margin-bottom: var(--space-3);
}

/* execute_command / run_code: 命令与代码用等宽字体代码块完整展示, 与说明文字区分 */
.approval-code {
  display: block;
  margin: var(--space-2) 0 0;
  padding: 10px 12px;
  max-height: 260px;
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: var(--fs-base);
  line-height: 1.6;
  text-align: left;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--code-fg);
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: var(--radius-sm);
}

.approval-actions {
  display: flex;
  gap: var(--space-2);
}

/* 批准 = 主操作 (强调实底); 拒绝 = 次要操作 (文字描边), 权重分明 */
.approval-actions button {
  padding: 5px 16px;
  font-size: var(--fs-base);
}

.approval-actions .reject {
  color: var(--error);
  background: transparent;
  border: 1px solid color-mix(in srgb, var(--error) 45%, transparent);
}

.approval-actions .reject:hover:not(:disabled) {
  color: var(--error);
  background: var(--error-light);
  border-color: var(--error);
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
