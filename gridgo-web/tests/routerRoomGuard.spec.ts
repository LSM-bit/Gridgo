// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const { getMyRoomMock, warnMock } = vi.hoisted(() => ({
  getMyRoomMock: vi.fn(),
  warnMock: vi.fn(),
}))

vi.mock('element-plus', async (importOriginal) => {
  const actual = await importOriginal<typeof import('element-plus')>()
  return { ...actual, ElMessage: { ...actual.ElMessage, warning: warnMock } }
})

vi.mock('@/api/room', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/room')>()
  return { ...actual, getMyRoom: getMyRoomMock }
})

vi.mock('@/pages/Home.vue', () => ({ default: { name: 'HomeStub', template: '<div />' } }))
vi.mock('@/pages/Room.vue', () => ({ default: { name: 'RoomStub', template: '<div />' } }))

import router from '@/router/index'
import { useUserStore } from '@/stores/user'

function roomInfo(code: string) {
  return {
    id: `room-${code}`,
    code,
    name: '测试房间',
    host_id: 1,
    max_players: 4,
    map_id: 'classic',
    ai_count: 0,
    ai_difficulty: 'easy',
    status: 'waiting',
    players: [],
    spectators: [],
    max_spectators: 8,
    created_at: null,
  }
}

function login() {
  useUserStore().setUserInfo({ token: 'token', userId: 1, username: 'tester', nickname: 'Tester' })
}

beforeEach(async () => {
  vi.clearAllMocks()
  localStorage.clear()
  setActivePinia(createPinia())
  await router.replace('/')
})

describe('/room/:code 路由守卫（防止未加入直访）', () => {
  it('未加入任何房间 → 回大厅并提示', async () => {
    login()
    getMyRoomMock.mockResolvedValue(null)

    await router.push('/room/ABC123')

    expect(router.currentRoute.value.name).toBe('Home')
    expect(warnMock).toHaveBeenCalled()
  })

  it('已加入该房间 → 正常放行', async () => {
    login()
    getMyRoomMock.mockResolvedValue(roomInfo('ABC123'))

    await router.push('/room/ABC123')

    expect(router.currentRoute.value.name).toBe('Room')
    expect(router.currentRoute.value.params.code).toBe('ABC123')
  })

  it('已加入其他房间 → 重定向到自己所在房间', async () => {
    login()
    getMyRoomMock.mockResolvedValue(roomInfo('ZZZ999'))

    await router.push('/room/ABC123')

    expect(router.currentRoute.value.name).toBe('Room')
    expect(router.currentRoute.value.params.code).toBe('ZZZ999')
  })

  it('活跃房间接口异常 → 放行不误伤', async () => {
    login()
    getMyRoomMock.mockRejectedValue(new Error('network down'))

    await router.push('/room/ABC123')

    expect(router.currentRoute.value.name).toBe('Room')
    expect(router.currentRoute.value.params.code).toBe('ABC123')
  })
})
