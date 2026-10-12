<template>
  <div class="input-wrap">
    <div class="input-box">
      <textarea
        ref="ta"
        v-model="text"
        rows="1"
        :placeholder="store.isStreaming ? 'AI 正在回复…' : '输入消息，Enter 发送'"
        :aria-label="'消息输入框'"
        @input="resize"
        @keydown.enter.exact.prevent="submit"
      ></textarea>
      <button
        v-if="store.isStreaming"
        class="send-btn stopping"
        :disabled="stopping"
        :title="stopping ? '正在停止…' : '停止生成'"
        :aria-label="'停止生成'"
        @click="stopGeneration"
      >
        <span v-if="stopping" class="spinner" aria-hidden="true"></span>
        <svg
          v-else
          xmlns="http://www.w3.org/2000/svg"
          width="13"
          height="13"
          viewBox="0 0 24 24"
          fill="currentColor"
          aria-hidden="true"
        >
          <rect x="5" y="5" width="14" height="14" rx="2"></rect>
        </svg>
      </button>
      <button
        v-else
        class="send-btn"
        :disabled="!canSend"
        title="发送 (Enter)"
        aria-label="发送消息"
        @click="submit"
      >
        <svg
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
      <WorkspacePicker :path="store.currentWorkspacePath" @error="onError" />
      <span class="hint"><kbd>Enter</kbd> 发送 · <kbd>Shift</kbd>+<kbd>Enter</kbd> 换行</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import { useChatStore } from '../stores/chat'
import { useToastStore } from '../stores/toast'
import WorkspacePicker from './WorkspacePicker.vue'

const store = useChatStore()
const toast = useToastStore()
const text = ref('')
const ta = ref(null)

/** 操作失败统一走全局 toast, 错误时长拉长便于阅读 */
function onError(message) {
  toast.error(message, 4200)
}

const canSend = computed(() => text.value.trim() && !store.isStreaming)

/* ---------- 停止生成 ---------- */
const stopping = ref(false)

async function stopGeneration() {
  if (stopping.value) return
  stopping.value = true
  try {
    await store.stopGeneration()
  } catch (e) {
    onError(`停止失败: ${e.message}`)
  } finally {
    stopping.value = false
  }
}

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
  padding: var(--space-3) var(--space-5);
  background: var(--bg-primary);
  border: none;
}

.input-box {
  display: flex;
  align-items: flex-end;
  gap: var(--space-3);
  background: var(--bg-primary);
  border: 1px solid var(--accent-border);
  border-radius: var(--radius-md);
  padding: 10px 12px 10px 14px;
  transition: border-color var(--dur-base), box-shadow var(--dur-base);
}

.input-box:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-ring);
}

.input-box textarea {
  flex: 1;
  border: none;
  background: transparent;
  resize: none;
  padding: 6px 4px;
  font-size: 14.5px;
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
  width: 36px;
  height: 36px;
  min-width: 36px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent);
  color: #fff;
  border-radius: 50%;
}

.send-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.send-btn:active:not(:disabled) {
  background: var(--accent-active);
}

.send-btn.sending {
  opacity: 1;
}

/* 停止按钮: 与发送同尺寸, 语义用错误色区分 (生成中随时可点) */
.send-btn.stopping {
  background: var(--error);
}

.send-btn.stopping:hover:not(:disabled) {
  background: var(--error-hover);
}

.send-btn.stopping:active:not(:disabled) {
  background: var(--error-hover);
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.input-footer {
  margin-top: var(--space-2);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 26px;
}

.fade-enter-active, .fade-leave-active { transition: opacity var(--dur-base) ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.hint {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-secondary);
  opacity: 0.8;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.hint kbd {
  font-size: 10px;
}
</style>
