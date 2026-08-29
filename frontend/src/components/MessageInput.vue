<template>
  <div class="input-wrap">
    <div class="input-box">
      <textarea
        ref="ta"
        v-model="text"
        rows="1"
        :placeholder="store.isStreaming ? 'AI 正在回复…' : '输入消息，Enter 发送'"
        @input="resize"
        @keydown.enter.exact.prevent="submit"
      ></textarea>
      <button
        class="send-btn"
        :class="{ sending: store.isStreaming }"
        :disabled="!canSend"
        @click="submit"
      >
        <span v-if="store.isStreaming" class="spinner"></span>
        <svg
          v-else
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <line x1="12" y1="19" x2="12" y2="5"></line>
          <polyline points="5 12 12 5 19 12"></polyline>
        </svg>
      </button>
    </div>
    <div class="hint">Enter 发送 · Shift + Enter 换行</div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { useChatStore } from '../stores/chat'

const store = useChatStore()
const text = ref('')
const ta = ref(null)

const canSend = computed(() => text.value.trim() && !store.isStreaming)

function resize() {
  const el = ta.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 140) + 'px'
}

async function submit() {
  if (!canSend.value) return
  const content = text.value.trim()
  text.value = ''
  await nextTick()
  resize()
  await store.sendMessage(content)
}
</script>

<style scoped>
.input-wrap {
  padding: 12px 16px 12px;
  background: var(--bg-primary);
  border: none;
}

.input-box {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: var(--bg-primary);
  border: 1px solid var(--accent);
  border-radius: 16px;
  padding: 10px 14px;
  transition: border-color 0.25s;
}

.input-box:focus-within {
  border-color: var(--accent);
}

.input-box textarea {
  flex: 1;
  border: none;
  background: transparent;
  resize: none;
  padding: 6px 4px;
  font-size: 15px;
  line-height: 1.6;
  max-height: 160px;
  font-family: inherit;
}

.input-box textarea:focus {
  outline: none;
  border: none;
  box-shadow: none;
}

.send-btn {
  width: 40px;
  height: 40px;
  min-width: 40px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
}

.send-btn.sending {
  opacity: 1;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  opacity: 0.7;
  text-align: right;
}
</style>
