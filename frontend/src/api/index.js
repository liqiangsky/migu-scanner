import axios from 'axios'
import { toast } from '@/components/Toast'

const request = axios.create({
  baseURL: '',
  timeout: 30000
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    const res = response.data
    // 后端返回格式: {code: 200, data: ..., msg: ...}
    // 直接返回 data 字段
    if (res && res.code === 200) {
      return res.data
    }
    return res
  },
  error => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    toast.error(message)
    return Promise.reject(error)
  }
)

export default request
