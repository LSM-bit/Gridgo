/**
 * 房间相关 API
 */

import request from './rest'

// ─── 类型定义 ───

export interface RoomPlayer {
  user_id: number
  username: string
  nickname: string
  avatar: string | null
  is_host: boolean
  is_ready: boolean
  is_ai: boolean
  ai_difficulty: string | null
}

export interface SpectatorInfo {
  user_id: number
  username: string
  nickname: string
  avatar: string | null
  is_host: boolean
}

export interface RoomInfo {
  id: string
  code: string
  name: string
  host_id: number
  max_players: number
  map_id: string
  ai_count: number
  ai_difficulty: string
  status: 'waiting' | 'playing' | 'finished'
  players: RoomPlayer[]
  spectators: SpectatorInfo[]
  max_spectators: number
  /** 是否设置了房间密码（后端 RoomInfo.has_password） */
  has_password?: boolean
  created_at: string | null
}

export interface RoomListItem {
  id: string
  code: string
  name: string
  host_nickname: string
  player_count: number
  max_players: number
  map_id: string
  ai_count: number
  spectator_count: number
  status: string
}

export interface CreateRoomData {
  name?: string
  max_players?: number
  map_id?: string
  ai_count?: number
  ai_difficulty?: string
  /** 房间密码（可选，设置后加入房间需提供） */
  password?: string | null
}

export interface UpdateRoomData {
  name?: string
  max_players?: number
  map_id?: string
  ai_count?: number
  ai_difficulty?: string
  /** 房间密码：传值表示设置/修改；配合 clear_password 可清除 */
  password?: string | null
  /** 清除房间密码 */
  clear_password?: boolean
}

// ─── 地图选项 ───

export const MAP_OPTIONS = [
  { value: 'classic', label: '经典地图' },
  { value: 'city', label: '城市风云' },
  { value: 'island', label: '海岛探险' },
] as const

export const AI_DIFFICULTY_OPTIONS = [
  { value: 'easy', label: '简单' },
  { value: 'medium', label: '中等' },
  { value: 'hard', label: '困难' },
] as const

// ─── API 方法 ───

/** 获取房间列表 */
export function getRooms() {
  return request.get<any, RoomListItem[]>('/rooms')
}

/** 获取当前用户所在（活跃）房间；未加入任何房间时返回 null */
export function getMyRoom() {
  return request.get<any, RoomInfo | null>('/rooms/active')
}

/** 创建房间 */
export function createRoom(data?: CreateRoomData) {
  return request.post<any, RoomInfo>('/rooms', data || {})
}

/** 通过房间代码获取房间 */
export function getRoomByCode(code: string) {
  return request.get<any, RoomInfo>(`/rooms/by-code/${code}`)
}

/** 获取房间详情 */
export function getRoom(roomId: string) {
  return request.get<any, RoomInfo>(`/rooms/${roomId}`)
}

/** 加入房间（密码房需传 password） */
export function joinRoom(code: string, asSpectator: boolean = false, password?: string) {
  const body: { code: string; as_spectator: boolean; password?: string } = {
    code,
    as_spectator: asSpectator,
  }
  if (password) body.password = password
  return request.post<any, RoomInfo>('/rooms/join', body)
}

/** 离开房间 */
export function leaveRoom(roomId: string) {
  return request.post<any, { code: number; destroyed: boolean; message: string }>(`/rooms/${roomId}/leave`)
}

/** 准备/取消准备 */
export function toggleReady(roomId: string) {
  return request.post<any, RoomInfo>(`/rooms/${roomId}/ready`)
}

/** 更新房间设置 */
export function updateRoomSettings(roomId: string, data: UpdateRoomData) {
  return request.patch<any, RoomInfo>(`/rooms/${roomId}/settings`, data)
}

/** 开始游戏 */
export function startGame(roomId: string) {
  return request.post<any, RoomInfo>(`/rooms/${roomId}/start`)
}

/** 切换角色（玩家 ↔ 观战者） */
export function switchRole(roomId: string, toSpectator: boolean) {
  return request.post<any, RoomInfo>(`/rooms/${roomId}/switch-role`, { to_spectator: toSpectator })
}

/** 房主重置房间（游戏结束后返回准备阶段） */
export function resetRoom(roomId: string) {
  return request.post<any, RoomInfo>(`/rooms/${roomId}/reset`)
}
