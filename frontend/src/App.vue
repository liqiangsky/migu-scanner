<template>
  <!-- 页面内容 -->
  <router-view />

  <!-- 底部导航 -->
  <nav class="bottom-tabbar">
      <router-link to="/hosts" class="tab-item" active-class="active" exact-active-class="active">
        <span class="material-symbols-outlined tab-icon">tv</span>
        <span class="tab-text">主机</span>
      </router-link>

      <router-link to="/subscriptions" class="tab-item" active-class="active" exact-active-class="active">
        <span class="material-symbols-outlined tab-icon">rss_feed</span>
        <span class="tab-text">订阅</span>
      </router-link>

      <router-link to="/channels" class="tab-item" active-class="active" exact-active-class="active">
        <span class="material-symbols-outlined tab-icon">live_tv</span>
        <span class="tab-text">频道</span>
      </router-link>
    </nav>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { connect, disconnect } from '@/composables/useNotifications'

onMounted(() => {
  // 全局 SSE 连接（只连接一次）
  connect()

  window.addEventListener('error', (e) => {
    console.error('Global error:', e)
  })
})

onUnmounted(() => {
  disconnect()
})
</script>

<style scoped>
/* ===== 底部 TabBar（iOS 悬浮药丸风格）===== */
.bottom-tabbar {
  position: fixed;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 32px);
  max-width: 358px;
  height: 60px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(40px) saturate(180%);
  border-radius: 20px;
  box-shadow: var(--shadow-tabbar);
  border: 1px solid rgba(0, 0, 0, 0.02);
  display: flex;
  justify-content: space-around;
  align-items: center;
  z-index: 99;
  margin-bottom: env(safe-area-inset-bottom);
}

.tab-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: var(--text-muted);
  text-decoration: none;
  transition: all 0.25s ease;
  width: 30%;
}

.tab-item.active {
  color: var(--color-blue);
}

.tab-icon {
  font-size: 22px;
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
  transition: all 0.25s var(--ease-icon);
}

.tab-item.active .tab-icon {
  font-variation-settings:
    'FILL' 1,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
  transform: scale(1.08);
}

.tab-text {
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-sans);
}
</style>
