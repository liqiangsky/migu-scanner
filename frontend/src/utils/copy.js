/**
 * 全局复制工具
 * @param {string} text - 要复制的文本
 * @param {object} [toast] - Vue toast 实例，用于显示反馈
 * @returns {Promise<boolean>} 是否复制成功
 */
export async function copyText(text, toast) {
  let ok = false
  // 方式1: 现代 Clipboard API（需要 HTTPS 或 localhost）
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      ok = true
    } catch {}
  }
  // 方式2: 传统 execCommand（兼容 HTTP）
  if (!ok) {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    textarea.style.pointerEvents = 'none'
    document.body.appendChild(textarea)
    try {
      textarea.select()
      document.execCommand('copy')
      ok = true
    } catch {}
    finally {
      document.body.removeChild(textarea)
    }
  }
  if (toast) {
    toast[ok ? 'success' : 'error'](ok ? `已复制: ${text}` : '复制失败')
  }
  return ok
}
