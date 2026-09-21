/**
 * useGame —— 对局编排层
 *
 * 负责：WS 生命周期 + 全量 game.* 事件归约到 store、对局派生算力、
 * 交易/拍卖/重连等新增能力的接入，并把"动画时机"暴露给页面层。
 */

import { computed, ref } from 'vue'
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
  const gameOver = ref<GameOverPayload | null>(null)
  const showGameOver = ref(false)
  const gameRecordId = ref<number | null>(null)

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
  }

  const bindHandlers = () => {
    if (bound.value) return
    bound.value = true

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

    ws.on<AuctionStartEvent>('game.auction_start', (d) =>
      gameStore.addLog('auction', `${d.tile_name} 进入拍卖，起拍价 ¥${d.start_price}（最小加价 ¥${d.min_increment}）`),
    )

    ws.on<{ player_id: number; amount: number }>('game.auction_bid', (d) =>
      gameStore.addLog('auction', `${playerName(d.player_id)} 出价 ¥${d.amount}`),
    )

    ws.on<{ winner_id: number | null; price: number }>('game.auction_end', (d) =>
      gameStore.addLog('auction', d.winner_id ? `${playerName(d.winner_id)} 以 ¥${d.price} 拍得` : '拍卖流拍'),
    )

    // ─── 新增：交易 ───

    ws.on('game.trade_offer', acceptTradePayload)
    ws.on('game.trade_received', acceptTradePayload)

    ws.on<{ trade_id: string }>('game.trade_completed', (d) => {
      gameStore.resolveTrade(d.trade_id)
      gameStore.addLog('trade', '交易达成')
    })

    ws.on<{ trade_id: string; reason?: string }>('game.trade_reject', (d) => {
      gameStore.resolveTrade(d.trade_id)
      gameStore.addLog('trade', d.reason ? `交易未达成：${d.reason}` : '交易被拒绝')
    })

    // ─── 连接状态 ───

    ws.on<{ player_id: number }>('system.player_connected', (d) => gameStore.addLog('system', `${playerName(d.player_id)} 重新连接`))

    ws.on<{ player_id: number }>('system.player_disconnected', (d) => gameStore.addLog('system', `${playerName(d.player_id)} 断线`))

    ws.on<PlayerReconnectedEvent>('system.player_reconnected', (d) => {
      gameStore.setReconnectNotice(d)
      gameStore.addLog('system', `${playerName(d.player_id)} ${reconnectModeText(d.mode)}（离线 ${d.offline_seconds}s）`)
    })

    ws.on('system.pong', () => {
      gameStore.connected = true
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

  // ─── 生命周期 ───

  const start = (rid?: string) => {
    const target = rid ?? roomId.value
    if (!target) return
    roomId.value = target
    gameStore.setCurrentUserId(userStore.userId)
    if (options.isSpectator !== undefined) gameStore.isSpectator = options.isSpectator
    bindHandlers()
    ws.connect(target)
  }

  const stop = () => {
    ws.disconnect()
    anim.killAll()
    gameStore.reset()
    bound.value = false
  }

  const endReasonText = computed(() => (gameOver.value ? END_REASON_TEXT[gameOver.value.end_reason] ?? gameOver.value.end_reason : ''))

  const sendTradeOffer = (payload: Parameters<typeof gameStore.sendTradeOffer>[0]) => gameStore.sendTradeOffer(payload)

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
    // 操作
    sendTradeOffer,
  }
}
