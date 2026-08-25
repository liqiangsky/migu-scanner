import axios from 'axios'
import { toast } from '@/components/Toast'
import { baseURL } from '@/constant.js'

const request = axios.create({
  baseURL: baseURL,
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
    // code 非 200，显示错误 toast 并返回错误
    toast.error(res?.msg || '请求失败')
    const error = new Error(res?.msg)
    error.response = { data: res }
    return Promise.reject(error)
  },
  error => {
    // 只有网络错误（没有 response.data.msg）时才显示 toast
    if (!error.response?.data?.msg) {
      const message = error.message || '请求失败'
      toast.error(message)
    }
    return Promise.reject(error)
  }
)

export default request
