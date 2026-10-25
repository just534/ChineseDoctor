import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import { tokenStore } from '@/utils/token'

const http = axios.create({ baseURL: '/api', timeout: 30000 })

http.interceptors.request.use((config) => {
  const token = tokenStore.access
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshing: Promise<string | null> | null = null

async function refreshAccess(): Promise<string | null> {
  const refresh = tokenStore.refresh
  if (!refresh) return null
  try {
    const { data } = await axios.post('/api/auth/refresh', { refresh_token: refresh })
    tokenStore.set(data.access_token, data.refresh_token)
    return data.access_token
  } catch {
    tokenStore.clear()
    return null
  }
}

type RetryConfig = InternalAxiosRequestConfig & { _retried?: boolean; silent?: boolean }

http.interceptors.response.use(
  (res) => res,
  async (error: AxiosError<{ detail?: string }>) => {
    const config = error.config as RetryConfig | undefined
    const status = error.response?.status
    if (status === 401 && config && !config._retried && !config.url?.startsWith('/auth/')) {
      config._retried = true
      refreshing ??= refreshAccess().finally(() => (refreshing = null))
      const token = await refreshing
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
        return http(config)
      }
      window.dispatchEvent(new CustomEvent('auth:expired'))
    }
    if (!config?.silent) {
      const detail = error.response?.data?.detail
      const msg = typeof detail === 'string' ? detail : status ? `请求失败（${status}）` : '网络异常，请稍后再试'
      if (status !== 401 || config?.url?.startsWith('/auth/')) ElMessage.error(msg)
    }
    return Promise.reject(error)
  },
)

declare module 'axios' {
  interface AxiosRequestConfig {
    silent?: boolean
  }
}

export default http
