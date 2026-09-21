<template>
  <div class="settings-modal" v-if="visible">
    <div class="modal-mask" @click="close"></div>
    <div class="modal-panel" role="dialog" aria-modal="true" aria-label="设置">
      <div class="modal-header">
        <h3>设置</h3>
        <button class="close-btn" title="关闭 (Esc)" aria-label="关闭设置" @click="close">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      <div class="modal-body">
        <div class="modal-section">
          <h4>模型配置</h4>

          <!-- 5 组配置选项卡: ←/→ 切换, 绿点标记当前已应用到后端的分组 -->
          <div class="tab-bar" role="tablist" aria-label="模型配置分组" @keydown="onTabKeydown">
            <button
              v-for="(p, i) in profiles"
              :key="i"
              ref="tabBtns"
              class="tab-btn"
              role="tab"
              :class="{ active: i === activeIndex }"
              :aria-selected="i === activeIndex"
              :title="tabTitle(i)"
              @click="activeIndex = i"
            >
              <span>配置{{ i + 1 }}</span>
              <span v-if="p.model" class="tab-model">{{ shortModel(p.model) }}</span>
              <span v-if="i === defaultIndex" class="tab-star" title="默认配置">★</span>
              <span v-if="i === appliedIndex" class="tab-dot" title="当前已应用"></span>
            </button>
          </div>

          <div class="field">
            <label :for="fieldId('model')">模型名</label>
            <input :id="fieldId('model')" v-model="currentProfile.model" placeholder="模型名" />
          </div>
          <div class="field">
            <label :for="fieldId('base-url')">Base URL</label>
            <input :id="fieldId('base-url')" v-model="currentProfile.base_url" placeholder="Base URL" />
          </div>
          <div class="field">
            <label :for="fieldId('api-key')">API Key</label>
            <input
              :id="fieldId('api-key')"
              v-model="currentProfile.api_key"
              type="password"
              placeholder="API Key"
              autocomplete="off"
            />
          </div>

          <div class="btn-row">
            <button
              class="primary-btn"
              :class="{ applied: isCurrentApplied }"
              :disabled="applying || isCurrentApplied"
              :title="isCurrentApplied
                ? '当前选项卡已是生效配置；修改输入内容后可重新应用'
                : '将当前选项卡的配置提交到后端'"
              @click="applyProfile"
            >
              {{ applying ? '应用中…' : isCurrentApplied ? '✓ 已应用' : '应用此配置' }}
            </button>
            <button
              class="ghost-btn"
              title="将当前选项卡设为默认配置，下次启动应用时自动使用"
              @click="setAsDefault"
            >
              设为默认
            </button>
            <button
              class="text-btn"
              title="仅清空当前选项卡的输入内容，不影响其他配置组"
              @click="resetCurrentProfile"
            >
              清空此组
            </button>
          </div>
          <p v-if="feedback" :class="['feedback', feedbackType]">{{ feedback }}</p>
        </div>
      </div>
      <div class="modal-footer">
        <span class="footer-hint"><kbd>Esc</kbd> 关闭 · <kbd>←</kbd><kbd>→</kbd> 切换配置组</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { useChatStore, MODEL_PROFILES_KEY } from '../stores/chat'

const props = defineProps({
  visible: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const store = useChatStore()

/* ================= 5 组模型配置 (选项卡分页) ================= */

const PROFILE_COUNT = 5
/** 本地持久化键 (定义在 store, 供启动时自动应用默认配置) */
const STORAGE_KEY = MODEL_PROFILES_KEY

function emptyProfile() {
  return { model: '', base_url: '', api_key: '' }
}

function loadStored() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    if (raw && Array.isArray(raw.profiles) && raw.profiles.length === PROFILE_COUNT) {
      const inRange = (n) => Number.isInteger(n) && n >= 0 && n < PROFILE_COUNT
      return {
        profiles: raw.profiles.map((p) => ({
          model: p?.model || '',
          base_url: p?.base_url || '',
          api_key: p?.api_key || '',
        })),
        activeIndex: inRange(raw.activeIndex) ? raw.activeIndex : 0,
        appliedIndex: raw.appliedIndex === -1 || inRange(raw.appliedIndex) ? raw.appliedIndex : -1,
        appliedSnapshots:
          Array.isArray(raw.appliedSnapshots) && raw.appliedSnapshots.length === PROFILE_COUNT
            ? raw.appliedSnapshots.map((s) => (typeof s === 'string' ? s : ''))
            : Array(PROFILE_COUNT).fill(''),
        defaultIndex: raw.defaultIndex === -1 || inRange(raw.defaultIndex) ? raw.defaultIndex : -1,
      }
    }
  } catch {
    /* 存储损坏时按无存储处理 */
  }
  return null
}

const stored = loadStored()
const profiles = ref(stored?.profiles ?? Array.from({ length: PROFILE_COUNT }, emptyProfile))
const activeIndex = ref(stored?.activeIndex ?? 0)
const appliedIndex = ref(stored?.appliedIndex ?? -1)
/** 各组「应用时」的数据快照: 与当前输入一致 = 该组已是生效配置 (应用按钮据此置灰) */
const appliedSnapshots = ref(stored?.appliedSnapshots ?? Array(PROFILE_COUNT).fill(''))
/** 应用请求进行中 (防重复提交) */
const applying = ref(false)
/** 用户设定的默认配置组: 应用启动时自动应用 (-1 = 未设置) */
const defaultIndex = ref(stored?.defaultIndex ?? -1)
/** 首次打开时用后端当前配置填充空「配置1」的一次性迁移标记 */
const seededFromStore = ref(false)
/** 操作反馈文案与语义类型 (success / error) */
const feedback = ref('')
const feedbackType = ref('success')
let feedbackTimer = null
const tabBtns = ref([])

/** 当前高亮 Tab 绑定的配置对象 (输入框直接 v-model 到该对象的字段) */
const currentProfile = computed(() => profiles.value[activeIndex.value])

/** 序列化一组配置, 用于「应用时快照 vs 当前输入」比较 */
function snapshotOf(p) {
  return JSON.stringify([p.model, p.base_url, p.api_key])
}

/** 当前 Tab 已应用且输入未被改动 → 「应用此配置」按钮置灰禁用; 一旦改动输入即恢复可点 */
const isCurrentApplied = computed(
  () =>
    appliedIndex.value === activeIndex.value &&
    appliedSnapshots.value[activeIndex.value] === snapshotOf(currentProfile.value)
)

function persist() {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        profiles: profiles.value.map((p) => ({ ...p })),
        activeIndex: activeIndex.value,
        appliedIndex: appliedIndex.value,
        appliedSnapshots: [...appliedSnapshots.value],
        defaultIndex: defaultIndex.value,
      })
    )
  } catch (e) {
    console.error('保存模型配置分组失败', e)
  }
}

/* 任何编辑(含输入)/切 Tab/应用状态变化 → 自动持久化 */
watch([profiles, activeIndex, appliedIndex, defaultIndex, appliedSnapshots], persist, { deep: true })

/* ---------- Tab 交互 ---------- */

function shortModel(m) {
  return m.length > 10 ? m.slice(0, 9) + '…' : m
}

function tabTitle(i) {
  const p = profiles.value[i]
  const filled = p.model ? ` · ${p.model}` : ''
  const isDefault = i === defaultIndex.value ? ' · 默认' : ''
  const applied = i === appliedIndex.value ? ' · 已应用' : ''
  return `配置${i + 1}${filled}${isDefault}${applied}`
}

/** Tab 内 ←/→ 循环切换, 焦点跟随 */
function onTabKeydown(e) {
  if (e.key === 'ArrowRight') {
    activeIndex.value = (activeIndex.value + 1) % PROFILE_COUNT
  } else if (e.key === 'ArrowLeft') {
    activeIndex.value = (activeIndex.value + PROFILE_COUNT - 1) % PROFILE_COUNT
  } else {
    return
  }
  e.preventDefault()
  nextTick(() => tabBtns.value?.[activeIndex.value]?.focus())
}

function fieldId(name) {
  return `setting-${name}-${activeIndex.value}`
}

/* ---------- 打开/关闭 ---------- */

function showFeedback(message, type = 'success') {
  feedback.value = message
  feedbackType.value = type
  clearTimeout(feedbackTimer)
  feedbackTimer = setTimeout(() => (feedback.value = ''), 2600)
}

watch(
  () => props.visible,
  async (v) => {
    if (!v) {
      window.removeEventListener('keydown', handleKeydown)
      return
    }
    // 首次打开且本地无存储: 把后端当前生效的配置迁入「配置1」, 避免用户以为丢了配置
    if (!seededFromStore.value) {
      seededFromStore.value = true
      const cur = store.modelConfig || {}
      const firstEmpty =
        !profiles.value[0].model && !profiles.value[0].base_url && !profiles.value[0].api_key
      if (!stored && firstEmpty && (cur.model || cur.base_url || cur.api_key)) {
        Object.assign(profiles.value[0], {
          model: cur.model || '',
          base_url: cur.base_url || '',
          api_key: cur.api_key || '',
        })
        // 迁入的即是后端当前生效配置 → 直接标记为已应用 (按钮呈「✓ 已应用」禁用态)
        appliedSnapshots.value[0] = snapshotOf(profiles.value[0])
        appliedIndex.value = 0
      }
    }
    feedback.value = ''
    await nextTick()
    tabBtns.value?.[activeIndex.value]?.focus()
    window.addEventListener('keydown', handleKeydown)
  }
)

/** Esc 关闭 + Tab 焦点循环 (简单 focus trap) */
function handleKeydown(e) {
  if (e.key === 'Escape') {
    e.preventDefault()
    close()
    return
  }
  if (e.key === 'Tab') {
    const focusables = Array.from(
      document.querySelectorAll('.modal-panel button, .modal-panel input')
    ).filter((el) => !el.disabled && el.offsetParent !== null)
    if (focusables.length === 0) return
    const first = focusables[0]
    const last = focusables[focusables.length - 1]
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }
}

function close() {
  emit('close')
}

onBeforeUnmount(() => window.removeEventListener('keydown', handleKeydown))

/* ---------- 按钮行为 ---------- */

/** 应用: 以当前高亮 Tab 的数据提交后端 (POST /MiniCode/model), 并标记该 Tab 为已应用 */
async function applyProfile() {
  if (applying.value || isCurrentApplied.value) return
  const p = currentProfile.value
  applying.value = true
  try {
    await store.switchModel({
      model: p.model,
      base_url: p.base_url,
      api_key: p.api_key,
    })
    appliedSnapshots.value[activeIndex.value] = snapshotOf(p)
    appliedIndex.value = activeIndex.value
    showFeedback(`已应用「配置${activeIndex.value + 1}」的模型配置`, 'success')
  } catch (e) {
    console.error('应用模型配置失败', e)
    showFeedback(`应用失败: ${e.message}`, 'error')
  } finally {
    applying.value = false
  }
}

/** 恢复默认: 仅重置当前 Tab 的输入框, 不影响其他 4 组配置, 也不请求后端 */
function resetCurrentProfile() {
  Object.assign(currentProfile.value, emptyProfile())
  showFeedback(`已重置「配置${activeIndex.value + 1}」（其他配置组不受影响）`, 'success')
}

/** 设为默认: 将当前 Tab 标记为默认配置, 应用启动时自动应用到后端 (最终用户无需重选模型) */
function setAsDefault() {
  const p = currentProfile.value
  if (!p.model && !p.base_url && !p.api_key) {
    showFeedback(`「配置${activeIndex.value + 1}」为空，请先填写模型信息`, 'error')
    return
  }
  defaultIndex.value = activeIndex.value
  showFeedback(`已将「配置${activeIndex.value + 1}」设为默认，下次启动自动应用`, 'success')
}
</script>

<style scoped>
.settings-modal {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-mask {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  animation: maskIn 0.2s ease both;
}

@keyframes maskIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-panel {
  position: relative;
  width: 440px;
  max-width: calc(100vw - 48px);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  animation: popIn 0.24s var(--ease-out) both;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-color);
  flex: none;
}

.modal-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.close-btn {
  width: 26px;
  height: 26px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--text-secondary);
  border: none;
  border-radius: var(--radius-xs);
}

.close-btn:hover:not(:disabled) {
  color: var(--error);
  background: var(--error-light);
  box-shadow: none;
  transform: none;
}

.modal-body {
  padding: var(--space-4);
  overflow-y: auto;
}

.modal-section h4 {
  margin: 0 0 var(--space-3);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

/* ---------- 5 组配置选项卡 (分段式控件, 未选中柔灰底 / 选中白底+主色) ---------- */
.tab-bar {
  display: flex;
  gap: 2px;
  padding: 3px;
  margin-bottom: var(--space-4);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}

.tab-btn {
  position: relative;
  flex: 1;
  min-width: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 5px 4px;
  font-size: 12px;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  border-radius: var(--radius-xs);
  user-select: none;
}

.tab-btn:hover:not(:disabled) {
  color: var(--text-primary);
  background: var(--bg-hover);
  background-image: none;
  box-shadow: none;
  transform: none;
}

.tab-btn.active {
  color: var(--accent);
  background: var(--bg-primary);
  font-weight: 600;
  box-shadow: var(--shadow-xs);
}

.tab-btn:focus-visible {
  box-shadow: 0 0 0 3px var(--accent-ring);
}

/* Tab 内的模型名缩写 (帮助区分 5 个分组) */
.tab-model {
  max-width: 64px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 10.5px;
  font-weight: 400;
  color: var(--text-tertiary);
}

.tab-btn.active .tab-model {
  color: var(--accent);
  opacity: 0.75;
}

/* 已应用标记: 绿点 */
.tab-dot {
  flex: none;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--success);
}

/* 默认配置标记: 金色星标 */
.tab-star {
  font-size: 10px;
  line-height: 1;
  color: var(--warning);
}

/* ---------- 表单 ---------- */
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: var(--space-3);
}

.field label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.field input {
  width: 100%;
}

.btn-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.primary-btn {
  background: var(--accent);
  color: #fff;
  font-weight: 500;
  border-radius: var(--radius-xs);
}

.primary-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.primary-btn:active:not(:disabled) {
  background: var(--accent-active);
}

/* 禁用态: 提交中 / 当前 Tab 已是生效配置, 挡掉重复点击 */
.primary-btn:disabled {
  cursor: not-allowed;
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
}

/* 「已应用」禁用态: 成功色软底 + 对勾, 比纯灰更能传达「已生效, 无需再点」 */
.primary-btn.applied {
  cursor: default;
  background: var(--success-light);
  color: var(--success);
}

.ghost-btn {
  background: var(--bg-primary);
  color: var(--accent);
  border: 1px solid var(--accent-border);
  border-radius: var(--radius-xs);
}

.ghost-btn:hover:not(:disabled) {
  background: var(--accent-light);
}

/* 文字按钮: 低频操作 (后端默认) 降噪处理 */
.text-btn {
  padding: 7px 8px;
  font-size: 12.5px;
  color: var(--text-secondary);
  background: transparent;
  border: none;
}

.text-btn:hover:not(:disabled) {
  color: var(--accent);
  background: transparent;
  background-image: none;
  box-shadow: none;
  transform: none;
}

/* 操作反馈: 成功 / 错误 */
.feedback {
  margin: var(--space-3) 0 0;
  padding: 6px 10px;
  font-size: 12.5px;
  border-radius: var(--radius-xs);
  animation: fadeUp 0.2s var(--ease-out) both;
}

.feedback.success {
  color: var(--success);
  background: var(--success-light);
}

.feedback.error {
  color: var(--error);
  background: var(--error-light);
}

.modal-footer {
  padding: var(--space-2) var(--space-4);
  border-top: 1px solid var(--border-color);
  flex: none;
}

.footer-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  color: var(--text-tertiary);
}

.footer-hint kbd {
  font-size: 10px;
}
</style>
