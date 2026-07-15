import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getGameReplay } from '@/api/replay'
import type { ReplayData, ReplayStep, ReplayPlayer } from '@/api/replay'
import { computeAllSnapshots, type ReplaySnapshot } from '@/game/replayEngine'

export type PlaybackStatus = 'idle' | 'loading' | 'playing' | 'paused' | 'ended'

export const useReplayStore = defineStore('replay', () => {
  // ─── 核心数据 ───

  const gameId = ref<number>(0)
  const roomId = ref('')
  const mapId = ref('')
  const endReason = ref('')
  const totalTurns = ref(0)
  const winnerId = ref<number | null>(null)
  const players = ref<ReplayPlayer[]>([])
  const replayData = ref<ReplayData | null>(null)
  const loading = ref(false)
  const error = ref('')

  // ─── 回放控制 ───

  const status = ref<PlaybackStatus>('idle')
  const currentStepIndex = ref(0)      // 当前步骤索引（0 = 初始状态）
  const snapshots = ref<ReplaySnapshot[]>([])
  const totalSteps = ref(0)
  const playInterval = ref(1000)         // 播放速度（毫秒/步）
  let playTimer: ReturnType<typeof setInterval> | null = null

  // ─── 计算属性 ───

  const currentSnapshot = computed<ReplaySnapshot | null>(() => {
    if (currentStepIndex.value < snapshots.value.length) {
      return snapshots.value[currentStepIndex.value]
    }
    return null
  })

  const currentTurn = computed(() => {
    return currentSnapshot.value?.turn_number ?? 0
  })

  const currentStep = computed<ReplayStep | null>(() => {
    if (!replayData.value || currentStepIndex.value === 0) return null
    // 找到当前步骤
    let stepCount = 0
    for (const turn of replayData.value.turns) {
      for (const step of turn.steps) {
        stepCount++
        if (stepCount === currentStepIndex.value) {
          return step
        }
      }
    }
    return null
  })

  const progress = computed(() => {
    if (totalSteps.value === 0) return 0
    return Math.round((currentStepIndex.value / totalSteps.value) * 100)
  })

  const isPlaying = computed(() => status.value === 'playing')
  const isPaused = computed(() => status.value === 'paused')

  // ─── 获取回放数据 ───

  async function fetchReplay(id: number) {
    loading.value = true
    error.value = ''
    status.value = 'loading'

    try {
      const res = await getGameReplay(id)
      const data = res.data

      gameId.value = data.game_id
      roomId.value = data.room_id
      mapId.value = data.map_id
      totalTurns.value = data.total_turns
      winnerId.value = data.winner_id
      endReason.value = data.end_reason
      players.value = data.players
      replayData.value = data.replay

      // 预计算所有快照（传入 finalState 确保最后一步与真实最终状态一致）
      const result = computeAllSnapshots(
        data.replay.init_state,
        data.replay.turns,
        data.replay.final_state,
      )
      snapshots.value = result.snapshots
      totalSteps.value = result.totalSteps

      // 重置播放位置
      currentStepIndex.value = 0
      status.value = 'paused'
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e.message || '加载回放数据失败'
      status.value = 'idle'
    } finally {
      loading.value = false
    }
  }

  // ─── 播放控制 ───

  function play() {
    if (status.value === 'ended') {
      currentStepIndex.value = 0
    }
    status.value = 'playing'
    startAutoPlay()
  }

  function pause() {
    status.value = 'paused'
    stopAutoPlay()
  }

  function togglePlay() {
    if (isPlaying.value) {
      pause()
    } else {
      play()
    }
  }

  function stepForward() {
    pause()
    if (currentStepIndex.value < totalSteps.value) {
      currentStepIndex.value++
    }
    if (currentStepIndex.value >= totalSteps.value) {
      status.value = 'ended'
    }
  }

  function stepBackward() {
    pause()
    if (currentStepIndex.value > 0) {
      currentStepIndex.value--
    }
  }

  function goToStep(index: number) {
    pause()
    currentStepIndex.value = Math.max(0, Math.min(index, totalSteps.value))
    if (currentStepIndex.value >= totalSteps.value) {
      status.value = 'ended'
    }
  }

  function goToTurn(turnNumber: number) {
    if (!replayData.value) return
    pause()

    // 计算该回合第一步在全局步骤中的位置
    let stepIndex = 0
    for (const turn of replayData.value.turns) {
      if (turn.turn_number === turnNumber) {
        goToStep(stepIndex)
        return
      }
      stepIndex += turn.steps.length
    }
  }

  function setSpeed(ms: number) {
    playInterval.value = ms
    if (isPlaying.value) {
      stopAutoPlay()
      startAutoPlay()
    }
  }

  // ─── 内部方法 ───

  function startAutoPlay() {
    stopAutoPlay()
    playTimer = setInterval(() => {
      if (currentStepIndex.value < totalSteps.value) {
        currentStepIndex.value++
      }
      if (currentStepIndex.value >= totalSteps.value) {
        status.value = 'ended'
        stopAutoPlay()
      }
    }, playInterval.value)
  }

  function stopAutoPlay() {
    if (playTimer) {
      clearInterval(playTimer)
      playTimer = null
    }
  }

  // ─── 重置 ───

  function reset() {
    stopAutoPlay()
    gameId.value = 0
    roomId.value = ''
    mapId.value = ''
    endReason.value = ''
    totalTurns.value = 0
    winnerId.value = null
    players.value = []
    replayData.value = null
    snapshots.value = []
    totalSteps.value = 0
    currentStepIndex.value = 0
    status.value = 'idle'
    loading.value = false
    error.value = ''
  }

  return {
    // 数据
    gameId, roomId, mapId, endReason, totalTurns, winnerId, players,
    replayData, loading, error,
    // 回放控制
    status, currentStepIndex, snapshots, totalSteps, playInterval,
    // 计算属性
    currentSnapshot, currentTurn, currentStep, progress,
    isPlaying, isPaused,
    // 方法
    fetchReplay, play, pause, togglePlay,
    stepForward, stepBackward, goToStep, goToTurn, setSpeed, reset,
  }
})
