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
    sendTradeOffer,
    sendTradeAccept,
    sendTradeReject,
  }
})
