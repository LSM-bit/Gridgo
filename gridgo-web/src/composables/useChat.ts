/**
 * useChat —— 对局内聊天
 *
 * 优先走 WebSocket（chat.send → chat.message 广播），
 * 断线或服务端未广播时回退 REST（GET/POST /rooms/{id}/chat）。
 * 服务端已改为 WS 广播，故不再依赖轮询。
 */

import { ref } from 'vue'
import { gameWS } from '@/api/ws'
import { getChatMessages, sendChatMessage } from '@/api/chat'
import type { ChatMessage } from '@/api/chat'
import type { ChatMessagePayload } from '@/types/game'
import { useWebSocket } from './useWebSocket'

export interface UseChatOptions {
  /** 房间 ID 取值器（游戏内房间 ID 可能来自快照） */
  roomId: () => string
  /** WS 不可用时是否回退 REST，默认 true */
  enableRestFallback?: boolean
  /** 单页消息条数 */
  pageSize?: number
  /** 内存中保留的最大消息条数 */
  maxMessages?: number
}

const MAX_CONTENT_LENGTH = 500

/** 把后端文本负载归一化为消息对象（兼容 content / message / 纯字符串） */
export function normalizeChatMessage(raw: unknown, roomId: string): ChatMessagePayload | null {
  const source = raw as Record<string, unknown> | string | null
  if (!source) return null
  if (typeof source === 'string') {
    return { id: `local-${Date.now()}-${Math.random()}`, room_id: roomId, user_id: 0, nickname: '系统', is_ai: false, content: source, created_at: new Date().toISOString() }
  }
  const content = (source.content ?? source.message ?? '') as string
  if (!content) return null
  return {
    id: String(source.id ?? `local-${Date.now()}-${Math.random()}`),
    room_id: String(source.room_id ?? roomId),
    user_id: Number(source.user_id ?? 0),
    nickname: String(source.nickname ?? '未知'),
    is_ai: Boolean(source.is_ai ?? false),
    content,
    created_at: String(source.created_at ?? new Date().toISOString()),
  }
}

export function useChat(options: UseChatOptions) {
  const { enableRestFallback = true, pageSize = 50, maxMessages = 300 } = options
  const ws = useWebSocket()

  const messages = ref<ChatMessagePayload[]>([])
  const loading = ref(false)
  const sending = ref(false)
  const hasMore = ref(false)
  const error = ref<string | null>(null)
  /** 最近一次发送是否走了 WS */
  const lastSendViaWS = ref(false)

  const toPayload = (msg: ChatMessage): ChatMessagePayload => normalizeChatMessage(msg, options.roomId()) as ChatMessagePayload

  const push = (msg: ChatMessagePayload) => {
    if (messages.value.some((m) => m.id === msg.id)) return
    messages.value.push(msg)
    if (messages.value.length > maxMessages) {
      messages.value = messages.value.slice(-maxMessages)
    }
  }

  /** WS chat.message 广播入口（useWebSocket 会在组件卸载时自动解绑） */
  ws.on('chat.message', (raw) => {
    const msg = normalizeChatMessage(raw, options.roomId())
    if (msg) push(msg)
  })

  const loadInitial = async () => {
    const roomId = options.roomId()
    if (!roomId) return
    loading.value = true
    error.value = null
    try {
      const list = await getChatMessages(roomId, undefined, pageSize)
      messages.value = list.map(toPayload).slice(-maxMessages)
      hasMore.value = list.length >= pageSize
    } catch (e) {
      error.value = e instanceof Error ? e.message : '聊天记录加载失败'
    } finally {
      loading.value = false
    }
  }

  const loadOlder = async () => {
    const roomId = options.roomId()
    if (!roomId || messages.value.length === 0) return
    loading.value = true
    try {
      const oldestId = messages.value[0].id
      const older = await getChatMessages(roomId, oldestId, pageSize)
      if (older.length === 0) {
        hasMore.value = false
        return
      }
      messages.value = [...older.map(toPayload), ...messages.value]
      hasMore.value = older.length >= pageSize
    } catch (e) {
      error.value = e instanceof Error ? e.message : '历史消息加载失败'
    } finally {
      loading.value = false
    }
  }

  /** 发送消息：优先 WS，失败回退 REST；返回是否发送成功 */
  const send = async (raw: string): Promise<boolean> => {
    const content = raw.trim().slice(0, MAX_CONTENT_LENGTH)
    const roomId = options.roomId()
    if (!content || !roomId) return false

    sending.value = true
    error.value = null
    try {
      if (gameWS.isConnected && gameWS.sendChat(content)) {
        lastSendViaWS.value = true
        return true
      }
      lastSendViaWS.value = false
      if (!enableRestFallback) {
        error.value = '连接已断开，消息未发送'
        return false
      }
      const saved = await sendChatMessage(roomId, content)
      if (saved) push(toPayload(saved))
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : '消息发送失败'
      return false
    } finally {
      sending.value = false
    }
  }

  const clear = () => {
    messages.value = []
    hasMore.value = false
    error.value = null
  }

  return {
    messages,
    loading,
    sending,
    hasMore,
    error,
    lastSendViaWS,
    loadInitial,
    loadOlder,
    send,
    push,
    clear,
  }
}
