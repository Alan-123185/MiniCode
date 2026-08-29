<template>
  <div class="session-list">
    <div class="session-header">
      <h3>会话</h3>
      <button @click="store.createNewChat()">+</button>
    </div>
    <ul>
      <li
        v-for="session in store.sessions"
        :key="session.id"
        :class="{ active: session.id === store.currentSessionId }"
        @click="selectSession(session.id)"
      >
        <span class="title">{{ session.title }}</span>
        <button class="delete-btn" title="删除会话" @click.stop="store.removeSession(session.id)">×</button>
      </li>
    </ul>
    <div v-if="store.sessions.length === 0" class="session-empty">
      暂无会话<br />点左上角 + 新建
    </div>
  </div>
</template>

<script setup>
import { useChatStore } from '../stores/chat'

const store = useChatStore()

async function selectSession(sessionId) {
  store.currentSessionId = sessionId
  await store.loadHistory(sessionId)
}
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
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.session-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

.session-header button {
  padding: 4px 14px;
  font-size: 18px;
  line-height: 1.2;
  transition: transform 0.3s var(--ease-out), background 0.25s;
}

.session-header button:hover {
  transform: rotate(90deg) scale(1.08);
}

ul {
  list-style: none;
  margin: 0;
  padding: 8px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  cursor: pointer;
  border-radius: 12px;
  transition: background 0.15s, transform 0.15s;
  color: var(--text-primary);
  animation: slideLeft 0.2s var(--ease-out) both;
}

li:hover {
  background: var(--bg-tertiary);
  transform: translateX(3px);
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
  padding: 24px 16px;
  text-align: center;
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-secondary);
  opacity: 0.7;
}

.title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 8px;
  font-size: 14px;
}

.delete-btn {
  background: transparent;
  color: var(--text-secondary);
  padding: 0;
  width: 24px;
  height: 24px;
  line-height: 24px;
  text-align: center;
  border-radius: 999px;
  opacity: 0;
  transition: opacity 0.15s, background 0.15s;
}

li:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: var(--error);
  color: #fff;
}
</style>
