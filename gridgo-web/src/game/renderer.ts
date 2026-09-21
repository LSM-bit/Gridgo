/**
 * Canvas 2D 棋盘渲染层
 *
 * 职责：维护地块/棋子实体、按帧绘制棋盘、命中测试、导出可交互坐标。
 * 所有动画通过修改实体坐标 + 重新 render() 实现（GSAP 补间见 animations.ts）。
 */

import { BOARD_GRID, DEFAULT_GROUP_COLORS, tileGridPos } from './board'
import { TileEntity, PlayerTokenEntity, syncTokens } from './entities'
import type { TokenPoint } from './entities'
import type { GameState } from '@/types/game'

export interface RenderOptions {
  currentUserId?: number
  /** 当前玩家可操作的地块（金色高亮） */
  highlight?: number[]
  /** 选中的地块 */
  selected?: number | null
  /** 棋盘中心文案 */
  centerTitle?: string
  centerLines?: string[]
  /** 动画中的棋子坐标覆盖（user_id → 像素坐标） */
  tokenOverrides?: Map<number, TokenPoint>
}

const FONT_FAMILY = '"Microsoft YaHei", "PingFang SC", system-ui, sans-serif'

export class BoardRenderer {
  private canvas: HTMLCanvasElement
  private ctx: CanvasRenderingContext2D
  private size = 0

  private state: GameState | null = null
  private opts: RenderOptions = {}
  private groupColors = new Map<string, string>()

  tiles: TileEntity[] = []
  tokens = new Map<number, PlayerTokenEntity>()

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('无法获取 Canvas 2D 上下文')
    this.ctx = ctx
  }

  get boardSize(): number {
    return this.size
  }

  get cell(): number {
    return this.size / BOARD_GRID
  }

  /** 设置 CSS 尺寸（像素），内部按 devicePixelRatio 放大保证清晰度 */
  setSize(size: number, dpr = window.devicePixelRatio || 1): void {
    this.size = size
    this.canvas.width = Math.round(size * dpr)
    this.canvas.height = Math.round(size * dpr)
    this.canvas.style.width = `${size}px`
    this.canvas.style.height = `${size}px`
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  }

  setState(state: GameState): Map<number, PlayerTokenEntity> {
    this.state = state
    this.groupColors = buildGroupColors(state)
    this.tiles = state.tiles.map((t) => new TileEntity(t, this.size))
    const anchors = this.anchors()
    this.tokens = syncTokens(state, this.tokens, anchors, this.cell)
    return this.tokens
  }

  setOptions(opts: RenderOptions): void {
    this.opts = { ...this.opts, ...opts }
  }

  /** 每个地块的棋子锚点 */
  anchors(): Map<number, TokenPoint> {
    const map = new Map<number, TokenPoint>()
    this.tiles.forEach((t) => map.set(t.position, t.anchor))
    return map
  }

  /** 命中测试（客户端坐标 → 地块 position） */
  tileAt(clientX: number, clientY: number): number | null {
    const rect = this.canvas.getBoundingClientRect()
    if (!rect.width) return null
    const scale = this.size / rect.width
    const x = (clientX - rect.left) * scale
    const y = (clientY - rect.top) * scale
    const hit = this.tiles.find((t) => t.contains(x, y))
    return hit ? hit.position : null
  }

  private ownerColor(userId: number): string {
    const index = this.state?.players.findIndex((p) => p.user_id === userId) ?? -1
    return DEFAULT_GROUP_COLORS[(index < 0 ? 0 : index) % DEFAULT_GROUP_COLORS.length]
  }

  private groupColor(tile: TileEntity): string {
    const key = tile.state.tile_group ?? tile.state.tile_type
    if (tile.state.group_color) return tile.state.group_color
    return this.groupColors.get(key) ?? '#cfd8dc'
  }

  render(): void {
    if (!this.size) return
    const ctx = this.ctx
    ctx.clearRect(0, 0, this.size, this.size)
    this.drawBackground()
    this.drawCenter()
    this.tiles.forEach((tile) => this.drawTile(tile))
    this.drawTokens()
    this.drawLegend()
  }

  private drawBackground(): void {
    const ctx = this.ctx
    const cell = this.cell
    ctx.fillStyle = '#eef3f8'
    ctx.fillRect(0, 0, this.size, this.size)
    ctx.strokeStyle = '#dbe3ec'
    ctx.lineWidth = 1
    for (let i = 0; i <= BOARD_GRID; i += 1) {
      ctx.beginPath()
      ctx.moveTo(i * cell, 0)
      ctx.lineTo(i * cell, this.size)
      ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(0, i * cell)
      ctx.lineTo(this.size, i * cell)
      ctx.stroke()
    }
  }

  private roundRect(x: number, y: number, w: number, h: number, r: number): void {
    const ctx = this.ctx
    const radius = Math.min(r, w / 2, h / 2)
    ctx.beginPath()
    ctx.moveTo(x + radius, y)
    ctx.lineTo(x + w - radius, y)
    ctx.quadraticCurveTo(x + w, y, x + w, y + radius)
    ctx.lineTo(x + w, y + h - radius)
    ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h)
    ctx.lineTo(x + radius, y + h)
    ctx.quadraticCurveTo(x, y + h, x, y + h - radius)
    ctx.lineTo(x, y + radius)
    ctx.quadraticCurveTo(x, y, x + radius, y)
    ctx.closePath()
  }

  private drawCenter(): void {
    const ctx = this.ctx
    const cell = this.cell
    const x = cell
    const y = cell
    const w = cell * (BOARD_GRID - 2)
    const h = cell * (BOARD_GRID - 2)

    const grad = ctx.createLinearGradient(x, y, x + w, y + h)
    grad.addColorStop(0, '#1f2b3a')
    grad.addColorStop(1, '#38495f')
    ctx.fillStyle = grad
    this.roundRect(x + cell * 0.25, y + cell * 0.25, w - cell * 0.5, h - cell * 0.5, cell * 0.6)
    ctx.fill()

    ctx.fillStyle = '#ffffff'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    const titleSize = Math.max(14, cell * 0.5)
    ctx.font = `600 ${titleSize}px ${FONT_FAMILY}`
    const centerX = x + w / 2
    ctx.fillText(this.opts.centerTitle ?? 'GridGo', centerX, y + h * 0.32)

    ctx.font = `${Math.max(11, cell * 0.32)}px ${FONT_FAMILY}`
    ctx.fillStyle = '#c3d0e0'
    const lines = this.opts.centerLines ?? []
    lines.forEach((line, i) => {
      ctx.fillText(line, centerX, y + h * (0.45 + i * 0.1))
    })

    this.drawDice(centerX, y + h * 0.72)
  }

  private drawDice(centerX: number, centerY: number): void {
    const dice = this.state?.dice
    if (!dice || dice.values.length === 0) return
    const ctx = this.ctx
    const size = Math.max(18, this.cell * 0.5)
    const gap = size * 0.3
    const totalWidth = dice.values.length * size + (dice.values.length - 1) * gap
    let cursor = centerX - totalWidth / 2
    dice.values.forEach((value) => {
      ctx.fillStyle = '#ffffff'
      this.roundRect(cursor, centerY - size / 2, size, size, size * 0.22)
      ctx.fill()
      ctx.fillStyle = '#1f2b3a'
      ctx.font = `700 ${size * 0.55}px ${FONT_FAMILY}`
      ctx.fillText(String(value), cursor + size / 2, centerY + size * 0.03)
      cursor += size + gap
    })
  }

  private drawTile(tile: TileEntity): void {
    const ctx = this.ctx
    const { x, y, w, h } = tile.rect
    const tileState = tile.state
    const highlight = this.opts.highlight?.includes(tileState.position) ?? false
    const selected = this.opts.selected === tileState.position

    ctx.save()
    ctx.globalAlpha = tileState.is_mortgaged ? 0.55 : 1

    ctx.fillStyle = tile.bg
    this.roundRect(x, y, w, h, Math.min(8, w * 0.18))
    ctx.fill()

    // 分组色条
    if (tileState.tile_group) {
      ctx.fillStyle = this.groupColor(tile)
      ctx.fillRect(x, y, w, Math.max(3, h * 0.14))
    }

    // 归属着色
    if (tileState.owner_id !== null && tileState.owner_id !== undefined) {
      ctx.save()
      this.roundRect(x, y, w, h, Math.min(8, w * 0.18))
      ctx.clip()
      ctx.globalAlpha = tileState.is_mortgaged ? 0.14 : 0.24
      ctx.fillStyle = this.ownerColor(tileState.owner_id)
      ctx.fillRect(x, y, w, h)
      ctx.restore()
    }

    // 边框
    if (highlight) {
      ctx.strokeStyle = '#ffb300'
      ctx.lineWidth = 3
    } else if (selected) {
      ctx.strokeStyle = '#409eff'
      ctx.lineWidth = 3
    } else if (tileState.owner_id === this.opts.currentUserId && tileState.owner_id !== null) {
      ctx.strokeStyle = '#2e7d32'
      ctx.lineWidth = 2
    } else {
      ctx.strokeStyle = '#c8d2dd'
      ctx.lineWidth = 1
    }
    this.roundRect(x, y, w, h, Math.min(8, w * 0.18))
    ctx.stroke()

    // 抵押斜线
    if (tileState.is_mortgaged) {
      ctx.strokeStyle = '#b71c1c'
      ctx.lineWidth = 1.5
      ctx.beginPath()
      ctx.moveTo(x + 2, y + h - 2)
      ctx.lineTo(x + w - 2, y + 2)
      ctx.stroke()
    }

    // 名称（最多两行）
    const nameSize = Math.max(8, Math.min(w * 0.2, h * 0.24))
    ctx.font = `600 ${nameSize}px ${FONT_FAMILY}`
    ctx.fillStyle = '#1f2b3a'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    const nameLines = splitName(tileState.name, 4)
    const nameTop = y + h * (tileState.tile_group ? 0.42 : 0.34)
    nameLines.forEach((line, i) => {
      ctx.fillText(line, x + w / 2, nameTop + i * nameSize * 1.1)
    })

    // 价格 / 等级
    const subSize = Math.max(7, nameSize * 0.82)
    ctx.font = `${subSize}px ${FONT_FAMILY}`
    ctx.fillStyle = '#5a6b7d'
    let subText = ''
    if (tileState.price) subText = `$${tileState.price}`
    else if (tileState.tax_amount) subText = tileState.tax_is_percent ? `${tileState.tax_amount}%` : `$${tileState.tax_amount}`
    if (subText) ctx.fillText(subText, x + w / 2, y + h * 0.82)

    if (tileState.build_level > 0) {
      const houseSize = Math.max(3, w * 0.12)
      const gap = houseSize * 0.35
      const totalW = tileState.build_level * houseSize + (tileState.build_level - 1) * gap
      let hx = x + w / 2 - totalW / 2
      for (let i = 0; i < tileState.build_level; i += 1) {
        ctx.fillStyle = '#2e7d32'
        ctx.fillRect(hx, y + h - houseSize - 3, houseSize, houseSize)
        hx += houseSize + gap
      }
    }
    ctx.restore()
  }

  private drawTokens(): void {
    const ctx = this.ctx
    const players = this.state?.players ?? []
    players.forEach((player) => {
      const token = this.tokens.get(player.user_id)
      if (!token) return
      const point = this.opts.tokenOverrides?.get(player.user_id) ?? token.snapshot()
      ctx.save()
      ctx.globalAlpha = player.is_bankrupt ? 0.35 : 1
      ctx.beginPath()
      ctx.arc(point.x, point.y, token.radius, 0, Math.PI * 2)
      ctx.fillStyle = token.color
      ctx.fill()
      ctx.strokeStyle = player.user_id === this.opts.currentUserId ? '#ffffff' : 'rgba(0,0,0,0.25)'
      ctx.lineWidth = 2
      ctx.stroke()

      const labelSize = Math.max(8, token.radius * 1.05)
      ctx.font = `700 ${labelSize}px ${FONT_FAMILY}`
      ctx.fillStyle = '#ffffff'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(token.initial, point.x, point.y + labelSize * 0.04)
      ctx.restore()
    })
  }

  private drawLegend(): void {
    const players = this.state?.players ?? []
    if (players.length === 0) return
    const ctx = this.ctx
    const cell = this.cell
    const boxW = cell * 3.1
    const boxH = cell * 0.42 * players.length + cell * 0.4
    const x = cell * (BOARD_GRID - 1) - boxW - cell * 0.3
    const y = this.size - cell - boxH - cell * 0.3

    ctx.save()
    ctx.fillStyle = 'rgba(255,255,255,0.88)'
    this.roundRect(x, y, boxW, boxH, cell * 0.16)
    ctx.fill()
    ctx.strokeStyle = 'rgba(31,43,58,0.15)'
    ctx.lineWidth = 1
    ctx.stroke()

    ctx.textAlign = 'left'
    ctx.textBaseline = 'middle'
    players.forEach((player, i) => {
      const token = this.tokens.get(player.user_id)
      const rowY = y + cell * 0.28 + i * cell * 0.42
      ctx.beginPath()
      ctx.arc(x + cell * 0.22, rowY, Math.max(3, cell * 0.1), 0, Math.PI * 2)
      ctx.fillStyle = token?.color ?? '#90a4ae'
      ctx.fill()
      ctx.font = `${Math.max(8, cell * 0.2)}px ${FONT_FAMILY}`
      ctx.fillStyle = '#1f2b3a'
      const label = `${player.nickname} $${player.cash}`
      ctx.fillText(label, x + cell * 0.42, rowY)
    })
    ctx.restore()
  }

  destroy(): void {
    this.tiles = []
    this.tokens.clear()
    this.state = null
  }
}

export function buildGroupColors(state: GameState): Map<string, string> {
  const map = new Map<string, string>()
  state.tiles.forEach((tile) => {
    const key = tile.tile_group ?? tile.tile_type
    if (map.has(key)) return
    const group = tile.tile_group ?? ''
    const order = Array.from(new Set(state.tiles.filter((t) => t.tile_group).map((t) => t.tile_group))).indexOf(group)
    map.set(key, tile.group_color ?? DEFAULT_GROUP_COLORS[(order < 0 ? 0 : order) % DEFAULT_GROUP_COLORS.length])
  })
  return map
}

/** 按固定长度切分名称，最多两行 */
export function splitName(name: string, perLine = 4): string[] {
  const chars = Array.from(name)
  if (chars.length <= perLine) return [name]
  const first = chars.slice(0, perLine).join('')
  const rest = chars.slice(perLine, perLine * 2).join('')
  return rest ? [first, chars.length > perLine * 2 ? `${rest.slice(0, perLine - 1)}…` : rest] : [first]
}

/** 供组件计算棋盘像素尺寸：取容器短边并减去内边距 */
export function fitBoardSize(containerWidth: number, containerHeight: number, padding = 16): number {
  return Math.max(240, Math.min(containerWidth, containerHeight) - padding * 2)
}

export { tileGridPos }
