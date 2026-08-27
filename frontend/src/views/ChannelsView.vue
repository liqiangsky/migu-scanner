<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="page-title">频道</h1>
      <div class="header-actions">
        <button class="action-btn primary-btn" @click="openAddModal" title="添加频道">
          <span class="material-symbols-outlined icon-g-btn">add</span>
        </button>
        <button class="fetch-all-btn" @click="openImportModal" title="批量导入">
          <span class="material-symbols-outlined icon-g-btn">upload_file</span>
        </button>
        <button class="action-btn primary-btn" @click="openGroupModal" title="管理分组">
          <span class="material-symbols-outlined icon-g-btn">folder_managed</span>
        </button>
        <button class="action-btn primary-btn" @click="openBatchGroupModal" title="批量分组">
          <span class="material-symbols-outlined icon-g-btn">batch_prediction</span>
        </button>
        <button class="action-btn primary-btn" @click="openBatchDeleteModal" title="批量删除" style="background: var(--color-red);">
          <span class="material-symbols-outlined icon-g-btn">delete</span>
        </button>
        <button class="action-btn primary-btn" @click="openUrlModal" title="订阅地址">
          <span class="material-symbols-outlined icon-g-btn">link</span>
        </button>
      </div>
    </div>

    <div class="header-spacer"></div>

    <!-- 频道列表 -->
    <div class="channel-list">
      <div v-if="!loaded" class="skeleton-list">
        <div v-for="i in 4" :key="i" class="skeleton-card">
          <div class="skeleton-line skeleton-icon"></div>
          <div class="skeleton-line skeleton-title"></div>
          <div class="skeleton-line skeleton-sub"></div>
        </div>
      </div>

      <template v-else-if="channels.length > 0">
        <!-- 按分组展示 -->
        <div v-for="group in channels" :key="group.id" class="group-section">
          <div class="group-header">
            <span class="group-name">{{ group.name || '未分组' }}</span>
            <span class="group-count">{{ group.channels?.length || 0 }} 个频道</span>
          </div>
          <div class="channel-grid">
            <div
              v-for="ch in group.channels"
              :key="ch.id"
              class="channel-card"
              @click="openEditModal(group, ch)"
            >
              <div class="channel-icon">
                <img
                  v-if="ch.logoUrl && ch.logoLoaded"
                  :src="ch.logoUrl"
                  :alt="ch.name"
                  class="channel-logo"
                  @error="ch.logoLoaded = false"
                />
                <span v-else class="material-symbols-outlined">live_tv</span>
              </div>
              <div class="channel-info">
                <div class="channel-name">{{ ch.name }}</div>
                <div class="channel-meta">
                  <span class="channel-code mono">{{ ch.code }}</span>
                  <span
                    v-if="playbackCacheMap[ch.code]"
                    class="cache-status"
                    :class="playbackCacheMap[ch.code].expired ? 'expired' : 'can-play'"
                    :title="playbackCacheMap[ch.code].expireTime"
                  >
                    {{ playbackCacheMap[ch.code].expired ? '已过期' : '有效' }}
                  </span>
                  <span v-else class="cache-status no-cache">无缓存</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div v-if="loaded && channels.length === 0" class="empty-state">
        <span class="material-symbols-outlined empty-icon">live_tv</span>
        <p>暂无频道数据</p>
        <p class="empty-hint">点击右上角「批量导入」添加频道</p>
      </div>
    </div>

    <!-- 批量导入弹窗 -->
    <div class="modal-overlay" v-if="showImportModal" @click="closeImportModal">
      <div class="import-modal" @click.stop>
        <div class="modal-handle"></div>
        <div class="modal-header">
          <h2 class="modal-title">批量导入频道</h2>
          <button class="modal-close-btn" @click="closeImportModal">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <!-- 步骤1：上传文件或输入URL -->
          <div v-if="importStep === 1" class="step-content">
            <!-- 模式切换 -->
            <div class="import-mode-tabs">
              <button
                class="mode-tab"
                :class="{ active: importMode === 'file' }"
                @click="importMode = 'file'"
              >
                <span class="material-symbols-outlined icon-sm">cloud_upload</span>
                上传文件
              </button>
              <button
                class="mode-tab"
                :class="{ active: importMode === 'url' }"
                @click="importMode = 'url'"
              >
                <span class="material-symbols-outlined icon-sm">link</span>
                远程URL
              </button>
            </div>

            <!-- 文件上传区域 -->
            <template v-if="importMode === 'file'">
              <div
                class="upload-area"
                :class="{ 'is-dragging': isDragging }"
                @dragover.prevent="isDragging = true"
                @dragleave="isDragging = false"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input
                  ref="fileInputRef"
                  type="file"
                  accept=".txt,.m3u,.m3u8"
                  class="file-input-hidden"
                  @change="handleFileSelect"
                />
                <span class="material-symbols-outlined upload-icon">cloud_upload</span>
                <p class="upload-title">点击或拖拽上传文件</p>
                <p class="upload-hint">支持 .txt 和 .m3u/.m3u8 格式</p>
              </div>

              <!-- 已选文件信息 -->
              <div v-if="selectedFile" class="selected-file">
                <span class="material-symbols-outlined file-icon">insert_drive_file</span>
                <div class="file-info">
                  <span class="file-name">{{ selectedFile.name }}</span>
                  <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
                </div>
                <button class="remove-file-btn" @click="removeFile">
                  <span class="material-symbols-outlined">close</span>
                </button>
              </div>
            </template>

            <!-- URL输入区域 -->
            <template v-else>
              <div class="url-input-area">
                <span class="material-symbols-outlined url-icon">public</span>
                <input
                  v-model="urlInput"
                  type="url"
                  class="url-input"
                  placeholder="请输入频道列表的远程URL地址…"
                />
                <button
                  class="fetch-url-btn"
                  :disabled="!urlInput.trim() || fetchingUrl"
                  @click="handleFetchUrl"
                >
                  <span v-if="fetchingUrl" class="material-symbols-outlined icon-sm">progress_activity</span>
                  <span v-else class="material-symbols-outlined icon-sm">cloud_download</span>
                  {{ fetchingUrl ? '获取中…' : '获取' }}
                </button>
              </div>
              <p class="url-hint">支持 .txt、.m3u、.m3u8 等格式的频道列表文件</p>
            </template>

            <button
              class="next-step-btn"
              :disabled="!canParse"
              @click="parseAndPreview"
            >
              下一步：预览数据
            </button>
          </div>

          <!-- 步骤2：预览数据 -->
          <div v-if="importStep === 2" class="step-content">
            <div class="preview-header">
              <div class="preview-stats">
                <span class="stat-item total">{{ dedupChannels.length }} 个频道</span>
                <span class="stat-item duplicate" v-if="dedupDuplicateCount > 0">
                  过滤 {{ dedupDuplicateCount }} 个重复
                </span>
              </div>
            </div>

            <div class="preview-list">
              <div
                v-for="(group, gIdx) in dedupGroupedChannels"
                :key="gIdx"
                class="preview-group"
              >
                <div class="preview-group-header" @click="togglePreviewGroup(group.name)">
                  <span class="preview-group-name">{{ group.name || '未分组' }}</span>
                  <span class="preview-group-count">{{ group.channels.length }} 个</span>
                  <span class="material-symbols-outlined preview-group-expand-icon">{{ previewExpandedGroups.has(group.name) ? 'expand_less' : 'expand_more' }}</span>
                </div>
                <div v-show="previewExpandedGroups.has(group.name)" class="preview-channels">
                  <div
                    v-for="(ch, cIdx) in group.channels"
                    :key="cIdx"
                    class="preview-channel-item"
                  >
                    <span class="preview-ch-name">{{ ch.name }}</span>
                    <span class="preview-ch-code mono">{{ extractCode(ch.url) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="step-actions">
              <button class="back-btn" @click="importStep = 1">
                <span class="material-symbols-outlined icon-sm">arrow_back</span>
                返回
              </button>
              <button
                class="confirm-import-btn"
                :disabled="importing || dedupChannels.length === 0"
                @click="confirmImport"
              >
                {{ importing ? '导入中...' : `确认导入 (${dedupChannels.length})` }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 管理分组弹窗 -->
    <div class="modal-overlay" v-if="showGroupModal" @click="closeGroupModal">
      <div class="import-modal channel-modal" @click.stop>
        <div class="modal-handle"></div>
        <div class="modal-header">
          <h2 class="modal-title">管理分组</h2>
          <button class="modal-close-btn" @click="closeGroupModal">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <!-- 添加分组表单 -->
          <div class="add-group-form">
            <input v-model="newGroupName" type="text" placeholder="输入分组名称…" maxlength="10" @keyup.enter="createGroup" />
            <button class="confirm-import-btn" :disabled="!newGroupName.trim() || creatingGroup" @click="createGroup">
              {{ creatingGroup ? '添加中…' : '添加' }}
            </button>
          </div>
          <!-- 分组列表 -->
          <div class="group-list">
            <div v-if="channelGroups.length === 0" class="empty-groups">暂无分组，请在上方添加</div>
            <div v-for="(g, idx) in channelGroups" :key="g.id" class="group-item">
              <template v-if="editingGroupId !== g.id">
                <span class="group-item-name">{{ g.name }}</span>
                <div class="group-item-actions">
                  <button class="group-action-btn move" :disabled="idx === 0" @click="moveGroupUp(g)" title="上移">
                    <span class="material-symbols-outlined icon-sm">arrow_upward</span>
                  </button>
                  <button class="group-action-btn move" :disabled="idx === channelGroups.length - 1" @click="moveGroupDown(g)" title="下移">
                    <span class="material-symbols-outlined icon-sm">arrow_downward</span>
                  </button>
                  <button class="group-action-btn" :class="{ 'eye-visible': g.visible, 'eye-hidden': !g.visible }" @click="toggleGroupVisible(g)" :title="g.visible ? '隐藏分组' : '显示分组'">
                    <span class="material-symbols-outlined icon-sm">{{ g.visible ? 'visibility' : 'visibility_off' }}</span>
                  </button>
                  <button class="group-action-btn edit" @click="startEditGroup(g)" title="重命名">
                    <span class="material-symbols-outlined icon-sm">edit</span>
                  </button>
                  <button class="group-action-btn delete" @click="deleteGroup(g)" title="删除">
                    <span class="material-symbols-outlined icon-sm">delete</span>
                  </button>
                </div>
              </template>
              <template v-else>
                <input v-model="editGroupName" type="text" maxlength="10" @keyup.enter="saveGroupName(g)" @keyup.escape="cancelEditGroup" />
                <div class="group-item-actions">
                  <button class="group-action-btn save" @click="saveGroupName(g)" title="保存">
                    <span class="material-symbols-outlined icon-sm">check</span>
                  </button>
                  <button class="group-action-btn cancel" @click="cancelEditGroup" title="取消">
                    <span class="material-symbols-outlined icon-sm">close</span>
                  </button>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 批量分组弹窗 -->
    <div class="modal-overlay" v-if="showBatchGroupModal" @click="closeBatchGroupModal">
      <div class="import-modal channel-modal" @click.stop>
        <div class="modal-handle"></div>
        <div class="modal-header">
          <h2 class="modal-title">批量分组</h2>
          <button class="modal-close-btn" @click="closeBatchGroupModal">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <!-- 选择分组 -->
          <div class="form-item">
            <label>目标分组</label>
            <select v-model="batchGroupTarget">
              <option :value="0">未分组</option>
              <option v-for="g in channelGroups" :key="g.id" :value="g.id">{{ g.name }}</option>
            </select>
          </div>
          <!-- 频道列表（分组展示） -->
          <div class="batch-group-list">
            <div v-if="groupedChannelsForBatch.length === 0" class="empty-batch">暂无频道</div>
            <template v-for="group in groupedChannelsForBatch" :key="group.name">
              <!-- 分组头部 -->
              <div
                class="batch-group-header"
                :class="{ 'is-selected': isBatchGroupAllSelected(group) }"
                @click="toggleGroupExpand(group.name)"
              >
                <BatchCheckbox
                  :checked="isBatchGroupAllSelected(group)"
                  :indeterminate="isBatchGroupPartiallySelected(group)"
                  @change="toggleBatchGroupAll(group)"
                />
                <span class="batch-group-header-name">{{ group.name }}</span>
                <span class="batch-group-header-count">{{ group.channels.length }} 个</span>
                <span class="material-symbols-outlined batch-group-expand-icon">{{ expandedGroups.has(group.name) ? 'expand_less' : 'expand_more' }}</span>
              </div>
              <!-- 频道列表 -->
              <div v-show="expandedGroups.has(group.name)">
                <div
                  v-for="ch in group.channels"
                  :key="ch.id"
                  class="batch-channel-item"
                  :class="{ selected: selectedChannelIds.includes(ch.id) }"
                  @click="toggleChannel(ch.id)"
                >
                  <BatchCheckbox
                    :checked="selectedChannelIds.includes(ch.id)"
                    @change="toggleChannel(ch.id)"
                  />
                  <span class="batch-ch-name">{{ ch.name }}</span>
                  <span class="batch-ch-code mono">{{ ch.code }}</span>
                </div>
              </div>
            </template>
          </div>
          <!-- 全选/反选 -->
          <div class="batch-select-actions">
            <button class="select-all-btn" @click="selectAll">全选</button>
            <button class="select-none-btn" @click="selectNone">全不选</button>
            <button class="select-invert-btn" @click="invertSelection">反选</button>
          </div>
        </div>
        <div class="modal-footer">
          <button class="back-btn" @click="closeBatchGroupModal">取消</button>
          <button
            class="confirm-import-btn"
            :disabled="selectedChannelIds.length === 0 || batchGrouping"
            @click="applyBatchGroup"
          >
            {{ batchGrouping ? '处理中...' : `应用到 ${selectedChannelIds.length} 个频道` }}
          </button>
        </div>
      </div>
    </div>

    <!-- 批量删除弹窗 -->
    <div class="modal-overlay" v-if="showBatchDeleteModal" @click="closeBatchDeleteModal">
      <div class="import-modal channel-modal" @click.stop>
        <div class="modal-handle"></div>
        <div class="modal-header">
          <h2 class="modal-title">批量删除</h2>
          <button class="modal-close-btn" @click="closeBatchDeleteModal">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <!-- 警告提示 -->
          <div class="batch-delete-warning">
            <span class="material-symbols-outlined warning-icon">warning</span>
            <span>删除后不可恢复，请谨慎操作</span>
          </div>
          <!-- 频道列表（分组展示） -->
          <div class="batch-group-list">
            <div v-if="groupedChannelsForBatch.length === 0" class="empty-batch">暂无频道</div>
            <template v-for="group in groupedChannelsForBatch" :key="group.name">
              <!-- 分组头部 -->
              <div
                class="batch-group-header"
                :class="{ 'is-selected': isBatchGroupAllSelected(group) }"
                @click="toggleGroupExpand(group.name)"
              >
                <BatchCheckbox
                  :checked="isBatchGroupAllSelected(group)"
                  :indeterminate="isBatchGroupPartiallySelected(group)"
                  @change="toggleBatchGroupAll(group)"
                />
                <span class="batch-group-header-name">{{ group.name }}</span>
                <span class="batch-group-header-count">{{ group.channels.length }} 个</span>
                <span class="material-symbols-outlined batch-group-expand-icon">{{ expandedGroups.has(group.name) ? 'expand_less' : 'expand_more' }}</span>
              </div>
              <!-- 频道列表 -->
              <div v-show="expandedGroups.has(group.name)">
                <div
                  v-for="ch in group.channels"
                  :key="ch.id"
                  class="batch-channel-item"
                  :class="{ selected: selectedChannelIds.includes(ch.id) }"
                  @click="toggleChannel(ch.id)"
                >
                  <BatchCheckbox
                    :checked="selectedChannelIds.includes(ch.id)"
                    @change="toggleChannel(ch.id)"
                  />
                  <span class="batch-ch-name">{{ ch.name }}</span>
                  <span class="batch-ch-code mono">{{ ch.code }}</span>
                </div>
              </div>
            </template>
          </div>
          <!-- 全选/反选 -->
          <div class="batch-select-actions">
            <button class="select-all-btn" @click="selectAll">全选</button>
            <button class="select-none-btn" @click="selectNone">全不选</button>
            <button class="select-invert-btn" @click="invertSelection">反选</button>
          </div>
        </div>
        <div class="modal-footer">
          <button class="back-btn" @click="closeBatchDeleteModal">取消</button>
          <button
            class="confirm-delete-btn"
            :disabled="selectedChannelIds.length === 0 || batchDeleting"
            @click="applyBatchDelete"
          >
            {{ batchDeleting ? '删除中...' : `删除 ${selectedChannelIds.length} 个频道` }}
          </button>
        </div>
      </div>
    </div>

    <!-- 添加/编辑 频道弹窗 -->
    <div class="modal-overlay" v-if="showChannelModal" @click="closeChannelModal">
      <div class="import-modal channel-modal" @click.stop>
        <div class="modal-handle"></div>
        <div class="modal-header">
          <h2 class="modal-title">{{ editingChannelId ? '编辑频道' : '添加频道' }}</h2>
          <button class="modal-close-btn" @click="closeChannelModal">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <div class="form-item">
            <label>频道名称</label>
            <input v-model="channelForm.name" type="text" placeholder="例如：CCTV1" />
          </div>
          <div class="form-item">
            <label>CODE（9位数字）</label>
            <input v-model="channelForm.code" type="text" placeholder="例如：608807420" maxlength="9" />
          </div>
          <div class="form-item">
            <label>台标</label>
            <input v-model="channelForm.logo" type="text" placeholder="粘贴图片地址 或 输入名称自动匹配" />
          </div>
          <div class="form-item">
            <label>分组</label>
            <select v-model="channelForm.groupId">
              <option :value="0">未分组</option>
              <option v-for="g in channelGroups" :key="g.id" :value="g.id">{{ g.name }}</option>
            </select>
          </div>

          <!-- 播放缓存信息（仅编辑时显示） -->
          <div v-if="editingChannelId && playbackCacheMap[channelForm.code]" class="cache-info-box">
            <div class="cache-info-header">
              <span class="cache-status" :class="playbackCacheMap[channelForm.code].expired ? 'expired' : 'can-play'">
                {{ playbackCacheMap[channelForm.code].expired ? '已过期' : '有效' }}
              </span>
              <span class="cache-expire-text" :title="playbackCacheMap[channelForm.code].expireTime">
                过期时间：{{ playbackCacheMap[channelForm.code].expireTime }}
              </span>
            </div>
            <div v-if="playbackCacheMap[channelForm.code].expired" class="cache-expired-hint">
              <span class="material-symbols-outlined icon-sm">warning</span>
              缓存已过期，下次播放将重新获取
            </div>
          </div>
          <div v-else-if="editingChannelId" class="cache-info-box no-cache">
            <span class="cache-status no-cache">无缓存</span>
          </div>
        </div>

        <div class="modal-footer">
          <button v-if="editingChannelId" class="delete-btn-modal" @click="handleDeleteChannelFromModal">删除</button>
          <button class="back-btn" @click="closeChannelModal">取消</button>
          <button
            class="confirm-import-btn"
            :disabled="savingChannel"
            @click="saveChannel"
          >
            {{ savingChannel ? '保存中...' : (editingChannelId ? '保存' : '添加') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 订阅地址弹窗 -->
    <div class="modal-overlay" v-if="showUrlModal" @click="closeUrlModal">
      <div class="import-modal" @click.stop>
        <div class="modal-handle"></div>
        <div class="modal-header">
          <h2 class="modal-title">订阅地址</h2>
          <button class="modal-close-btn" @click="closeUrlModal">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <div class="url-item" v-for="item in urlItems" :key="item.type" @click="copyUrl(item.url)" title="点击复制">
            <div class="url-item-header">
              <span class="url-type-badge" :class="item.type.toLowerCase()">{{ item.type }}</span>
              <span class="url-type-desc">{{ item.desc }}</span>
            </div>
            <div class="url-item-content">
              <span class="url-text mono">{{ item.url }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { toast } from '@/components/Toast'
import BatchCheckbox from '@/components/BatchCheckbox.vue'
import request from '@/api'
import { baseURL } from '../constant'
import { copyText } from '@/utils/copy'

// 状态
const loaded = ref(false)
const channels = ref([])
const playbackCacheMap = ref({})  // channelCode -> {playUrl, ttl, expired, expireTime}
const showImportModal = ref(false)
const importStep = ref(1)
const importing = ref(false)

// 订阅地址弹窗
const showUrlModal = ref(false)
const urlItems = ref([])

// 分组管理
const showGroupModal = ref(false)
const channelGroups = ref([])
const newGroupName = ref('')
const creatingGroup = ref(false)
const editingGroupId = ref(null)
const editGroupName = ref('')

// 频道添加/编辑
const showChannelModal = ref(false)
const editingChannelId = ref(null)
const savingChannel = ref(false)
const channelForm = ref({ name: '', code: '', logo: '', groupId: 0 })

// 文件上传
const fileInputRef = ref(null)
const selectedFile = ref(null)
const isDragging = ref(false)
const importMode = ref('file') // 'file' or 'url'
const urlInput = ref('')
const fetchingUrl = ref(false)
const urlFetched = ref(false)
const canParse = computed(() => {
  if (importMode.value === 'url') return urlFetched.value
  return selectedFile.value !== null
})

// 解析结果
const parsedChannels = ref([])
const parsedGroups = ref([])
const parsedGroupedChannels = ref([])

// 去重结果
const dedupChannels = ref([])
const duplicateGroups = ref([])

// 预览分组展开状态
const previewExpandedGroups = ref(new Set())
const togglePreviewGroup = (groupName) => {
  const set = previewExpandedGroups.value
  if (set.has(groupName)) {
    set.delete(groupName)
  } else {
    set.add(groupName)
  }
  previewExpandedGroups.value = new Set(set)
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// 解析 m3u 格式 (#EXTINF 行 + URL)
const parseM3U = (content) => {
  const lines = content.split('\n')
  const result = []
  let currentChannel = null

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue

    // EXTINF 行: #EXTINF:-1 group-title="分组",频道名称
    if (trimmed.startsWith('#EXTINF')) {
      const groupMatch = trimmed.match(/group-title="([^"]*)"/)
      // 匹配最后一个逗号后面的名称
      const lastCommaIdx = trimmed.lastIndexOf(',')
      const name = lastCommaIdx > 0 ? trimmed.substring(lastCommaIdx + 1).trim() : `频道${result.length + 1}`

      currentChannel = {
        name: name || `频道${result.length + 1}`,
        group: groupMatch ? groupMatch[1].trim() : '',
        url: ''
      }
      continue
    }

    // 注释行跳过
    if (trimmed.startsWith('#')) continue

    // URL 行（非注释，且有上一个 EXTINF）
    if (currentChannel) {
      // 跳过空 URL 或明显不是 URL 的行
      if (!trimmed || trimmed.length < 5) {
        currentChannel = null
        continue
      }
      // 去除 URL 末尾的 $备注
      let url = trimmed
      const dollarIdx = url.indexOf('$')
      if (dollarIdx > 0) {
        url = url.substring(0, dollarIdx).trim()
      }
      currentChannel.url = url
      result.push(currentChannel)
      currentChannel = null
    }
  }
  return result
}

// 解析 txt/genre 格式 (名称,#genre# 分组 + 频道名,url 条目)
const parseTXT = (content) => {
  const lines = content.split('\n')
  const result = []
  let currentGroup = '未分组'

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue

    // 分组行：名称,#genre#
    if (trimmed.toLowerCase().endsWith(',#genre#')) {
      const groupName = trimmed.replace(/,#genre#/i, '').trim()
      if (groupName) currentGroup = groupName
      continue
    }

    // 频道行：必须包含英文逗号，且逗号后是有效的 URL
    const commaIdx = trimmed.indexOf(',')
    if (commaIdx <= 0) continue

    const name = trimmed.substring(0, commaIdx).trim()
    let url = trimmed.substring(commaIdx + 1).trim()

    // 跳过不符合格式的行：名称为空或 URL 不包含协议
    if (!name || !url) continue
    if (!url.match(/^https?:\/\//i) && !url.match(/^\//) && !url.match(/^[a-zA-Z][a-zA-Z0-9+.-]*:/)) continue

    // 去除 URL 末尾的 $备注 部分
    const dollarIdx = url.indexOf('$')
    if (dollarIdx > 0) {
      url = url.substring(0, dollarIdx).trim()
    }

    result.push({ name, group: currentGroup, url })
  }
  return result
}

// 自动检测文件格式并解析
const detectAndParse = (content, filename) => {
  const lowerContent = content.toLowerCase()
  const lowerName = filename.toLowerCase()

  // 根据文件扩展名或内容特征判断格式
  if (lowerName.endsWith('.m3u') || lowerName.endsWith('.m3u8') || lowerContent.includes('#extinf')) {
    return parseM3U(content)
  }
  return parseTXT(content)
}

// Migu 频道 URL 特征：以 /9位数字 结尾
const MIGU_URL_PATTERN = /\/\d{9}$/

// 过滤只保留 Migu 格式的频道
const filterMiguChannels = (channels) => {
  return channels.filter(ch => MIGU_URL_PATTERN.test(ch.url))
}
const triggerFileInput = () => {
  fileInputRef.value?.click()
}

// 处理文件选择
const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file) {
    selectedFile.value = file
    importStep.value = 1
  }
}

// 处理拖拽上传
const handleDrop = (e) => {
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) {
    selectedFile.value = file
  }
}

// 移除文件
const removeFile = () => {
  selectedFile.value = null
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

// 解析并预览
const parseAndPreview = async () => {
  if (importMode.value === 'url') {
    // 如果还没获取过数据，先获取
    if (!urlFetched.value) {
      await fetchUrlPreview()
      if (!urlFetched.value) return // 获取失败，不跳转
    }
    // 跳转到预览步骤
    importStep.value = 2
  } else {
    await parseFilePreview()
  }
}

// 从文件预览
const parseFilePreview = async () => {
  if (!selectedFile.value) return
  try {
    const text = await selectedFile.value.text()
    const rawChannels = detectAndParse(text, selectedFile.value.name)
    const channels = filterMiguChannels(rawChannels)
    processChannels(channels)
  } catch (e) {
    toast.error('文件读取失败')
  }
}

// 从URL预览（仅获取数据，不跳转步骤）
const fetchUrlPreview = async () => {
  if (!urlInput.value.trim()) return
  fetchingUrl.value = true
  try {
    const result = await request.post('/channels/batch-import-preview', { url: urlInput.value.trim() })
    if (result && result.channels && result.channels.length > 0) {
      parsedChannels.value = result.channels
      parsedGroups.value = [...new Set(result.channels.map(ch => ch.group).filter(Boolean))]
      parsedGroupedChannels.value = buildGroupedChannels(result.channels)
      calculateDuplicates()
      urlFetched.value = true
      // 默认展开所有分组
      previewExpandedGroups.value = new Set(parsedGroupedChannels.value.map(g => g.name))
      toast.success(`成功获取 ${result.channels.length} 个频道`)
    }
  } catch {
    urlFetched.value = false
  } finally {
    fetchingUrl.value = false
  }
}

// 点击获取按钮
const handleFetchUrl = async () => {
  if (!urlInput.value.trim() || fetchingUrl.value) return
  // 验证URL格式
  const url = urlInput.value.trim()
  if (!/^https?:\/\/.+/.test(url)) {
    toast.warning('请输入合法的URL地址（以 http:// 或 https:// 开头）')
    return
  }
  urlFetched.value = false
  await fetchUrlPreview()
}

// 处理频道数据（通用逻辑）
const processChannels = (channels) => {
  if (channels.length === 0) {
    toast.warning('未找到符合条件的 Migu 频道（需以 /9位数字 结尾）')
    return
  }
  parsedChannels.value = channels
  parsedGroups.value = [...new Set(channels.map(ch => ch.group).filter(Boolean))]
  parsedGroupedChannels.value = buildGroupedChannels(channels)
  calculateDuplicates()
  importStep.value = 2
  toast.success(`成功解析 ${channels.length} 个频道`)
}

// 构建分组后的频道列表
const buildGroupedChannels = (channels) => {
  const groups = {}
  for (const ch of channels) {
    const groupName = ch.group || '未分组'
    if (!groups[groupName]) {
      groups[groupName] = { name: groupName, channels: [] }
    }
    groups[groupName].channels.push(ch)
  }
  return Object.values(groups)
}

// 打开导入弹窗
const openImportModal = () => {
  showImportModal.value = true
  resetImportState()
}

// 关闭导入弹窗
const closeImportModal = () => {
  showImportModal.value = false
  resetImportState()
}

// 重置导入状态
const resetImportState = () => {
  importStep.value = 1
  importMode.value = 'file'
  selectedFile.value = null
  urlInput.value = ''
  urlFetched.value = false
  parsedChannels.value = []
  parsedGroups.value = []
  parsedGroupedChannels.value = []
  previewExpandedGroups.value = new Set()
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

// 确认导入
const confirmImport = async () => {
  if (importing.value) return
  importing.value = true

  try {
    // 准备导入数据
    const importData = dedupChannels.value.map(ch => ({
      name: ch.name,
      code: extractCode(ch.url),
      group: ch.group || '未分组'
    }))

    console.log('导入数据:', importData)

    const result = await request.post('/channels/batch-import', { channels: importData })

    console.log('导入结果:', result)

    // 刷新列表
    await loadChannels()

    // result 是 res.data，所以直接访问 result.added
    const added = result?.added ?? dedupChannels.value.length
    const newGroups = result?.newGroups ?? 0
    if (newGroups > 0) {
      await loadChannelGroups()
    }
    toast.success(`已导入 ${added} 个频道`)
    closeImportModal()
  } catch (e) {
    // 错误已由拦截器处理
  } finally {
    importing.value = false
  }
}

// 提取频道 CODE（URL 末尾的 9 位数字）
const extractCode = (url) => {
  const match = url.match(/\/(\d{9})$/)
  return match ? match[1] : null
}

// 计算重复项
const calculateDuplicates = () => {
  const codeMap = {}
  const duplicates = []

  parsedChannels.value.forEach((ch, idx) => {
    const code = extractCode(ch.url)
    if (!code) return

    if (!codeMap[code]) {
      codeMap[code] = { code, channels: [] }
    }
    codeMap[code].channels.push({ ...ch, originalIdx: idx })
  })

  // 只保留有重复的
  Object.values(codeMap).forEach(group => {
    if (group.channels.length > 1) {
      duplicates.push(group)
    }
  })

  duplicateGroups.value = duplicates

  // 去重：每个 CODE 只保留第一个
  const seenCodes = new Set()
  dedupChannels.value = parsedChannels.value.filter(ch => {
    const code = extractCode(ch.url)
    if (!code) return true
    if (seenCodes.has(code)) return false
    seenCodes.add(code)
    return true
  })
}

// 去重统计
const dedupDuplicateCount = computed(() => parsedChannels.value.length - dedupChannels.value.length)

// 去重后的分组列表
const dedupGroupedChannels = computed(() => buildGroupedChannels(dedupChannels.value))

// 复制到剪贴板（已移除，不再需要）

// 是否可以确认导入
const canConfirmImport = computed(() => parsedChannels.value.length > 0 && importMode.value !== '')

// 加载播放缓存
const loadPlaybackCaches = async () => {
  try {
    const data = await request.get('/playback-caches')
    const now = Math.floor(Date.now() / 1000)
    const map = {}
    for (const item of data) {
      const expired = item.ttl <= now
      const expireDate = new Date(item.ttl * 1000)
      const pad = (n) => String(n).padStart(2, '0')
      const expireTime = `${expireDate.getFullYear()}-${pad(expireDate.getMonth() + 1)}-${pad(expireDate.getDate())} ${pad(expireDate.getHours())}:${pad(expireDate.getMinutes())}`
      map[item.channelCode] = {
        playUrl: item.playUrl,
        ttl: item.ttl,
        expired,
        expireTime
      }
    }
    playbackCacheMap.value = map
  } catch (e) {
    console.error('加载播放缓存失败', e)
  }
}

// 加载频道列表
const loadChannels = async () => {
  try {
    const data = await request.get('/channels')
    if (Array.isArray(data)) {
      // 直接使用分组结构，每个频道加上 logoUrl
      channels.value = data.map(group => ({
        ...group,
        channels: (group.channels || []).map(ch => ({
          ...ch,
          logoUrl: ch.logo && (ch.logo.startsWith('http://') || ch.logo.startsWith('https://')) ? ch.logo : `https://v4.gh-proxy.org/https://raw.githubusercontent.com/fanmingming/live/refs/heads/main/tv/${encodeURIComponent(ch.logo)}.png`,
          logoLoaded: true
        }))
      }))
    }
  } catch (e) {
    console.error('加载频道失败', e)
  } finally {
    loaded.value = true
  }
}

// 加载分组列表（供弹窗下拉使用）
const loadChannelGroups = async () => {
  try {
    const res = await request.get('/channel-groups')
    channelGroups.value = res ?? []
  } catch (e) {
    console.error('加载分组失败', e)
  }
}

// ===== 分组管理 =====
const openGroupModal = async () => {
  await loadChannelGroups()
  newGroupName.value = ''
  editingGroupId.value = null
  editGroupName.value = ''
  showGroupModal.value = true
}

const closeGroupModal = () => {
  showGroupModal.value = false
  editingGroupId.value = null
  editGroupName.value = ''
}

const createGroup = async () => {
  const name = newGroupName.value.trim()
  if (!name) return
  creatingGroup.value = true
  try {
    await request.post('/channel-groups', { name })
    toast.success('分组已添加')
    newGroupName.value = ''
    await loadChannelGroups()
    await loadChannels()
  } catch (e) {
    // 错误已由拦截器处理
  } finally {
    creatingGroup.value = false
  }
}

const startEditGroup = (g) => {
  editingGroupId.value = g.id
  editGroupName.value = g.name
}

const saveGroupName = async (g) => {
  const name = editGroupName.value.trim()
  if (!name) return
  try {
    await request.put(`/channel-groups/${g.id}`, { name })
    toast.success('已更新')
    editingGroupId.value = null
    editGroupName.value = ''
    await loadChannelGroups()
    await loadChannels()
  } catch (e) {
    // 错误已由拦截器处理
  }
}

const cancelEditGroup = () => {
  editingGroupId.value = null
  editGroupName.value = ''
}

const deleteGroup = async (g) => {
  if (!confirm(`确定删除分组「${g.name}」？该分组下的频道将移入「未分组」。`)) return
  try {
    await request.delete(`/channel-groups/${g.id}`)
    toast.success('已删除')
    await loadChannelGroups()
    await loadChannels()
  } catch (e) {
    // 错误已由拦截器处理
  }
}

const moveGroupUp = async (g) => {
  try {
    await request.post(`/channel-groups/${g.id}/move-up`)
    toast.success('已上移')
    await loadChannelGroups()
    await loadChannels()
  } catch (e) {
    // 错误已由拦截器处理
  }
}

const moveGroupDown = async (g) => {
  try {
    await request.post(`/channel-groups/${g.id}/move-down`)
    toast.success('已下移')
    await loadChannelGroups()
    await loadChannels()
  } catch (e) {
    // 错误已由拦截器处理
  }
}

const toggleGroupVisible = async (g) => {
  try {
    const res = await request.post(`/channel-groups/${g.id}/toggle-visible`)
    g.visible = res?.visible
    toast.success(g.visible ? '分组已显示' : '分组已隐藏')
    await loadChannels()
  } catch (e) {
    // 错误已由拦截器处理
  }
}

// ===== 批量分组 =====
const showBatchGroupModal = ref(false)
const batchGroupTarget = ref(0)
const selectedChannelIds = ref([])
const batchGrouping = ref(false)
const expandedGroups = ref(new Set())

// 按分组组织的频道列表（用于批量弹窗）
const groupedChannelsForBatch = computed(() => {
  const groups = {}
  for (const ch of allChannels.value) {
    const name = ch.groupName || '未分组'
    if (!groups[name]) {
      groups[name] = { name, channels: [] }
    }
    groups[name].channels.push(ch)
  }
  return Object.values(groups)
})

// 切换分组展开/收起
const toggleGroupExpand = (groupName) => {
  const set = expandedGroups.value
  if (set.has(groupName)) {
    set.delete(groupName)
  } else {
    set.add(groupName)
  }
  expandedGroups.value = new Set(set) // trigger reactivity
}

// 展开所有分组
const expandAllGroups = () => {
  expandedGroups.value = new Set(groupedChannelsForBatch.value.map(g => g.name))
}

// 收起所有分组
const collapseAllGroups = () => {
  expandedGroups.value = new Set()
}

// 扁平化的所有频道列表
const allChannels = computed(() => {
  const result = []
  for (const group of channels.value) {
    for (const ch of group.channels || []) {
      result.push({
        id: ch.id,
        name: ch.name,
        code: ch.code,
        groupId: ch.groupId,
        groupName: group.name || '未分组'
      })
    }
  }
  return result
})

const openBatchGroupModal = () => {
  batchGroupTarget.value = 0
  selectedChannelIds.value = []
  expandedGroups.value = new Set(groupedChannelsForBatch.value.map(g => g.name))
  showBatchGroupModal.value = true
}

// ===== 分组勾选功能（主列表用） =====
// 检查分组是否全选
const isGroupAllSelected = (group) => {
  if (!group?.channels?.length) return false
  return group.channels.every(ch => selectedChannelIds.value.includes(ch.id))
}

// 检查分组是否部分选中
const isGroupPartiallySelected = (group) => {
  if (!group?.channels?.length) return false
  const selectedCount = group.channels.filter(ch => selectedChannelIds.value.includes(ch.id)).length
  return selectedCount > 0 && selectedCount < group.channels.length
}

// 切换分组全选/取消全选
const toggleGroupAll = (group) => {
  const groupChannels = group.channels || []
  const allSelected = isGroupAllSelected(group)

  if (allSelected) {
    // 取消全选：移除该分组下所有频道
    groupChannels.forEach(ch => {
      const idx = selectedChannelIds.value.indexOf(ch.id)
      if (idx >= 0) selectedChannelIds.value.splice(idx, 1)
    })
  } else {
    // 全选：添加该分组下所有频道
    groupChannels.forEach(ch => {
      if (!selectedChannelIds.value.includes(ch.id)) {
        selectedChannelIds.value.push(ch.id)
      }
    })
  }
}

// ===== 批量弹窗分组勾选功能 =====
// 检查批量弹窗分组是否全选
const isBatchGroupAllSelected = (group) => {
  if (!group?.channels?.length) return false
  return group.channels.every(ch => selectedChannelIds.value.includes(ch.id))
}

// 检查批量弹窗分组是否部分选中
const isBatchGroupPartiallySelected = (group) => {
  if (!group?.channels?.length) return false
  const selectedCount = group.channels.filter(ch => selectedChannelIds.value.includes(ch.id)).length
  return selectedCount > 0 && selectedCount < group.channels.length
}

// 切换批量弹窗分组全选/取消全选
const toggleBatchGroupAll = (group) => {
  const groupChannels = group.channels || []
  const allSelected = isBatchGroupAllSelected(group)

  if (allSelected) {
    groupChannels.forEach(ch => {
      const idx = selectedChannelIds.value.indexOf(ch.id)
      if (idx >= 0) selectedChannelIds.value.splice(idx, 1)
    })
  } else {
    groupChannels.forEach(ch => {
      if (!selectedChannelIds.value.includes(ch.id)) {
        selectedChannelIds.value.push(ch.id)
      }
    })
  }
}

const closeBatchGroupModal = () => {
  showBatchGroupModal.value = false
  selectedChannelIds.value = []
  expandedGroups.value = new Set()
}

const selectAll = () => {
  selectedChannelIds.value = allChannels.value.map(ch => ch.id)
}

const selectNone = () => {
  selectedChannelIds.value = []
}

const invertSelection = () => {
  const allIds = allChannels.value.map(ch => ch.id)
  selectedChannelIds.value = allIds.filter(id => !selectedChannelIds.value.includes(id))
}

const toggleChannel = (id) => {
  const idx = selectedChannelIds.value.indexOf(id)
  if (idx >= 0) {
    selectedChannelIds.value.splice(idx, 1)
  } else {
    selectedChannelIds.value.push(id)
  }
}

const applyBatchGroup = async () => {
  if (selectedChannelIds.value.length === 0) return
  batchGrouping.value = true
  try {
    await request.post('/channels/batch-update-group', {
      channel_ids: selectedChannelIds.value,
      group_id: batchGroupTarget.value
    })
    toast.success(`已将 ${selectedChannelIds.value.length} 个频道移动到「${batchGroupTarget.value === 0 ? '未分组' : channelGroups.value.find(g => g.id === batchGroupTarget.value)?.name || '未知'}」`)
    closeBatchGroupModal()
    await loadChannels()
  } catch (e) {
    // 错误已由拦截器处理
  } finally {
    batchGrouping.value = false
  }
}

// ===== 批量删除 =====
const showBatchDeleteModal = ref(false)
const batchDeleting = ref(false)

const openBatchDeleteModal = () => {
  selectedChannelIds.value = []
  showBatchDeleteModal.value = true
}

const closeBatchDeleteModal = () => {
  showBatchDeleteModal.value = false
  selectedChannelIds.value = []
}

const applyBatchDelete = async () => {
  if (selectedChannelIds.value.length === 0) return
  if (!confirm(`确定删除选中的 ${selectedChannelIds.value.length} 个频道？此操作不可恢复。`)) return
  batchDeleting.value = true
  try {
    await request.post('/channels/batch-delete', {
      channel_ids: selectedChannelIds.value
    })
    toast.success(`已删除 ${selectedChannelIds.value.length} 个频道`)
    closeBatchDeleteModal()
    await loadChannels()
  } catch (e) {
    // 错误已由拦截器处理
  } finally {
    batchDeleting.value = false
  }
}

// 打开添加频道弹窗
const openAddModal = () => {
  editingChannelId.value = null
  channelForm.value = { name: '', code: '', logo: '', groupId: 0 }
  showChannelModal.value = true
}

// 打开订阅地址弹窗
const openUrlModal = () => {
  urlItems.value = [
    { type: 'TXT', desc: '文本订阅', url: window.location.origin + baseURL + '/sub/txt', copied: false },
    { type: 'M3U', desc: '播放列表', url: window.location.origin + baseURL + '/sub/m3u', copied: false }
  ]
  showUrlModal.value = true
}

const closeUrlModal = () => {
  showUrlModal.value = false
}

const copyUrl = (url) => copyText(url, toast)

// 打开编辑频道弹窗
const openEditModal = (group, ch) => {
  editingChannelId.value = ch.id
  channelForm.value = {
    name: ch.name,
    code: ch.code,
    logo: ch.logo || ch.name,
    groupId: ch.groupId
  }
  showChannelModal.value = true
}

// 关闭弹窗
const closeChannelModal = () => {
  showChannelModal.value = false
  editingChannelId.value = null
}

// 保存频道（新增或更新）
const saveChannel = async () => {
  const { name, code, logo, groupId } = channelForm.value
  if (!name.trim() || !code.trim()) {
    toast.warning('名称和 CODE 不能为空')
    return
  }
  if (!/^\d{9}$/.test(code.trim())) {
    toast.warning('CODE 必须是 9 位数字')
    return
  }
  savingChannel.value = true
  try {
    const payload = {
      name: name.trim(),
      code: code.trim(),
      logo: logo.trim() || name.trim(),
      group_id: groupId != null ? Number(groupId) : 0
    }
    let result
    if (editingChannelId.value) {
      result = await request.put(`/channels/${editingChannelId.value}`, payload)
      toast.success('已更新')
    } else {
      result = await request.post('/channels', payload)
      toast.success('已添加')
    }
    closeChannelModal()
    await loadChannels()
  } catch (e) {
    // 错误已由拦截器处理
  } finally {
    savingChannel.value = false
  }
}

// 从弹窗删除频道
const handleDeleteChannelFromModal = async () => {
  if (!confirm(`确定删除频道「${channelForm.value.name}」？`)) return
  try {
    await request.delete(`/channels/${editingChannelId.value}`)
    toast.success('已删除')
    closeChannelModal()
    await loadChannels()
  } catch (e) {
    // 错误已由拦截器处理
  }
}

onMounted(() => {
  loadChannels()
  loadChannelGroups()
  loadPlaybackCaches()
})

onUnmounted(() => {
  // 清理
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
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
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

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
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
.primary-btn:active {
  transform: scale(0.9);
  background: #0066d6;
}
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
.icon-g-btn {
  font-size: 18px;
}

.header-spacer {
  height: 56px;
  flex-shrink: 0;
}

/* ===== 频道列表 ===== */
.channel-list {
  width: 100%;
  max-width: var(--max-content);
  padding-bottom: 40px;
}
@media (min-width: 768px) {
  .channel-list {
    max-width: 720px;
  }
}
@media (min-width: 1024px) {
  .channel-list {
    max-width: 1100px;
  }
}

/* 分组 */
.group-section {
  margin-bottom: 24px;
}
.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  margin-bottom: 12px;
  position: sticky;
  top: 56px;
  background: rgba(245, 245, 247, 0.95);
  backdrop-filter: blur(10px);
  z-index: 10;
  border-bottom: 1px solid var(--bg-neutral);
}
.group-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.group-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--color-blue);
  flex-shrink: 0;
  appearance: auto;
  -webkit-appearance: auto;
}
.group-name {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.2px;
}
.group-count {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-card);
  padding: 3px 10px;
  border-radius: 10px;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

/* 频道网格 */
.channel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
@media (min-width: 768px) {
  .channel-grid {
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 14px;
  }
}

.channel-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fc 100%);
  border-radius: var(--radius-card);
  padding: 14px 16px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
  cursor: pointer;
  border: 1px solid rgba(0, 122, 255, 0.08);
}
.channel-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
  border-color: rgba(0, 122, 255, 0.2);
  background: linear-gradient(135deg, #ffffff 0%, #f5f7ff 100%);
}
.channel-icon {
  width: 80px;
  height: 46px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
  background: #3a3a4a;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.2);
}
.channel-logo {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 10px;
}
.channel-icon .material-symbols-outlined {
  font-size: 22px;
  color: #aaa;
}
.channel-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.channel-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
}
.channel-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.channel-code {
  font-size: 11px;
  color: var(--color-blue);
  font-family: var(--font-mono);
  background: rgba(0, 122, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}
.cache-status {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  cursor: default;
  flex-shrink: 0;
}
.cache-status.can-play {
  background: rgba(52, 199, 89, 0.12);
  color: var(--color-green);
}
.cache-status.expired {
  background: rgba(255, 199, 0, 0.15);
  color: #ffc107;
}
.cache-status.no-cache {
  background: var(--bg-neutral);
  color: var(--text-muted);
}
.cache-info-box {
  margin-top: 12px;
  padding: 12px;
  background: var(--bg-neutral);
  border-radius: var(--radius-input);
}
.cache-info-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.cache-expire-text {
  font-size: 12px;
  color: var(--text-secondary);
}
.cache-expired-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #ff9500;
  display: flex;
  align-items: center;
  gap: 4px;
}
.cache-info-box.no-cache {
  text-align: center;
  padding: 16px;
}
.icon-sm {
  font-size: 16px;
}

/* ===== 空状态 ===== */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
}
.empty-icon {
  font-size: 48px;
  color: var(--text-disabled);
  margin-bottom: 16px;
}
.empty-state p {
  font-size: 15px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.empty-hint {
  font-size: 13px;
  color: var(--text-muted);
}

/* ===== 弹窗样式 ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(10px);
  z-index: 100;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}
@media (min-width: 768px) {
  .modal-overlay {
    align-items: center;
  }
}

.import-modal {
  background: var(--bg-card);
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  border-top-left-radius: var(--radius-card);
  border-top-right-radius: var(--radius-card);
  display: flex;
  flex-direction: column;
  animation: slideUp 0.35s var(--ease-spring);
}
@media (min-width: 768px) {
  .import-modal {
    border-radius: var(--radius-card);
    max-height: 85vh;
  }
}

.modal-handle {
  width: 36px;
  height: 4px;
  background: var(--text-disabled);
  border-radius: 2px;
  margin: 12px auto 0;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--bg-neutral);
}
.modal-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}
.modal-close-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--bg-neutral);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.modal-close-btn:hover {
  background: #e8e8ed;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ===== 步骤内容 ===== */
.step-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== 上传区域 ===== */
.upload-area {
  border: 2px dashed var(--bg-neutral);
  border-radius: var(--radius-card);
  padding: 32px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}
.upload-area:hover,
.upload-area.is-dragging {
  border-color: var(--color-blue);
  background: rgba(0, 122, 255, 0.04);
}
.upload-icon {
  font-size: 48px;
  color: var(--text-muted);
  margin-bottom: 12px;
}
.upload-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}
.upload-hint {
  font-size: 12px;
  color: var(--text-muted);
}
.file-input-hidden {
  display: none;
}

/* ===== 导入模式切换 ===== */
.import-mode-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
}
.mode-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 16px;
  border: 2px solid var(--bg-neutral);
  border-radius: var(--radius-input);
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.mode-tab:hover {
  border-color: var(--color-blue);
  color: var(--text-primary);
}
.mode-tab.active {
  border-color: var(--color-blue);
  background: rgba(0, 122, 255, 0.08);
  color: var(--color-blue);
}
.mode-tab .icon-sm {
  font-size: 18px;
}

/* ===== URL 输入区域 ===== */
.url-input-area {
  display: flex;
  gap: 10px;
  align-items: center;
}
.url-icon {
  font-size: 22px;
  color: var(--text-muted);
  flex-shrink: 0;
}
.url-input {
  flex: 1;
  padding: 10px 14px;
  border: 2px solid var(--bg-neutral);
  border-radius: var(--radius-input);
  background: var(--bg-elevated);
  color: var(--text-primary);
  font-size: 14px;
  font-family: monospace;
  outline: none;
  transition: border-color 0.2s;
}
.url-input:focus {
  border-color: var(--color-blue);
}
.url-input::placeholder {
  color: var(--text-muted);
  font-family: inherit;
}
.url-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: -4px;
}

/* 获取URL按钮 */
.fetch-url-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 14px;
  border: none;
  border-radius: var(--radius-input);
  background: var(--color-blue);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s ease;
  white-space: nowrap;
}
.fetch-url-btn:hover:not(:disabled) {
  background: #0066d6;
}
.fetch-url-btn:active:not(:disabled) {
  transform: scale(0.96);
}
.fetch-url-btn:disabled {
  background: var(--bg-neutral);
  color: var(--text-muted);
  cursor: not-allowed;
}

/* 已选文件 */
.selected-file {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-neutral);
  border-radius: var(--radius-input);
}
.file-icon {
  font-size: 28px;
  color: var(--color-blue);
}
.file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.file-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-size {
  font-size: 11px;
  color: var(--text-muted);
}
.remove-file-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--bg-card);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.remove-file-btn:hover {
  background: #ffebeb;
}

/* ===== 预览区域 ===== */
.preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.preview-counts {
  display: flex;
  align-items: center;
  gap: 8px;
}
.preview-count {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-blue);
}
.preview-actions {
  display: flex;
  gap: 6px;
}
.select-all-btn,
.select-none-btn {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}
.select-all-btn {
  background: rgba(0, 122, 255, 0.1);
  color: var(--color-blue);
}
.select-all-btn:hover {
  background: rgba(0, 122, 255, 0.18);
}
.select-none-btn {
  background: var(--bg-neutral);
  color: var(--text-secondary);
}
.select-none-btn:hover {
  background: #e8e8ed;
}
.preview-groups {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-neutral);
  padding: 2px 10px;
  border-radius: 10px;
}
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: var(--bg-neutral);
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
  margin-left: auto;
}
.back-btn:hover {
  background: #e8e8ed;
}

.preview-list {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--bg-neutral);
  border-radius: var(--radius-input);
  padding-right: 4px;
}
.preview-group {
  margin-bottom: 4px;
}
.preview-group:last-child {
  margin-bottom: 0;
}
.preview-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 0.2s;
  background: var(--bg-neutral);
  position: sticky;
  top: 0;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.preview-group-header:hover {
  background: #e8e8ed;
}
.preview-group-expand-icon {
  font-size: 20px;
  color: var(--text-muted);
  transition: transform 0.2s;
}
.group-checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}
.group-checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--color-blue);
}
.preview-group-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  flex: 1;
}
.preview-group-count {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-neutral);
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: 8px;
  flex-shrink: 0;
}
.preview-channels {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.preview-channel-item {
  padding: 8px 10px;
  border-radius: 8px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  transition: background 0.2s;
  margin-left: 12px;
}
.preview-channel-item:hover {
  background: var(--bg-neutral);
}
.channel-checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.channel-checkbox-label input[type="checkbox"] {
  width: 14px;
  height: 14px;
  cursor: pointer;
  accent-color: var(--color-blue);
  flex-shrink: 0;
}
.preview-ch-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}
.preview-ch-code {
  font-size: 12px;
  color: var(--color-blue);
  font-family: var(--font-mono);
  background: rgba(0, 122, 255, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
  flex-shrink: 0;
}
.preview-ch-group {
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
}
.preview-ch-time {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  flex-shrink: 0;
}

/* ===== 导入选项 ===== */
.import-desc {
  font-size: 13px;
  color: var(--text-secondary);
  text-align: center;
  margin: 0;
}
.import-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.import-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: var(--bg-neutral);
  border: 2px solid transparent;
  border-radius: var(--radius-input);
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}
.import-option:hover {
  background: #e8e8ed;
}
.import-option.selected {
  border-color: var(--color-blue);
  background: rgba(0, 122, 255, 0.04);
}
.option-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.option-icon .material-symbols-outlined {
  font-size: 22px;
  color: var(--color-blue);
}
.option-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.option-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}
.option-desc {
  font-size: 12px;
  color: var(--text-muted);
}
.option-radio {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid var(--text-disabled);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s;
}
.option-radio.checked {
  border-color: var(--color-blue);
  background: var(--color-blue);
}
.check-icon {
  font-size: 16px;
  color: #fff;
}

/* ===== 按钮 ===== */
.step-actions {
  display: flex;
  gap: 10px;
  margin-top: 8px;
}
.next-step-btn,
.confirm-import-btn {
  flex: 1;
  padding: 12px 16px;
  border: none;
  border-radius: var(--radius-input);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}
.next-step-btn {
  background: var(--color-blue);
  color: #fff;
}
.next-step-btn:hover {
  background: #0066d6;
}
.next-step-btn:disabled {
  background: var(--bg-neutral);
  color: var(--text-muted);
  cursor: not-allowed;
}
.confirm-import-btn {
  background: var(--color-green);
  color: #fff;
}
.confirm-import-btn:hover {
  background: #2db84e;
}
.confirm-import-btn:disabled {
  background: var(--bg-neutral);
  color: var(--text-muted);
  cursor: not-allowed;
}

/* ===== 动画 ===== */
@keyframes slideUp {
  from {
    transform: translateY(100%);
  }
  to {
    transform: translateY(0);
  }
}

/* ===== 工具类 ===== */
.mono {
  font-family: var(--font-mono);
}
.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== 去重样式 ===== */
.dedup-stats {
  display: flex;
  gap: 12px;
}
.stat-item {
  font-size: 13px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 8px;
}
.stat-item.total {
  color: var(--text-secondary);
  background: var(--bg-neutral);
}
.stat-item.duplicate {
  color: var(--color-red);
  background: rgba(255, 59, 48, 0.1);
}
.stat-item.unique {
  color: var(--color-green);
  background: rgba(52, 199, 89, 0.1);
}

.dedup-section {
  margin-bottom: 16px;
}
.dedup-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-red);
  margin-bottom: 12px;
}
.dedup-icon {
  font-size: 18px;
}
.duplicate-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 300px;
  overflow-y: auto;
  padding: 12px;
  background: var(--bg-neutral);
  border-radius: var(--radius-input);
}
.duplicate-group {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 12px;
}
.dup-code {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-blue);
  font-family: var(--font-mono);
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--bg-neutral);
}
.dup-channels {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.dup-channel-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 12px;
}
.dup-channel-item.is-first {
  background: rgba(52, 199, 89, 0.08);
}
.dup-channel-item.is-duplicate {
  background: rgba(255, 59, 48, 0.06);
  opacity: 0.8;
}
.dup-badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}
.badge-keep {
  background: var(--color-green);
  color: #fff;
}
.badge-remove {
  background: var(--color-red);
  color: #fff;
}
.dup-name {
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}
.dup-code {
  font-family: var(--font-mono);
  color: var(--color-blue);
}
.dup-group {
  color: var(--text-muted);
  font-size: 11px;
}
.no-duplicate {
  text-align: center;
  padding: 32px 20px;
  color: var(--color-green);
}
.no-dup-icon {
  font-size: 48px;
  margin-bottom: 12px;
}
.no-duplicate p {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

/* ===== 频道添加/编辑弹窗 ===== */
.channel-modal {
  max-width: 420px;
}
.channel-modal .modal-body {
  flex-direction: column;
  gap: 0px;
}
.channel-modal .form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.channel-modal .form-item label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}
.channel-modal .form-item input,
.channel-modal .form-item select {
  appearance: none;
  -webkit-appearance: none;
  background: var(--bg-neutral);
  border: 1px solid transparent;
  outline: none;
  padding: 10px 12px;
  border-radius: var(--radius-input);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  width: 100%;
  box-sizing: border-box;
  transition: border-color 0.2s;
}
.channel-modal .form-item input:focus,
.channel-modal .form-item select:focus {
  border-color: var(--color-blue);
}
.modal-footer {
  display: flex;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--bg-neutral);
  margin-top: 4px;
}
.modal-footer .back-btn {
  flex: 1;
  margin-left: 0;
  justify-content: center;
}
.modal-footer .confirm-import-btn {
  flex: 1;
  justify-content: center;
}
.modal-footer .delete-btn-modal {
  padding: 8px 14px;
  background: rgba(255, 59, 48, 0.1);
  color: var(--color-red);
  border: none;
  border-radius: var(--radius-input);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.modal-footer .delete-btn-modal:hover {
  background: rgba(255, 59, 48, 0.18);
}

/* ===== 分组管理弹窗 ===== */
.add-group-form {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
.add-group-form input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--bg-neutral);
  border-radius: var(--radius-input);
  font-size: 13px;
  background: var(--bg-neutral);
  color: var(--text-primary);
  outline: none;
}
.add-group-form input:focus {
  border-color: var(--color-blue);
}
.add-group-form .confirm-import-btn {
  padding: 8px 16px;
  white-space: nowrap;
}
.group-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}
.empty-groups {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 13px;
}
.group-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-neutral);
  border-radius: var(--radius-input);
}
.group-item-name {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.group-item input {
  flex: 1;
  padding: 4px 8px;
  border: 1px solid var(--color-blue);
  border-radius: 6px;
  font-size: 13px;
  background: var(--bg-card);
  color: var(--text-primary);
  outline: none;
}
.group-item-actions {
  display: flex;
  gap: 4px;
}
.group-action-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  background: transparent;
}
.group-action-btn.edit {
  color: var(--color-blue);
  background: rgba(0, 122, 255, 0.08);
}
.group-action-btn.edit:hover {
  background: rgba(0, 122, 255, 0.18);
}
.group-action-btn.delete {
  color: var(--color-red);
  background: rgba(255, 59, 48, 0.08);
}
.group-action-btn.delete:hover {
  background: rgba(255, 59, 48, 0.18);
}
.group-action-btn.save {
  color: var(--color-green);
  background: rgba(52, 199, 89, 0.08);
}
.group-action-btn.save:hover {
  background: rgba(52, 199, 89, 0.18);
}
.group-action-btn.cancel {
  color: var(--text-secondary);
  background: var(--bg-card);
}
.group-action-btn.cancel:hover {
  background: #e8e8ed;
}
.group-action-btn.move {
  color: var(--text-muted);
  background: rgba(0, 0, 0, 0.04);
}
.group-action-btn.move:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.08);
  color: var(--text-primary);
}
.group-action-btn.move:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.group-action-btn.eye-visible {
  color: var(--color-blue);
  background: rgba(0, 122, 255, 0.08);
}
.group-action-btn.eye-visible:hover {
  background: rgba(0, 122, 255, 0.18);
}
.group-action-btn.eye-hidden {
  color: var(--text-muted);
  background: rgba(0, 0, 0, 0.04);
}
.group-action-btn.eye-hidden:hover {
  background: rgba(0, 0, 0, 0.08);
  color: var(--text-secondary);
}

/* ===== 订阅地址弹窗 ===== */
.url-item {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  padding: 16px;
  box-shadow: var(--shadow-sm);
  border: 1.5px solid rgba(0, 0, 0, 0.08);
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.url-item:hover {
  border-color: var(--color-blue);
  background: rgba(0, 122, 255, 0.03);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.url-item:active {
  transform: scale(0.98);
  box-shadow: var(--shadow-sm);
}

.url-item-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.url-type-badge {
  font-size: 14px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(0, 122, 255, 0.1);
  color: var(--color-blue);
}

.url-type-badge.m3u {
  background: rgba(88, 86, 214, 0.1);
  color: #5856d6;
}

.url-type-desc {
  font-size: 13px;
  color: var(--text-muted);
}

.url-item-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.url-text {
  font-size: 12px;
  color: var(--text-primary);
  flex: 1;
  word-break: break-all;
  line-height: 1.5;
}

/* ===== 批量分组弹窗 ===== */
.batch-group-list {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--bg-neutral);
  border-radius: var(--radius-input);
  padding-right: 4px;
  margin-top: 8px;
}
/* 分组头部 */
.batch-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 0.2s;
  background: var(--bg-neutral);
}
.batch-group-header:hover {
  background: #e8e8ed;
}
.batch-group-header.is-selected {
  background: rgba(0, 122, 255, 0.12);
}
.batch-group-header-name {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.batch-group-header-count {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-neutral);
  padding: 2px 8px;
  border-radius: 10px;
}
.batch-group-expand-icon {
  font-size: 20px;
  color: var(--text-muted);
  transition: transform 0.2s;
}
.batch-channel-item {
  padding: 8px 10px;
  border-radius: 8px;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  margin-left: 12px;
}
.batch-channel-item:last-child {
  margin-bottom: 0;
}
.batch-channel-item:hover {
  background: var(--bg-neutral);
}
.batch-channel-item.selected {
  background: rgba(0, 122, 255, 0.08);
}
.batch-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--color-blue);
  flex-shrink: 0;
}
.batch-ch-name {
  font-weight: 500;
  color: var(--text-secondary);
  font-size: 12px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.batch-ch-code {
  font-size: 11px;
  color: var(--color-blue);
  font-family: var(--font-mono);
  background: rgba(0, 122, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}
.batch-ch-group {
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
}
.batch-select-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.select-all-btn,
.select-none-btn,
.select-invert-btn {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}
.select-all-btn {
  background: var(--bg-neutral);
  color: var(--text-secondary);
}
.select-all-btn:hover {
  background: #e8e8ed;
}
.select-none-btn {
  background: var(--bg-neutral);
  color: var(--text-secondary);
}
.select-none-btn:hover {
  background: #e8e8ed;
}
.select-invert-btn {
  background: var(--bg-neutral);
  color: var(--text-secondary);
}
.select-invert-btn:hover {
  background: #e8e8ed;
}
.empty-batch {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 13px;
}

/* ===== 批量删除弹窗样式 ===== */
.confirm-delete-btn {
  flex: 1;
  padding: 12px 16px;
  border: none;
  border-radius: var(--radius-input);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--color-red);
  color: #fff;
  justify-content: center;
}
.confirm-delete-btn:hover:not(:disabled) {
  background: #e03e3e;
}
.confirm-delete-btn:disabled {
  background: var(--bg-neutral);
  color: var(--text-muted);
  cursor: not-allowed;
}
.modal-footer .confirm-delete-btn {
  flex: 1;
  justify-content: center;
}
.batch-delete-warning {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(255, 59, 48, 0.08);
  border-radius: var(--radius-input);
  font-size: 13px;
  color: var(--color-red);
  font-weight: 600;
  margin-bottom: 10px;
}
.warning-icon {
  font-size: 20px;
}
</style>
