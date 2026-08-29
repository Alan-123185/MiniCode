<template>
  <!-- 底部"选择工作目录"按钮: 仅作用于当前会话 -->
  <button
    class="workspace-picker"
    :class="{ active: !!path }"
    :title="path ? `更换当前会话的工作目录（当前: ${path}）` : '为当前会话选择工作目录'"
    :disabled="busy"
    @click="onPick"
  >
    <svg
      class="picker-icon"
      xmlns="http://www.w3.org/2000/svg"
      width="15"
      height="15"
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
    <span v-if="busy" class="picker-spinner"></span>
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
  if (props.path) return '更换目录'
  return '选择工作目录'
})

async function onPick() {
  if (busy.value) return
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
.workspace-picker {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
}

.workspace-picker:hover:not(:disabled) {
  color: var(--accent);
  background: var(--accent-light);
  border-color: var(--accent-border);
  box-shadow: var(--shadow-sm);
}

.workspace-picker.active {
  color: var(--accent);
  background: var(--accent-light);
  border-color: var(--accent-border);
}

.workspace-picker:disabled {
  opacity: 0.6;
  cursor: progress;
  transform: none;
}

.picker-icon {
  flex: none;
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
