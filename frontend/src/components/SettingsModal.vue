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

          <!-- 已保存的模型: 数据来自后端数据库 (GET /MiniCode/get_model), 点击一行即切换生效模型 (POST /MiniCode/set_model) -->
          <div class="model-list" role="listbox" aria-label="已保存的模型">
            <p v-if="listLoading" class="list-hint">正在从后端加载模型列表…</p>
            <p v-else-if="!models.length" class="list-hint">后端暂无已保存的模型, 请在下方填写并添加</p>
            <button
              v-for="m in models"
              :key="m.id"
              class="model-row"
              role="option"
              :class="{ active: m.id === activeModelId }"
              :aria-selected="m.id === activeModelId"
              :disabled="selectingId !== null"
              :title="`${m.model_name} · ${m.base_url}`"
              @click="selectModel(m)"
            >
              <span class="model-main">
                <span class="model-name">{{ m.model_name }}</span>
                <span class="model-url">{{ m.base_url }}</span>
              </span>
              <span v-if="m.is_default" class="model-badge default" title="库中标记为默认模型">默认</span>
              <span v-if="m.id === activeModelId" class="model-badge in-use">
                {{ selectingId === m.id ? '切换中…' : '使用中' }}
              </span>
            </button>
          </div>

          <!-- 新增模型表单: 提交到 POST /MiniCode/add_model, 后端落库并立即生效 -->
          <div class="field">
            <label for="model-name">模型名</label>
            <input id="model-name" v-model="form.model" placeholder="模型名, 如 qwen3.6-plus" />
          </div>
          <div class="field">
            <label for="model-base-url">Base URL</label>
            <input id="model-base-url" v-model="form.base_url" placeholder="Base URL" />
          </div>
          <div class="field">
            <label for="model-api-key">API Key</label>
            <input
              id="model-api-key"
              v-model="form.api_key"
              type="password"
              placeholder="API Key"
              autocomplete="off"
            />
          </div>

          <div class="btn-row">
            <button
              class="primary-btn"
              :disabled="adding || listLoading"
              title="新增模型到后端数据库 (POST /MiniCode/add_model), 添加后立即生效"
              @click="addModelFromForm"
            >
              {{ adding ? '添加中…' : '添加模型' }}
            </button>
            <button
              class="ghost-btn"
              :disabled="listLoading"
              title="重新从后端拉取模型列表 (GET /MiniCode/get_model)"
              @click="reloadModels"
            >
              刷新列表
            </button>
          </div>
        </div>

        <!-- 生成参数: 对应后端 settingsRequest (temperature/theme/think_level), POST /MiniCode/settings 持久化 -->
        <div class="modal-section">
          <h4>生成参数</h4>

          <div class="field">
            <label for="setting-temperature">
              温度 ({{ appSettings.temperature.toFixed(1) }})
            </label>
            <input
              id="setting-temperature"
              v-model.number="appSettings.temperature"
              type="range"
              min="0"
              max="2"
              step="0.1"
              class="range-input"
              aria-label="模型温度, 范围 0~2, 越大越随机"
            />
            <p class="field-hint">范围 0~2: 越大越发散随机, 越小越稳定确定</p>
          </div>

          <div class="field">
            <label>思考等级</label>
            <div class="level-row" role="radiogroup" aria-label="思考等级">
              <button
                v-for="lv in [1, 2, 3]"
                :key="lv"
                class="level-btn"
                role="radio"
                :aria-checked="appSettings.think_level === lv"
                :class="{ active: appSettings.think_level === lv }"
                @click="appSettings.think_level = lv"
              >
                {{ levelLabels[lv] }}
              </button>
            </div>
            <p class="field-hint">1 快速响应 · 2 均衡 · 3 深度思考</p>
          </div>

          <div class="btn-row">
            <button
              class="primary-btn"
              :disabled="savingSettings"
              title="保存生成参数到后端 (POST /MiniCode/settings)"
              @click="saveAppSettings"
            >
              {{ savingSettings ? '保存中…' : '保存生成参数' }}
            </button>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <span class="footer-hint"><kbd>Esc</kbd> 关闭 · 点击列表行切换生效模型</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, watch, nextTick, onBeforeUnmount } from 'vue'
import { useChatStore } from '../stores/chat'
import { useToastStore } from '../stores/toast'

const props = defineProps({
  visible: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const store = useChatStore()
const toast = useToastStore()

/* ================= 生成参数 (后端 settingsRequest: temperature / theme / think_level) ================= */

const appSettings = computed(() => store.appSettings)
const levelLabels = { 1: '快速', 2: '均衡', 3: '深度' }
const savingSettings = ref(false)
/** 保存生成参数到后端 (POST /MiniCode/settings); 首次打开未加载时先拉一次 */
async function saveAppSettings() {
  if (savingSettings.value) return
  savingSettings.value = true
  try {
    await store.saveSettings({
      temperature: Number(appSettings.value.temperature),
      think_level: Number(appSettings.value.think_level),
      // 必须带上主题: 后端 settingsRequest.settings 是完整的 Settings(temperature/theme/think_level),
      // 缺字段时 pydantic 会用「当前全局默认主题」补上, 于是保存一次生成参数就把用户
      // 已持久化的主题偏好(以及后端的 DEFAULT_THEME)覆盖回默认值。
      theme: !!appSettings.value.theme,
    })
    toast.success('生成参数已保存')
  } catch (e) {
    console.error('保存生成参数失败', e)
    toast.error(`保存失败: ${e.message}`)
  } finally {
    savingSettings.value = false
  }
}

/* ================= 模型配置 (数据源: 后端数据库, GET /MiniCode/get_model) ================= */

/** 数据库返回的模型列表 (list[ModelGetRequest]: id/base_url/api_key/model_name/is_default) */
const models = computed(() => store.models)
const activeModelId = computed(() => store.activeModelId)
/** 新增模型表单 (POST /MiniCode/add_model 的 body) */
const form = reactive({ model: '', base_url: '', api_key: '' })
/** 正在切换生效模型的 id (防重复点击) */
const selectingId = ref(null)
/** 正在新增模型 */
const adding = ref(false)
/** 正在拉取模型列表 */
const listLoading = ref(false)

/* ---------- 列表 / 切换 / 新增 ---------- */

/** 打开或手动刷新时从后端拉取模型列表, 并用当前生效模型回填新增表单 (仅在表单为空时) */
async function reloadModels() {
  if (listLoading.value) return
  listLoading.value = true
  try {
    await store.refreshModels()
    seedForm()
  } catch (e) {
    console.error('加载模型列表失败', e)
    toast.error(`加载模型列表失败: ${e.message}`)
  } finally {
    listLoading.value = false
  }
}

function seedForm() {
  const filled = form.model || form.base_url || form.api_key
  if (filled) return
  const cur =
    models.value.find((m) => m.id === activeModelId.value) ||
    models.value.find((m) => m.is_default) ||
    models.value[0]
  if (cur) {
    Object.assign(form, { model: cur.model_name, base_url: cur.base_url, api_key: cur.api_key })
  }
}

/** 点击列表行: POST /MiniCode/set_model?id=xxx, 把该模型设为运行时生效模型 */
async function selectModel(m) {
  if (selectingId.value) return
  selectingId.value = m.id
  try {
    await store.activateModel(m.id)
    toast.success(`已切换至「${m.model_name}」`)
  } catch (e) {
    console.error('切换模型失败', e)
    toast.error(`切换失败: ${e.message}`)
  } finally {
    selectingId.value = null
  }
}

/** 新增模型: POST /MiniCode/add_model, 后端落库并立即生效 */
async function addModelFromForm() {
  if (adding.value) return
  if (!form.model || !form.base_url || !form.api_key) {
    toast.error('请完整填写模型名 / Base URL / API Key')
    return
  }
  adding.value = true
  try {
    const created = await store.addNewModel({ ...form })
    toast.success(
      created ? `已添加并启用「${created.model_name}」` : '该配置已存在于数据库, 已直接启用'
    )
  } catch (e) {
    console.error('添加模型失败', e)
    toast.error(`添加失败: ${e.message}`)
  } finally {
    adding.value = false
  }
}

/* ---------- 打开/关闭 ---------- */

watch(
  () => props.visible,
  async (v) => {
    if (!v) {
      window.removeEventListener('keydown', handleKeydown)
      return
    }
    // 立即注册快捷键监听: 打开瞬间(列表还在路上)Esc 也必须能关闭
    window.addEventListener('keydown', handleKeydown)
    // 每次打开都从后端拉最新模型列表 (界面数据以数据库为准), 拉取失败由 reloadModels 内部提示
    // 必须 await: 否则 nextTick 时列表还空着, 下面的 focus 永远找不到行, 弹窗打开后无初始焦点
    await reloadModels()
    await nextTick()
    document.querySelector('.model-row.active, .model-row')?.focus()
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
    return
  }
  // 模型列表上下键移动焦点 (role=listbox 的基本可访问性要求)
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    const active = document.activeElement
    if (!active || !active.classList?.contains('model-row')) return
    e.preventDefault()
    const rows = Array.from(document.querySelectorAll('.model-row')).filter(
      (el) => !el.disabled && el.offsetParent !== null
    )
    const idx = rows.indexOf(active)
    const next = rows[idx + (e.key === 'ArrowDown' ? 1 : -1)]
    if (next) next.focus()
  }
}

function close() {
  emit('close')
}

onBeforeUnmount(() => window.removeEventListener('keydown', handleKeydown))
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

/* ---------- 模型列表 (数据来自后端数据库, 点击切换) ---------- */
.model-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: var(--space-3);
  max-height: 190px;
  overflow-y: auto;
}

.list-hint {
  margin: 0;
  padding: 8px 10px;
  font-size: 12px;
  color: var(--text-tertiary);
  background: var(--bg-tertiary);
  border-radius: var(--radius-xs);
}

.model-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  text-align: left;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs);
}

.model-row:hover:not(:disabled) {
  color: inherit;
  background: var(--bg-hover);
  background-image: none;
  box-shadow: none;
  transform: none;
  border-color: var(--accent-border);
}

.model-row.active {
  background: var(--accent-light);
  border-color: var(--accent-border);
}

.model-row:focus-visible {
  box-shadow: 0 0 0 3px var(--accent-ring);
}

.model-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.model-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-url {
  font-size: 11px;
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-badge {
  flex: none;
  padding: 2px 6px;
  font-size: 10px;
  line-height: 1.4;
  border-radius: 999px;
}

/* 库中标记的默认模型 (is_default=1) */
.model-badge.default {
  color: var(--warning);
  background: var(--bg-tertiary);
}

/* 当前运行时生效模型 */
.model-badge.in-use {
  color: var(--success);
  background: var(--success-light);
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

/* 生成参数: 温度滑条与思考等级分段按钮 */
.range-input {
  padding: 0;
  accent-color: var(--accent);
}

.field-hint {
  margin: 2px 0 0;
  font-size: 11.5px;
  color: var(--text-tertiary);
}

.level-row {
  display: flex;
  gap: var(--space-2);
}

.level-btn {
  flex: 1;
  padding: 6px 8px;
  font-size: 12.5px;
  color: var(--text-secondary);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs);
}

.level-btn:hover:not(:disabled) {
  color: var(--accent);
  background: var(--bg-hover);
  background-image: none;
  box-shadow: none;
  transform: none;
}

.level-btn.active {
  color: var(--accent);
  background: var(--accent-light);
  border-color: var(--accent-border);
  font-weight: 600;
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

/* 禁用态: 提交中 / 正在拉取列表, 挡掉重复点击 */
.primary-btn:disabled {
  cursor: not-allowed;
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
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
