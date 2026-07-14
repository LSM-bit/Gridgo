/**
 * 聊天相关 API
 */

import request from './rest'

// ─── 类型定义 ───

export interface ChatMessage {
  id: string
  room_id: string
  user_id: number
  nickname: string
  is_ai: boolean
  content: string
  created_at: string
}

// ─── API 方法 ───

/** 获取聊天消息 */
export function getChatMessages(roomId: string, before?: string, limit = 50) {
  const params: Record<string, string | number> = { limit }
  if (before) params.before = before
  return request.get<any, ChatMessage[]>(`/rooms/${roomId}/chat`, { params })
}

/** 发送聊天消息 */
export function sendChatMessage(roomId: string, content: string) {
  return request.post<any, ChatMessage>(`/rooms/${roomId}/chat`, { content })
}
