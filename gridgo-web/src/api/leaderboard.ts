/**
 * 排行榜 API（GET /leaderboard，游客可见）
 */

import request from './rest'
import type { LeaderboardEntry, LeaderboardResponse } from '@/types/api'

export type { LeaderboardEntry, LeaderboardResponse }

export function getLeaderboard(params: { limit?: number; offset?: number } = {}) {
  return request.get<any, LeaderboardResponse>('/leaderboard', { params })
}
