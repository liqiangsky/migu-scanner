<template>
  <div class="sc-toast-container">
    <TransitionGroup name="toast-slide" tag="div" class="sc-toast-group">
      <div
        v-for="item in items"
        :key="item.id"
        class="sc-toast-item"
        :class="[`type-${item.type}`, { 'is-notif': item.notification }]"
      >
        <span class="sc-toast-icon material-symbols-outlined">{{ icons[item.type] }}</span>
        <div class="sc-toast-content">{{ item.message }}</div>
        <button class="sc-toast-close" @click="remove(item.id)">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'

defineOptions({ name: 'ToastContainer' })

const items = ref([])
let idCounter = 0
const timers = new Set()

const icons = {
  success: 'check_circle',
  error: 'error',
  info: 'info',
  warning: 'warning',
}

const MAX_VISIBLE = 3

const add = (message, type = 'info', duration = 3500, notification = false) => {
  const id = idCounter++
  items.value.push({ id, message, type, notification })

  if (items.value.length > MAX_VISIBLE) {
    const oldest = items.value[0]
    remove(oldest.id)
  }

  if (duration > 0) {
    const timer = setTimeout(() => {
      timers.delete(timer)
      remove(id)
    }, duration)
    timers.add(timer)
  }
}

const remove = (id) => {
  items.value = items.value.filter((item) => item.id !== id)
}

onUnmounted(() => {
  for (const timer of timers) {
    clearTimeout(timer)
  }
  timers.clear()
})

defineExpose({ add })
</script>

<style scoped>
.sc-toast-container {
  position: fixed;
  top: calc(12px + env(safe-area-inset-top));
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  pointer-events: none;
  width: calc(100% - 32px);
  max-width: min(400px, calc(100% - 32px));
}

.sc-toast-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sc-toast-item {
  display: flex;
  align-items: center;
  padding: 12px 14px;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.06);
  backdrop-filter: blur(20px);
  pointer-events: auto;
  box-sizing: border-box;
  transition: opacity 0.35s cubic-bezier(0.25, 1, 0.5, 1), transform 0.35s cubic-bezier(0.25, 1, 0.5, 1);
}

.sc-toast-content {
  flex: 1;
  margin-left: 10px;
  margin-right: 8px;
  font-size: 13px;
  font-family: var(--font-sans);
  font-weight: 500;
  line-height: 1.4;
  word-break: break-all;
}

.sc-toast-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.sc-toast-close {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 2px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}
.sc-toast-close:hover {
  background-color: rgba(255, 255, 255, 0.1);
}
.sc-toast-close .material-symbols-outlined {
  font-size: 18px;
}

.sc-toast-item {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  color: var(--text-primary);
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.type-success .sc-toast-icon { color: var(--color-green); }
.type-error .sc-toast-icon { color: var(--color-red); }
.type-info .sc-toast-icon { color: var(--color-blue); }
.type-warning .sc-toast-icon { color: var(--color-orange); }

.toast-slide-enter-from { opacity: 0; transform: scale(0.85); }
.toast-slide-enter-to { opacity: 1; transform: scale(1); }
.toast-slide-leave-from { opacity: 1; transform: scale(1); }
.toast-slide-leave-to { opacity: 0; transform: scale(0.75); }
.toast-slide-move { transition: transform 0.3s cubic-bezier(0.25, 1, 0.5, 1); }
.toast-slide-leave-active { position: absolute; width: 100%; }
</style>