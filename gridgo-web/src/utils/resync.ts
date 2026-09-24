/**
 * 状态同步看门狗（纯判定）
 *
 * 背景：界面完全由 WS 推送（state.snapshot / state.update）驱动。一旦服务端
 * 因异常停止推送（或推送在链路中丢失），而前端不做兜底，界面就会停在旧的
 * 快照上——表现为"状态卡死"（按钮无响应、倒计时/阶段不再变化）。
 *
 * 这里的判定用于触发一次 REST 权威快照拉取自愈：WS 静默超过阈值即允许拉取，
 * 并带冷却时间避免在服务端真的卡住时形成请求风暴。
 */

/** WS 静默多久（毫秒）即认为界面可能已陈旧 */
export const RESYNC_STALE_MS = 8000

/** 两次自愈拉取之间的最小间隔（毫秒） */
export const RESYNC_COOLDOWN_MS = 5000

export interface ResyncInput {
  /** 当前时间戳（毫秒） */
  now: number
  /** 最近一次收到带状态的事件的时间戳（毫秒） */
  lastEventAt: number
  /** 最近一次发起自愈拉取的时间戳（毫秒），未发起过传 0 */
  lastResyncAt: number
  /** 对局是否已结束（结束后不再需要自愈） */
  isGameOver: boolean
  /** 当前是否已有快照可展示（没有快照时首帧由 WS 负责，不抢跑） */
  hasState: boolean
}

/** 是否需要发起一次 REST 快照自愈 */
export function shouldResync(input: ResyncInput): boolean {
  if (input.isGameOver || !input.hasState) return false
  if (input.now - input.lastResyncAt < RESYNC_COOLDOWN_MS) return false
  return input.now - input.lastEventAt >= RESYNC_STALE_MS
}
