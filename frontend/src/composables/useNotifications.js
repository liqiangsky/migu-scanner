/**
 * 全局通知 composable - SSE 连接
 * 在 App.vue 中调用 connect() 即可全局订阅通知
 */
import { onMounted, onUnmounted } from 'vue'
import { toast } from '@/components/Toast'
import { baseURL, NOTIFICATION_SOURCE } from '@/constant'

let eventSource = null
export const notificationEvent = new EventTarget()

/**
 * 连接到 SSE 事件流（全局只连接一次）
 */
export function connect() {
  if (eventSource) {
    eventSource.close()
  }

  eventSource = new EventSource(baseURL + '/events')

  eventSource.addEventListener('message', (event) => {
    try {
      const payload = JSON.parse(event.data)
      // payload 结构: {type: "success"/"error", data: {...}, ts: ...}
      const type = payload.type || 'info'
      const data = payload.data || {}
      // 显示 toast
      if (type === 'success') {
        toast.success(data.title)
      } else if (type === 'error') {
        toast.error(data.title)
      } else {
        toast.notify(data.title || '通知', type)
      }
      // 派发自定义事件，供组件监听
      // 如果 triggerEvent 为 true 且 source 有值，派发 source 命名的自定义事件
      // 事件名为英文标识，如 HOST_RETEST、SUBSCRIPTION_FETCH 等
      if (data?.triggerEvent && data?.source) {
        notificationEvent.dispatchEvent(new CustomEvent(data.source, { detail: { type, data } }))
      }
    } catch {
      // 忽略解析失败
    }
  })

  eventSource.addEventListener('heartbeat', () => {
    // 心跳保持连接
  })

  eventSource.onerror = () => {
    console.warn('[SSE] 连接错误，尝试重连...')
  }
}

/**
 * 断开 SSE 连接
 */
export function disconnect() {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}

/**
 * 通知监听 composable
 * 用于组件监听特定来源的 SSE 通知事件
 *
 * @param {string} source - 通知来源标识，如 'HOST_RETEST'、'SUBSCRIPTION'
 * @param {Function} onNotify - 收到通知时的回调函数
 */
export function useNotificationListener(source, onNotify) {
  const eventKey = NOTIFICATION_SOURCE[source]

  onMounted(() => {
    if (eventKey) {
      notificationEvent.addEventListener(eventKey, onNotify)
    }
  })

  onUnmounted(() => {
    if (eventKey) {
      notificationEvent.removeEventListener(eventKey, onNotify)
    }
  })
}
