import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useGameStore } from '@/stores/game'
import type { GameState, TradeOffer } from '@/types/game'

const TILE = {
  position: 1,
  name: '北京路',
  tile_type: 'PROPERTY',
  tile_group: 'A',
  group_color: '#ef5350',
  price: 1200,
  build_cost: 300,
  rent_0: 40,
  rent_1: 200,
  rent_2: 600,
  rent_3: 1400,
  rent_4: 1700,
  rent_5: 2000,
  tax_amount: null,
  tax_is_percent: null,
  owner_id: null,
  build_level: 0,
  is_mortgaged: false,
}

const START_TILE = {
  ...TILE,
  position: 0,
  name: '起点',
  tile_type: 'START',
  tile_group: null,
  price: null,
  owner_id: null,
}

const snapshot = (patch: Partial<GameState> = {}): GameState =>
  ({
    game_id: 'g1',
    room_id: 'r1',
    map_id: 'classic',
    turn_number: 1,
    current_player_index: 0,
    phase: 'WAIT_ROLL',
    players: [
      {
        user_id: 1,
        nickname: '张三',
        cash: 15000,
        position: 0,
        is_bankrupt: false,
        is_in_jail: false,
        jail_turns: 0,
        properties: [1],
        get_out_of_jail_cards: 0,
        is_ai: false,
        ai_difficulty: null,
        is_connected: true,
        consecutive_timeouts: 0,
      },
      {
        user_id: 2,
        nickname: '李四',
        cash: 15000,
        position: 0,
        is_bankrupt: false,
        is_in_jail: false,
        jail_turns: 0,
        properties: [],
        get_out_of_jail_cards: 1,
        is_ai: true,
        ai_difficulty: 'hard',
        is_connected: true,
        consecutive_timeouts: 0,
      },
    ],
    tiles: [START_TILE, TILE],
    dice: { values: [], total: 0, is_double: false },
    consecutive_doubles: 0,
    chance_deck: [],
    fate_deck: [],
    chance_discard: [],
    fate_discard: [],
    auction: null,
    station_rent: {},
    utility_multiplier: {},
    start_bonus: 200,
    jail_bail: 1500,
    max_build_level: 5,
    initial_cash: 15000,
    max_turns: 50,
    turn_timeout: 60,
    created_at: '2026-01-01T00:00:00Z',
    ...patch,
  }) as GameState

const trade = (patch: Partial<TradeOffer> = {}): TradeOffer => ({
  trade_id: 't1',
  from_id: 1,
  to_id: 2,
  offer_cash: 500,
  request_cash: 0,
  offer_properties: [],
  request_properties: [1],
  created_turn: 1,
  ...patch,
})

describe('game store 快照归约', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('applySnapshot 写入状态并推导我的玩家/我的地产', () => {
    const store = useGameStore()
    store.setCurrentUserId(1)
    store.applySnapshot(snapshot())

    expect(store.phase).toBe('WAIT_ROLL')
    expect(store.myPlayer?.nickname).toBe('张三')
    expect(store.myProperties.map((t) => t.position)).toEqual([1])
    expect(store.currentPlayer?.user_id).toBe(1)
  })

  it('回合与阶段门控：仅我的回合可掷骰', () => {
    const store = useGameStore()
    store.setCurrentUserId(2)
    store.applySnapshot(snapshot())
    expect(store.isMyTurn).toBe(false)
    expect(store.canRoll).toBe(false)

    store.setCurrentUserId(1)
    expect(store.canRoll).toBe(true)
  })

  it('观战者不可操作，拍卖/破产状态可读取', () => {
    const store = useGameStore()
    store.setCurrentUserId(1)
    store.isSpectator = true
    store.applySnapshot(
      snapshot({
        phase: 'AUCTION',
        auction: {
          tile_position: 1,
          start_price: 600,
          current_bid: 620,
          current_bidder_id: 2,
          bidders: [1, 2],
          countdown: 12,
        },
      }),
    )
    expect(store.canRoll).toBe(false)
    expect(store.activeAuction?.start_price).toBe(600)
    expect(store.activeAuction?.current_bidder_id).toBe(2)
  })

  it('非 WAIT_DECISION 快照会清理待决策', () => {
    const store = useGameStore()
    store.setCurrentUserId(1)
    store.applySnapshot(snapshot({ phase: 'WAIT_DECISION' }))
    store.pendingDecision = { type: 'property_unowned', tile_id: 1, tile_name: '北京路', price: 1200 }
    expect(store.canBuyProperty).toBe(true)

    store.applySnapshot(snapshot({ phase: 'FREE_ACTION' }))
    expect(store.pendingDecision).toBeNull()
  })

  it('锁消息不影响快照覆盖（state.update 幂等）', () => {
    const store = useGameStore()
    store.setCurrentUserId(1)
    store.applySnapshot(snapshot({ turn_number: 3 }))
    store.applySnapshot(snapshot({ turn_number: 4 }))
    expect(store.state?.turn_number).toBe(4)
  })
})

describe('game store 交易与重连', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('收到的报价入 incoming，我发出的入 outgoing', () => {
    const store = useGameStore()
    store.setCurrentUserId(1)
    store.applySnapshot(snapshot())

    store.receiveTradeOffer(trade(), false)
    store.receiveTradeOffer(trade({ trade_id: 't2', from_id: 1, to_id: 2 }), true)

    expect(store.incomingTrades.map((t) => t.trade_id)).toEqual(['t1'])
    expect(store.outgoingTrades.map((t) => t.trade_id)).toEqual(['t2'])
    expect(store.tradePartners.map((p) => p.user_id)).toEqual([2])
  })

  it('同一 trade_id 重复推送时原地更新而非重复插入', () => {
    const store = useGameStore()
    store.setCurrentUserId(1)
    store.receiveTradeOffer(trade({ offer_cash: 500 }), false)
    store.receiveTradeOffer(trade({ offer_cash: 900 }), false)

    expect(store.incomingTrades.length).toBe(1)
    expect(store.incomingTrades[0].offer_cash).toBe(900)
  })

  it('resolveTrade 同时清理收发两侧', () => {
    const store = useGameStore()
    store.setCurrentUserId(1)
    store.receiveTradeOffer(trade(), false)
    store.receiveTradeOffer(trade({ trade_id: 't2' }), true)
    store.resolveTrade('t1')
    store.resolveTrade('t2')

    expect(store.incomingTrades).toEqual([])
    expect(store.outgoingTrades).toEqual([])
  })

  it('破产玩家会从交易列表与可交易对象中剔除', () => {
    const store = useGameStore()
    store.setCurrentUserId(1)
    store.applySnapshot(snapshot())
    store.receiveTradeOffer(trade(), false)

    const next = snapshot()
    next.players[1].is_bankrupt = true
    store.applySnapshot(next)

    expect(store.incomingTrades).toEqual([])
    expect(store.tradePartners).toEqual([])
  })

  it('system.player_reconnected 写入重连提示并翻译档位文案', () => {
    const store = useGameStore()
    store.setReconnectNotice({ player_id: 2, mode: 'resume_snapshot', offline_seconds: 42 })

    expect(store.reconnectNotice?.playerId).toBe(2)
    expect(store.reconnectNotice?.modeText).toBe('快照恢复')
    expect(store.reconnectNotice?.offlineSeconds).toBe(42)
  })
})

describe('game store 日志与重置', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('日志超过 200 条时裁剪为最近 100 条', () => {
    const store = useGameStore()
    for (let i = 0; i < 199; i += 1) store.addLog('system', `log-${i}`)
    expect(store.logs.length).toBe(199)

    // 满 200 条不裁剪
    store.addLog('system', 'log-199')
    expect(store.logs.length).toBe(200)
    expect(store.logs[0].message).toBe('log-0')

    // 第 201 条触发裁剪：仅保留最近 100 条（log-101 ~ log-200）
    store.addLog('system', 'log-200')
    expect(store.logs.length).toBe(100)
    expect(store.logs[0].message).toBe('log-101')
    expect(store.logs[store.logs.length - 1].message).toBe('log-200')

    for (let i = 201; i < 205; i += 1) store.addLog('system', `log-${i}`)
    expect(store.logs.length).toBe(104)
    expect(store.logs[0].message).toBe('log-101')
    expect(store.logs[store.logs.length - 1].message).toBe('log-204')
    expect(store.logs.every((l) => l.type === 'system')).toBe(true)
  })

  it('reset 清空对局态与交易/重连残留', () => {
    const store = useGameStore()
    store.setCurrentUserId(1)
    store.applySnapshot(snapshot())
    store.receiveTradeOffer(trade(), false)
    store.setReconnectNotice({ player_id: 2, mode: 'left_game', offline_seconds: 5 })

    store.reset()

    expect(store.state).toBeNull()
    expect(store.connected).toBe(false)
    expect(store.incomingTrades).toEqual([])
    expect(store.reconnectNotice).toBeNull()
    expect(store.currentUserId).toBe(0)
    expect(store.logs).toEqual([])
  })
})
