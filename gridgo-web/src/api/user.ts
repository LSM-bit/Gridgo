/**
 * 用户相关 API
 */

import request from './rest'

// ─── 类型定义 ───

export interface UserProfile {
  id: number
  username: string
  nickname: string
  avatar: string | null
  email: string | null
  status: number
  created_at: string | null
}

export interface UserStats {
  total_games: number
  wins: number
  total_assets: number
  avg_rank: number
  bankruptcies: number
}

export interface GameRecordItem {
  id: number
  room_id: string
  map_id: string
  total_turns: number
  player_count: number
  winner_id: number | null
  winner_nickname: string | null
  end_reason: string
  created_at: string | null
  my_rank: number | null
  my_total_assets: number | null
  my_is_bankrupt: boolean | null
}

export interface GamePlayerItem {
  user_id: number
  nickname: string
  rank: number
  total_assets: number
  is_bankrupt: boolean
  is_ai: boolean
  ai_difficulty: string | null
}

export interface GameRecordDetail {
  id: number
  room_id: string
  map_id: string
  total_turns: number
  player_count: number
  winner_id: number | null
  end_reason: string
  created_at: string | null
  players: GamePlayerItem[]
}

export interface UpdateProfileData {
  nickname?: string
  avatar?: string
  email?: string
}

// ─── API 方法 ───

/** 获取当前用户详细信息 */
export function getMyProfile() {
  return request.get<any, UserProfile>('/users/me')
}

/** 修改当前用户个人信息 */
export function updateMyProfile(data: UpdateProfileData) {
  return request.patch<any, UserProfile>('/users/me', data)
}

/** 修改密码 */
export function changePassword(data: { old_password: string; new_password: string }) {
  return request.post<any, { message: string }>('/users/me/change-password', data)
}

/** 获取当前用户统计数据 */
export function getMyStats() {
  return request.get<any, UserStats>('/users/me/stats')
}

/** 获取当前用户对局记录 */
export function getMyRecords(limit = 20, offset = 0) {
  return request.get<any, GameRecordItem[]>('/users/me/records', { params: { limit, offset } })
}

/** 获取对局记录详情 */
export function getGameRecordDetail(gameId: number) {
  return request.get<any, GameRecordDetail>(`/users/records/${gameId}`)
}
