<template>
  <div class="app">
    <aside class="sidebar">
      <SessionList />
      <div class="sidebar-footer">
        <button class="gear-btn" title="设置" @click="showSettings = true">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="3"></circle>
            <path
              d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"
            ></path>
          </svg>
        </button>
        <div class="theme-switch">
          <button class="switch-btn" @click="toggleTheme">
            {{ isDarkMode ? '🌙' : '☀️' }}
          </button>
        </div>
      </div>
    </aside>
    <main class="main">
      <ChatWindow />
    </main>
    <SettingsModal :visible="showSettings" @close="showSettings = false" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import ChatWindow from './components/ChatWindow.vue'
import SessionList from './components/SessionList.vue'
import SettingsModal from './components/SettingsModal.vue'
import MessageInput from './components/MessageInput.vue'
import { useChatStore } from './stores/chat'

const store = useChatStore()
const showSettings = ref(false)

// Theme state
const isDarkMode = ref(localStorage.getItem('dark-mode') === 'true')

// Toggle theme function
const toggleTheme = () => {
  isDarkMode.value = !isDarkMode.value
  localStorage.setItem('dark-mode', isDarkMode.value)
  document.documentElement.classList.toggle('dark-mode', isDarkMode.value)
}

onMounted(() => {
  store.init()
  // Apply initial theme
  if (isDarkMode.value) {
    document.documentElement.classList.add('dark-mode')
  }
})
</script>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.sidebar {
  width: 260px;
  min-width: 260px;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
}

.sidebar-footer {
  margin-top: auto;
  padding: 12px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.gear-btn {
  width: 36px;
  height: 36px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: 999px;
}

.gear-btn:hover {
  color: var(--accent);
  background: var(--accent-light);
  border-color: var(--accent);
}

.gear-btn svg {
  transition: transform 0.5s var(--ease-out);
  transform-origin: center 30%;
}

.gear-btn:hover svg {
  transform: rotate(90deg);
}

.theme-switch {
  margin-left: 8px;
}

.switch-btn {
  width: 36px;
  height: 36px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: 999px;
  cursor: pointer;
  font-size: 18px;
  transition: all 0.3s ease;
}

.switch-btn:hover {
  color: var(--accent);
  background: var(--accent-light);
  border-color: var(--accent);
  transform: scale(1.1);
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
</style>
