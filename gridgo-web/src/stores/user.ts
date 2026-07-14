import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const STORAGE_KEY = 'gridgo_user'

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {
    // ignore
  }
  return null
}

function saveToStorage(data: Record<string, unknown>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
}

function clearStorage() {
  localStorage.removeItem(STORAGE_KEY)
}

export const useUserStore = defineStore('user', () => {
  const saved = loadFromStorage()

  const token = ref<string>(saved?.token ?? '')
  const refreshToken = ref<string>(saved?.refreshToken ?? '')
  const userId = ref<number>(saved?.userId ?? 0)
  const username = ref<string>(saved?.username ?? '')
  const nickname = ref<string>(saved?.nickname ?? '')
  const avatar = ref<string>(saved?.avatar ?? '')

  const isLoggedIn = computed(() => !!token.value)

  const setUserInfo = (info: {
    token: string
    refreshToken?: string
    userId: number
    username: string
    nickname: string
    avatar?: string
  }) => {
    token.value = info.token
    refreshToken.value = info.refreshToken ?? ''
    userId.value = info.userId
    username.value = info.username
    nickname.value = info.nickname
    avatar.value = info.avatar ?? ''
    saveToStorage({
      token: info.token,
      refreshToken: info.refreshToken ?? '',
      userId: info.userId,
      username: info.username,
      nickname: info.nickname,
      avatar: info.avatar ?? '',
    })
  }

  const clearUserInfo = () => {
    token.value = ''
    refreshToken.value = ''
    userId.value = 0
    username.value = ''
    nickname.value = ''
    avatar.value = ''
    clearStorage()
  }

  return {
    token,
    refreshToken,
    userId,
    username,
    nickname,
    avatar,
    isLoggedIn,
    setUserInfo,
    clearUserInfo,
  }
})
