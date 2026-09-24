import request from './rest'
import type { GameState } from '@/types/game'

/**
 * 拉取对局权威快照（GET /api/v1/games/{room_id}/state，后端 app/api/v1/game.py）。
 *
 * 用途：WS 推送静默时的自愈通道——用 HTTP 快照刷新界面，避免"状态卡死"。
 * 该接口返回 { code, data }，data 即与 WS state.snapshot 同构的完整状态。
 */
export async function fetchGameState(roomId: string): Promise<GameState | null> {
  const res = (await request.get(`/games/${roomId}/state`)) as unknown as { data?: GameState } | null
  return res?.data ?? null
}
