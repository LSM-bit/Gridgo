/**
 * 游戏领域类型定义（与后端 app/game/schemas.py 对齐）
 */

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

export interface PendingDecision {
  type: string
  tile_id: number
  tile_name: string
  price: number
}

// ─── 交易（docs/GAME_FLOW.md 9.2 交易系统） ───

export interface TradeOffer {
  trade_id: string
  from_id: number
  to_id: number
  offer_cash: number
  request_cash: number
  offer_properties: number[]
  request_properties: number[]
  created_turn: number
}

export interface TradeOfferPayload {
  target_id: number
  offer: { cash: number; properties: number[] }
  request: { cash: number; properties: number[] }
}

export interface TradeOfferEvent {
  trade_id: string
  from_id: number
  to_id: number
  offer: TradeOffer
}

export interface TradeReceivedEvent {
  trade_id: string
  from_id: number
  offer: TradeOffer
}

export interface TradeCompletedEvent {
  trade_id: string
  from_id: number
  to_id: number
  cash: Record<string, number>
}

export interface TradeRejectEvent {
  trade_id: string
  from_id: number
  to_id: number
  reason: string
}

export interface AuctionStartEvent {
  tile_id: number
  tile_name: string
  start_price: number
  min_increment: number
  bidders: number[]
  countdown: number
}

// ─── 聊天（chat.message / chat.send） ───

export interface ChatMessagePayload {
  id: string
  room_id: string
  user_id: number
  nickname: string
  is_ai: boolean
  content: string
  created_at: string
}

// ─── 重连（system.player_reconnected） ───

export type ReconnectMode = 'resume_incremental' | 'resume_snapshot' | 'left_game'

export interface PlayerReconnectedEvent {
  player_id: number
  mode: ReconnectMode
  offline_seconds: number
}

export interface GameOverPayload {
  end_reason: string
  winner_id: number | null
  rankings: Array<{
    rank: number
    user_id: number
    nickname: string
    total_assets: number
    is_ai: boolean
    is_bankrupt: boolean
  }>
  total_turns: number
  game_record_id: number | null
}

export interface DiceResultPayload {
  player_id: number
  dice: number[]
  total: number
  is_double: boolean
}

export interface PlayerMovedPayload {
  player_id: number
  from_position: number
  to_position: number
  passed_go: boolean
}

export interface TileEventPayload {
  player_id: number
  tile_id: number
  tile_name: string
  event_type: string
  price?: number
  amount?: number
}

export interface MoneyChangePayload {
  player_id: number
  amount: number
  reason: string
}

export interface CardDrawnPayload {
  player_id: number
  card_type: 'CHANCE' | 'FATE'
  card_id: string
  card_name: string
  effect_type: string
  effect_value: number | null
  description: string
}

export interface TurnChangePayload {
  turn_number: number
  current_player_index: number
  current_player_nickname: string
}

export interface PlayerRefPayload {
  player_id: number
}

export interface TileRefPayload {
  player_id: number
  tile_id: number
}

export interface PropertyBoughtPayload {
  player_id: number
  tile_id: number
  tile_name: string
  price: number
}

export interface RentPaidPayload {
  from_id: number
  to_id: number
  amount: number
  tile_name: string
}

export interface JailReleasedPayload {
  player_id: number
  method: string
}

export interface JailSentPayload {
  player_id: number
  reason: string
}

export interface TaxPaidPayload {
  player_id: number
  tile_name: string
  amount: number
}

export interface BuildPayload {
  player_id: number
  tile_id: number
  tile_name: string
  level: number
}
