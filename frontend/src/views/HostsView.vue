<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="page-title">主机</h1>
      <div class="header-right">
        <div class="filter-counter-top">
          <span>{{ totalCount }}</span> 个
        </div>
        <div class="header-filters">
          <RegionFilter v-model="selectedProvince" @change="handleFilterChange" />
          <OperatorFilter v-model="selectedIsp" @change="handleFilterChange" />
        </div>
        <button class="action-btn primary-btn" :class="{ loading: retestingAll }" @click="handleRetestAll" title="复测所有主机">
          <span class="material-symbols-outlined icon-g-btn">{{ retestingAll ? 'sync' : 'refresh' }}</span>
        </button>
      </div>
    </div>

    <div class="header-spacer"></div>

    <!-- 主机列表 -->
    <div class="list-wrapper">
      <div v-if="loading" class="skeleton-list">
        <div v-for="i in 5" :key="i" class="skeleton-card">
          <div class="skeleton-line skeleton-title"></div>
          <div class="skeleton-line skeleton-sub"></div>
        </div>
      </div>
      <template v-else>
        <div
          v-for="host in hosts"
          :key="host.id"
          class="hosts-grid-card"
        >
          <div class="section-host">
            <div class="host-ip font-mono">{{ host.host }}</div>
            <div class="host-actions">
              <button class="action-btn copy-btn" @click.stop="handleCopy(host)" title="复制">
                <span class="material-symbols-outlined icon-g">content_copy</span>
              </button>
              <button class="action-btn delete-btn" @click.stop="handleDelete(host)" title="删除">
                <span class="material-symbols-outlined icon-g">delete</span>
              </button>
            </div>
          </div>

          <div class="section-metrics-grid">
            <div class="grid-item">
              <span class="badge-lbl">地区</span>
              <span class="badge-txt color-blue">{{ host.province || '未知' }}</span>
            </div>
            <div class="grid-item">
              <span class="badge-lbl">运营商</span>
              <span class="badge-txt color-blue">{{ host.isp || '未知' }}</span>
            </div>
            <div class="grid-item">
              <span class="badge-lbl">延迟</span>
              <div
                class="delay-interactive-badge"
                :class="{ 'state-error': host.latency < 0 }"
                @click.stop="handleTestDelay(host)"
              >
                <span class="material-symbols-outlined icon-g">bolt</span>
                <span class="badge-txt font-mono">{{ host.latency }} ms</span>
              </div>
            </div>
            <div class="grid-item time-column full-width">
              <span class="badge-lbl">发现</span>
              <div class="time-wrapper">
                <span class="material-symbols-outlined icon-g">history</span>
                <span class="badge-txt color-gray font-mono">{{ formatTime(host.createdAt) }}</span>
              </div>
            </div>
            <div class="grid-item time-column full-width">
              <span class="badge-lbl">验证</span>
              <div class="time-wrapper">
                <span class="material-symbols-outlined icon-g">update</span>
                <span class="badge-txt color-gray font-mono">{{ formatTime(host.updatedAt) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-show="hosts.length < totalCount" class="load-more-wrap">
          <button
            class="load-more-btn"
            :class="{ loading: loadingMore }"
            :disabled="loadingMore"
            @click="loadMore"
          >
            <span v-if="loadingMore" class="material-symbols-outlined spinner-icon spinning">sync</span>
            加载更多（剩余 {{ totalCount - hosts.length }} 条）
          </button>
        </div>

        <div v-if="hosts.length >= totalCount" class="all-loaded-hint">
          已加载全部 {{ totalCount }} 条
        </div>
      </template>

      <div v-if="!loading && hosts.length === 0" class="empty-state">
        暂无主机数据
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/api'
import { toast } from '@/components/Toast'
import RegionFilter from '@/components/RegionFilter.vue'
import OperatorFilter from '@/components/OperatorFilter.vue'
import { copyText } from '@/utils/copy'
import { useNotificationListener } from '@/composables/useNotifications'

const hosts = ref([])
const selectedProvince = ref('')
const selectedIsp = ref('')
const totalCount = ref(0)
const currentPage = ref(1)
const pageSize = 20
const totalPages = ref(1)
const loading = ref(false)
const loadingMore = ref(false)
const retestingAll = ref(false)

const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  const date = new Date(timestamp * 1000)
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

const loadHosts = async (reset = false) => {
  if (reset) {
    currentPage.value = 1
    hosts.value = []
  }
  loading.value = reset

  try {
    const params = { page: currentPage.value, page_size: pageSize }
    if (selectedProvince.value) params.province = selectedProvince.value
    if (selectedIsp.value) params.isp = selectedIsp.value

    const data = await request.get('/hosts', { params })
    if (reset) {
      hosts.value = data.items || []
    } else {
      hosts.value.push(...(data.items || []))
    }
    totalCount.value = data.total || 0
    totalPages.value = data.totalPages || 1
  } catch (e) {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

const loadMore = async () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    await loadHosts()
  }
}

const handleFilterChange = () => {
  loadHosts(true)
}

const handleCopy = async (host) => {
  const url = host.full_path || `http://${host.host}/`
  await copyText(url, toast)
}

const handleDelete = async (host) => {
  if (!confirm(`确定删除主机 ${host.host}？`)) return
  try {
    await request.delete(`/hosts/${host.id}`)
    toast.success('已删除')
    await loadHosts(true)
  } catch (e) {
    // 错误已由拦截器处理
  }
}

const handleTestDelay = async (host) => {
  try {
    const res = await request.post(`/hosts/${host.id}/test-delay`)
    if (res) {
      host.latency = res.delay
      host.updatedAt = res.updatedAt
      if (host.latency >= 0) {
        toast.success(`延迟: ${host.latency}ms`)
      } else {
        toast.warning('超时或不可达')
      }
    }
  } catch {
    host.latency = -1
  }
}

const handleRetestAll = async () => {
  if (retestingAll.value) return
  retestingAll.value = true
  try {
    await request.post('/hosts/retest-all')
    toast.success('复测任务已启动')
  } catch {
    toast.error('复测启动失败')
    retestingAll.value = false
  }
}

// 监听复测完成通知，自动刷新列表
const handleNotification = () => {
  loadHosts(true)
  retestingAll.value = false
}

onMounted(() => {
  loadHosts(true)
})

useNotificationListener('HOST_RETEST', handleNotification)
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
  min-height: 58px;
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
  .header-right {
    max-width: 720px;
  }
}

@media (min-width: 1024px) {
  .page-header {
    max-width: 1100px;
  }
  .header-right {
    max-width: 1100px;
  }
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  white-space: nowrap;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  justify-content: flex-end;
}

.filter-counter-top {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.filter-counter-top span {
  color: var(--color-green);
  font-weight: 700;
}

.header-filters {
  display: flex;
  gap: 8px;
}

.apple-select-sm {
  appearance: none;
  -webkit-appearance: none;
  background-color: var(--bg-neutral);
  color: var(--text-primary);
  border: none;
  padding: 6px 28px 6px 10px;
  border-radius: var(--radius-input);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  outline: none;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path fill='%238E8E93' d='M0 0h10L5 6z'/></svg>");
  background-repeat: no-repeat;
  background-position: right 10px center;
}

.apple-select-sm:active,
.apple-select-sm:hover {
  background-color: #e8e8ed;
}

/* ===== 页头间距 ===== */
.header-spacer {
  height: 58px;
  flex-shrink: 0;
}

/* ===== 列表 ===== */
.list-wrapper {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
  width: 100%;
  max-width: var(--max-content);
  padding-bottom: 40px;
}

@media (min-width: 768px) {
  .list-wrapper {
    max-width: 720px;
  }
}

@media (min-width: 1024px) {
  .list-wrapper {
    max-width: 1100px;
  }
}

/* ===== 卡片样式 ===== */
.hosts-grid-card {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  padding: 18px;
  box-shadow: var(--shadow-md);
  border: 1px solid rgba(0, 0, 0, 0.01);
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: border-color 0.2s ease;
}

.section-host {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
}

.host-ip {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.font-mono {
  font-family: var(--font-mono);
  letter-spacing: -0.3px;
}

.host-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.action-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  border: none;
  cursor: pointer;
}

/* 页头主要按钮 */
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
  border: none;
}
.primary-btn:active {
  transform: scale(0.9);
  background: #0066d6;
}

.delete-btn {
  background: #fdecea;
  color: #e5484d;
}

.delete-btn:active {
  transform: scale(0.9);
  background: #f5d6d3;
}

.delete-btn .icon-g {
  color: #e5484d;
}

.copy-btn {
  background: #e3f2fd;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  border: none;
  cursor: pointer;
  flex-shrink: 0;
}

.copy-btn:active {
  transform: scale(0.9);
  background: #bbdefb;
}

.section-metrics-grid {
  border-top: 1px solid #f1f5f9;
  padding-top: 10px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
}

.grid-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.grid-item.full-width {
  grid-column: span 2;
}

.badge-lbl {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  width: 38px;
  flex-shrink: 0;
}

.badge-txt {
  font-size: 12px;
  font-weight: 600;
}

.color-blue {
  color: var(--color-blue);
}

.color-gray {
  color: var(--text-secondary);
}

.time-wrapper {
  display: flex;
  align-items: center;
  gap: 4px;
}

.icon-g {
  font-size: 16px;
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
  display: inline-block;
  vertical-align: middle;
}

.icon-g-btn {
  font-size: 18px;
}

.copy-btn .icon-g {
  color: var(--color-blue);
}

.time-wrapper .icon-g {
  color: var(--text-muted);
}

/* ===== 延迟徽章 ===== */
.delay-interactive-badge {
  background: var(--bg-status-good);
  color: var(--color-green);
  padding: 3px 8px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 12px;
}
.delay-interactive-badge:active {
  transform: scale(0.95);
}
.delay-interactive-badge.state-error {
  background: #fdecea;
  color: #e5484d;
}
.delay-interactive-badge.state-error .icon-g {
  color: #e5484d;
}
.delay-interactive-badge .icon-g {
  color: var(--color-green);
}

/* ===== 空状态 ===== */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
  font-size: 14px;
  grid-column: 1 / -1;
}

/* ===== 加载更多 ===== */
.load-more-wrap {
  grid-column: 1 / -1;
  text-align: center;
  padding: 16px 0;
}
.load-more-btn {
  background: var(--bg-neutral);
  color: var(--color-blue);
  border: none;
  padding: 10px 24px;
  border-radius: var(--radius-input);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}
.load-more-btn:active {
  transform: scale(0.96);
  background: #e8e8ed;
}
.load-more-btn:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}
.spinner-icon {
  font-size: 16px;
  vertical-align: middle;
  margin-right: 4px;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.spinning {
  animation: spin 1s linear infinite;
}
.all-loaded-hint {
  grid-column: 1 / -1;
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  padding: 8px 0;
}

/* ===== Transition ===== */
.list-fade-enter-active,
.list-fade-leave-active {
  transition: all 0.3s ease;
}

.list-fade-enter-from,
.list-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
