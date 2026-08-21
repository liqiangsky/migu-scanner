<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="page-title">订阅</h1>
      <div class="header-actions">
        <button class="fetch-all-btn" @click="fetchAll" :disabled="fetchingAll" title="一键拉取所有订阅">
          <span class="material-symbols-outlined icon-g-btn">cloud_download</span>
        </button>
        <button class="action-btn primary-btn" @click="startAddSub" title="添加订阅">
          <span class="material-symbols-outlined icon-g-btn">add</span>
        </button>
      </div>
    </div>

    <div class="header-spacer"></div>

    <!-- 订阅列表 -->
    <div class="config-list">
      <div v-if="!loaded" class="skeleton-list">
        <div v-for="i in 3" :key="i" class="skeleton-card">
          <div class="skeleton-line skeleton-title"></div>
          <div class="skeleton-line skeleton-sub"></div>
          <div class="skeleton-line skeleton-sub narrow"></div>
        </div>
      </div>

      <TransitionGroup v-else name="list-fade">
        <div
          v-for="sub in subscriptions"
          :key="sub.id"
          class="config-card"
          :class="{ 'status-disabled': !sub.enabled }"
        >
          <div class="card-top">
            <div class="config-identity">
              <h3 class="config-name">{{ sub.name || '未命名' }}</h3>
            </div>
            <label class="toggle-switch" @click.stop>
              <input type="checkbox" :checked="sub.enabled" @change="handleToggleEnabled(sub)" />
              <span class="slider"></span>
            </label>
          </div>

          <div class="card-grid">
            <div class="grid-item">
              <span class="lbl">订阅 URL</span>
              <span class="txt mono truncate">{{ sub.url }}</span>
            </div>
            <div class="grid-item">
              <span class="lbl">定时拉取</span>
              <span class="txt">{{ sub.fetchCron || '未设置' }}</span>
            </div>
            <div class="grid-item">
              <span class="lbl">最后更新</span>
              <span class="txt">{{ formatTime(sub.updatedAt) || '未更新' }}</span>
            </div>
          </div>

          <div class="card-actions">
            <button
              class="text-btn fetch-btn"
              @click="handleFetchSub(sub)"
              :class="{ fetching: fetchingMap[sub.id] }"
            >
              <span class="material-symbols-outlined icon-g-btn">{{ fetchingMap[sub.id] ? 'hourglass_empty' : 'cloud_download' }}</span>
              {{ fetchingMap[sub.id] ? '拉取中' : '拉取' }}
            </button>
            <button class="text-btn edit" @click="startEditSub(sub)">
              <span class="material-symbols-outlined icon-g-btn">edit</span> 编辑
            </button>
            <button class="text-btn delete" @click="handleDeleteSub(sub)">
              <span class="material-symbols-outlined icon-g-btn">delete</span> 删除
            </button>
          </div>
        </div>
      </TransitionGroup>

      <div v-if="loaded && subscriptions.length === 0" class="empty-state">
        暂无订阅，点击右上角添加
      </div>
    </div>

    <!-- 添加/编辑 弹窗 -->
    <div class="form-overlay" v-if="formVisible" @click="cancelForm">
      <div class="form-drawer" @click.stop>
        <div class="drawer-header">
          <h2>{{ editingId ? '编辑订阅' : '添加订阅' }}</h2>
          <button class="close-x-btn" @click="cancelForm">×</button>
        </div>
        <div class="drawer-form">
          <div class="form-item">
            <label>订阅名称</label>
            <input v-model="formData.name" type="text" placeholder="例如：GitHub 源" />
          </div>
          <div class="form-item">
            <label>订阅 URL</label>
            <input v-model="formData.url" type="text" placeholder="https://example.com/source.txt" />
          </div>
          <div class="form-item">
            <label>定时拉取 (Cron)，留空不执行</label>
            <input v-model="formData.fetchCron" type="text" placeholder="留空不执行" />
          </div>
          <div class="drawer-actions">
            <button type="button" class="drawer-btn drawer-btn-primary" @click="handleSaveSub" :disabled="saving">
              {{ saving ? '保存中...' : (editingId ? '保存' : '添加') }}
            </button>
            <button type="button" class="drawer-btn drawer-btn-cancel" @click="cancelForm">
              取消
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/api'
import { toast } from '@/components/Toast'

const subscriptions = ref([])
const loaded = ref(false)
const fetchingMap = ref({})
const fetchingAll = ref(false)
const saving = ref(false)
const formVisible = ref(false)
const editingId = ref(null)
const formData = ref({ name: '', url: '', fetchCron: '' })

const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  const date = new Date(timestamp * 1000)
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

const loadSubscriptions = async () => {
  try {
    const data = await request.get('/api/subscriptions')
    subscriptions.value = data || []
  } catch (e) {
    toast.error('加载订阅失败')
  } finally {
    loaded.value = true
  }
}

const startAddSub = () => {
  editingId.value = null
  formData.value = { name: '', url: '', fetchCron: '' }
  formVisible.value = true
}

const startEditSub = (sub) => {
  editingId.value = sub.id
  formData.value = {
    name: sub.name || '',
    url: sub.url,
    fetchCron: sub.fetchCron || ''
  }
  formVisible.value = true
}

const cancelForm = () => {
  formVisible.value = false
  editingId.value = null
}

const handleSaveSub = async () => {
  if (!formData.value.url.trim()) {
    toast.warning('请输入 URL')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await request.put(`/api/subscriptions/${editingId.value}`, formData.value)
      toast.success('已更新')
    } else {
      await request.post('/api/subscriptions', formData.value)
      toast.success('已添加')
    }
    formVisible.value = false
    editingId.value = null
    await loadSubscriptions()
  } catch (e) {
    toast.error(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

const handleDeleteSub = async (sub) => {
  if (!confirm(`确定删除订阅「${sub.name || sub.url}」？`)) return
  try {
    await request.delete(`/api/subscriptions/${sub.id}`)
    toast.success('已删除')
    await loadSubscriptions()
  } catch (e) {
    toast.error('删除失败')
  }
}

const handleToggleEnabled = async (sub) => {
  const wasEnabled = sub.enabled
  try {
    await request.put(`/api/subscriptions/${sub.id}`, {
      ...sub,
      enabled: !wasEnabled
    })
    toast.success(wasEnabled ? '已停用' : '已启用')
    await loadSubscriptions()
  } catch (e) {
    toast.error('更新失败')
  }
}

const fetchAll = async () => {
  fetchingAll.value = true
  try {
    await request.post('/api/subscriptions/fetch-all')
    toast.success('批量拉取已启动')
    setTimeout(() => {
      loadSubscriptions()
    }, 3000)
  } catch (e) {
    toast.error('批量拉取失败')
  } finally {
    fetchingAll.value = false
  }
}

const handleFetchSub = async (sub) => {
  fetchingMap.value[sub.id] = true
  try {
    await request.post(`/api/subscriptions/${sub.id}/fetch`)
    toast.success('拉取已启动')
    setTimeout(() => {
      loadSubscriptions()
    }, 3000)
  } catch (e) {
    toast.error('拉取失败')
  } finally {
    fetchingMap.value[sub.id] = false
  }
}

onMounted(() => {
  loadSubscriptions()
})
</script>

<style scoped>
/* ===== 页头 ===== */
.page-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 20;
  background: rgba(245, 245, 247, 0.92);
  backdrop-filter: blur(20px);
  padding: 12px 16px;
  min-height: 56px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 100vw;
}
@media (min-width: 768px) {
  .page-header {
    max-width: 720px;
    left: 50%;
    transform: translateX(-50%);
  }
}
@media (min-width: 1024px) {
  .page-header {
    max-width: 1100px;
  }
}

.header-actions {
  display: flex;
  gap: 4px;
}

/* ===== 页头间距 ===== */
.header-spacer {
  height: 56px;
  flex-shrink: 0;
}

/* ===== 列表 Grid ===== */
.config-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  width: 100%;
  max-width: var(--max-content);
  padding-bottom: 70px;
}
@media (min-width: 768px) {
  .config-list {
    max-width: 720px;
  }
}
@media (min-width: 1024px) {
  .config-list {
    max-width: 1100px;
  }
}

/* ===== 卡片 ===== */
.config-card {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  padding: 20px;
  box-shadow: var(--shadow-md);
  border: 1px solid rgba(0, 0, 0, 0.01);
  display: flex;
  flex-direction: column;
  transition: all 0.3s var(--ease-spring);
}
.config-card.status-disabled {
  opacity: 0.5;
}

/* ===== 卡片顶部 ===== */
.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.config-identity {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.config-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

/* ===== 信息网格 ===== */
.card-grid {
  margin-top: 14px;
  border-top: 1px solid var(--bg-neutral);
  padding-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.grid-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.lbl {
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
  font-weight: 500;
}
.txt {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.txt.mono {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  letter-spacing: -0.2px;
}
.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== Toggle Switch ===== */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 42px;
  height: 24px;
  flex-shrink: 0;
}
.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #e8e8ed;
  transition: 0.3s;
  border-radius: 24px;
}
.slider:before {
  position: absolute;
  content: '';
  height: 20px;
  width: 20px;
  left: 2px;
  bottom: 2px;
  background: white;
  transition: 0.3s;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}
input:checked + .slider {
  background: #34c759;
}
input:checked + .slider:before {
  transform: translateX(18px);
}

/* ===== 操作按钮 ===== */
.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px dashed var(--bg-neutral);
}
.text-btn {
  background: none;
  border: none;
  outline: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  -webkit-tap-highlight-color: transparent;
  transition: all 0.2s ease;
}
.text-btn:active {
  transform: scale(0.94);
}
.text-btn.fetch-btn {
  color: var(--color-blue);
}
.text-btn.fetch-btn.fetching {
  opacity: 0.5;
  pointer-events: none;
}
.text-btn.edit {
  color: var(--color-blue);
}
.text-btn.delete {
  color: var(--color-red);
}

/* ===== 头部按钮 ===== */
.action-btn {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  -webkit-tap-highlight-color: transparent;
}
.primary-btn {
  background: var(--color-blue);
  color: #fff;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}
.icon-g-btn {
  font-size: 18px !important;
}
.primary-btn:active {
  transform: scale(0.9);
  background: #0066d6;
}

/* 一键拉取按钮 */
.fetch-all-btn {
  background: var(--color-green);
  color: #fff;
  border: none;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}
.fetch-all-btn:active {
  transform: scale(0.9);
}
.fetch-all-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ===== 空状态 ===== */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
  font-size: 14px;
  grid-column: 1 / -1;
}

/* ===== Drawer ===== */
.form-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(10px);
  z-index: 100;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}
.form-drawer {
  background: var(--bg-card);
  width: 100%;
  max-width: 420px;
  border-top-left-radius: var(--radius-card);
  border-top-right-radius: var(--radius-card);
  padding: 24px 24px calc(24px + env(safe-area-inset-bottom)) 24px;
  box-shadow: 0 -10px 40px rgba(0, 0, 0, 0.1);
  animation: slide-up 0.35s var(--ease-spring);
}
.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.drawer-header h2 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}
.close-x-btn {
  background: var(--bg-neutral);
  border: none;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 18px;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.drawer-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.drawer-form input {
  appearance: none;
  -webkit-appearance: none;
  background: var(--bg-neutral);
  border: none;
  outline: none;
  padding: 12px;
  border-radius: var(--radius-input);
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  width: 100%;
  box-sizing: border-box;
}
.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-item label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}
.drawer-actions {
  display: flex;
  gap: 10px;
  margin-top: 6px;
}
.drawer-btn {
  flex: 1;
  padding: 12px;
  border: none;
  border-radius: var(--radius-input);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}
.drawer-btn:active {
  transform: scale(0.97);
}
.drawer-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.drawer-btn-primary {
  background: var(--color-blue);
  color: #fff;
}
.drawer-btn-cancel {
  background: var(--bg-neutral);
  color: var(--text-secondary);
}

@keyframes slide-up {
  from {
    transform: translateY(100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

/* ===== Transition ===== */
.list-fade-enter-active,
.list-fade-leave-active {
  transition: all 0.3s ease;
}
.list-fade-enter-from,
.list-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}


.section-divider {
  height: 1px;
  background: var(--bg-neutral);
  margin: 24px 0;
}

/* ===== 空状态 ===== */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
  font-size: 14px;
  grid-column: 1 / -1;
}
</style>
