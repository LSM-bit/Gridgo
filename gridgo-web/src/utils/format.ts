/**
 * 展示格式化工具（纯函数，便于单测）
 */

import type { TileState } from '@/types/game'

const PHASE_TEXT: Record<string, string> = {
  TURN_START: '回合开始',
  WAIT_ROLL: '等待掷骰',
  ROLLING: '掷骰中',
  MOVING: '移动中',
  TILE_EFFECT: '地块结算',
  WAIT_DECISION: '等待决策',
  FREE_ACTION: '自由行动',
  TURN_END: '回合结束',
  AUCTION: '拍卖中',
  BANKRUPTCY: '破产结算',
  GAME_OVER: '游戏结束',
}

const PHASE_TAG: Record<string, string> = {
  TURN_START: 'info',
  WAIT_ROLL: 'primary',
  ROLLING: 'warning',
  MOVING: 'warning',
  TILE_EFFECT: 'warning',
  WAIT_DECISION: 'danger',
  FREE_ACTION: 'success',
  TURN_END: 'info',
  AUCTION: 'danger',
  BANKRUPTCY: 'danger',
  GAME_OVER: 'info',
}

const TILE_TYPE_TEXT: Record<string, string> = {
  START: '起点',
  PROPERTY: '地产',
  STATION: '车站',
  UTILITY: '公共设施',
  CHANCE: '机会',
  FATE: '命运',
  TAX: '税收',
  JAIL: '监狱',
  GO_TO_JAIL: '入狱',
  PARKING: '停车场',
}

const EFFECT_TEXT: Record<string, string> = {
  MOVE: '移动',
  MOVE_TO: '移动到指定位置',
  MONEY: '现金变动',
  GET_OUT_OF_JAIL: '出狱卡',
  GO_TO_JAIL: '立即入狱',
  FREE_PARKING: '停车场奖励',
}

const AI_DIFFICULTY_TEXT: Record<string, string> = {
  easy: '简单',
  normal: '普通',
  hard: '困难',
  expert: '专家',
}

export function formatMoney(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return '$0'
  return `$${amount.toLocaleString('en-US')}`
}

export function formatSignedMoney(amount: number): string {
  return `${amount >= 0 ? '+' : '-'}$${Math.abs(amount).toLocaleString('en-US')}`
}

export function phaseText(phase: string | undefined): string {
  if (!phase) return '未知'
  return PHASE_TEXT[phase] ?? phase
}

export function phaseTagType(phase: string | undefined): string {
  if (!phase) return 'info'
  return PHASE_TAG[phase] ?? 'info'
}

export function tileTypeText(tileType: string | undefined): string {
  if (!tileType) return '未知'
  return TILE_TYPE_TEXT[tileType] ?? tileType
}

export function effectText(effectType: string | undefined): string {
  if (!effectType) return ''
  return EFFECT_TEXT[effectType] ?? effectType
}

export function aiDifficultyText(difficulty: string | null | undefined): string {
  if (!difficulty) return ''
  return AI_DIFFICULTY_TEXT[difficulty] ?? difficulty
}

export function formatTime(input: string | number | Date | null | undefined): string {
  if (input === null || input === undefined) return ''
  const date = input instanceof Date ? input : new Date(input)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function formatLogTime(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

export function formatSeconds(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

export function tileSubtitle(tile: TileState | null | undefined): string {
  if (!tile) return ''
  if (tile.price) return formatMoney(tile.price)
  if (tile.tax_amount) return tile.tax_is_percent ? `${tile.tax_amount}%` : formatMoney(tile.tax_amount)
  return tileTypeText(tile.tile_type)
}

/** 当前地块租金（按建筑等级） */
export function tileRent(tile: TileState | null | undefined): number | null {
  if (!tile) return null
  const rents = [tile.rent_0, tile.rent_1, tile.rent_2, tile.rent_3, tile.rent_4, tile.rent_5]
  const level = Math.min(Math.max(tile.build_level, 0), rents.length - 1)
  return rents[level] ?? null
}

export function winRate(totalGames: number, totalWins: number): string {
  if (!totalGames) return '0%'
  return `${Math.round((totalWins / totalGames) * 100)}%`
}
