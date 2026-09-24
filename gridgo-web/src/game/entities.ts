/**
 * Canvas 渲染实体：地块实体与棋子实体
 *
 * 实体只负责"几何 + 绘制参数"，绘制指令由 renderer 统一执行，
 * 便于 GSAP 对实体坐标做补间后重绘。
 */

import { BOARD_GRID, tileBg, tileGridPos, tokenColor } from './board'
import type { GameState, PlayerState, TileState } from '@/types/game'

export interface Rect {
  x: number
  y: number
  w: number
  h: number
}

export interface TokenPoint {
  x: number
  y: number
}

export class TileEntity {
  readonly position: number
  readonly state: TileState
  readonly rect: Rect

  constructor(state: TileState, boardSize: number, gap = 2) {
    this.state = state
    this.position = state.position
    const { row, col } = tileGridPos(state.position)
    const cell = boardSize / BOARD_GRID
    this.rect = {
      x: (col - 1) * cell + gap,
      y: (row - 1) * cell + gap,
      w: cell - gap * 2,
      h: cell - gap * 2,
    }
  }

  get isProperty(): boolean {
    return this.state.tile_type === 'PROPERTY' || this.state.tile_type === 'STATION' || this.state.tile_type === 'UTILITY'
  }

  get bg(): string {
    return tileBg(this.state.tile_type)
  }

  contains(x: number, y: number): boolean {
    const { x: rx, y: ry, w, h } = this.rect
    return x >= rx && x <= rx + w && y >= ry && y <= ry + h
  }

  /** 棋子落位锚点（底边居中） */
  get anchor(): TokenPoint {
    return { x: this.rect.x + this.rect.w / 2, y: this.rect.y + this.rect.h - this.rect.h * 0.18 }
  }
}

export class PlayerTokenEntity {
  readonly user_id: number
  readonly nickname: string
  readonly is_ai: boolean
  readonly color: string
  position: number
  x: number
  y: number
  radius: number

  constructor(player: PlayerState, order: number, point: TokenPoint, cell: number) {
    this.user_id = player.user_id
    this.nickname = player.nickname
    this.is_ai = player.is_ai
    this.color = tokenColor(order)
    this.position = player.position
    this.x = point.x
    this.y = point.y
    this.radius = Math.max(5, cell * 0.16)
  }

  get initial(): string {
    return this.is_ai ? 'AI' : (this.nickname.charAt(0) || '?')
  }

  snapshot(): TokenPoint {
    return { x: this.x, y: this.y }
  }
}

/** 同一格多棋子横向错开，避免重叠 */
export function tokenSlot(base: TokenPoint, index: number, count: number, cell: number): TokenPoint {
  if (count <= 1) return base
  const step = Math.min(cell * 0.22, 14)
  const offset = (index - (count - 1) / 2) * step
  return { x: base.x + offset, y: base.y - Math.abs(offset) * 0.15 }
}

/** 由快照构建棋子实体，并尽量沿用既有实体（保留动画中的坐标） */
export function syncTokens(
  state: GameState,
  previous: Map<number, PlayerTokenEntity>,
  tileAnchors: Map<number, TokenPoint>,
  cell: number,
): Map<number, PlayerTokenEntity> {
  const next = new Map<number, PlayerTokenEntity>()
  const byPosition = new Map<number, PlayerState[]>()
  state.players.forEach((p) => {
    const list = byPosition.get(p.position) ?? []
    list.push(p)
    byPosition.set(p.position, list)
  })

  state.players.forEach((player, order) => {
    const anchor = tileAnchors.get(player.position) ?? { x: 0, y: 0 }
    const peers = byPosition.get(player.position) ?? [player]
    const index = peers.findIndex((p) => p.user_id === player.user_id)
    const point = tokenSlot(anchor, index, peers.length, cell)
    const existing = previous.get(player.user_id)
    if (existing) {
      // 关键修复：位置变化时必须同步刷新像素坐标，
      // 否则棋子会停留在旧格（drawTokens 只读 token.x/y，不再读取 position）
      existing.position = player.position
      existing.x = point.x
      existing.y = point.y
      next.set(player.user_id, existing)
      return
    }
    next.set(player.user_id, new PlayerTokenEntity(player, order, point, cell))
  })
  return next
}
