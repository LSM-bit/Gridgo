import { describe, expect, it } from 'vitest'
import {
  BOARD_CENTER,
  BOARD_GRID,
  DEFAULT_GROUP_COLORS,
  DEFAULT_TILE_BG,
  TILE_COUNT,
  gridPosTile,
  tileBg,
  tileGridPos,
  tokenColor,
} from '@/game/board'

describe('棋盘几何', () => {
  it('常量与后端地图一致', () => {
    expect(BOARD_GRID).toBe(11)
    expect(TILE_COUNT).toBe(40)
    expect(BOARD_CENTER).toEqual({ rowStart: 2, rowEnd: 10, colStart: 2, colEnd: 10 })
  })

  it('position → 网格坐标', () => {
    expect(tileGridPos(0)).toEqual({ row: 11, col: 11 })
    expect(tileGridPos(10)).toEqual({ row: 11, col: 1 })
    expect(tileGridPos(11)).toEqual({ row: 10, col: 1 })
    expect(tileGridPos(20)).toEqual({ row: 1, col: 1 })
    expect(tileGridPos(30)).toEqual({ row: 1, col: 11 })
    expect(tileGridPos(31)).toEqual({ row: 2, col: 11 })
    expect(tileGridPos(39)).toEqual({ row: 10, col: 11 })
  })

  it('非外圈/越界位置兜底', () => {
    expect(tileGridPos(40)).toEqual({ row: 1, col: 1 })
    expect(tileGridPos(-1)).toEqual({ row: 1, col: 1 })
  })

  it('网格坐标 → position 的双向一致性', () => {
    for (let position = 0; position < TILE_COUNT; position += 1) {
      const { row, col } = tileGridPos(position)
      expect(gridPosTile(row, col)).toBe(position)
    }
  })

  it('中心区域不映射到地块', () => {
    expect(gridPosTile(5, 5)).toBeNull()
    expect(gridPosTile(1, 1)).toBe(20)
  })
})

describe('配色工具', () => {
  it('棋子在 8 色间循环', () => {
    expect(tokenColor(0)).toBe(tokenColor(8))
    expect(tokenColor(0)).not.toBe(tokenColor(1))
  })

  it('地块底色按类型兜底', () => {
    expect(tileBg('CHANCE')).not.toBe(DEFAULT_TILE_BG)
    expect(tileBg('UNKNOWN_TYPE')).toBe(DEFAULT_TILE_BG)
    expect(DEFAULT_GROUP_COLORS.length).toBeGreaterThanOrEqual(4)
  })
})
