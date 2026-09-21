<template>
  <!-- 顶栏: 当前会话绑定的工作目录徽章 -->
  <div class="workspace-badge" :class="{ empty: !path, 'pulse-in': animate }">
    <button
      class="badge-body"
      :title="path ? `会话工作目录: ${path}（点击更换）` : '为当前会话选择工作目录'"
      :disabled="busy"
      @click="onPick"
    >
      <svg
        class="badge-icon"
        xmlns="http://www.w3.org/2000/svg"
        width="13"
        height="13"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
      </svg>
      <span class="badge-text">{{ path ? shortPath : '未绑定目录' }}</span>
      <span v-if="path" class="badge-pulse" aria-hidden="true"></span>
    </button>
    <button
      v-if="path"
      class="badge-clear"
      title="解绑当前会话的工作目录"
      aria-label="解绑当前会话的工作目录"
      @click.stop="onClear"
    >×</button>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useChatStore } from '../stores/chat'
import { useWorkspacePicker } from '../composables/useWorkspacePicker'

const store = useChatStore()
const { pickDirectory } = useWorkspacePicker()
const busy = ref(false)

const path = computed(() => store.currentWorkspacePath)

/** 长路径只显示末段 + 省略号，完整路径放 title 悬浮提示 */
const shortPath = computed(() => {
  if (!path.value) return ''
  const parts = path.value.replace(/[\\/]+$/, '').split(/[\\/]/)
  const name = parts[parts.length - 1] || path.value
  return name.length > 18 ? name.slice(0, 17) + '…' : name
})

/** 点击徽章 = 重新选择目录（仅作用于当前会话） */
async function onPick() {
  if (busy.value) return
  busy.value = true
  try {
    const dir = await pickDirectory()
    if (!dir) return // 用户取消
    await store.setSessionWorkspace(store.currentSessionId, dir)
  } catch (e) {
    console.error('设置工作目录失败', e)
  } finally {
    busy.value = false
  }
}

/** 解绑当前会话目录 */
async function onClear() {
  try {
    await store.clearSessionWorkspace(store.currentSessionId)
  } catch (e) {
    console.error('解绑工作目录失败', e)
  }
}

/** 路径变化时播放一次入场脉冲动画（体现"绑定成功"的生命力） */
const animate = ref(false)
watch(
  () => path.value,
  (val, old) => {
    if (val && val !== old) {
      animate.value = true
      setTimeout(() => (animate.value = false), 650)
    }
  }
)
</script>

<style scoped>
.workspace-badge {
  position: relative;
  display: inline-flex;
  align-items: center;
  max-width: 260px;
  animation: badgeIn 0.35s var(--ease-out) both;
}

@keyframes badgeIn {
  from {
    opacity: 0;
    transform: translateY(-4px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.badge-body {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding: 4px 10px;
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-pill);
  box-shadow: none;
}

.badge-body:hover:not(:disabled) {
  color: var(--accent);
  background: var(--accent-light);
  border-color: var(--accent-border);
  box-shadow: none;
  transform: none;
}

.badge-icon {
  flex: none;
  opacity: 0.85;
}

.badge-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

/* 绑定成功的一次性脉冲光环 */
.badge-pulse {
  position: absolute;
  inset: -2px;
  border-radius: var(--radius-pill);
  pointer-events: none;
  opacity: 0;
}

.pulse-in .badge-pulse {
  animation: badgePulse 0.6s var(--ease-out);
}

@keyframes badgePulse {
  0% {
    opacity: 0.6;
    box-shadow: 0 0 0 0 var(--accent-ring);
  }
  100% {
    opacity: 0;
    box-shadow: 0 0 0 8px transparent;
  }
}

.badge-clear {
  width: 15px;
  height: 15px;
  margin-left: -6px;
  padding: 0;
  font-size: 11px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  background: var(--border-color);
  border-radius: 50%;
  z-index: 1;
}

.badge-clear:hover:not(:disabled) {
  color: #fff;
  background: var(--error);
}

.workspace-badge.empty .badge-body {
  border-style: dashed;
  background: transparent;
}
</style>
