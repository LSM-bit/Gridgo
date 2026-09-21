/**
 * WebSocket 客户端封装
 * 支持：自动重连、心跳、消息分发、room_id 绑定、Token 自动刷新、关闭码语义化
 */

import { useUserStore } from '@/stores/user'
import { describeCloseCode } from '@/utils/ws'
import type { CloseCodeInfo } from '@/utils/ws'
import type { ChatMessagePayload, TradeOfferPayload } from '@/types/game'

interface WSMessage {
  type: string
  data: unknown
  seq?: number
  timestamp: number
}

type MessageHandler = (data: unknown) => void
type CloseHandler = (info: CloseCodeInfo) => void

/** 这些关闭码表示服务端已拒绝本次对局上下文，重连无意义 */
const FATAL_CLOSE_CODES = new Set([4002, 4003, 4004, 4005])

class GameWebSocket {
  private ws: WebSocket | null = null
  private roomId = ''
  private seq = 0
  private handlers = new Map<string, MessageHandler[]>()
  private closeHandlers: CloseHandler[] = []
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private maxReconnectAttempts = 5
  private reconnectAttempts = 0
  private reconnectDelay = 3000
  private _isConnected = false
  private _lastCloseCode = 0

  get isConnected() {
    return this._isConnected
  }

  get lastCloseCode() {
    return this._lastCloseCode
  }

  /**
   * 连接到游戏 WebSocket
   * @param token JWT access token（仅作签名占位，实际总是从 store 动态读取最新值）
   * @param roomId 房间 ID，连接成功后发送首帧初始化消息
   */
  connect(_token: string, roomId: string) {
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      this.stopHeartbeat()
      this.reconnectAttempts = this.maxReconnectAttempts
      this.ws.close(1000, 'reconnect')
      this.ws = null
      this._isConnected = false
    }
    this.reconnectAttempts = 0
    this.roomId = roomId
    this.doConnect()
  }

  /** 获取当前最新的 access token（从 store 动态读取） */
  private getCurrentToken(): string {
    const userStore = useUserStore()
    return userStore.token
  }

  /** 构建 WebSocket URL（始终使用最新 token） */
  private buildWsUrl(token: string): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/ws/game?token=${token}`
  }

  private doConnect() {
    if (this.ws?.readyState === WebSocket.OPEN) return

    const token = this.getCurrentToken()
    if (!token) {
      this.emitClose(4001)
      return
    }

    this.ws = new WebSocket(this.buildWsUrl(token))

    this.ws.onopen = () => {
      this._isConnected = true
      this.reconnectAttempts = 0
      // 首帧握手：后端在 accept() 后直接 receive_json() 取 room_id（docs/PROJECT.md 7.2）
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ room_id: this.roomId }))
      }
      setTimeout(() => this.startHeartbeat(), 2000)
    }

    this.ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        this.dispatch(msg.type, msg.data)
      } catch (e) {
        console.error('[WS] 消息解析失败:', e)
      }
    }

    this.ws.onclose = (event) => {
      this._isConnected = false
      this._lastCloseCode = event.code
      this.stopHeartbeat()
      this.emitClose(event.code)

      if (event.code === 4001) {
        const userStore = useUserStore()
        userStore.clearUserInfo()
        window.location.href = '/login'
        return
      }
      if (FATAL_CLOSE_CODES.has(event.code)) return
      if (event.code !== 1000) this.tryReconnect()
    }

    this.ws.onerror = () => {
      this._isConnected = false
    }
  }

  disconnect() {
    this.stopHeartbeat()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.reconnectAttempts = this.maxReconnectAttempts
    this.ws?.close(1000, 'user disconnect')
    this.ws = null
    this._isConnected = false
  }

  /**
   * 发送游戏操作消息
   * 格式: { type: string, data: unknown, seq: number, timestamp: number }
   */
  send(type: string, data: unknown = {}): boolean {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      console.warn('[WS] 未连接，消息未发送:', type)
      return false
    }
    const msg: WSMessage = { type, data, seq: ++this.seq, timestamp: Date.now() }
    this.ws.send(JSON.stringify(msg))
    return true
  }

  // ─── 新增能力封装（与后端 game_ws.py 对齐） ───

  /** 聊天（chat.send，载荷字段以 content 为准） */
  sendChat(content: string): boolean {
    return this.send('chat.send', { content })
  }

  /** 发起交易（game.trade_offer） */
  sendTradeOffer(payload: TradeOfferPayload): boolean {
    return this.send('game.trade_offer', payload)
  }

  /** 接受交易（game.trade_accept） */
  sendTradeAccept(tradeId: string): boolean {
    return this.send('game.trade_accept', { trade_id: tradeId })
  }

  /** 拒绝/撤回交易（game.trade_reject） */
  sendTradeReject(tradeId: string): boolean {
    return this.send('game.trade_reject', { trade_id: tradeId })
  }

  on(type: string, handler: MessageHandler) {
    if (!this.handlers.has(type)) this.handlers.set(type, [])
    this.handlers.get(type)!.push(handler)
    return () => this.off(type, handler)
  }

  off(type: string, handler: MessageHandler) {
    const handlers = this.handlers.get(type)
    if (!handlers) return
    const idx = handlers.indexOf(handler)
    if (idx > -1) handlers.splice(idx, 1)
  }

  onClose(handler: CloseHandler) {
    this.closeHandlers.push(handler)
    return () => {
      const idx = this.closeHandlers.indexOf(handler)
      if (idx > -1) this.closeHandlers.splice(idx, 1)
    }
  }

  /** 清空全部监听（页面卸载时调用） */
  clearHandlers() {
    this.handlers.clear()
    this.closeHandlers = []
  }

  private emitClose(code: number) {
    const info = describeCloseCode(code)
    this.closeHandlers.forEach((h) => h(info))
  }

  private dispatch(type: string, data: unknown) {
    this.handlers.get(type)?.forEach((h) => h(data))
    this.handlers.get('*')?.forEach((h) => h({ type, data }))
  }

  private startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => this.send('system.ping'), 30000)
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private tryReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn('[WS] 已达最大重连次数')
      return
    }
    if (!this.getCurrentToken()) {
      const userStore = useUserStore()
      userStore.clearUserInfo()
      window.location.href = '/login'
      return
    }
    this.reconnectAttempts += 1
    this.reconnectTimer = setTimeout(() => this.doConnect(), this.reconnectDelay)
  }
}

export const gameWS = new GameWebSocket()

export type { CloseCodeInfo, ChatMessagePayload }
