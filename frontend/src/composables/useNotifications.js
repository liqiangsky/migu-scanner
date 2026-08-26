/**
 * 全局通知 composable - SSE 连接
 * 在 App.vue 中调用 connect() 即可全局订阅通知
 */
import { toast } from '@/components/Toast'
import { baseURL } from '@/constant'

let eventSource = null

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
