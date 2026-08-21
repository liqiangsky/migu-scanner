import { createVNode, render } from 'vue'
import ToastComponent from './Index.vue'

// 模块级单例：Toast 挂载在 document.body 下，与 Vue 组件树独立。
const div = document.createElement('div')
document.body.appendChild(div)

const vnode = createVNode(ToastComponent)
render(vnode, div)

export const toast = {
  info(msg, duration) {
    vnode.component.exposed.add(msg, 'info', duration)
  },
  success(msg, duration) {
    vnode.component.exposed.add(msg, 'success', duration)
  },
  warning(msg, duration) {
    vnode.component.exposed.add(msg, 'warning', duration)
  },
  error(msg, duration) {
    vnode.component.exposed.add(msg, 'error', duration)
  },
  notify(msg, type = 'info', duration = 3500) {
    vnode.component.exposed.add(msg, type, duration, true)
  },
}
