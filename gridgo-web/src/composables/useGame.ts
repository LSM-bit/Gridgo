/**
 * useGame —— 对局编排层
 *
 * 负责：WS 生命周期 + 全量 game.* 事件归约到 store、对局派生算力、
 * 交易/拍卖/重连等新增能力的接入，并把"动画时机"暴露给页面层。
 */

import { computed, ref } from 'vue'
import { fetchGameState } from '@/api/game'
import { shouldResync } from '@/utils/resync'
import { useGameStore } from '@/stores/game'
import { useRoomStore } from '@/stores/room'
import { useUserStore } from '@/stores/user'
import { reconnectModeText } from '@/utils/ws'
import type {
  AuctionStartEvent,
  CardDrawnPayload,
  DiceResultPayload,
  GameOverPayload,
  GameState,
  MoneyChangePayload,
  PlayerMovedPayload,
  PlayerReconnectedEvent,
  PropertyBoughtPayload,
  RentPaidPayload,
  TileEventPayload,
  TradeOffer,
  TradeOfferEvent,
  TurnChangePayload,
} from '@/types/game'
import { useAnimation } from './useAnimation'
import { useWebSocket } from './useWebSocket'

export interface UseGameOptions {
  roomId?: string
  isSpectator?: boolean
}

/** 状态看门狗轮询间隔（毫秒） */
const WATCHDOG_INTERVAL_MS = 2000

const PHASE_TEXT: Record<string, string> = {
  TURN_START: '回合开始',
  WAIT_ROLL: '等待掷骰',
  ROLLING: '掷骰中',
  MOVING: '移动中',
  TILE_EFFECT: '地块效果',
  WAIT_DECISION: '等待决策',
  FREE_ACTION: '自由行动',
  TURN_END: '回合结束',
  AUCTION: '拍卖中',
  BANKRUPTCY: '破产处理',
  GAME_OVER: '游戏结束',
}

const JAIL_RELEASE_TEXT: Record<string, string> = {
  double: '掷出双数',
  bail: '支付保释金',
  card: '使用免罪卡',
  forced_bail: '强制保释',
}

const END_REASON_TEXT: Record<string, string> = {
  last_standing: '仅剩一人',
  turn_limit: '达到回合上限',
  vote_end: '投票结束',
}

export function useGame(options: UseGameOptions = {}) {
  const gameStore = useGameStore()
  const roomStore = useRoomStore()
  const userStore = useUserStore()
  const ws = useWebSocket()
  const anim = useAnimation()

  const roomId = ref(options.roomId ?? '')
  const bound = ref(false)
  /** 拍卖当前领先者（用于"出价被超越"提示，服务端不单独下发被超越事件） */
  let lastAuctionLeader: number | null = null
  const gameOver = ref<GameOverPayload | null>(null)
  const showGameOver = ref(false)
  const gameRecordId = ref<number | null>(null)

  // ─── 状态同步看门狗 ───
  // 界面完全由 WS 推送（state.snapshot / state.update）驱动；一旦推送停摆，
  // 界面就会停在旧快照上（表现为"状态卡死"）。这里记录最近一次带状态推送的时间，
  // 超时即用 REST 权威快照自愈，保证对局界面不会永久冻结。
  const lastEventAt = ref(Date.now())
  const lastResyncAt = ref(0)
  const syncing = ref(false)
  let watchdogTimer: ReturnType<typeof setInterval> | null = null

  const playerName = (userId: number) => gameStore.state?.players.find((p) => p.user_id === userId)?.nickname ?? '未知'
  const tileName = (position: number) => gameStore.state?.tiles[position]?.name ?? `#${position}`

  // ─── 派生算力 ───

  const phaseText = computed(() => PHASE_TEXT[gameStore.phase] ?? gameStore.phase)

  const phaseTagType = computed(() => {
    if (gameStore.isMyTurn) return 'success'
    if (gameStore.phase === 'GAME_OVER') return 'danger'
    return 'info'
  })

  const waitText = computed(() => {
    if (gameStore.isSpectator) return `观战中 · ${gameStore.currentPlayer?.nickname ?? ''} 的回合`
    if (gameStore.isGameOver) return '游戏已结束'
    if (!gameStore.isMyTurn) return `${gameStore.currentPlayer?.nickname ?? ''} 的回合...`
    return '等待中...'
  })

  const canBuild = (tile: { build_cost: number | null }) =>
    (gameStore.myPlayer?.cash ?? 0) >= (tile.build_cost ?? 0)

  const buildableProperties = computed(() => {
    const maxLevel = gameStore.state?.max_build_level ?? 5
    return gameStore.myProperties.filter((t) => t.tile_type === 'PROPERTY' && t.build_level < maxLevel && !t.is_mortgaged)
  })

  // ─── WS 事件归约 ───

  const acceptTradePayload = (raw: unknown) => {
    const payload = (raw ?? {}) as TradeOfferEvent & { offer?: TradeOffer }
    const offer: TradeOffer | undefined = payload.offer ?? (raw as TradeOffer)
    if (!offer?.trade_id) return
    const mine = offer.from_id === userStore.userId
    gameStore.receiveTradeOffer(offer, mine)
    gameStore.addLog('trade', mine ? '交易报价已发出，等待对方确认' : `${playerName(offer.from_id)} 向你发起交易`)
    if (!mine) {
      gameStore.setTradeNotice({
        kind: 'received',
        tradeId: offer.trade_id,
        text: `${playerName(offer.from_id)} 向你发起交易，请在交易面板中处理`,
      })
    }
  }

  const bindHandlers = () => {
    if (bound.value) return
    bound.value = true

    // 活性探针：任何 state.* / game.* 推送都说明服务端在正常推进对局，
    // 用于喂饱看门狗（看门狗超时后会用 REST 快照自愈，避免界面永久卡死）。
    ws.on<{ type?: string }>('*', (msg) => {
      const type = (msg as { type?: string } | null)?.type ?? ''
      if (type.startsWith('state.') || type.startsWith('game.')) lastEventAt.value = Date.now()
    })

    ws.on<GameState & { is_spectator?: boolean }>('state.snapshot', (data) => {
      const { is_spectator: isSpectator, ...snapshot } = data
      if (isSpectator !== undefined) gameStore.isSpectator = isSpectator
      gameStore.applySnapshot(snapshot as GameState)
      gameStore.connected = true
    })

    ws.on<GameState>('state.update', (data) => gameStore.applySnapshot(data))

    ws.on<TurnChangePayload>('game.turn_change', (d) =>
      gameStore.addLog('turn', `第 ${d.turn_number} 回合：${d.current_player_nickname}`),
    )

    ws.on<DiceResultPayload>('game.dice_result', (d) => {
      gameStore.addLog('dice', `${playerName(d.player_id)} 掷出 [${d.dice[0]}][${d.dice[1]}] = ${d.total}${d.is_double ? ' (双数!)' : ''}`)
      anim.playDice(d.dice)
    })

    ws.on<PlayerMovedPayload>('game.player_moved', (d) => {
      if (d.passed_go) gameStore.addLog('money', `${playerName(d.player_id)} 经过起点，获得 ¥${gameStore.state?.start_bonus ?? 200}`)
      // 逐格补间：把棋子从起点沿棋盘一格一格走到终点（steps 由后端给出）
      if (typeof d.steps === 'number' && d.steps > 0) {
        anim.playTokenMoveByPositions(d.player_id, d.from, d.steps)
      }
    })

    ws.on<TileEventPayload>('game.tile_event', (d) => {
      if (d.event_type === 'property_unowned') {
        gameStore.pendingDecision = { type: 'property_unowned', tile_id: d.tile_id, tile_name: d.tile_name, price: d.price ?? 0 }
        gameStore.addLog('tile', `${playerName(d.player_id)} 停在 ${d.tile_name}，可购买 (¥${d.price})`)
      }
    })

    ws.on<PropertyBoughtPayload>('game.property_bought', (d) => {
      gameStore.addLog('buy', `${playerName(d.player_id)} 购买了 ${d.tile_name} (¥${d.price})`)
      gameStore.clearPendingDecision()
    })

    ws.on<RentPaidPayload>('game.rent_paid', (d) =>
      gameStore.addLog('rent', `${playerName(d.from_id)} 向 ${playerName(d.to_id)} 支付租金 ¥${d.amount} (${d.tile_name})`),
    )

    ws.on<CardDrawnPayload>('game.card_drawn', (d) => {
      gameStore.addLog('card', `${playerName(d.player_id)} 抽到${d.card_type === 'CHANCE' ? '机会' : '命运'}卡：${d.card_name}`)
      gameStore.showCard({ ...d })
    })

    ws.on<{ player_id: number; tile_name: string; level: number }>('game.building_built', (d) =>
      gameStore.addLog('build', `${playerName(d.player_id)} 在 ${d.tile_name} 建造至 Lv.${d.level}`),
    )

    ws.on<{ player_id: number; tile_name: string }>('game.building_demolished', (d) =>
      gameStore.addLog('build', `${playerName(d.player_id)} 拆除了 ${d.tile_name} 的房屋`),
    )

    ws.on<{ player_id: number; tile_id: number }>('game.property_mortgaged', (d) =>
      gameStore.addLog('mortgage', `${playerName(d.player_id)} 抵押了 ${tileName(d.tile_id)}`),
    )

    ws.on<{ player_id: number; tile_id: number }>('game.property_redeemed', (d) =>
      gameStore.addLog('mortgage', `${playerName(d.player_id)} 赎回了 ${tileName(d.tile_id)}`),
    )

    ws.on<{ player_id: number; tile_id: number }>('game.property_declined', (d) => {
      gameStore.addLog('tile', `${playerName(d.player_id)} 放弃了 ${tileName(d.tile_id)}`)
      gameStore.clearPendingDecision()
    })

    ws.on<{ player_id: number; reason: string }>('game.jail_sent', (d) =>
      gameStore.addLog('jail', `${playerName(d.player_id)} 入狱 (${d.reason})`),
    )

    ws.on<{ player_id: number; method: string }>('game.jail_released', (d) =>
      gameStore.addLog('jail', `${playerName(d.player_id)} 出狱 (${JAIL_RELEASE_TEXT[d.method] ?? d.method})`),
    )

    ws.on<{ player_id: number }>('game.player_bankrupt', (d) => gameStore.addLog('bankrupt', `${playerName(d.player_id)} 破产了！`))

    ws.on<MoneyChangePayload>('game.money_change', (d) =>
      gameStore.addLog('money', `${playerName(d.player_id)} ${d.amount > 0 ? '+' : ''}¥${d.amount} (${d.reason})`),
    )

    ws.on<{ player_id: number; total_cards: number }>('game.get_out_of_jail_card', (d) =>
      gameStore.addLog('card', `${playerName(d.player_id)} 获得免罪卡（共 ${d.total_cards} 张）`),
    )

    ws.on<{ player_id: number; tile_name: string; amount: number }>('game.tax_paid', (d) =>
      gameStore.addLog('tax', `${playerName(d.player_id)} 支付 ${d.tile_name} ¥${d.amount}`),
    )

    ws.on<{ player_id: number }>('game.extra_roll', (d) =>
      gameStore.addLog('dice', `${playerName(d.player_id)} 掷出双数，可以再掷一次！`),
    )

    // ─── 新增：拍卖 ───

    ws.on<AuctionStartEvent>('game.auction_start', (d) => {
      lastAuctionLeader = null
      gameStore.addLog('auction', `${d.tile_name} 进入拍卖，起拍价 ¥${d.start_price}（最小加价 ¥${d.min_increment}）`)
    })

    ws.on<{ player_id: number; amount: number }>('game.auction_bid', (d) =>
      gameStore.addLog('auction', `${playerName(d.player_id)} 出价 ¥${d.amount}`),
    )

    // 服务端每次出价（真人 / AI）实际广播的事件；出价同时会重置拍卖倒计时
    ws.on<{ tile_id: number; current_bid: number; bidder_id: number | null; min_increment: number }>(
      'game.auction_update',
      (d) => {
        const bidder = d.bidder_id ?? null
        gameStore.addLog('auction', `${playerName(bidder ?? 0)} 出价 ¥${d.current_bid}`)
        // 出价反馈：自己出价成功 / 自己原领先被他人超越（避免"点了出价没反应"）
        if (bidder === userStore.userId) {
          gameStore.setAuctionNotice({ kind: 'bid_accepted', text: `出价成功：¥${d.current_bid}，你当前领先` })
        } else if (bidder !== null && lastAuctionLeader === userStore.userId) {
          gameStore.setAuctionNotice({
            kind: 'outbid',
            text: `你的出价被 ${playerName(bidder)} 超越，当前最高 ¥${d.current_bid}`,
          })
        }
        lastAuctionLeader = bidder
      },
    )

    ws.on<{ winner_id: number | null; final_price?: number; price?: number; start_price?: number }>('game.auction_end', (d) => {
      const price = d.final_price ?? d.price ?? 0
      const auction = gameStore.activeAuction
      const tile = auction ? tileName(auction.tile_position) : '该地块'
      gameStore.addLog('auction', d.winner_id ? `${playerName(d.winner_id)} 以 ¥${price} 拍得` : '拍卖流拍')
      if (d.winner_id === null || d.winner_id === undefined) {
        gameStore.setAuctionNotice({ kind: 'unsold', text: `拍卖流拍：${tile} 无人应价，仍归银行` })
      } else if (d.winner_id === userStore.userId) {
        gameStore.setAuctionNotice({ kind: 'sold', text: `拍卖成交：你以 ¥${price} 拍得 ${tile}` })
      } else {
        gameStore.setAuctionNotice({ kind: 'sold', text: `拍卖成交：${playerName(d.winner_id)} 以 ¥${price} 拍得 ${tile}` })
      }
      lastAuctionLeader = null
    })

    // ─── 新增：交易 ───

    ws.on('game.trade_offer', acceptTradePayload)
    ws.on('game.trade_received', acceptTradePayload)

    ws.on<{ trade_id: string }>('game.trade_completed', (d) => {
      gameStore.resolveTrade(d.trade_id)
      gameStore.addLog('trade', '交易达成')
      gameStore.setTradeNotice({ kind: 'completed', tradeId: d.trade_id, text: '交易达成，资产已按报价完成交换' })
    })

    ws.on<{ trade_id: string; reason?: string }>('game.trade_reject', (d) => {
      gameStore.resolveTrade(d.trade_id)
      gameStore.addLog('trade', d.reason ? `交易未达成：${d.reason}` : '交易被拒绝')
      gameStore.setTradeNotice({
        kind: 'rejected',
        tradeId: d.trade_id,
        text: d.reason ? `交易未达成：${d.reason}` : '交易被对方拒绝或已撤回',
      })
    })

    // ─── 连接状态 ───

    ws.on<{ player_id: number }>('system.player_connected', (d) => gameStore.addLog('system', `${playerName(d.player_id)} 重新连接`))

    ws.on<{ player_id: number }>('system.player_disconnected', (d) => gameStore.addLog('system', `${playerName(d.player_id)} 断线`))

    // ─── 强制退出本局 / 房间解散 ───

    ws.on<{ player_id: number; nickname?: string; ai_difficulty?: string | null }>('system.player_quit', (d) =>
      gameStore.addLog('system', `${d.nickname ?? playerName(d.player_id)} 强制退出本局，由 AI 接管继续对局`),
    )

    ws.on<{ ok: boolean; reason: string | null; ai_difficulty?: string | null }>('game.quit_result', (d) => {
      gameStore.setQuitResult(d)
    })

    ws.on<{ room_id: string; reason: string }>('room.dissolved', (d) => {
      gameStore.addLog('system', '房间已解散：房间内已无真人玩家')
      gameStore.setRoomDissolved(d)
    })

    ws.on<PlayerReconnectedEvent>('system.player_reconnected', (d) => {
      gameStore.setReconnectNotice(d)
      gameStore.addLog('system', `${playerName(d.player_id)} ${reconnectModeText(d.mode)}（离线 ${d.offline_seconds}s）`)
    })

    ws.on('system.pong', () => {
      gameStore.connected = true
    })

    // ─── 操作被拒绝 / 连接异常（用户可见反馈） ───

    // 服务端对非法操作的显式拒绝（不再静默丢弃，也不断开连接）
    ws.on<{ code?: number; message?: string; action?: string | null }>('system.error', (d) => {
      const message = d?.message || '操作未被服务端接受'
      gameStore.setServerError({ code: Number(d?.code ?? 0), message, action: d?.action ?? null })
      gameStore.addLog('system', `操作未生效：${message}`)
    })

    // 连接关闭：把关闭码语义化后交给页面提示（区分「可重连」与「必须人工退出」）
    ws.onClose((info) => {
      gameStore.connected = false
      gameStore.setConnectionNotice(info)
    })

    ws.on<GameOverPayload>('game.over', (d) => {
      gameStore.addLog('over', '游戏结束！')
      gameOver.value = d
      gameRecordId.value = d.game_record_id ?? null
      showGameOver.value = true
      roomStore.setGameOverData({
        end_reason: d.end_reason,
        winner_id: d.winner_id,
        rankings: d.rankings,
        total_turns: d.total_turns,
      })
    })
  }

  // ─── 状态自愈 ───

  /**
   * 用 REST 权威快照刷新界面。
   * 当 WS 静默（推送停摆 / 服务端卡住 / 重连后漏推）时，作为兜底通道把界面重新拉回正轨。
   */
  const resyncFromServer = async (): Promise<boolean> => {
    if (!roomId.value) return false
    syncing.value = true
    try {
      const snapshot = await fetchGameState(roomId.value)
      if (!snapshot) return false
      gameStore.applySnapshot(snapshot)
      gameStore.connected = true
      lastEventAt.value = Date.now()
      return true
    } catch {
      // 自愈失败不打断对局：保留当前界面，等待 WS 自动重连后再次尝试
      return false
    } finally {
      syncing.value = false
    }
  }

  const stopWatchdog = () => {
    if (watchdogTimer !== null) {
      clearInterval(watchdogTimer)
      watchdogTimer = null
    }
  }

  const startWatchdog = () => {
    stopWatchdog()
    watchdogTimer = setInterval(() => {
      const now = Date.now()
      const needResync = shouldResync({
        now,
        lastEventAt: lastEventAt.value,
        lastResyncAt: lastResyncAt.value,
        isGameOver: gameStore.isGameOver,
        hasState: !!gameStore.state,
      })
      if (!needResync) return
      lastResyncAt.value = now
      void resyncFromServer()
    }, WATCHDOG_INTERVAL_MS)
  }

  // ─── 生命周期 ───

  const start = (rid?: string) => {
    const target = rid ?? roomId.value
    if (!target) return
    roomId.value = target
    gameStore.setCurrentUserId(userStore.userId)
    if (options.isSpectator !== undefined) gameStore.isSpectator = options.isSpectator
    bindHandlers()
    lastEventAt.value = Date.now()
    startWatchdog()
    ws.connect(target)
  }

  const stop = () => {
    stopWatchdog()
    ws.disconnect()
    anim.killAll()
    gameStore.reset()
    lastAuctionLeader = null
    bound.value = false
  }

  const endReasonText = computed(() => (gameOver.value ? END_REASON_TEXT[gameOver.value.end_reason] ?? gameOver.value.end_reason : ''))

  const sendTradeOffer = (payload: Parameters<typeof gameStore.sendTradeOffer>[0]) => gameStore.sendTradeOffer(payload)

  // 底层 WS 连接态（页面用于禁用无效操作 / 展示关闭原因）
  const wsConnected = ws.connected
  const lastClose = ws.lastClose

  return {
    // store 透传（页面模板直接用）
    store: gameStore,
    roomStore,
    userStore,
    // 状态
    roomId,
    gameOver,
    showGameOver,
    gameRecordId,
    endReasonText,
    syncing,
    lastEventAt,
    wsConnected,
    lastClose,
    // 派生
    phaseText,
    phaseTagType,
    waitText,
    canBuild,
    buildableProperties,
    playerName,
    tileName,
    // 动画
    anim,
    // 生命周期
    start,
    stop,
    // 状态自愈
    resyncFromServer,
    startWatchdog,
    stopWatchdog,
    // 操作
    sendTradeOffer,
  }
}
