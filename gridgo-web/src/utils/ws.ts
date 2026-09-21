/**
 * WS 关闭码与连接状态文案（对齐 docs/PROJECT.md 7.2 关闭码表）
 */

export interface CloseCodeInfo {
  code: number
  label: string
  message: string
  needReauth: boolean
}

export const WS_CLOSE_CODES: Record<number, CloseCodeInfo> = {
  4001: { code: 4001, label: '认证失败', message: '登录状态已失效，请重新登录', needReauth: true },
  4002: { code: 4002, label: '初始化消息格式错误', message: '连接初始化失败（消息格式错误）', needReauth: false },
  4003: { code: 4003, label: '缺少 room_id', message: '连接初始化失败（缺少房间信息）', needReauth: false },
  4004: { code: 4004, label: '游戏初始化失败', message: '游戏初始化失败，请退出房间后重试', needReauth: false },
  4005: { code: 4005, label: '游戏状态不存在', message: '游戏状态不存在，可能已结束', needReauth: false },
  1000: { code: 1000, label: '正常关闭', message: '连接已关闭', needReauth: false },
  1001: { code: 1001, label: '端侧离开', message: '连接已断开', needReauth: false },
}

export function describeCloseCode(code: number): CloseCodeInfo {
  return (
    WS_CLOSE_CODES[code] ?? {
      code,
      label: `关闭码 ${code}`,
      message: '连接已断开，正在尝试重连',
      needReauth: false,
    }
  )
}

/** 重连档位文案（后端 system.player_reconnected.mode） */
export const RECONNECT_MODE_TEXT: Record<string, string> = {
  resume_incremental: '增量恢复',
  resume_snapshot: '快照恢复',
  left_game: '已离开对局',
}

export function reconnectModeText(mode: string): string {
  return RECONNECT_MODE_TEXT[mode] ?? mode
}
