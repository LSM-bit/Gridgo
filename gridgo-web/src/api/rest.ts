import axios from 'axios'
import { useUserStore } from '@/stores/user'

// 扩展 Axios 配置类型，支持附加自定义属性
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    /** 请求发起时间戳，用于计算耗时 */
    _startTime?: number
    /** 标记该请求是 token 刷新请求，避免无限循环 */
    _isRefresh?: boolean
  }
}

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

// ─── 日志工具 ───

/** 截断过长字符串 */
function truncate(str: string, max = 200): string {
  return str.length > max ? str.slice(0, max) + '…' : str
}

/** 日志脱敏：递归隐藏密码 / Token 等敏感字段，避免开发调试日志泄露凭据 */
const SENSITIVE_KEYS = [
  'password',
  'old_password',
  'new_password',
  'token',
  'access_token',
  'refresh_token',
  'authorization',
]

function redact(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(redact)
  }
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, val]) => [
        key,
        SENSITIVE_KEYS.includes(key.toLowerCase()) ? '***' : redact(val),
      ]),
    )
  }
  return value
}

// ─── Token 刷新锁，防止并发请求同时触发多次刷新 ───

let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

/** 将等待刷新完成的请求加入队列 */
function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

/** 刷新成功后，通知所有排队的请求用新 token 重试 */
function onTokenRefreshed(newToken: string) {
  refreshSubscribers.forEach((cb) => cb(newToken))
  refreshSubscribers = []
}

/** 刷新失败，拒绝所有排队的请求 */
function onRefreshFailed() {
  refreshSubscribers = []
}

// ─── 请求拦截器 ───

request.interceptors.request.use((config) => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }

  // 记录请求开始时间，用于计算耗时
  config._startTime = Date.now()

  // 仅开发环境输出请求日志（生产构建不打印请求内容，避免敏感信息泄露）
  if (import.meta.env.DEV) {
    const method = (config.method ?? 'GET').toUpperCase()
    const url = `${config.baseURL ?? ''}${config.url ?? ''}`
    const body = config.data ? truncate(JSON.stringify(redact(config.data))) : '-'

    console.log(
      `%c→ %c${method} %c${url} %c${body}`,
      'color:#6cf;font-weight:bold',   // 箭头
      'color:#fd6;font-weight:bold',   // 方法
      'color:#aaa',                    // URL
      'color:#666',                    // 请求体
    )
  }

  return config
})

// ─── 响应拦截器 ───

request.interceptors.response.use(
  (response) => {
    // 仅开发环境输出响应日志（生产构建不打印响应内容）
    if (import.meta.env.DEV) {
      const method = (response.config.method ?? 'GET').toUpperCase()
      const url = `${response.config.baseURL ?? ''}${response.config.url ?? ''}`
      const status = response.status
      const duration = Date.now() - (response.config._startTime ?? Date.now())
      const body = truncate(JSON.stringify(redact(response.data)))

      console.log(
        `%c← %c${status} %c${method} ${url} %c${duration}ms %c${body}`,
        'color:#6cf;font-weight:bold',   // 箭头
        'color:#4f4;font-weight:bold',   // 状态码
        'color:#aaa',                    // 方法 + URL
        'color:#888',                    // 耗时
        'color:#666',                    // 响应体
      )
    }

    return response.data
  },
  async (error) => {
    const config = error.config ?? {}

    // 仅开发环境输出错误响应日志（生产构建不打印响应内容）
    if (import.meta.env.DEV) {
      const method = (config.method ?? 'GET').toUpperCase()
      const url = `${config.baseURL ?? ''}${config.url ?? ''}`
      const status = error.response?.status ?? 'N/A'
      const duration = Date.now() - (config._startTime ?? Date.now())
      const detail = error.response?.data
        ? truncate(JSON.stringify(redact(error.response.data)))
        : error.message ?? 'Unknown error'

      console.log(
        `%c← %c${status} %c${method} ${url} %c${duration}ms %c${detail}`,
        'color:#6cf;font-weight:bold',   // 箭头
        'color:#f44;font-weight:bold',   // 状态码（红色=错误）
        'color:#aaa',                    // 方法 + URL
        'color:#888',                    // 耗时
        'color:#f66',                    // 错误详情（红色）
      )
    }

    if (error.response?.status === 401 && !config._isRefresh) {
      const userStore = useUserStore()

      // 如果有 refresh_token，尝试刷新
      if (userStore.refreshToken) {
        // 如果已经有请求在刷新 token，排队等待
        if (isRefreshing) {
          return new Promise((resolve) => {
            subscribeTokenRefresh((newToken: string) => {
              config.headers.Authorization = `Bearer ${newToken}`
              resolve(request(config))
            })
          })
        }

        isRefreshing = true

        try {
          // 用原始 axios 实例发刷新请求，避免走拦截器
          const { data } = await axios.post('/api/v1/auth/refresh', {
            refresh_token: userStore.refreshToken,
          })

          // 更新 store 中的 token
          userStore.setUserInfo({
            token: data.access_token,
            refreshToken: data.refresh_token,
            userId: userStore.userId,
            username: userStore.username,
            nickname: userStore.nickname,
            avatar: userStore.avatar,
          })

          console.log('[Auth] Token refreshed successfully')

          // 通知所有排队的请求
          onTokenRefreshed(data.access_token)

          // 用新 token 重试原始请求
          config.headers.Authorization = `Bearer ${data.access_token}`
          return request(config)
        } catch (refreshError) {
          console.warn('[Auth] Token refresh failed, redirecting to login')
          onRefreshFailed()
          userStore.clearUserInfo()
          window.location.href = '/login'
          return Promise.reject(refreshError)
        } finally {
          isRefreshing = false
        }
      } else {
        // 没有 refresh_token，直接跳登录
        userStore.clearUserInfo()
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  },
)

export default request
