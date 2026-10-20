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
  /* 输入区直接坐落于对话区底部: 纯色底, 无渐变无悬浮层 */
  padding: var(--space-2) var(--space-5) var(--space-4);
  background: var(--bg-primary);
  border: none;
}

/* 单一轻边框输入容器: 与消息居中通道同宽, 只有一层轮廓 */
.input-box {
  display: flex;
  align-items: flex-end;
  gap: var(--space-3);
  max-width: var(--content-max);
  margin: 0 auto;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 9px 10px 9px 14px;
  transition: border-color var(--dur-base), box-shadow var(--dur-base);
}

/* 聚焦: 一圈克制的强调色 ring, 与全局输入控件一致 */
.input-box:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-ring);
}

.input-box textarea {
  flex: 1;
  border: none;
  background: transparent;
  resize: none;
  padding: 5px 2px;
  font-size: var(--fs-md);
  line-height: 1.55;
  max-height: 160px;
  font-family: inherit;
}

.input-box textarea:focus {
  outline: none;
  border: none;
  box-shadow: none;
}

/* 发送: 主交互, 强调色圆形按钮 (醒目但尺寸克制) */
.send-btn {
  width: 34px;
  height: 34px;
  min-width: 34px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent);
  /* 用主题反色而非硬编码白: 暗色主题的强调色偏亮, 白图标对比度不足 (3.1:1) */
  color: var(--text-inverse);
  border: none;
  border-radius: 50%;
}

.send-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.send-btn:active:not(:disabled) {
  background: var(--accent-active);
  opacity: 1;
}

.send-btn:disabled {
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
  opacity: 1;
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
  opacity: 1;
}

.spinner {
  width: 15px;
  height: 15px;
  /* 轨道用 currentColor 淡化, 指示弧用满色: 随按钮文字色自适应明暗主题 */
  border: 2px solid color-mix(in srgb, currentColor 35%, transparent);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

/* 底部操作行: 目录 / 模式 / 快捷提示, 均为无框轻量控件。
   允许换行: 极窄窗口下宁可让控件折到第二行, 也不横向溢出被裁掉 */
.input-footer {
  margin-top: var(--space-2);
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  max-width: var(--content-max);
  margin-inline: auto;
  min-height: 26px;
}

.fade-enter-active, .fade-leave-active { transition: opacity var(--dur-base) ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* 快捷键提示: 最弱一档辅助文字 */
.hint {
  margin-left: auto;
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.hint kbd {
  font-size: var(--fs-xs);
  opacity: 0.8;
}

/* 窄窗口: 侧栏占去 264px 后主区已放不下三个控件, 优先舍弃最弱的快捷键提示
   (它只是辅助说明, 而目录/模式是必需操作), 避免底部操作行被挤到溢出 */
@media (max-width: 780px) {
  .hint {
    display: none;
  }
}
</style>
