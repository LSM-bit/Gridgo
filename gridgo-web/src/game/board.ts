/**
 * 棋盘几何与静态配置
 *
 * 11×11 网格外圈共 40 个地块，索引与网格坐标映射（与后端 map 定义一致）：
 *   底部行（网格 Row 11）：position 0 → 10，左起向右（col 1 → 11）
 *   左侧列（网格 Col 1） ：position 11 → 19，上起向下（row 10 → 2）
 *   顶部行（网格 Row 1） ：position 20 → 30，左起向右（col 1 → 11）
 *   右侧列（网格 Col 11）：position 31 → 39，上起向下（row 2 → 10）
 */

export const BOARD_GRID = 11
export const TILE_COUNT = 40

export interface GridPos {
  row: number
  col: number
}

/** 地块 position → 网格坐标（1-based） */
export function tileGridPos(position: number): GridPos {
  if (position >= 0 && position <= 10) {
    return { row: BOARD_GRID, col: BOARD_GRID - position }
  }
  if (position >= 11 && position <= 19) {
    return { row: 21 - position, col: 1 }
  }
  if (position >= 20 && position <= 30) {
    return { row: 1, col: position - 19 }
  }
  if (position >= 31 && position <= 39) {
    return { row: position - 29, col: BOARD_GRID }
  }
  return { row: 1, col: 1 }
}

/** 网格坐标（1-based） → 地块 position，非外圈返回 null */
export function gridPosTile(row: number, col: number): number | null {
  if (row === BOARD_GRID && col >= 1 && col <= 11) return BOARD_GRID - col
  if (col === 1 && row >= 2 && row <= 10) return 21 - row
  if (row === 1 && col >= 1 && col <= 11) return col + 19
  if (col === BOARD_GRID && row >= 2 && row <= 10) return row + 29
  return null
}

/** 棋盘中心区域（放置骰子/回合信息） */
export const BOARD_CENTER = { rowStart: 2, rowEnd: 10, colStart: 2, colEnd: 10 }

/** 非地产类地块底色 */
export const TILE_BG: Record<string, string> = {
  START: '#e6f7e6',
  JAIL: '#f0f0f0',
  GO_TO_JAIL: '#fde6e6',
  PARKING: '#e6f0ff',
  CHANCE: '#fff7e6',
  FATE: '#f5e6ff',
  TAX: '#ffe6e6',
}

export const DEFAULT_TILE_BG = '#ffffff'

/** 默认地块分组配色（后端未给出 group_color 时兜底） */
export const DEFAULT_GROUP_COLORS = [
  '#8d6e63',
  '#42a5f5',
  '#ab47bc',
  '#ffa726',
  '#ef5350',
  '#26a69a',
  '#5c6bc0',
  '#66bb6a',
]

/** 棋子配色（按玩家在牌桌上的顺序循环取色） */
export const TOKEN_COLORS = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#9c27b0', '#00bcd4', '#795548', '#607d8b']

export function tokenColor(index: number): string {
  return TOKEN_COLORS[index % TOKEN_COLORS.length]
}

export function tileBg(tileType: string): string {
  return TILE_BG[tileType] ?? DEFAULT_TILE_BG
}
