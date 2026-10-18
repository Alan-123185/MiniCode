<template>
  <div class="input-wrap">
    <div class="input-box">
      <textarea
        ref="ta"
        v-model="text"
        rows="1"
        :placeholder="inputPlaceholder"
        :aria-label="'消息输入框'"
        @input="resize"
        @keydown.enter.exact.prevent="submit"
      ></textarea>
      <!-- 停止按钮只对「当前会话自己在生成」时出现: 别的会话在后台跑时不能在这里亮,
           否则用户会以为当前会话在运行, 点了还会把停止请求发到错误的会话上 -->
      <button
        v-if="store.isCurrentSessionStreaming"
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
    <!-- 底部操作区: 左侧为会话级工作目录选择 + 会话模式选择, 右侧为快捷键提示 -->
    <div class="input-footer">
      <WorkspacePicker :path="store.currentWorkspacePath" @error="onError" />
      <ModeSelector :mode="store.currentMode" @error="onError" />
      <span class="hint"><kbd>Enter</kbd> 发送 · <kbd>Shift</kbd>+<kbd>Enter</kbd> 换行</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import { useChatStore } from '../stores/chat'
import { useToastStore } from '../stores/toast'
import WorkspacePicker from './WorkspacePicker.vue'
import ModeSelector from './ModeSelector.vue'

const store = useChatStore()
const toast = useToastStore()
const text = ref('')
const ta = ref(null)

/** 操作失败统一走全局 toast, 错误时长拉长便于阅读 */
function onError(message) {
  toast.error(message, 4200)
}

/**
 * 能否发送: 只看「当前会话」是否在生成。
 * 并行生成后, 别的会话在后台跑不影响本会话发送 —— 后端按 session_id/thread_id
 * 完全隔离, 闸门也是按会话的 (sendMessage 里的 isSessionStreaming)。
 */
const canSend = computed(() => text.value.trim() && !store.isCurrentSessionStreaming)

/** 输入框占位符: 当前会话在生成 / 别的会话在并行生成 / 空闲, 三种状态说三种话 */
const inputPlaceholder = computed(() => {
  if (store.isCurrentSessionStreaming) return 'AI 正在回复…'
  if (store.hasBackgroundStreaming) {
    return `另有 ${store.streamingCount} 个会话生成中 · 本会话可直接发消息`
  }
  return '输入消息，Enter 发送'
})

/* ---------- 停止生成 ---------- */
const stopping = ref(false)

async function stopGeneration() {
  // 双保险: 当前会话没在生成就不发请求 (store.stopGeneration 内部也会按会话校验)
  if (stopping.value || !store.isCurrentSessionStreaming) return
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
  /* 悬浮输入区: 底部留白不贴底, 顶部渐隐让滚动内容自然过渡到输入卡片 */
  padding: var(--space-3) var(--space-5) var(--space-5);
  background: linear-gradient(to top, var(--bg-primary) 55%, transparent);
  border: none;
}

/* 毛玻璃悬浮输入卡片: 与消息居中通道同宽, blur 模糊其下滚动内容 */
.input-box {
  display: flex;
  align-items: flex-end;
  gap: var(--space-3);
  max-width: min(880px, 100%);
  margin: 0 auto;
  background: var(--bg-glass);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 10px 12px 10px 14px;
  box-shadow: var(--shadow-md);
  transition: border-color var(--dur-base), box-shadow var(--dur-base);
}

/* 聚焦: 淡蓝发光边框 (一圈柔和光晕), 强化悬浮层级 */
.input-box:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-ring), var(--shadow-md);
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
  max-width: min(880px, 100%);
  margin-inline: auto;
  min-height: 26px;
}

.fade-enter-active, .fade-leave-active { transition: opacity var(--dur-base) ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* 快捷键提示: 更轻量的小字 (置于输入卡片下方, 弱化不抢焦点) */
.hint {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-tertiary);
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.hint kbd {
  font-size: 10px;
  opacity: 0.75;
}
</style>
