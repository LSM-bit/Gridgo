/**
 * useWebSocket —— 页面级 WS 生命周期管理
 *
 * 统一处理：连接/断开、事件订阅（自动随组件卸载解绑）、发送封装、关闭码语义。
 */

import { getCurrentInstance, onUnmounted, ref } from 'vue'
import { gameWS } from '@/api/ws'
import { useUserStore } from '@/stores/user'
import { describeCloseCode } from '@/utils/ws'
import type { CloseCodeInfo } from '@/utils/ws'
import type { TradeOfferPayload } from '@/types/game'

export interface UseWebSocketOptions {
  onClose?: (info: CloseCodeInfo) => void
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const userStore = useUserStore()
  const connected = ref(gameWS.isConnected)
  const lastClose = ref<CloseCodeInfo | null>(null)
  const unbinders: Array<() => void> = []

  const connect = (roomId: string) => {
    gameWS.connect(userStore.token, roomId)
    connected.value = true
  }

  const disconnect = () => {
    gameWS.disconnect()
    connected.value = false
  }

  const send = (type: string, data: unknown = {}) => gameWS.send(type, data)

  /** 订阅消息，返回值可用于手动解绑；组件卸载时自动解绑 */
  const on = <T = unknown>(type: string, handler: (data: T) => void) => {
    const wrapped = (data: unknown) => handler(data as T)
    const off = gameWS.on(type, wrapped)
    unbinders.push(off)
    return off
  }

  const offAll = () => {
    unbinders.forEach((off) => off())
    unbinders.length = 0
  }

  const onClose = (handler: (info: CloseCodeInfo) => void) => {
    const off = gameWS.onClose(handler)
    unbinders.push(off)
    return off
  }

  onClose((info) => {
    connected.value = false
    lastClose.value = info
    options.onClose?.(info)
  })

  if (getCurrentInstance()) {
    onUnmounted(() => {
      offAll()
    })
  }

  return {
    connected,
    lastClose,
    connect,
    disconnect,
    send,
    on,
    offAll,
    onClose,
    sendChat: (content: string) => gameWS.sendChat(content),
    sendTradeOffer: (payload: TradeOfferPayload) => gameWS.sendTradeOffer(payload),
    sendTradeAccept: (tradeId: string) => gameWS.sendTradeAccept(tradeId),
    sendTradeReject: (tradeId: string) => gameWS.sendTradeReject(tradeId),
    describeCloseCode,
  }
}
