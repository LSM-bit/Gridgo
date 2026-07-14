import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { gameWS } from '@/api/ws'

// ─── 类型定义 ───

export interface PlayerState {
  user_id: number
  nickname: string
  cash: number
  position: number
  is_bankrupt: boolean
  is_in_jail: boolean
  jail_turns: number
  properties: number[]
  get_out_of_jail_cards: number
  is_ai: boolean
  ai_difficulty: string | null
  is_connected: boolean
  consecutive_timeouts: number
}

export interface TileState {
  position: number
  name: string
  tile_type: string
  tile_group: string | null
  group_color: string | null
  price: number | null
  build_cost: number | null
  rent_0: number | null
  rent_1: number | null
  rent_2: number | null
  rent_3: number | null
  rent_4: number | null
  rent_5: number | null
  tax_amount: number | null
  tax_is_percent: boolean | null
  owner_id: number | null
  build_level: number
  is_mortgaged: boolean
}

export interface DiceState {
  values: number[]
  total: number
  is_double: boolean
}

export interface AuctionState {
  tile_position: number
  start_price: number
  current_bid: number
  current_bidder_id: number | null
  bidders: number[]
  countdown: number
}

export type GamePhase =
  | 'TURN_START'
  | 'WAIT_ROLL'
  | 'ROLLING'
  | 'MOVING'
  | 'TILE_EFFECT'
  | 'WAIT_DECISION'
  | 'FREE_ACTION'
  | 'TURN_END'
  | 'AUCTION'
  | 'BANKRUPTCY'
  | 'GAME_OVER'

export interface GameState {
  game_id: string
  room_id: string
  map_id: string
  turn_number: number
  current_player_index: number
  phase: GamePhase
  players: PlayerState[]
  tiles: TileState[]
  dice: DiceState
  consecutive_doubles: number
  chance_deck: string[]
  fate_deck: string[]
  chance_discard: string[]
  fate_discard: string[]
  auction: AuctionState | null
  station_rent: Record<number, number>
  utility_multiplier: Record<number, number>
  start_bonus: number
  jail_bail: number
  max_build_level: number
  initial_cash: number
  max_turns: number
  turn_timeout: number
  created_at: string
}

export interface GameLog {
  type: string
  message: string
  timestamp: number
}

export interface CardDisplay {
  card_type: 'CHANCE' | 'FATE'
  card_id: string
  card_name: string
  effect_type: string
  effect_value: number | null
  description: string
  player_id: number
}

export const useGameStore = defineStore('game', () => {
  // ─── 核心状态 ───

  const state = ref<GameState | null>(null)
  const connected = ref(false)
  const logs = ref<GameLog[]>([])
  const isSpectator = ref(false)  // 是否观战者
  const pendingDecision = ref<{
    type: string // 'buy' | 'auction' | ...
    tile_id: number
    tile_name: string
    price: number
  } | null>(null)

  const activeCard = ref<CardDisplay | null>(null)

  // ─── 计算属性 ───

  const myPlayer = computed(() => {
    // 由外部设置 currentUserId
    return state.value?.players.find((p) => p.user_id === currentUserId.value)
  })

  const currentPlayer = computed(() => {
    if (!state.value) return null
    return state.value.players[state.value.current_player_index] || null
  })

  const isMyTurn = computed(() => {
    return !isSpectator.value && currentPlayer.value?.user_id === currentUserId.value
  })

  const phase = computed(() => state.value?.phase ?? '')

  const isGameOver = computed(() => state.value?.phase === 'GAME_OVER')

  const canRoll = computed(() => {
    return !isSpectator.value && isMyTurn.value && (phase.value === 'WAIT_ROLL')
  })

  const canBuyProperty = computed(() => {
    return !isSpectator.value && isMyTurn.value && phase.value === 'WAIT_DECISION' && pendingDecision.value?.type === 'property_unowned'
  })

  const canAct = computed(() => {
    return !isSpectator.value && isMyTurn.value && phase.value === 'FREE_ACTION'
  })

  const isInJail = computed(() => myPlayer.value?.is_in_jail ?? false)

  const hasJailCard = computed(() => (myPlayer.value?.get_out_of_jail_cards ?? 0) > 0)

  const myProperties = computed(() => {
    if (!state.value || !myPlayer.value) return []
    return myPlayer.value.properties.map((pos) => state.value!.tiles[pos])
  })

  // ─── 当前用户 ID（由 Game.vue 设置） ───

  const currentUserId = ref(0)

  const setCurrentUserId = (id: number) => {
    currentUserId.value = id
  }

  // ─── WebSocket 操作 ───

  const sendRollDice = () => {
    gameWS.send('game.roll_dice')
  }

  const sendBuyProperty = (tileId: number) => {
    gameWS.send('game.buy_property', { tile_id: tileId })
  }

  const sendDeclineProperty = (tileId: number) => {
    gameWS.send('game.decline_property', { tile_id: tileId })
  }

  const sendSkipProperty = (tileId: number) => {
    gameWS.send('game.skip_property', { tile_id: tileId })
  }

  const sendAuctionBid = (amount: number) => {
    gameWS.send('game.auction_bid', { amount })
  }

  const sendBuild = (tileId: number) => {
    gameWS.send('game.build', { tile_id: tileId })
  }

  const sendDemolish = (tileId: number) => {
    gameWS.send('game.demolish', { tile_id: tileId })
  }

  const sendMortgage = (tileId: number) => {
    gameWS.send('game.mortgage', { tile_id: tileId })
  }

  const sendRedeem = (tileId: number) => {
    gameWS.send('game.redeem', { tile_id: tileId })
  }

  const sendEndTurn = () => {
    gameWS.send('game.end_turn')
  }

  const sendJailPayBail = () => {
    gameWS.send('game.jail_pay_bail')
  }

  const sendJailUseCard = () => {
    gameWS.send('game.jail_use_card')
  }

  // ─── 状态更新 ───

const applySnapshot = (snapshot: GameState) => {
  state.value = snapshot
  // 如果阶段已不再是等待决策，自动清除 pendingDecision
  if (snapshot.phase !== 'WAIT_DECISION') {
    pendingDecision.value = null
  }
  // 注意：不再根据 phase 自动关闭卡片弹窗
  // 卡片弹窗由用户手动点击关闭（dismissCard）
}

  const addLog = (type: string, message: string) => {
    logs.value.push({ type, message, timestamp: Date.now() })
    // 限制日志条数
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

  const reset = () => {
    state.value = null
    connected.value = false
    logs.value = []
    pendingDecision.value = null
    activeCard.value = null
    currentUserId.value = 0
    isSpectator.value = false
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
    // 方法
    setCurrentUserId,
    applySnapshot,
    addLog,
    clearPendingDecision,
    showCard,
    dismissCard,
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
  }
})
