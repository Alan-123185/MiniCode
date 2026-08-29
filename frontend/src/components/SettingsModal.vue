<template>
  <div class="settings-modal" v-if="visible">
    <div class="modal-mask" @click="close"></div>
    <div class="modal-panel">
      <div class="modal-header">
        <h3>设置</h3>
        <button class="close-btn" @click="close">×</button>
      </div>
      <div class="modal-body">
        <div class="modal-section">
          <h4>模型配置</h4>
          <label>模型名</label>
          <input v-model="model" placeholder="模型名" />
          <label>Base URL</label>
          <input v-model="baseUrl" placeholder="Base URL" />
          <label>API Key</label>
          <input v-model="apiKey" type="password" placeholder="API Key" />
          <div class="btn-row">
            <button class="primary-btn" @click="saveModel">切换模型</button>
            <button class="ghost-btn" @click="restoreModel">恢复默认</button>
          </div>
        </div>
        <div class="modal-section">
          <h4>工作目录</h4>
          <label>目录路径</label>
          <input v-model="path" placeholder="例如: D:/workspace" />
          <div class="btn-row">
            <button class="primary-btn" @click="saveWorkplace">设置工作目录</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useChatStore } from '../stores/chat'

const props = defineProps({
  visible: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const store = useChatStore()
const model = ref('')
const baseUrl = ref('')
const apiKey = ref('')
const path = ref('')

watch(
  () => props.visible,
  (v) => {
    if (v) {
      model.value = store.modelConfig.model
      baseUrl.value = store.modelConfig.base_url
      apiKey.value = store.modelConfig.api_key
      path.value = store.workplace
    }
  }
)

function close() {
  emit('close')
}

async function saveModel() {
  try {
    await store.switchModel({
      model: model.value,
      base_url: baseUrl.value,
      api_key: apiKey.value,
    })
  } catch (e) {
    console.error('切换模型失败', e)
  }
}

async function restoreModel() {
  try {
    await store.restoreModel()
  } catch (e) {
    console.error('恢复默认模型失败', e)
  }
}

async function saveWorkplace() {
  try {
    await store.setWorkplace(path.value)
  } catch (e) {
    console.error('设置工作目录失败', e)
  }
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
  background: rgba(0, 0, 0, 0.3);
  animation: maskIn 0.2s ease both;
}

@keyframes maskIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-panel {
  position: relative;
  width: 400px;
  max-height: 80vh;
  overflow-y: auto;
  background: var(--bg-primary);
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
  padding: 20px;
  animation: popIn 0.28s var(--ease-out) both;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.close-btn {
  padding: 4px 12px;
  font-size: 16px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.close-btn:hover {
  background: var(--bg-tertiary);
}

.modal-section {
  margin-bottom: 16px;
}

.modal-section h4 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--accent);
}

.modal-section label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin: 8px 0 4px;
}

.modal-section input {
  width: 100%;
}

.btn-row {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.primary-btn {
  background: var(--accent);
}

.primary-btn:hover {
  background: var(--accent-hover);
}

.ghost-btn {
  background: var(--bg-primary);
  color: var(--accent);
  border: 1px solid var(--accent);
}

.ghost-btn:hover {
  background: var(--accent-light);
}
</style>