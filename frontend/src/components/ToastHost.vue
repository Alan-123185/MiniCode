<template>
  <!--
    全局提示宿主: 唯一的 toast 渲染出口, 挂在 App 根节点下。
    各组件不再自持提示 state, 统一调 useToastStore().success/error/info。
    z-index 高于设置弹窗(100), 保证操作反馈永远可见。
  -->
  <div v-if="visible" class="toast-host" role="status" aria-live="polite" aria-atomic="false">
    <transition-group name="toast">
      <div
        v-for="toast in store.toasts"
        :key="toast.id"
        class="toast"
        :class="toast.type"
      >
        <span class="toast-icon" aria-hidden="true">{{ iconOf(toast.type) }}</span>
        <span class="toast-text">{{ toast.message }}</span>
        <button
          v-if="toast.duration > 0"
          class="toast-close"
          type="button"
          aria-label="关闭提示"
          title="关闭"
          @click="store.dismiss(toast.id)"
        >
          ×
        </button>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useToastStore } from '../stores/toast'

const store = useToastStore()

const ICONS = { success: '✓', error: '✕', info: 'ⓘ' }
const iconOf = (type) => ICONS[type] || ICONS.info

/** 空队列时不占位, 避免挡住下层点击 */
const visible = computed(() => store.toasts.length > 0)
</script>

<style scoped>
/* 宿主容器: 固定顶部居中, 不拦截鼠标事件 (只有气泡本身可交互) */
.toast-host {
  position: fixed;
  top: calc(var(--topbar-height, 44px) + 12px);
  left: 50%;
  transform: translateX(-50%);
  /* 高于设置弹窗 (z-index: 100), 保证操作反馈永远可见 */
  z-index: 200;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  max-width: min(520px, 88vw);
  padding: 8px 10px 8px 12px;
  font-size: 13px;
  line-height: 1.45;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: var(--bg-elevated, var(--bg-primary));
  color: var(--text-primary);
  box-shadow: var(--shadow-lg);
  pointer-events: auto;
}

.toast-icon {
  flex: none;
  width: 16px;
  height: 16px;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 700;
  border-radius: 50%;
  color: #fff;
}

.toast-text {
  min-width: 0;
  overflow-wrap: anywhere;
}

.toast-close {
  flex: none;
  width: 20px;
  height: 20px;
  margin-left: 2px;
  display: grid;
  place-items: center;
  font-size: 15px;
  line-height: 1;
  color: var(--text-tertiary);
  background: transparent;
  border: none;
  border-radius: var(--radius-xs);
  cursor: pointer;
}

.toast-close:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

/* 类型配色: 图标底色用语义色, 文案保持可读 */
.toast.success {
  border-color: color-mix(in srgb, var(--success) 40%, var(--border-color));
  background: var(--success-light);
}
.toast.success .toast-icon {
  background: var(--success);
}

.toast.error {
  border-color: color-mix(in srgb, var(--error) 40%, var(--border-color));
  background: var(--error-light);
}
.toast.error .toast-icon {
  background: var(--error);
}

.toast.info {
  border-color: color-mix(in srgb, var(--info) 40%, var(--border-color));
  background: var(--info-light);
}
.toast.info .toast-icon {
  background: var(--info);
}

/* 进出场: 上滑淡入, 多条同时存在时逐个错开 */
.toast-enter-active,
.toast-leave-active {
  transition:
    opacity var(--dur-fast, 0.18s) var(--ease-out),
    transform var(--dur-fast, 0.18s) var(--ease-out);
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.toast-leave-active {
  position: absolute;
}
</style>
