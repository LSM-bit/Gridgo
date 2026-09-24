import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { gameWS } from '@/api/ws'
import { reconnectModeText } from '@/utils/ws'
import type { CardDisplay, GameState, PlayerReconnectedEvent, TradeOffer, TradeOfferPayload } from '@/types/game'
import type { GameLog } from '@/types/game'

export * from '@/types/game'

export interface PendingDecision {
  type: string
  tile_id: number
  tile_name: string
  price: number
}

export interface ReconnectNotice {
  playerId: number
  mode: string
  modeText: string
  offlineSeconds: number
  at: number
}

/** 「强制退出本局」结果（game.quit_result） */
export interface QuitGameResult {
  ok: boolean
  reason: string | null
  aiDifficulty: string | null
  at: number
}

/** 房间解散通知（room.dissolved，房间内已无真人玩家） */
export interface RoomDissolvedNotice {
  roomId: string
  reason: string
  at: number
}

/** 服务端拒绝/异常提示（WS system.error） */
export interface ServerErrorNotice {
  code: number
  message: string
  action: string | null
  at: number
}

/** 连接异常提示（WS 关闭码语义） */
export interface ConnectionNotice {
  code: number
  label: string
  message: string
  /** 服务端已拒绝本次对局上下文，重连无意义（需人工退出/重进） */
  fatal: boolean
  at: number
}

/** 交易结果提示（收到报价 / 达成 / 被拒） */
export interface TradeNotice {
  kind: 'received' | 'completed' | 'rejected'
  tradeId: string
  text: string
  at: number
}

/** 拍卖结果提示（出价成功 / 被超越 / 成交 / 流拍） */
export interface AuctionNotice {
  kind: 'bid_accepted' | 'outbid' | 'sold' | 'unsold'
  text: string
  at: number
}

/** 致命关闭码（与 api/ws.ts FATAL_CLOSE_CODES 对齐，4001 由登录态失效流程单独处理） */
const FATAL_CLOSE_CODES = new Set([4002, 4003, 4004, 4005])

/** 退出本局失败原因 → 中文文案 */
const QUIT_FAIL_TEXT: Record<string, string> = {
  no_state: '对局尚未就绪',
  game_over: '对局已结束',
  not_human_player: '你已不是本局真人玩家',
  bankrupt: '你已破产，无需退出',
}

export const quitFailText = (reason: string | null | undefined) =>
  (reason ? QUIT_FAIL_TEXT[reason] : undefined) ?? '操作未被接受'

export const useGameStore = defineStore('game', () => {
  // ─── 核心状态 ───

  const state = ref<GameState | null>(null)
  const connected = ref(false)
  const logs = ref<GameLog[]>([])
  const isSpectator = ref(false) // 是否观战者
  const pendingDecision = ref<PendingDecision | null>(null)
  const activeCard = ref<CardDisplay | null>(null)

  /** 收到的交易报价（待我处理） */
  const incomingTrades = ref<TradeOffer[]>([])
  /** 我发出的交易报价 */
  const outgoingTrades = ref<TradeOffer[]>([])
  /** 最近一次重连提示（system.player_reconnected） */
  const reconnectNotice = ref<ReconnectNotice | null>(null)
  /** 强制退出本局结果（game.quit_result），供页面提示与跳转 */
  const quitResult = ref<QuitGameResult | null>(null)
  /** 房间解散通知（room.dissolved） */
  const roomDissolved = ref<RoomDissolvedNotice | null>(null)
  /** 服务端拒绝/异常提示（system.error），页面消费后调用 clearServerError */
  const serverError = ref<ServerErrorNotice | null>(null)
  /** 连接异常提示（WS 关闭码），页面消费后调用 clearConnectionNotice */
  const connectionNotice = ref<ConnectionNotice | null>(null)
  /** 交易结果提示，页面消费后调用 clearTradeNotice */
  const tradeNotice = ref<TradeNotice | null>(null)
  /** 拍卖结果提示，页面消费后调用 clearAuctionNotice */
  const auctionNotice = ref<AuctionNotice | null>(null)

  // ─── 当前用户 ID（由 useGame 设置） ───

  const currentUserId = ref(0)

  // ─── 计算属性 ───

  const myPlayer = computed(() => state.value?.players.find((p) => p.user_id === currentUserId.value) ?? null)

  const currentPlayer = computed(() => {
    if (!state.value) return null
    return state.value.players[state.value.current_player_index] || null
  })

  const isMyTurn = computed(() => !isSpectator.value && currentPlayer.value?.user_id === currentUserId.value)

  const phase = computed(() => state.value?.phase ?? '')

  const isGameOver = computed(() => state.value?.phase === 'GAME_OVER')

  const canRoll = computed(() => !isSpectator.value && isMyTurn.value && phase.value === 'WAIT_ROLL')

  const canBuyProperty = computed(
    () => !isSpectator.value && isMyTurn.value && phase.value === 'WAIT_DECISION' && pendingDecision.value?.type === 'property_unowned',
  )

  const canAct = computed(() => !isSpectator.value && isMyTurn.value && phase.value === 'FREE_ACTION')

  const isInJail = computed(() => myPlayer.value?.is_in_jail ?? false)

  const hasJailCard = computed(() => (myPlayer.value?.get_out_of_jail_cards ?? 0) > 0)

  const myProperties = computed(() => {
    if (!state.value || !myPlayer.value) return []
    return myPlayer.value.properties.map((pos) => state.value!.tiles[pos]).filter(Boolean)
  })

  const activeAuction = computed(() => state.value?.auction ?? null)

  /** 可交易对象：除我以外的未破产玩家 */
  const tradePartners = computed(() =>
    (state.value?.players ?? []).filter((p) => p.user_id !== currentUserId.value && !p.is_bankrupt),
  )

  // ─── 状态更新 ───

  const setCurrentUserId = (id: number) => {
    currentUserId.value = id
  }

  const applySnapshot = (snapshot: GameState) => {
    state.value = snapshot
    if (snapshot.phase !== 'WAIT_DECISION') {
      pendingDecision.value = null
    }
    // 已不在交易环节的存在于快照外的报价直接清空（服务端 pending_trades 权威）
    const alive = new Set(snapshot.players.filter((p) => !p.is_bankrupt).map((p) => p.user_id))
    incomingTrades.value = incomingTrades.value.filter((t) => alive.has(t.from_id) && alive.has(t.to_id))
    outgoingTrades.value = outgoingTrades.value.filter((t) => alive.has(t.from_id) && alive.has(t.to_id))
  }

  const addLog = (type: string, message: string) => {
    logs.value.push({ type, message, timestamp: Date.now() })
    if (logs.value.length > 200) {
      logs.value = logs.value.slice(-100)
    }
  }

  const clearPendingDecision = () => {
    pendingDecision.value = null
  }

  const showCard = (card: CardDisplay) => {
    activeCard.value = card
  }

  const dismissCard = () => {
    activeCard.value = null
  }

  // ─── 交易状态 ───

  const upsertTrade = (trade: TradeOffer, mine: boolean) => {
    const list = mine ? outgoingTrades : incomingTrades
    const idx = list.value.findIndex((t) => t.trade_id === trade.trade_id)
    if (idx > -1) list.value[idx] = trade
    else list.value.push(trade)
  }

  const receiveTradeOffer = (trade: TradeOffer, mine: boolean) => {
    upsertTrade(trade, mine)
  }

  const resolveTrade = (tradeId: string) => {
    incomingTrades.value = incomingTrades.value.filter((t) => t.trade_id !== tradeId)
    outgoingTrades.value = outgoingTrades.value.filter((t) => t.trade_id !== tradeId)
  }

  const setReconnectNotice = (payload: PlayerReconnectedEvent) => {
    reconnectNotice.value = {
      playerId: payload.player_id,
      mode: payload.mode,
      modeText: reconnectModeText(payload.mode),
      offlineSeconds: payload.offline_seconds,
      at: Date.now(),
    }
  }

  const setQuitResult = (payload: { ok: boolean; reason?: string | null; ai_difficulty?: string | null }) => {
    quitResult.value = {
      ok: !!payload.ok,
      reason: payload.reason ?? null,
      aiDifficulty: payload.ai_difficulty ?? null,
      at: Date.now(),
    }
  }

  const clearQuitResult = () => {
    quitResult.value = null
  }

  const setRoomDissolved = (payload: { room_id: string; reason: string }) => {
    roomDissolved.value = { roomId: payload.room_id, reason: payload.reason, at: Date.now() }
  }

  // ─── 操作反馈（服务端拒绝 / 连接异常 / 交易结果） ───

  const setServerError = (payload: { code?: number; message?: string; action?: string | null }) => {
    serverError.value = {
      code: Number(payload.code ?? 0),
      message: payload.message || '操作未被服务端接受',
      action: payload.action ?? null,
      at: Date.now(),
    }
  }

  const clearServerError = () => {
    serverError.value = null
  }

  const setConnectionNotice = (info: { code: number; label: string; message: string }) => {
    connectionNotice.value = {
      code: info.code,
      label: info.label,
      message: info.message,
      fatal: FATAL_CLOSE_CODES.has(info.code),
      at: Date.now(),
    }
  }

  const clearConnectionNotice = () => {
    connectionNotice.value = null
  }

  const setTradeNotice = (payload: { kind: TradeNotice['kind']; tradeId: string; text: string }) => {
    tradeNotice.value = { kind: payload.kind, tradeId: payload.tradeId, text: payload.text, at: Date.now() }
  }

  const clearTradeNotice = () => {
    tradeNotice.value = null
  }

  const setAuctionNotice = (payload: { kind: AuctionNotice['kind']; text: string }) => {
    auctionNotice.value = { kind: payload.kind, text: payload.text, at: Date.now() }
  }

  const clearAuctionNotice = () => {
    auctionNotice.value = null
  }

  // ─── WebSocket 操作 ───

  const sendRollDice = () => gameWS.send('game.roll_dice')
  const sendBuyProperty = (tileId: number) => gameWS.send('game.buy_property', { tile_id: tileId })
  const sendDeclineProperty = (tileId: number) => gameWS.send('game.decline_property', { tile_id: tileId })
  const sendSkipProperty = (tileId: number) => gameWS.send('game.skip_property', { tile_id: tileId })
  const sendAuctionBid = (amount: number) => gameWS.send('game.auction_bid', { amount })
  const sendBuild = (tileId: number) => gameWS.send('game.build', { tile_id: tileId })
  const sendDemolish = (tileId: number) => gameWS.send('game.demolish', { tile_id: tileId })
  const sendMortgage = (tileId: number) => gameWS.send('game.mortgage', { tile_id: tileId })
  const sendRedeem = (tileId: number) => gameWS.send('game.redeem', { tile_id: tileId })
  const sendEndTurn = () => gameWS.send('game.end_turn')
  const sendJailPayBail = () => gameWS.send('game.jail_pay_bail')
  const sendJailUseCard = () => gameWS.send('game.jail_use_card')
  /** 强制退出本局：退出后本局角色由 AI 接管继续对局 */
  const sendQuitGame = () => gameWS.send('game.quit_game')

  const sendTradeOffer = (payload: TradeOfferPayload) => gameWS.sendTradeOffer(payload)
  const sendTradeAccept = (tradeId: string) => gameWS.sendTradeAccept(tradeId)
  const sendTradeReject = (tradeId: string) => gameWS.sendTradeReject(tradeId)

  const reset = () => {
    state.value = null
    connected.value = false
    logs.value = []
    pendingDecision.value = null
    activeCard.value = null
    currentUserId.value = 0
    isSpectator.value = false
    incomingTrades.value = []
    outgoingTrades.value = []
    reconnectNotice.value = null
    quitResult.value = null
    roomDissolved.value = null
    serverError.value = null
    connectionNotice.value = null
    tradeNotice.value = null
    auctionNotice.value = null
  }

  return {
    // 状态
    state,
    connected,
    logs,
    pendingDecision,
    activeCard,
    currentUserId,
    isSpectator,
    incomingTrades,
    outgoingTrades,
    reconnectNotice,
    quitResult,
    roomDissolved,
    serverError,
    connectionNotice,
    tradeNotice,
    auctionNotice,
    // 计算属性
    myPlayer,
    currentPlayer,
    isMyTurn,
    phase,
    isGameOver,
    canRoll,
    canBuyProperty,
    canAct,
    isInJail,
    hasJailCard,
    myProperties,
    activeAuction,
    tradePartners,
    // 方法
    setCurrentUserId,
    applySnapshot,
    addLog,
    clearPendingDecision,
    showCard,
    dismissCard,
    receiveTradeOffer,
    resolveTrade,
    setReconnectNotice,
    setQuitResult,
    clearQuitResult,
    setRoomDissolved,
    setServerError,
    clearServerError,
    setConnectionNotice,
    clearConnectionNotice,
    setTradeNotice,
    clearTradeNotice,
    setAuctionNotice,
    clearAuctionNotice,
    reset,
    // WebSocket 操作
    sendRollDice,
    sendBuyProperty,
    sendDeclineProperty,
    sendSkipProperty,
    sendAuctionBid,
    sendBuild,
    sendDemolish,
    sendMortgage,
    sendRedeem,
    sendEndTurn,
    sendJailPayBail,
    sendJailUseCard,
    sendQuitGame,
    sendTradeOffer,
    sendTradeAccept,
    sendTradeReject,
  }
})
