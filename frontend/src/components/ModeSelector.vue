<template>
  <!-- 输入区底部「会话模式」分段选择器: 对应 POST /MiniCode/mode (routers/chatRouter.py)。
       模式按会话生效 (存 LangGraph 检查点), 与左侧工作目录选择器同为会话级设置 -->
  <div class="mode-selector" role="radiogroup" aria-label="会话模式">
    <button
      v-for="m in MODE_OPTIONS"
      :key="m.id"
      class="mode-btn"
      :class="{ active: m.id === mode, danger: m.id === 'free_fly' }"
      role="radio"
      :aria-checked="m.id === mode ? 'true' : 'false'"
      :disabled="disabled"
      :title="disabled ? disabledTitle : `${m.title}（POST /MiniCode/mode）`"
      @click="onPick(m.id)"
    >
      {{ m.label }}
    </button>
    <span v-if="busy" class="mode-spinner" aria-hidden="true"></span>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { MODE_OPTIONS, useChatStore } from '../stores/chat'
import { useToastStore } from '../stores/toast'

const props = defineProps({
  /** 当前会话的模式 id (work/plan/free_fly), 由父组件从 store.currentMode 传入 */
  mode: { type: String, default: 'work' },
})
const emit = defineEmits(['error'])

const store = useChatStore()
const toast = useToastStore()
const busy = ref(false)

/**
 * 禁用条件:
 *  - 还没有会话: 后端 update_mode 需要已存在的会话 (LangGraph 检查点)
 *  - 本会话生成中: 中途 aupdate_state 会与运行中的图竞争, 统一等收尾后再切
 *  - 上一次切换请求尚未返回 (busy)
 */
const disabled = computed(() => busy.value || !store.currentSessionId || store.isCurrentSessionStreaming)

const disabledTitle = computed(() => {
  if (busy.value) return '正在切换…'
  if (!store.currentSessionId) return '请先创建会话再选择模式'
  return '生成结束后可切换模式'
})

async function onPick(id) {
  if (disabled.value || id === props.mode) return
  busy.value = true
  try {
    const result = await store.setSessionMode(store.currentSessionId, id)
    if (result === 'deferred') {
      // 新会话检查点尚未建立: 本地已按选择展示, 首轮流式结束后 store 会自动补同步后端
      toast.info('新会话将在首轮对话开始后应用所选模式')
    }
  } catch (e) {
    emit('error', e?.message || '切换模式失败')
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
/* 无框分段控件: 轻底轨道 + 选中块, 不用整圈描边与逐格分隔线 */
.mode-selector {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  flex: none;
}

.mode-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  font-size: var(--fs-sm);
  font-weight: 500;
  line-height: 1.5;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  border-radius: var(--radius-xs);
  transition: color var(--dur-fast), background var(--dur-fast);
}

.mode-btn:hover:not(:disabled):not(.active) {
  color: var(--text-primary);
  background: transparent;
}

/* 选中: 抬起的浅色块 + 主文字, 高度一眼可辨但不刺眼 */
.mode-btn.active {
  color: var(--text-primary);
  background: var(--bg-primary);
  box-shadow: var(--shadow-xs);
}

/* 自由飞行是「跳过审批」的高风险模式, 选中时用警示色区分 */
.mode-btn.active.danger {
  color: var(--warning);
}

.mode-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.mode-spinner {
  width: 10px;
  height: 10px;
  margin: 0 7px;
  flex: none;
  border: 2px solid var(--accent-border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
</style>
