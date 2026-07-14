/**
 * 对局回放状态模拟引擎
 *
 * 职责：
 *   1. 基于初始状态和已解析的操作列表，逐步模拟每步操作后的游戏状态
 *   2. 在最后一步使用后端保存的 final_snapshot 覆盖模拟状态，确保最终状态与真实一致
 *   3. 供 Replay 页面逐步回放
 *
 * 注意：actions 的解码已在后端完成，前端只需处理状态模拟
 */

import type { ReplayInitState, ReplayStep, ReplayTurn, ReplayFinalState } from '@/api/replay'
import type { PlayerState, TileState, DiceState } from '@/stores/game'

// ─── 状态模拟引擎 ───

/** 回放快照：某一步操作后的游戏状态 */
export interface ReplaySnapshot {
  turn_number: number
  current_player_idx: number
  players: PlayerState[]
  tiles: TileState[]
  dice: DiceState
  phase: string
  logs: string[]
}

/** 根据初始状态创建一个模拟状态快照 */
export function createInitialSnapshot(initState: ReplayInitState): ReplaySnapshot {
  const players: PlayerState[] = initState.players.map((p) => ({
    user_id: p.user_id,
    nickname: p.nickname,
    cash: initState.initial_cash,
    position: p.start_position,
    is_bankrupt: false,
    is_in_jail: false,
    jail_turns: 0,
    properties: [],
    get_out_of_jail_cards: 0,
    is_ai: p.is_ai,
    ai_difficulty: null,
    is_connected: true,
    consecutive_timeouts: 0,
  }))

  const tiles: TileState[] = initState.tiles.map((t) => ({
    position: t.pos,
    name: t.name,
    tile_type: t.type,
    tile_group: t.group,
    group_color: null,
    price: t.price,
    build_cost: null,
    rent_0: null, rent_1: null, rent_2: null, rent_3: null, rent_4: null, rent_5: null,
    tax_amount: null, tax_is_percent: null,
    owner_id: null,
    build_level: 0,
    is_mortgaged: false,
  }))

  return {
    turn_number: 0,
    current_player_idx: 0,
    players,
    tiles,
    dice: { values: [0, 0], total: 0, is_double: false },
    phase: 'WAIT_ROLL',
    logs: [],
  }
}

/** 根据后端 final_snapshot 创建真实的最终状态快照 */
export function createFinalSnapshot(
  lastSimulatedSnapshot: ReplaySnapshot,
  finalState: ReplayFinalState,
): ReplaySnapshot {
  // 基于 lastSimulated 的结构，用 final_state 的真实数据覆盖
  const players: PlayerState[] = finalState.players.map((fp) => {
    // 从模拟快照中找对应玩家，保留模拟快照中未在 final_state 中保存的字段
    const simPlayer = lastSimulatedSnapshot.players[fp.idx]
    return {
      user_id: fp.user_id,
      nickname: fp.nickname,
      cash: fp.cash,
      position: fp.position,
      is_bankrupt: fp.is_bankrupt,
      is_in_jail: fp.is_in_jail,
      jail_turns: simPlayer?.jail_turns ?? 0,
      properties: [...fp.properties],
      get_out_of_jail_cards: fp.get_out_of_jail_cards,
      is_ai: fp.is_ai,
      ai_difficulty: simPlayer?.ai_difficulty ?? null,
      is_connected: true,
      consecutive_timeouts: 0,
    }
  })

  // 用 final_state 的 tiles 真实数据更新棋盘
  const tiles: TileState[] = lastSimulatedSnapshot.tiles.map((simTile) => {
    // 找到 final_state 中对应位置的 tile
    const ft = finalState.tiles.find((t) => t.pos === simTile.position)
    if (ft) {
      return {
        ...simTile,
        owner_id: ft.owner_id,
        build_level: ft.build_level,
        is_mortgaged: ft.is_mortgaged,
      }
    }
    return { ...simTile }
  })

  return {
    turn_number: finalState.turn_number,
    current_player_idx: lastSimulatedSnapshot.current_player_idx,
    players,
    tiles,
    dice: { ...lastSimulatedSnapshot.dice },
    phase: 'GAME_OVER',
    logs: [...lastSimulatedSnapshot.logs, '游戏结束'],
  }
}

/** 对快照应用一个操作，返回新快照 */
export function applyStep(snapshot: ReplaySnapshot, step: ReplayStep): ReplaySnapshot {
  // 深拷贝
  const s: ReplaySnapshot = {
    turn_number: snapshot.turn_number,
    current_player_idx: snapshot.current_player_idx,
    players: snapshot.players.map((p) => ({ ...p, properties: [...p.properties] })),
    tiles: snapshot.tiles.map((t) => ({ ...t })),
    dice: { ...snapshot.dice },
    phase: snapshot.phase,
    logs: [...snapshot.logs],
  }

  const pIdx = step.player_idx
  const player = s.players[pIdx]
  if (!player) return s

  s.current_player_idx = pIdx

  switch (step.action) {
    case 'ROLL': {
      const [d1, d2] = step.params as [number, number]
      s.dice = { values: [d1, d2], total: d1 + d2, is_double: d1 === d2 }
      s.phase = 'ROLLING'
      break
    }
    case 'MOVE': {
      const pos = step.params[0] as number
      player.position = pos
      s.phase = 'MOVING'
      break
    }
    case 'BUY': {
      // 注意：后端在 BUY 之外还额外记录了 MONEY 步骤来扣减购买金额
      // 所以这里不再自动扣钱，避免双重扣减
      const pos = step.params[0] as number
      const tile = s.tiles[pos]
      if (tile) {
        tile.owner_id = player.user_id
        if (!player.properties.includes(pos)) {
          player.properties.push(pos)
        }
      }
      break
    }
    case 'DECLINE':
    case 'SKIP':
      break
    case 'BUILD': {
      // 后端在 BUILD 之外还额外记录了 MONEY 步骤来扣钱
      const pos = step.params[0] as number
      const tile = s.tiles[pos]
      if (tile) {
        tile.build_level++
      }
      break
    }
    case 'DEMOLISH': {
      // 后端在 DEMOLISH 之外还额外记录了 MONEY 步骤来加钱
      const pos = step.params[0] as number
      const tile = s.tiles[pos]
      if (tile && tile.build_level > 0) {
        tile.build_level--
      }
      break
    }
    case 'MORTGAGE': {
      // 后端在 MORTGAGE 之外还额外记录了 MONEY 步骤来加钱
      const pos = step.params[0] as number
      const tile = s.tiles[pos]
      if (tile) {
        tile.is_mortgaged = true
      }
      break
    }
    case 'REDEEM': {
      // 后端在 REDEEM 之外还额外记录了 MONEY 步骤来扣钱
      const pos = step.params[0] as number
      const tile = s.tiles[pos]
      if (tile) {
        tile.is_mortgaged = false
      }
      break
    }
    case 'JAIL': {
      const method = step.params[0] as string
      // 注意：后端在 JAIL('b') 之外还额外记录了 MONEY 步骤来扣减保释金
      // 所以这里不再自动扣钱，避免双重扣减
      if (method === 'b' || method === 'c' || method === 'r') {
        player.is_in_jail = false
        player.jail_turns = 0
      }
      break
    }
    case 'MONEY': {
      const amount = step.params[0] as number
      player.cash += amount
      break
    }
    case 'RENT': {
      // 租金已在 MONEY 步骤中处理
      break
    }
    case 'CARD':
      // 卡片效果已由后续的 MOVE/MONEY 步骤处理
      break
    case 'AUCTION_BID':
      // 拍卖细节不影响基本状态
      break
    case 'END_TURN': {
      s.phase = 'TURN_END'
      break
    }
    case 'EXTRA_ROLL': {
      s.phase = 'WAIT_ROLL'
      break
    }
  }

  // 添加日志
  s.logs.push(step.description)

  return s
}

/** 预计算所有步骤的快照列表（用于快速跳转）
 *
 * 最后一步会使用 final_state 的真实数据覆盖模拟状态，
 * 确保回放结束时的棋盘状态与服务器保存的最终状态完全一致。
 */
export function computeAllSnapshots(
  initState: ReplayInitState,
  turns: ReplayTurn[],
  finalState?: ReplayFinalState,
): { snapshots: ReplaySnapshot[]; totalSteps: number } {
  let snapshot = createInitialSnapshot(initState)
  const snapshots: ReplaySnapshot[] = [snapshot]

  for (const turn of turns) {
    snapshot = { ...snapshot, turn_number: turn.turn_number, phase: 'WAIT_ROLL', logs: [...snapshot.logs] }
    for (const step of turn.steps) {
      snapshot = applyStep(snapshot, step)
      snapshots.push(snapshot)
    }
  }

  // 使用 final_state 覆盖最后一步的模拟状态
  if (finalState) {
    const finalSnapshot = createFinalSnapshot(snapshot, finalState)
    // 替换最后一个快照
    snapshots[snapshots.length - 1] = finalSnapshot
  }

  return { snapshots, totalSteps: snapshots.length - 1 }
}
