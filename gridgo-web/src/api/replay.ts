/**
 * 对局回放相关 API
 */

import request from './rest'

// ─── 类型定义 ───

export interface ReplayPlayer {
  rank: number
  user_id: number
  nickname: string
  total_assets: number
  settlement_amount: number
  is_bankrupt: boolean
  is_ai: boolean
}

export interface ReplayInitPlayer {
  idx: number
  user_id: number
  nickname: string
  is_ai: boolean
  start_position: number
}

export interface ReplayInitTile {
  pos: number
  name: string
  type: string
  group: string | null
  price: number | null
}

export interface ReplayInitState {
  map_id: string
  initial_cash: number
  start_bonus: number
  jail_bail: number
  max_turns: number
  players: ReplayInitPlayer[]
  tiles: ReplayInitTile[]
}

export interface ReplayStep {
  player_idx: number
  action: string
  params: (number | string)[]
  description: string
}

export interface ReplayTurn {
  turn_number: number
  steps: ReplayStep[]
}

export interface ReplayFinalPlayer {
  idx: number
  user_id: number
  nickname: string
  cash: number
  position: number
  is_bankrupt: boolean
  is_in_jail: boolean
  properties: number[]
  get_out_of_jail_cards: number
  is_ai: boolean
}

export interface ReplayFinalTile {
  pos: number
  name: string
  type: string
  group: string | null
  price: number | null
  owner_id: number | null
  build_level: number
  is_mortgaged: boolean
}

export interface ReplayFinalState {
  turn_number: number
  end_reason: string
  rankings: any[]
  players: ReplayFinalPlayer[]
  tiles: ReplayFinalTile[]
}

export interface ReplayData {
  init_state: ReplayInitState
  turns: ReplayTurn[]
  final_state: ReplayFinalState
}

export interface GameReplayResponse {
  code: number
  data: {
    game_id: number
    room_id: string
    map_id: string
    total_turns: number
    winner_id: number | null
    end_reason: string
    created_at: string | null
    players: ReplayPlayer[]
    replay: ReplayData
  }
}

export interface GameHistoryItem {
  game_id: number
  room_id: string
  map_id: string
  total_turns: number
  end_reason: string
  created_at: string | null
  my_rank: number
  my_settlement: number
  winner_id: number | null
  players: ReplayPlayer[]
}

// ─── API 方法 ───

/** 获取对局回放数据 */
export function getGameReplay(gameId: number) {
  return request.get<any, GameReplayResponse>(`/games/replay/${gameId}`)
}

/** 获取用户对局历史 */
export function getUserGameHistory(userId: number, limit = 20, offset = 0) {
  return request.get<any, { code: number; data: GameHistoryItem[]; total: number }>(
    `/games/history/${userId}`,
    { params: { limit, offset } },
  )
}
