<template>
  <!-- 顶栏: 当前会话绑定的工作目录徽章 -->
  <div class="workspace-badge" :class="{ empty: !path, 'pulse-in': animate }">
    <button
      class="badge-body"
      :title="bodyTitle"
      :disabled="busy || !!path"
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
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useChatStore } from '../stores/chat'
import { useToastStore } from '../stores/toast'
import { useWorkspacePicker } from '../composables/useWorkspacePicker'

const store = useChatStore()
const toast = useToastStore()
const { pickDirectory } = useWorkspacePicker()
const busy = ref(false)

const path = computed(() => store.currentWorkspacePath)

/** 已绑定 → 只读展示: 后端不允许修改已选定的工作目录, 因此不再提供"更换/解绑"入口 */
const bodyTitle = computed(() =>
  path.value
    ? `会话工作目录: ${path.value}（已绑定，后端不支持更改；如需更换请新建会话）`
    : '为当前会话选择工作目录'
)

/** 长路径只显示末段 + 省略号，完整路径放 title 悬浮提示 */
const shortPath = computed(() => {
  if (!path.value) return ''
  const parts = path.value.replace(/[\\/]+$/, '').split(/[\\/]/)
  const name = parts[parts.length - 1] || path.value
  return name.length > 18 ? name.slice(0, 17) + '…' : name
})

/** 点击徽章 = 为该会话绑定目录（仅未绑定时可用，只作用于当前会话） */
async function onPick() {
  if (busy.value || path.value) return
  busy.value = true
  try {
    const dir = await pickDirectory()
    if (!dir) return // 用户取消
    await store.setSessionWorkspace(store.currentSessionId, dir)
  } catch (e) {
    // 失败必须让用户看见(原来只打 console, 点一下没反应像是坏了)
    toast.error(e?.message || '设置工作目录失败', 4200)
    console.error('设置工作目录失败', e)
  } finally {
    busy.value = false
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
  max-width: 240px;
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

/* 顶栏目录指示: 无底色无描边的安静文本, 与主题/设置图标同一视觉权重。
   已绑定时是只读状态文本, 未绑定时才是一个可点的次要操作。 */
.badge-body {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  padding: 4px 8px;
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  box-shadow: none;
}

.badge-body:hover:not(:disabled) {
  color: var(--text-primary);
  background: var(--bg-hover);
  border: none;
  box-shadow: none;
  transform: none;
}

/* 已绑定时是只读指示器(后端不允许改), 不能给"可点击"的光标暗示 */
.badge-body:disabled {
  cursor: default;
  opacity: 1;
}

.badge-icon {
  flex: none;
  opacity: 0.7;
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
  border-radius: var(--radius-sm);
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

/* 未绑定: 用虚线轮廓提示"这里可以点", 但仍是轻量文本按钮而非胶囊徽章 */
.workspace-badge.empty .badge-body {
  border: 1px dashed var(--border-strong);
  color: var(--text-tertiary);
}

.workspace-badge.empty .badge-body:hover:not(:disabled) {
  color: var(--text-secondary);
  border-color: var(--text-tertiary);
  background: transparent;
}
</style>
