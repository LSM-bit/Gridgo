/**
 * WebSocket 客户端封装
 * 支持：自动重连、心跳、消息分发、room_id 绑定、Token 自动刷新
 */

import { useUserStore } from '@/stores/user'

interface WSMessage {
  type: string
  data: unknown
  seq?: number
  timestamp: number
}

type MessageHandler = (data: unknown) => void

class GameWebSocket {
  private ws: WebSocket | null = null
  private roomId = ''
  private seq = 0
  private handlers = new Map<string, MessageHandler[]>()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private maxReconnectAttempts = 5
  private reconnectAttempts = 0
  private reconnectDelay = 3000
  private _isConnected = false

  get isConnected() {
    return this._isConnected
  }

  /**
   * 连接到游戏 WebSocket
   * @param token JWT access token（初始 token，重连时会自动从 store 获取最新值）
   * @param roomId 房间 ID，连接成功后发送初始化消息
   */
  connect(_token: string, roomId: string) {
    // 如果已有连接，先断开
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      console.log(`[WS] Closing existing connection (state=${this.ws.readyState}) before reconnect`)
      this.stopHeartbeat()
      this.reconnectAttempts = this.maxReconnectAttempts // 阻止旧连接的自动重连
      this.ws.close(1000, 'reconnect')
      this.ws = null
      this._isConnected = false
    }
    this.reconnectAttempts = 0 // 重置重连计数

    this.roomId = roomId
    this.doConnect()
  }

  /** 获取当前最新的 access token（从 store 动态读取） */
  private getCurrentToken(): string {
    const userStore = useUserStore()
    return userStore.token
  }

  /** 构建 WebSocket URL（始终使用最新 token） */
  private buildWsUrl(): string {
    const token = this.getCurrentToken()
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/ws/game?token=${token}`
  }

  private doConnect() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('[WS] Already connected, skip')
      return
    }

    // 每次连接都使用最新的 token
    const token = this.getCurrentToken()
    if (!token) {
      console.error('[WS] No token available, cannot connect')
      return
    }

    const url = this.buildWsUrl()
    console.log(`[WS] ====== CONNECT START ======`)
    console.log(`[WS] URL: ${url.substring(0, url.indexOf('token='))}token=...`)
    console.log(`[WS] roomId: ${this.roomId}`)
    console.log(`[WS] token (first 30): ${token.substring(0, 30)}...`)

    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      console.log('[WS] ✅ Connected to game websocket')
      console.log(`[WS] Sending init: room_id=${this.roomId}`)
      this._isConnected = true
      this.reconnectAttempts = 0

      // 发送初始化消息 — 后端期望的格式是 { "room_id": "xxx" }
      // 注意：不能用 this.send() 因为它会包装成 { type, data, seq, timestamp }
      // 后端 game_ws.py 在 accept() 后直接 receive_json() 取 room_id
      if (this.ws?.readyState === WebSocket.OPEN) {
        const initMsg = JSON.stringify({ room_id: this.roomId })
        console.log(`[WS] Sending init message: ${initMsg}`)
        this.ws.send(initMsg)
        console.log(`[WS] Init message sent`)
      } else {
        console.error(`[WS] Cannot send init: readyState=${this.ws?.readyState}`)
      }

      // 延迟启动心跳，等 init 消息被后端处理后再发 ping
      setTimeout(() => {
        this.startHeartbeat()
      }, 2000)
    }

    this.ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        this.dispatch(msg.type, msg.data)
      } catch (e) {
        console.error('[WS] Parse message error:', e)
      }
    }

    this.ws.onclose = (event) => {
      console.log(`[WS] Disconnected (code=${event.code}, reason=${event.reason})`)
      this._isConnected = false
      this.stopHeartbeat()
      // 注意：不清理 handlers，重连后仍然有效

      // 认证失败（4001）不重连，需要重新登录
      if (event.code === 4001) {
        console.warn('[WS] Authentication failed, redirecting to login')
        const userStore = useUserStore()
        userStore.clearUserInfo()
        window.location.href = '/login'
        return
      }

      // 非正常关闭时尝试重连
      if (event.code !== 1000) {
        this.tryReconnect()
      }
    }

    this.ws.onerror = (error) => {
      console.error('[WS] ❌ Connection error:', error)
    }
  }

  disconnect() {
    this.stopHeartbeat()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.reconnectAttempts = this.maxReconnectAttempts // 阻止重连
    this.ws?.close(1000, 'user disconnect')
    this.ws = null
    this._isConnected = false
    // 注意：不再清理 handlers，让重连或重新挂载后仍然有效
  }

  /**
   * 发送游戏操作消息
   * 格式: { type: string, data: unknown, seq: number, timestamp: number }
   */
  send(type: string, data: unknown = {}) {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      console.warn('[WS] Not connected, cannot send:', type)
      return
    }

    const msg: WSMessage = {
      type,
      data,
      seq: ++this.seq,
      timestamp: Date.now(),
    }

    this.ws.send(JSON.stringify(msg))
  }

  on(type: string, handler: MessageHandler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, [])
    }
    this.handlers.get(type)!.push(handler)
  }

  off(type: string, handler: MessageHandler) {
    const handlers = this.handlers.get(type)
    if (handlers) {
      const idx = handlers.indexOf(handler)
      if (idx > -1) handlers.splice(idx, 1)
    }
  }

  private dispatch(type: string, data: unknown) {
    const handlers = this.handlers.get(type)
    if (handlers) {
      handlers.forEach((h) => h(data))
    }
    // 通配符处理
    const wildcardHandlers = this.handlers.get('*')
    if (wildcardHandlers) {
      wildcardHandlers.forEach((h) => h({ type, data }))
    }
  }

  private startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      this.send('system.ping')
    }, 30000)
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private tryReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn('[WS] Max reconnect attempts reached')
      return
    }

    // 重连前检查 token 是否还有效
    const token = this.getCurrentToken()
    if (!token) {
      console.warn('[WS] No token available, cannot reconnect')
      const userStore = useUserStore()
      userStore.clearUserInfo()
      window.location.href = '/login'
      return
    }

    this.reconnectAttempts++
    console.log(`[WS] Reconnecting (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)

    this.reconnectTimer = setTimeout(() => {
      this.doConnect()
    }, this.reconnectDelay)
  }
}

export const gameWS = new GameWebSocket()
