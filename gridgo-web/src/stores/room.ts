import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import type { RoomInfo } from '@/api/room'

export interface GameOverRanking {
  rank: number
  user_id: number
  nickname: string
  total_assets: number
  is_ai: boolean
  is_bankrupt: boolean
}

export interface GameOverData {
  end_reason: string
  winner_id: number | null
  rankings: GameOverRanking[]
  total_turns: number
}

export const useRoomStore = defineStore('room', () => {
  const room = ref<RoomInfo | null>(null)
  const pollingTimer = ref<ReturnType<typeof setInterval> | null>(null)
  const gameOverData = ref<GameOverData | null>(null)

  const roomId = computed(() => room.value?.id ?? '')
  const roomCode = computed(() => room.value?.code ?? '')
  const inRoom = computed(() => !!room.value)
  const playerCount = computed(() => room.value?.players.length ?? 0)
  const allReady = computed(() => {
    if (!room.value) return false
    return room.value.players.every((p) => p.is_ready || p.is_host || p.is_ai)
  })

  const setRoom = (data: RoomInfo) => {
    room.value = data
  }

  const setGameOverData = (data: GameOverData) => {
    gameOverData.value = data
  }

  const reset = () => {
    room.value = null
    stopPolling()
    gameOverData.value = null
  }

  const startPolling = (fetchFn: () => Promise<void>, interval = 3000) => {
    stopPolling()
    pollingTimer.value = setInterval(fetchFn, interval)
  }

  const stopPolling = () => {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  return {
    room,
    roomId,
    roomCode,
    inRoom,
    playerCount,
    allReady,
    gameOverData,
    setRoom,
    setGameOverData,
    reset,
    startPolling,
    stopPolling,
  }
})
