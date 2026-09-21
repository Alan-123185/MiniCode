<template>
  <div class="session-list">
    <div class="session-header">
      <h3>会话</h3>
      <button class="new-btn" title="新建对话 (Ctrl+N)" @click="store.requestNewChat()">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </button>
    </div>

    <!-- 会话搜索: 前端过滤标题 (Ctrl+K 聚焦) -->
    <div class="search-wrap">
      <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"></circle>
        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
      </svg>
      <input
        ref="searchInput"
        v-model="keyword"
        class="search-input"
        type="text"
        placeholder="搜索会话…"
        @keydown.down.prevent="focusFirstItem"
      />
      <button
        v-if="keyword"
        class="search-clear"
        title="清除搜索"
        @click="keyword = ''; searchInput?.focus()"
      >×</button>
    </div>

    <ul role="listbox" aria-label="会话列表" @keydown="onListKeydown">
      <li
        v-for="session in filteredSessions"
        :key="session.id"
        :class="{ active: session.id === store.currentSessionId }"
        role="option"
        :aria-selected="session.id === store.currentSessionId"
        tabindex="0"
        :title="session.title"
        @click="selectSession(session.id)"
        @keydown.enter.prevent="selectSession(session.id)"
        @keydown.space.prevent="selectSession(session.id)"
        @contextmenu.prevent="openContextMenu($event, session)"
      >
        <span class="title">{{ session.title }}</span>
        <!-- 正在生成的会话: 标题尾部三点动画 (仅流式进行中的会话显示) -->
        <span
          v-if="session.id === store.streamingSessionId"
          class="streaming-dots"
          title="AI 正在思考"
          aria-label="AI 正在思考"
        >
          <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </span>
        <button
          class="delete-btn"
          title="删除会话"
          aria-label="删除会话"
          @click.stop="requestDelete(session)"
        >×</button>
      </li>
    </ul>

    <!-- 空状态: 无会话 -->
    <div v-if="store.sessions.length === 0" class="session-empty">
      暂无会话<br />点上方 <strong>+</strong> 或按 <kbd>Ctrl</kbd>+<kbd>N</kbd> 新建
    </div>
    <!-- 空状态: 搜索无结果 -->
    <div v-else-if="filteredSessions.length === 0" class="session-empty">
      没有匹配「<strong>{{ keyword }}</strong>」的会话
    </div>

    <!-- 会话右键菜单: 桌面端右键操作 -->
    <teleport to="body">
      <div
        v-if="contextMenu.visible"
        class="ctx-mask"
        @click="closeContextMenu"
        @contextmenu.prevent="closeContextMenu"
      ></div>
      <div
        v-if="contextMenu.visible"
        class="ctx-menu"
        :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
        role="menu"
      >
        <button class="ctx-item" role="menuitem" @click="ctxSelect">
          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          切换到此会话
        </button>
        <button
          v-if="ctxSession?.workspacePath"
          class="ctx-item"
          role="menuitem"
          @click="ctxUnbindWorkspace"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            <line x1="3" y1="3" x2="21" y2="21"></line>
          </svg>
          解绑工作目录
        </button>
        <div class="ctx-sep" role="separator"></div>
        <button class="ctx-item danger" role="menuitem" @click="ctxDelete">
          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
          删除会话
        </button>
      </div>
    </teleport>

    <!-- 删除确认对话框: 防误触, Enter 确认 / Esc 取消 -->
    <teleport to="body">
      <div v-if="confirmDelete.visible" class="confirm-mask" @click="cancelDelete"></div>
      <div
        v-if="confirmDelete.visible"
        class="confirm-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-delete-title"
      >
        <div class="confirm-icon" aria-hidden="true">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </div>
        <h4 id="confirm-delete-title">删除会话</h4>
        <p>
          确定删除「<strong>{{ confirmDelete.session?.title || '未命名会话' }}</strong>」吗？
          <span class="confirm-warn">删除后无法恢复。</span>
        </p>
        <div class="confirm-actions">
          <button ref="cancelBtn" class="ghost-btn" @click="cancelDelete">取消 (Esc)</button>
          <button class="danger-btn" @click="confirmDeleteSession">删除 (Enter)</button>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { useChatStore } from '../stores/chat'

const store = useChatStore()

/* ---------- 搜索过滤 (纯前端, 不影响数据层) ---------- */
const keyword = ref('')
const searchInput = ref(null)

const filteredSessions = computed(() => {
  const k = keyword.value.trim().toLowerCase()
  if (!k) return store.sessions
  return store.sessions.filter((s) => s.title.toLowerCase().includes(k))
})

/** Ctrl+K 信号 → 聚焦搜索框 */
watch(
  () => store.searchFocusSignal,
  () => searchInput.value?.focus()
)

function focusFirstItem() {
  const first = document.querySelector('.session-list ul li')
  first?.focus()
}

/** 列表内 ↑/↓ 键在会话项间移动焦点 (桌面键盘导航) */
function onListKeydown(e) {
  if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
  const items = Array.from(document.querySelectorAll('.session-list ul li'))
  const idx = items.indexOf(e.target)
  if (idx === -1) return
  e.preventDefault()
  const next = e.key === 'ArrowDown' ? idx + 1 : idx - 1
  if (next >= 0 && next < items.length) items[next].focus()
  else if (e.key === 'ArrowUp') searchInput.value?.focus()
}

async function selectSession(sessionId) {
  store.currentSessionId = sessionId
  await store.loadHistory(sessionId)
}

/* ---------- 右键菜单 ---------- */
const contextMenu = ref({ visible: false, x: 0, y: 0, sessionId: null, session: null })
const ctxSession = computed(() => contextMenu.value.session)

function openContextMenu(e, session) {
  const menuWidth = 180
  const menuHeight = 120
  contextMenu.value = {
    visible: true,
    x: Math.min(e.clientX, window.innerWidth - menuWidth - 8),
    y: Math.min(e.clientY, window.innerHeight - menuHeight - 8),
    sessionId: session.id,
    session,
  }
  window.addEventListener('resize', closeContextMenu, { once: true })
}

function closeContextMenu() {
  contextMenu.value = { visible: false, x: 0, y: 0, sessionId: null, session: null }
}

async function ctxSelect() {
  const id = contextMenu.value.sessionId
  closeContextMenu()
  if (id) await selectSession(id)
}

async function ctxDelete() {
  const session = contextMenu.value.session
  if (session) requestDelete(session)
}

/* ---------- 删除确认对话框 ---------- */
const confirmDelete = ref({ visible: false, session: null })
const cancelBtn = ref(null)

/** 统一删除入口: 悬浮 × / 右键菜单都先弹确认, 防误触 */
function requestDelete(session) {
  closeContextMenu()
  confirmDelete.value = { visible: true, session }
}

function cancelDelete() {
  confirmDelete.value = { visible: false, session: null }
}

async function confirmDeleteSession() {
  const id = confirmDelete.value.session?.id
  cancelDelete()
  if (!id) return
  try {
    await store.removeSession(id)
  } catch (e) {
    console.error('删除会话失败', e)
  }
}

/** 对话框打开时: 焦点落到「取消」防回车误删; Enter=确认, Esc=取消 */
watch(
  () => confirmDelete.value.visible,
  async (v) => {
    if (!v) {
      window.removeEventListener('keydown', onConfirmKeydown)
      return
    }
    await nextTick()
    cancelBtn.value?.focus()
    window.addEventListener('keydown', onConfirmKeydown)
  }
)

function onConfirmKeydown(e) {
  if (e.key === 'Escape') {
    e.preventDefault()
    cancelDelete()
  } else if (e.key === 'Enter') {
    e.preventDefault()
    confirmDeleteSession()
  }
}

async function ctxUnbindWorkspace() {
  const id = contextMenu.value.sessionId
  closeContextMenu()
  if (!id) return
  try {
    await store.clearSessionWorkspace(id)
  } catch (e) {
    console.error('解绑工作目录失败', e)
  }
}

onBeforeUnmount(() => {
  window.removeEventListener('resize', closeContextMenu)
})
</script>

<style scoped>
.session-list {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.session-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4) var(--space-2);
}

.session-header h3 {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

/* 新建按钮: 桌面工具栏小图标形态 */
.new-btn {
  width: 24px;
  height: 24px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs);
}

.new-btn:hover:not(:disabled) {
  color: var(--accent);
  background: var(--accent-light);
  border-color: var(--accent-border);
  box-shadow: none;
  transform: none;
}

/* 搜索框 */
.search-wrap {
  position: relative;
  margin: 0 var(--space-3) var(--space-2);
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 9px;
  color: var(--text-tertiary);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 6px 26px 6px 28px;
  font-size: 13px;
  background: var(--bg-primary);
  border-color: var(--border-color);
  border-radius: var(--radius-xs);
}

.search-clear {
  position: absolute;
  right: 4px;
  width: 18px;
  height: 18px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  line-height: 1;
  color: var(--text-tertiary);
  background: transparent;
  border: none;
  border-radius: 3px;
}

.search-clear:hover:not(:disabled) {
  color: var(--text-primary);
  background: var(--bg-hover);
  box-shadow: none;
  transform: none;
}

ul {
  list-style: none;
  margin: 0;
  padding: 0 var(--space-2) var(--space-2);
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background var(--dur-fast) ease;
  color: var(--text-primary);
  font-size: 13.5px;
  animation: slideLeft 0.2s var(--ease-out) both;
}

li:hover {
  background: var(--bg-tertiary);
}

/* 键盘焦点环 (focus-visible 全局 outline 适配) */
li:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}

li.active {
  background: var(--accent-light);
  color: var(--accent);
  font-weight: 600;
}

li.active:hover {
  background: var(--accent-light);
}

.session-empty {
  padding: var(--space-6) var(--space-4);
  text-align: center;
  font-size: 13px;
  line-height: 1.9;
  color: var(--text-secondary);
}

.session-empty kbd {
  font-size: 10px;
}

/* ===== 响应式断点 1: ≤1024px 侧边栏折叠为 56px 窄图标栏 ===== */
/* 窄栏下只保留 + 按钮和会话列表 (标题文字/搜索框收起), 悬停侧边栏整体展开时恢复 */
@media (max-width: 1024px) {
  .session-list {
    min-width: 0;
  }

  .session-header h3 {
    display: none;
  }

  .session-header {
    justify-content: center;
    padding: var(--space-3) var(--space-2) var(--space-2);
  }

  .search-wrap {
    display: none;
  }

  li {
    justify-content: center;
    padding: 8px 6px;
  }

  li .title {
    display: none;
  }

  li .delete-btn {
    display: none;
  }
}

.title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: var(--space-2);
}

/* 正在生成的会话: 尾部三点动画 (复用全局 typingBounce, 固定宽度容器防标题跳动) */
.streaming-dots {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  width: 18px;
}

.streaming-dots .dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--accent);
  animation: typingBounce 1.2s infinite;
}

.delete-btn {
  background: transparent;
  color: var(--text-tertiary);
  padding: 0;
  width: 22px;
  height: 22px;
  line-height: 22px;
  text-align: center;
  font-size: 14px;
  border: none;
  border-radius: 50%;
  opacity: 0;
  flex: none;
  transition: opacity var(--dur-fast) ease, background var(--dur-fast) ease;
}

li:hover .delete-btn,
li:focus-within .delete-btn {
  opacity: 1;
}

.delete-btn:hover:not(:disabled) {
  background: var(--error);
  color: #fff;
  transform: none;
  box-shadow: none;
}

/* ---------- 右键菜单 ---------- */
.ctx-mask {
  position: fixed;
  inset: 0;
  z-index: 90;
}

.ctx-menu {
  position: fixed;
  z-index: 91;
  min-width: 172px;
  padding: 4px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-lg);
  animation: popIn 0.15s var(--ease-out) both;
}

.ctx-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 10px;
  font-size: 13px;
  text-align: left;
  color: var(--text-primary);
  background: transparent;
  border: none;
  border-radius: var(--radius-xs);
}

.ctx-item:hover:not(:disabled) {
  background: var(--bg-tertiary);
  box-shadow: none;
  transform: none;
  background-image: none;
}

.ctx-item.danger {
  color: var(--error);
}

.ctx-item.danger:hover:not(:disabled) {
  background: var(--error-light);
}

.ctx-sep {
  height: 1px;
  margin: 4px 6px;
  background: var(--border-color);
}

/* ---------- 删除确认对话框 ---------- */
.confirm-mask {
  position: fixed;
  inset: 0;
  z-index: 110;
  background: rgba(15, 23, 42, 0.4);
  animation: maskIn 0.2s ease both;
}

@keyframes maskIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.confirm-dialog {
  position: fixed;
  z-index: 111;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 360px;
  max-width: calc(100vw - 48px);
  padding: var(--space-5);
  text-align: center;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  /* 不能复用全局 popIn: 其 transform 关键帧会覆盖居中位移, 导致弹窗偏移到屏幕右下 */
  animation: confirmPopIn 0.2s var(--ease-out) both;
}

/* 弹窗入场动画: 始终保留 translate(-50%, -50%) 居中位移 */
@keyframes confirmPopIn {
  from {
    opacity: 0;
    transform: translate(-50%, -50%) translateY(10px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}

.confirm-icon {
  width: 40px;
  height: 40px;
  margin: 0 auto var(--space-3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--error);
  background: var(--error-light);
  border-radius: 50%;
}

.confirm-dialog h4 {
  margin: 0 0 var(--space-2);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.confirm-dialog p {
  margin: 0 0 var(--space-4);
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-secondary);
  word-break: break-all;
}

.confirm-warn {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  color: var(--error);
}

.confirm-actions {
  display: flex;
  justify-content: center;
  gap: var(--space-2);
}

.ghost-btn {
  padding: 6px 14px;
  font-size: 13px;
  color: var(--text-secondary);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs);
}

.ghost-btn:hover:not(:disabled) {
  color: var(--text-primary);
  background: var(--bg-tertiary);
  box-shadow: none;
  transform: none;
}

.danger-btn {
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  color: #fff;
  background: var(--error);
  border: none;
  border-radius: var(--radius-xs);
}

.danger-btn:hover:not(:disabled) {
  background: var(--error-hover);
}
</style>
