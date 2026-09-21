<template>
  <div class="app">
    <!-- 桌面端顶部工具栏: 品牌 + 当前会话 + 工作目录徽章 + 主题/设置 -->
    <header class="titlebar">
      <div class="brand">
        <span class="brand-logo" aria-hidden="true">✦</span>
        <span class="brand-name">MiniCode</span>
      </div>

      <div class="titlebar-center">
        <span class="session-title" :title="store.currentTitle">
          {{ store.currentTitle }}
        </span>
      </div>

      <div class="titlebar-actions">
        <!-- 窄屏 (≤768px) 汉堡按钮: 打开侧边栏抽屉 -->
        <button
          v-if="isNarrowViewport"
          class="icon-btn hamburger-btn"
          title="打开会话列表"
          aria-label="打开会话列表"
          @click="drawerOpen = true"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
        <WorkspaceBadge />
        <div class="action-divider" role="separator" aria-orientation="vertical"></div>
        <button
          class="icon-btn"
          :title="isDarkMode ? '切换到浅色主题 (Ctrl+Shift+L)' : '切换到深色主题 (Ctrl+Shift+L)'"
          :aria-label="isDarkMode ? '切换到浅色主题' : '切换到深色主题'"
          @click="toggleTheme"
        >
          <svg v-if="isDarkMode" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
          </svg>
        </button>
        <button
          class="icon-btn"
          title="设置 (Ctrl+,)"
          aria-label="打开设置"
          @click="showSettings = true"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
        </button>
      </div>
    </header>

    <!-- 主工作区: 左侧导航 + 内容区 -->
    <div class="app-body">
      <!-- 窄屏抽屉遮罩: 点击关闭 -->
      <transition name="fade">
        <div
          v-if="drawerOpen && isNarrowViewport"
          class="drawer-mask"
          @click="drawerOpen = false"
        ></div>
      </transition>
      <aside class="sidebar" :class="{ 'drawer-open': drawerOpen && isNarrowViewport }">
        <SessionList />
      </aside>
      <main class="main">
        <ChatWindow />
      </main>
    </div>

    <!-- 桌面端状态栏: 运行模式 / 后端地址 / 流式状态 / 统计 / 快捷键 -->
    <footer class="statusbar">
      <span class="status-item">
        <span class="status-dot" :class="store.backendOnline ? 'ok' : 'bad'" aria-hidden="true"></span>
        <span class="status-mode">{{ isElectron ? '桌面' : 'Web' }}</span>
        <span class="status-text" :title="`后端地址: ${apiBase}`">{{ apiBase }}</span>
      </span>
      <span class="status-spacer"></span>
      <transition name="fade">
        <span v-if="store.isStreaming" class="status-item status-streaming">
          <span class="mini-spinner" aria-hidden="true"></span>
          生成中…
        </span>
      </transition>
      <span class="status-item">{{ store.sessions.length }} 个会话</span>
      <span class="status-item kbd-hint">
        <kbd>Ctrl</kbd>+<kbd>K</kbd> 搜索 · <kbd>Ctrl</kbd>+<kbd>N</kbd> 新建
      </span>
    </footer>

    <SettingsModal :visible="showSettings" @close="showSettings = false" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import ChatWindow from './components/ChatWindow.vue'
import SessionList from './components/SessionList.vue'
import SettingsModal from './components/SettingsModal.vue'
import WorkspaceBadge from './components/WorkspaceBadge.vue'
import { useChatStore } from './stores/chat'
import { getBase } from './api'

const store = useChatStore()
const showSettings = ref(false)

/* ---------- 响应式: 窄屏侧边栏抽屉 ---------- */
const drawerOpen = ref(false)
/** 768px 与 CSS 断点 --bp-sidebar-drawer 保持一致 */
const narrowBreakpoint = 768
const isNarrowViewport = ref(
  typeof window !== 'undefined' ? window.innerWidth <= narrowBreakpoint : false
)

function onViewportResize() {
  isNarrowViewport.value = window.innerWidth <= narrowBreakpoint
  if (!isNarrowViewport.value) drawerOpen.value = false
}

// 选中会话后自动收起抽屉 (与 SessionList 里 li 的点击行为解耦, 通过 store 会话 id 观察)
watch(
  () => store.currentSessionId,
  () => {
    if (isNarrowViewport.value) drawerOpen.value = false
  }
)

/* ---------- 主题 ---------- */
const isDarkMode = ref(localStorage.getItem('dark-mode') === 'true')

function applyTheme(dark) {
  document.documentElement.classList.toggle('dark-mode', dark)
}

function toggleTheme() {
  isDarkMode.value = !isDarkMode.value
  localStorage.setItem('dark-mode', isDarkMode.value)
  applyTheme(isDarkMode.value)
}

/* ---------- 运行环境 / 后端地址 (状态栏展示) ---------- */
const isElectron = computed(() => typeof window !== 'undefined' && !!window.electronAPI)
const apiBase = ref('…')

/* ---------- 全局快捷键 (纯 Web 模式; Electron 模式由原生菜单加速键驱动) ---------- */
function handleKeydown(e) {
  if (!(e.ctrlKey || e.metaKey)) return
  const key = (e.key || '').toLowerCase()
  if (key === 'n') {
    e.preventDefault()
    store.requestNewChat()
  } else if (key === 'k') {
    e.preventDefault()
    store.focusSessionSearch()
  } else if (key === ',') {
    e.preventDefault()
    showSettings.value = true
  } else if (key === 'l' && e.shiftKey) {
    e.preventDefault()
    toggleTheme()
  }
}

/** Electron 原生菜单命令分发 (preload onMenuCommand 回调) */
function handleMenuCommand(action) {
  if (action === 'new-chat') store.requestNewChat()
  else if (action === 'focus-search') store.focusSessionSearch()
  else if (action === 'open-settings') showSettings.value = true
  else if (action === 'toggle-theme') toggleTheme()
}

let offMenuCommand = null

onMounted(async () => {
  store.init()
  applyTheme(isDarkMode.value)

  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('resize', onViewportResize)

  if (window.electronAPI?.onMenuCommand) {
    offMenuCommand = window.electronAPI.onMenuCommand(handleMenuCommand)
  }

  try {
    apiBase.value = await getBase()
  } catch {
    apiBase.value = '不可用'
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', onViewportResize)
  if (offMenuCommand) offMenuCommand()
})
</script>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  min-width: var(--app-min-width);
  overflow: hidden;
  background: var(--bg-primary);
}

/* ---------- 顶部工具栏 ---------- */
.titlebar {
  height: var(--topbar-height);
  min-height: var(--topbar-height);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: 0 var(--space-4);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  user-select: none;
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding-right: var(--space-4);
  border-right: 1px solid var(--border-color);
}

.brand-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  font-size: 13px;
  color: #fff;
  background: linear-gradient(135deg, var(--accent), var(--accent-active));
  border-radius: var(--radius-xs);
  box-shadow: var(--shadow-xs);
}

.brand-name {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--text-primary);
}

.titlebar-center {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}


.titlebar-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: none;
}

.action-divider {
  width: 1px;
  height: 18px;
  margin: 0 var(--space-1);
  background: var(--border-color);
}

/* 顶栏图标按钮 (设置 / 主题): 方正的桌面工具栏形态 */
.icon-btn {
  width: 30px;
  height: 30px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
}

.icon-btn:hover:not(:disabled) {
  color: var(--accent);
  background: var(--accent-light);
  border-color: var(--accent-border);
  box-shadow: none;
  transform: none;
}

.icon-btn:active:not(:disabled) {
  transform: scale(0.94);
}

/* ---------- 主工作区 ---------- */
.app-body {
  flex: 1;
  min-height: 0;
  display: flex;
}

.sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  overflow: hidden;
  transition: width var(--dur-base) var(--ease-out);
}

/* ===== 响应式断点 1: ≤1024px 侧边栏折叠为窄图标栏 (悬停临时展开) ===== */
@media (max-width: 1024px) {
  .sidebar {
    position: relative;
    z-index: 20;
  }

  .sidebar:hover {
    width: 268px;
    min-width: 268px;
    box-shadow: var(--shadow-lg);
  }
}

/* ===== 响应式断点 2: ≤768px 侧边栏隐藏为抽屉 (汉堡按钮 + 遮罩) ===== */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    top: var(--topbar-height);
    bottom: var(--statusbar-height);
    left: 0;
    z-index: 40;
    width: min(280px, 84vw);
    min-width: 0;
    transform: translateX(-100%);
    transition: transform var(--dur-base) var(--ease-out);
  }

  .sidebar:hover {
    width: min(280px, 84vw);
    min-width: 0;
    box-shadow: none;
  }

  .sidebar.drawer-open {
    transform: translateX(0);
    box-shadow: var(--shadow-lg);
  }

  .main {
    width: 100%;
  }
}

/* 抽屉遮罩: 仅 ≤768px 渲染 (模板 v-if 已控制), CSS 兜底 */
.drawer-mask {
  display: none;
  position: fixed;
  top: var(--topbar-height);
  bottom: var(--statusbar-height);
  left: 0;
  right: 0;
  z-index: 30;
  background: rgba(15, 23, 42, 0.4);
}

@media (max-width: 768px) {
  .drawer-mask {
    display: block;
  }
}

/* 遮罩淡入淡出 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--dur-base) ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 窄屏汉堡按钮 (模板 v-if 控制, 默认隐藏兜底) */
.hamburger-btn {
  display: none;
}

@media (max-width: 768px) {
  .hamburger-btn {
    display: flex;
  }
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

/* ---------- 状态栏 ---------- */
.statusbar {
  height: var(--statusbar-height);
  min-height: var(--statusbar-height);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: 0 var(--space-4);
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
  user-select: none;
}

.status-item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  white-space: nowrap;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: none;
}

.status-dot.ok {
  background: var(--success);
  box-shadow: 0 0 0 3px var(--success-light);
}

.status-dot.bad {
  background: var(--error);
  box-shadow: 0 0 0 3px var(--error-light);
}

.status-mode {
  padding: 0 6px;
  font-size: 11px;
  line-height: 16px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-light);
  border-radius: 3px;
}

.status-text {
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-spacer {
  flex: 1;
}

.status-streaming {
  color: var(--accent);
}

.mini-spinner {
  width: 10px;
  height: 10px;
  border: 2px solid var(--accent-border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.kbd-hint {
  opacity: 0.85;
}

.kbd-hint kbd {
  margin: 0 1px;
}

/* 过渡: 状态元素淡入淡出 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--dur-base) ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
