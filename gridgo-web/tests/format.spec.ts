import { describe, expect, it } from 'vitest'
import {
  aiDifficultyText,
  formatLogTime,
  formatMoney,
  formatSeconds,
  formatSignedMoney,
  formatTime,
  phaseTagType,
  phaseText,
  tileRent,
  tileSubtitle,
  tileTypeText,
  winRate,
} from '@/utils/format'
import type { TileState } from '@/types/game'

const tile = (patch: Partial<TileState> = {}): TileState => ({
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
  ...patch,
})

describe('formatMoney / formatSignedMoney', () => {
  it('千分位与空值兜底', () => {
    expect(formatMoney(1234567)).toBe('$1,234,567')
    expect(formatMoney(0)).toBe('$0')
    expect(formatMoney(null)).toBe('$0')
    expect(formatMoney(undefined)).toBe('$0')
    expect(formatMoney(Number.NaN)).toBe('$0')
  })

  it('带符号金额', () => {
    expect(formatSignedMoney(500)).toBe('+$500')
    expect(formatSignedMoney(-500)).toBe('-$500')
    expect(formatSignedMoney(0)).toBe('+$0')
  })
})

describe('阶段文案与标签', () => {
  it('已知阶段映射中文', () => {
    expect(phaseText('WAIT_ROLL')).toBe('等待掷骰')
    expect(phaseText('AUCTION')).toBe('拍卖中')
    expect(phaseTagType('WAIT_DECISION')).toBe('danger')
  })

  it('未知/空阶段回退', () => {
    expect(phaseText('SOMETHING')).toBe('SOMETHING')
    expect(phaseText(undefined)).toBe('未知')
    expect(phaseTagType(undefined)).toBe('info')
    expect(phaseTagType('NOPE')).toBe('info')
  })
})

describe('地块展示', () => {
  it('租金按建筑等级取档', () => {
    expect(tileRent(tile({ build_level: 0 }))).toBe(40)
    expect(tileRent(tile({ build_level: 5 }))).toBe(2000)
    expect(tileRent(tile({ build_level: 9 }))).toBe(2000)
    expect(tileRent(null)).toBeNull()
  })

  it('副标题优先价格，其次税额/类型', () => {
    expect(tileSubtitle(tile())).toBe('$1,200')
    expect(tileSubtitle(tile({ price: null, tax_amount: 10, tax_is_percent: true }))).toBe('10%')
    expect(tileSubtitle(tile({ price: null, tax_amount: 200 }))).toBe('$200')
    expect(tileSubtitle(tile({ price: null, tax_amount: null, tile_type: 'CHANCE' }))).toBe('机会')
    expect(tileSubtitle(null)).toBe('')
  })

  it('地块类型与 AI 难度文案', () => {
    expect(tileTypeText('STATION')).toBe('车站')
    expect(tileTypeText('UNKNOWN')).toBe('UNKNOWN')
    expect(aiDifficultyText('hard')).toBe('困难')
    expect(aiDifficultyText(null)).toBe('')
  })
})

describe('时间与比率', () => {
  it('formatTime 输出到分钟', () => {
    expect(formatTime(new Date(2026, 0, 5, 9, 7))).toBe('2026-01-05 09:07')
    expect(formatTime('not-a-date')).toBe('')
    expect(formatTime(null)).toBe('')
  })

  it('formatLogTime 输出时分秒', () => {
    const ts = new Date(2026, 0, 5, 9, 7, 3).getTime() / 1000
    expect(formatLogTime(ts)).toBe('09:07:03')
  })

  it('formatSeconds 分秒格式', () => {
    expect(formatSeconds(75)).toBe('1:15')
    expect(formatSeconds(0)).toBe('0:00')
    expect(formatSeconds(-5)).toBe('0:00')
  })

  it('winRate', () => {
    expect(winRate(10, 3)).toBe('30%')
    expect(winRate(0, 0)).toBe('0%')
    expect(winRate(3, 1)).toBe('33%')
  })
})
