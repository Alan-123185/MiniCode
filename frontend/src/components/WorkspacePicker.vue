<template>
  <!-- 底部"选择工作目录"按钮: 仅作用于当前会话; 已绑定时只读 -->
  <button
    class="workspace-picker"
    :class="{ active: !!path, bound: !!path }"
    :title="buttonTitle"
    :disabled="busy || !!path"
    @click="onPick"
  >
    <svg
      class="picker-icon"
      xmlns="http://www.w3.org/2000/svg"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
    </svg>
    <span class="picker-label">{{ label }}</span>
    <span v-if="busy" class="picker-spinner" aria-hidden="true"></span>
  </button>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useChatStore } from '../stores/chat'
import { useWorkspacePicker } from '../composables/useWorkspacePicker'

const props = defineProps({
  path: { type: String, default: '' },
})
const emit = defineEmits(['error'])

const store = useChatStore()
const { isElectron, pickDirectory } = useWorkspacePicker()
const busy = ref(false)

const label = computed(() => {
  if (busy.value) return '选择中…'
  if (props.path) return '已绑定目录'
  return '选择工作目录'
})

/** 后端契约(choose_workplace): 工作目录一旦绑定就不能再改, 因此已绑定时按钮置灰并说明原因 */
const buttonTitle = computed(() =>
  props.path
    ? `当前会话工作目录: ${props.path}（已绑定，后端不支持更改；如需更换请新建会话）`
    : '为当前会话选择工作目录'
)

async function onPick() {
  if (busy.value || props.path) return
  busy.value = true
  try {
    const dir = await pickDirectory()
    if (!dir) return // 用户取消
    await store.setSessionWorkspace(store.currentSessionId, dir)
  } catch (e) {
    emit('error', e?.message || '设置工作目录失败')
  } finally {
    busy.value = false
  }
}

defineExpose({ isElectron })
</script>

<style scoped>
/* 输入区底部目录选择: 安静文本按钮, 与模式选择器/快捷键提示同处一行,
   不再单独套一层描边容器 (输入区周围只保留 input-box 一层轮廓) */
.workspace-picker {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 8px;
  font-size: var(--fs-sm);
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
}

.workspace-picker:hover:not(:disabled) {
  color: var(--text-primary);
  background: var(--bg-hover);
  border: none;
  box-shadow: none;
  transform: none;
}

/* 已绑定: 只读状态文本, 用强调色点出"已生效", 但不做底色块 */
.workspace-picker.active {
  color: var(--text-secondary);
  background: transparent;
}

.workspace-picker.active .picker-icon {
  color: var(--success);
}

.workspace-picker:disabled {
  opacity: 0.6;
  cursor: progress;
  transform: none;
}

/* 已绑定: 只读态, 不是"正在加载" */
.workspace-picker.bound:disabled {
  opacity: 1;
  cursor: default;
}

.workspace-picker.bound:hover:not(:disabled) {
  background: transparent;
}

.picker-icon {
  flex: none;
  opacity: 0.8;
}

.picker-spinner {
  width: 11px;
  height: 11px;
  border: 2px solid var(--accent-border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
</style>
