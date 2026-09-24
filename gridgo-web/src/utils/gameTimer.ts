/**
 * 对局倒计时（纯计算）
 *
 * 背景：后端的超时计时器在服务端内存中运行，状态快照里只带**倒计时初值**
 * （auction.countdown），不逐秒推送。因此界面上任何"剩余秒数"都必须由前端
 * 本地按秒递减，否则倒计时永远停在初值上（历史缺陷：界面上看不到倒计时）。
 *
 * 这里的时长常量与后端 engine.py 一一对应，改后端超时值时必须同步改这里。
 */

/** 与后端 engine.py / settings 对齐的倒计时初值（秒） */
export const TIMEOUT_SECONDS = {
  /** settings.GAME_TURN_TIMEOUT → 掷骰 / 自由行动阶段 */
  turn: 30,
  /** engine.DECISION_TIMEOUT_SECONDS → 等待购买决策阶段 */
  decision: 15,
  /** engine.AUCTION_TIMEOUT_SECONDS → 拍卖竞价轮 */
  auction: 15,
} as const

/**
 * 相位 → 该相位服务端计时器的初值（秒）；返回 null 表示该相位没有可展示的倒计时。
 * 仅覆盖服务端确实会启动计时器的相位（见 engine.py 的 _start_timer 调用点）。
 */
export function phaseCountdownSeconds(phase: string | null | undefined): number | null {
  switch (phase) {
    case 'WAIT_ROLL':
    case 'FREE_ACTION':
      return TIMEOUT_SECONDS.turn
    case 'WAIT_DECISION':
      return TIMEOUT_SECONDS.decision
    case 'AUCTION':
      return TIMEOUT_SECONDS.auction
    default:
      return null
  }
}

/**
 * 回合倒计时的重置键：相位 / 回合数 / 当前玩家 / 拍卖进度任一变化，
 * 都代表服务端重置了计时器，本地倒计时应重新从初值开始。
 */
export function countdownResetKey(input: {
  phase?: string | null
  turnNumber?: number | null
  currentPlayerIndex?: number | null
  auctionBid?: number | null
  auctionRounds?: number | null
}): string {
  return [
    input.phase ?? '-',
    input.turnNumber ?? '-',
    input.currentPlayerIndex ?? '-',
    input.auctionBid ?? '-',
    input.auctionRounds ?? '-',
  ].join('|')
}
