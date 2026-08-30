<template>
  <div class="input-wrap">
    <!-- 空会话轻提示: 点击"新建对话"但当前会话尚无消息时出现, 2s 后自动消失 -->
    <transition name="toast-fade">
      <div v-if="store.emptySessionToast" class="empty-toast">当前对话尚未开始</div>
    </transition>
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
    <!-- 底部操作区: 左侧为会话级工作目录选择按钮, 右侧为快捷键提示 -->
    <div class="input-footer">
      <WorkspacePicker :path="store.currentWorkspacePath" @error="showError" />
      <transition name="fade">
        <span v-if="errorMsg" class="footer-error">{{ errorMsg }}</span>
      </transition>
      <span class="hint">Enter 发送 · Shift + Enter 换行</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import { useChatStore } from '../stores/chat'
import WorkspacePicker from './WorkspacePicker.vue'

const store = useChatStore()
const text = ref('')
const ta = ref(null)
const errorMsg = ref('')

let errorTimer = null
function showError(message) {
  errorMsg.value = message
  clearTimeout(errorTimer)
  errorTimer = setTimeout(() => (errorMsg.value = ''), 3200)
}

const canSend = computed(() => text.value.trim() && !store.isStreaming)

// 「新建对话」被拦截时, store 发出聚焦信号 → 自动聚焦输入框
watch(
  () => store.inputFocusSignal,
  async () => {
    await nextTick()
    ta.value?.focus()
  }
)

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
  position: relative;
  padding: 12px 16px 12px;
  background: var(--bg-primary);
  border: none;
}

/* 空会话轻提示 Toast: 悬浮于输入框上方, 深色半透明胶囊 */
.empty-toast {
  position: absolute;
  left: 50%;
  bottom: calc(100% + 10px);
  transform: translateX(-50%);
  padding: 8px 16px;
  border-radius: 999px;
  background: rgba(28, 30, 34, 0.82);
  color: #fff;
  font-size: 13px;
  letter-spacing: 0.02em;
  white-space: nowrap;
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  pointer-events: none;
  z-index: 20;
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s var(--ease-out);
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(6px);
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

.input-footer {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.footer-error {
  font-size: 12px;
  color: var(--error);
  animation: shake 0.35s var(--ease-out);
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-3px); }
  75% { transform: translateX(3px); }
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.25s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.hint {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-secondary);
  opacity: 0.7;
}
</style>
