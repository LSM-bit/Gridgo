import { describe, expect, it } from 'vitest'
import { WS_CLOSE_CODES, describeCloseCode, reconnectModeText } from '@/utils/ws'

describe('WS 关闭码语义', () => {
  it('4001 认证失败需要重新登录', () => {
    const info = describeCloseCode(4001)
    expect(info.code).toBe(4001)
    expect(info.needReauth).toBe(true)
    expect(info.message).toContain('重新登录')
  })

  it('4002~4005 为致命初始化错误但无需重登', () => {
    for (const code of [4002, 4003, 4004, 4005]) {
      const info = describeCloseCode(code)
      expect(info.needReauth).toBe(false)
      expect(info.label.length).toBeGreaterThan(0)
    }
    expect(Object.keys(WS_CLOSE_CODES)).toEqual(expect.arrayContaining(['4001', '4002', '4003', '4004', '4005']))
  })

  it('未知关闭码回退可重连文案', () => {
    const info = describeCloseCode(4999)
    expect(info.code).toBe(4999)
    expect(info.needReauth).toBe(false)
    expect(info.message).toContain('重连')
  })
})

describe('重连档位文案', () => {
  it('三档与后端 system.player_reconnected.mode 对齐', () => {
    expect(reconnectModeText('resume_incremental')).toBe('增量恢复')
    expect(reconnectModeText('resume_snapshot')).toBe('快照恢复')
    expect(reconnectModeText('left_game')).toBe('已离开对局')
  })

  it('未知档位原样返回', () => {
    expect(reconnectModeText('unknown_mode')).toBe('unknown_mode')
  })
})
