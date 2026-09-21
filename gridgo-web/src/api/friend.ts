/**
 * 好友 API（/friends）
 *
 * 对齐后端 app/api/v1/friend.py：
 *   GET    /friends                     好友列表
 *   GET    /friends/requests            收到的好友申请
 *   POST   /friends/requests            发送好友申请
 *   POST   /friends/requests/{id}/respond  处理好友申请
 *   DELETE /friends/{friend_id}         删除好友
 */

import request from './rest'
import type { FriendItem, FriendRequestItem } from '@/types/api'

export type { FriendItem, FriendRequestItem }

export function getFriends() {
  return request.get<any, FriendItem[]>('/friends')
}

export function getFriendRequests() {
  return request.get<any, FriendRequestItem[]>('/friends/requests')
}

export function sendFriendRequest(targetId: number) {
  return request.post<any, { message: string; request_id: number }>('/friends/requests', { target_id: targetId })
}

export function respondFriendRequest(requestId: number, accept: boolean) {
  return request.post<any, { message: string }>(`/friends/requests/${requestId}/respond`, { accept })
}

export function deleteFriend(friendId: number) {
  return request.delete<any, { message: string }>(`/friends/${friendId}`)
}
