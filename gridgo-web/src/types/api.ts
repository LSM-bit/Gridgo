/**
 * REST 接口类型定义（与后端 app/schemas 对齐）
 */

// ─── 排行榜（GET /leaderboard，游客可见） ───

export interface LeaderboardEntry {
  rank: number
  user_id: number
  username: string
  nickname: string
  avatar: string | null
  score: number
  total_games: number
  total_wins: number
  best_rank: number | null
  win_streak: number
}

export interface LeaderboardResponse {
  total: number
  limit: number
  offset: number
  items: LeaderboardEntry[]
}

// ─── 好友（/friends） ───

export interface FriendItem {
  user_id: number
  username: string
  nickname: string
  avatar: string | null
  score: number
  total_games: number
  total_wins: number
  friendship_id: number
}

export interface FriendRequestItem {
  request_id: number
  user_id: number
  username: string
  nickname: string
  avatar: string | null
  created_at: string | null
}
