<template>
  <div class="room-page">
    <el-container style="height: 100vh">
      <!-- 顶栏 -->
      <el-header>
        <div class="flex-between w-full h-full">
          <div>
            <el-button text @click="handleBack">
              <el-icon><ArrowLeft /></el-icon>
              返回
            </el-button>
            <span class="ml-4 text-lg font-bold">{{ roomData?.name || '房间' }}</span>
          </div>
          <div>
            <span class="mr-2">房间代码：</span>
            <el-tag type="success" size="large" class="font-mono text-lg">{{ code }}</el-tag>
            <el-button class="ml-2" size="small" @click="copyCode">复制</el-button>
          </div>
        </div>
      </el-header>

      <!-- 主体 -->
      <el-main v-loading="loading" class="room-main">
        <el-row :gutter="20" class="room-body">
          <!-- 左侧：玩家 + 操作 -->
          <el-col :span="8">
            <!-- 玩家列表 -->
            <el-card class="player-card">
              <template #header>
                <div class="flex-between">
                  <span>玩家 ({{ roomData?.players.length || 0 }}/{{ roomData?.max_players || 8 }})</span>
                  <el-tag v-if="roomData?.status === 'waiting'" type="info">等待中</el-tag>
                  <el-tag v-else-if="roomData?.status === 'playing'" type="success">游戏中</el-tag>
                  <el-tag v-else-if="roomData?.status === 'finished'" type="danger">已结束</el-tag>
                </div>
              </template>

              <div class="player-list">
                <div v-for="p in roomData?.players || []" :key="p.user_id" class="player-item">
                  <div class="flex items-center gap-2">
                    <el-avatar :size="28" :src="p.avatar || undefined">
                      {{ p.is_ai ? '🤖' : p.nickname.charAt(0) }}
                    </el-avatar>
                    <span class="player-name">{{ p.nickname }}</span>
                    <el-tag v-if="p.is_host" type="warning" size="small">房主</el-tag>
                    <el-tag v-if="p.is_ai" type="info" size="small">
                      AI · {{ difficultyText(p.ai_difficulty) }}
                    </el-tag>
                  </div>
                  <!-- 右侧只显示准备状态（房主和AI不显示） -->
                  <el-tag v-if="!p.is_host && !p.is_ai && p.is_ready" type="success" size="small">已准备</el-tag>
                  <el-tag v-else-if="!p.is_host && !p.is_ai && !p.is_ready" type="info" size="small">未准备</el-tag>
                </div>
              </div>
            </el-card>

            <!-- 观战者列表 -->
            <el-card v-if="(roomData?.spectators?.length ?? 0) > 0" class="mt-4">
              <template #header>
                <span>👀 观战者 ({{ roomData?.spectators?.length || 0 }}/{{ roomData?.max_spectators || 10 }})</span>
              </template>
              <div class="spectator-list">
                <div v-for="s in roomData?.spectators || []" :key="s.user_id" class="spectator-item">
                  <div class="flex items-center gap-2">
                    <el-avatar :size="24" :src="s.avatar || undefined">
                      {{ s.nickname.charAt(0) }}
                    </el-avatar>
                    <span class="spectator-name">{{ s.nickname }}</span>
                    <el-tag v-if="s.is_host" type="warning" size="small">房主</el-tag>
                    <el-tag v-if="s.user_id === userStore.userId" type="info" size="small">我</el-tag>
                  </div>
                  <el-tag type="info" size="small">👀 观战</el-tag>
                </div>
              </div>
            </el-card>

            <!-- 操作区 -->
            <el-card class="mt-4">
              <div class="flex-col gap-3">
                <!-- 游戏已结束 -->
                <template v-if="roomData?.status === 'finished'">
                  <el-tag type="danger" size="large" class="w-full text-center" style="justify-content: center">🏁 游戏已结束</el-tag>
                  <div class="gameover-summary">
                    <div class="gameover-winner" v-if="roomData?.players?.length">
                      <span>🏆 获胜者：{{ winnerNickname }}</span>
                    </div>
                  </div>
                  <el-button v-if="isHost" type="primary" size="large" class="w-full" :loading="resetLoading" @click="handleResetRoom">
                    🔄 返回准备阶段
                  </el-button>
                  <p v-else class="text-center text-gray-400 text-sm">等待房主重置房间</p>
                </template>

                <!-- 游戏进行中 -->
                <template v-else-if="roomData?.status === 'playing'">
                  <el-tag type="success" size="large" class="w-full text-center" style="justify-content: center">🎮 游戏进行中</el-tag>
                  <el-button type="primary" size="large" class="w-full" @click="handleEnterGame">
                    🖥️ 进入游戏
                  </el-button>
                </template>

                <!-- 等待中状态的操作 -->
                <template v-else>
                  <!-- 房主专属操作（无论玩家还是观战者） -->
                  <template v-if="isHost">
                    <el-button
                      type="primary"
                      size="large"
                      class="w-full"
                      :disabled="!canStart"
                      :loading="startLoading"
                      @click="handleStart"
                    >
                      🎮 开始游戏
                    </el-button>
                    <p v-if="!canStart" class="text-center text-gray-400 text-sm">
                      {{ startHint }}
                    </p>
                    <el-button size="large" class="w-full" @click="showSettingsDialog = true">
                      ⚙️ 房间设置
                    </el-button>
                  </template>

                  <!-- 观战者操作 -->
                  <template v-if="isSpectator">
                    <el-tag type="info" size="large" class="w-full text-center" style="justify-content: center">👀 观战模式</el-tag>
                    <p class="text-center text-gray-400 text-sm">你正在观战，无法参与游戏操作</p>
                    <el-button
                      v-if="(roomData?.players.length ?? 0) < (roomData?.max_players ?? 8)"
                      type="primary"
                      plain
                      size="large"
                      class="w-full"
                      :loading="switchRoleLoading"
                      @click="handleSwitchToPlayer"
                    >
                      🎮 加入玩家席
                    </el-button>
                  </template>

                  <!-- 非房主玩家操作 -->
                  <template v-if="!isHost && !isSpectator">
                    <el-button
                      :type="amReady ? 'success' : 'default'"
                      size="large"
                      class="w-full"
                      :loading="readyLoading"
                      @click="handleToggleReady"
                    >
                      {{ amReady ? '✅ 已准备' : '☝️ 点击准备' }}
                    </el-button>
                  </template>

                  <!-- 切换为观战（仅玩家可操作） -->
                  <el-button
                    v-if="!isSpectator"
                    type="info"
                    plain
                    size="large"
                    class="w-full"
                    :loading="switchRoleLoading"
                    @click="handleSwitchToSpectator"
                  >
                    👀 切换为观战
                  </el-button>
                </template>

                <!-- 离开 -->
                <el-button type="danger" plain size="large" class="w-full" @click="handleLeave">
                  离开房间
                </el-button>
              </div>
            </el-card>

            <!-- 房间信息 -->
            <el-card class="mt-4">
              <template #header>房间信息</template>
              <p>房间名：{{ roomData?.name }}</p>
              <p>最大人数：{{ roomData?.max_players }}</p>
              <p>地图：{{ mapLabel }}</p>
              <p>AI 数量：{{ roomData?.ai_count ?? 0 }}</p>
              <p v-if="(roomData?.ai_count ?? 0) > 0">AI 难度：{{ difficultyText(roomData?.ai_difficulty) }}</p>
              <p>房间代码：<span class="font-mono font-bold">{{ code }}</span></p>
            </el-card>
          </el-col>

          <!-- 右侧：游戏结果 / 聊天区 -->
          <el-col :span="16">
            <!-- 游戏结束回顾 -->
            <el-card v-if="roomData?.status === 'finished' && roomStore.gameOverData" class="gameover-card mb-4">
              <template #header>
                <div class="flex-between">
                  <span>🏆 游戏结果</span>
                  <el-tag type="info" size="small">{{ roomStore.gameOverData.total_turns }} 回合</el-tag>
                </div>
              </template>
              <div class="gameover-rankings">
                <div
                  v-for="(r, i) in roomStore.gameOverData.rankings"
                  :key="r.user_id"
                  class="gameover-rank-row"
                  :class="{ 'rank-row-me': r.user_id === userStore.userId }"
                >
                  <span class="rank-pos">{{ ['🥇', '🥈', '🥉'][i] || `#${r.rank}` }}</span>
                  <span class="rank-name">{{ r.is_ai ? '🤖 ' : '' }}{{ r.nickname }}</span>
                  <span class="rank-assets">¥{{ r.total_assets.toLocaleString() }}</span>
                  <el-tag v-if="r.is_bankrupt" type="danger" size="small">破产</el-tag>
                </div>
              </div>
            </el-card>

            <el-card class="chat-card">
              <template #header>
                <span>💬 聊天</span>
              </template>

              <!-- 消息列表 -->
              <div ref="chatContainer" class="chat-messages" @scroll="onChatScroll">
                <div v-if="chatLoading" class="chat-loading">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  加载中...
                </div>
                <div v-if="hasMoreMessages" class="load-more" @click="loadOlderMessages">
                  ↑ 加载更早的消息
                </div>
                <div v-if="!chatLoading && messages.length === 0" class="chat-empty">
                  暂无消息，快来打个招呼吧 👋
                </div>
                <div v-for="msg in messages" :key="msg.id" class="chat-msg" :class="{ 'chat-msg-self': msg.user_id === userStore.userId }">
                  <div class="chat-msg-header">
                    <span class="chat-msg-nickname">
                      {{ msg.is_ai ? '🤖 ' : '' }}{{ msg.nickname }}
                    </span>
                    <span class="chat-msg-time">{{ formatTime(msg.created_at) }}</span>
                  </div>
                  <div class="chat-msg-content">{{ msg.content }}</div>
                </div>
              </div>

              <!-- 输入区 -->
              <div class="chat-input">
                <el-input
                  v-model="chatInput"
                  placeholder="输入消息..."
                  maxlength="500"
                  @keyup.enter="handleSendMessage"
                >
                  <template #append>
                    <el-button :loading="sendLoading" @click="handleSendMessage">发送</el-button>
                  </template>
                </el-input>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>

    <!-- 房间设置对话框（仅房主） -->
    <el-dialog v-model="showSettingsDialog" title="房间设置" width="480px" :close-on-click-modal="false">
      <el-form :model="settingsForm" label-width="100px" label-position="left">
        <el-form-item label="房间名称">
          <el-input v-model="settingsForm.name" placeholder="给房间起个名字" maxlength="50" show-word-limit />
        </el-form-item>

        <el-form-item label="最大人数">
          <el-slider
            v-model="settingsForm.max_players"
            :min="2"
            :max="8"
            :step="1"
            show-stops
            :marks="{ 2: '2', 4: '4', 6: '6', 8: '8' }"
          />
        </el-form-item>

        <el-form-item label="选择地图">
          <el-radio-group v-model="settingsForm.map_id">
            <el-radio-button
              v-for="m in MAP_OPTIONS"
              :key="m.value"
              :value="m.value"
            >
              {{ m.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="AI 数量">
          <el-slider
            v-model="settingsForm.ai_count"
            :min="0"
            :max="settingsMaxAi"
            :step="1"
            show-stops
          />
        </el-form-item>

        <el-form-item v-if="(settingsForm.ai_count ?? 0) > 0" label="AI 难度">
          <el-radio-group v-model="settingsForm.ai_difficulty">
            <el-radio-button
              v-for="opt in AI_DIFFICULTY_OPTIONS"
              :key="opt.value"
              :value="opt.value"
            >
              {{ opt.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showSettingsDialog = false">取消</el-button>
        <el-button type="primary" :loading="settingsLoading" @click="handleSaveSettings">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Loading } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useRoomStore } from '@/stores/room'
import {
  getRoomByCode,
  leaveRoom,
  toggleReady,
  startGame,
  updateRoomSettings,
  switchRole,
  resetRoom,
  MAP_OPTIONS,
  AI_DIFFICULTY_OPTIONS,
} from '@/api/room'
import type { RoomInfo, UpdateRoomData } from '@/api/room'
import { getChatMessages, sendChatMessage } from '@/api/chat'
import type { ChatMessage } from '@/api/chat'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const roomStore = useRoomStore()

const code = route.params.code as string
const loading = ref(true)
const readyLoading = ref(false)
const startLoading = ref(false)
const settingsLoading = ref(false)
const switchRoleLoading = ref(false)
const roomData = ref<RoomInfo | null>(null)

// ─── 聊天相关 ───

const messages = ref<ChatMessage[]>([])
const chatInput = ref('')
const sendLoading = ref(false)
const chatLoading = ref(false)
const hasMoreMessages = ref(false)
const chatContainer = ref<HTMLElement | null>(null)
let chatPollingTimer: ReturnType<typeof setInterval> | null = null

// 是否房主
const isHost = computed(() => roomData.value?.host_id === userStore.userId)

// 是否观战者
const isSpectator = computed(() => {
  if (!roomData.value) return false
  return roomData.value.spectators?.some((s) => s.user_id === userStore.userId) ?? false
})

// 我是否已准备
const amReady = computed(() => {
  if (!roomData.value) return false
  const me = roomData.value.players.find((p) => p.user_id === userStore.userId)
  return me?.is_ready ?? false
})

// 能否开始
const canStart = computed(() => {
  if (!roomData.value || roomData.value.status !== 'waiting') return false
  if (roomData.value.players.length < 2) return false
  return roomData.value.players.every((p) => p.is_ready || p.is_host || p.is_ai)
})

const startHint = computed(() => {
  if (!roomData.value) return ''
  if (roomData.value.players.length < 2) return '至少需要2名玩家'
  if (!roomData.value.players.every((p) => p.is_ready || p.is_host || p.is_ai)) return '还有玩家未准备'
  return ''
})

// 地图显示文本
const mapLabel = computed(() => {
  const found = MAP_OPTIONS.find((m) => m.value === roomData.value?.map_id)
  return found?.label ?? roomData.value?.map_id ?? ''
})

// AI 难度显示文本
const difficultyText = (difficulty: string | null | undefined) => {
  const found = AI_DIFFICULTY_OPTIONS.find((d) => d.value === difficulty)
  return found?.label ?? difficulty ?? ''
}

// 格式化聊天时间
const formatTime = (isoStr: string) => {
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

// ─── 聊天逻辑 ───

// 拉取最新消息（增量：只取比当前最新消息更新的）
const fetchMessages = async () => {
  if (!roomData.value) return
  try {
    const latestId = messages.value.length > 0 ? messages.value[messages.value.length - 1].id : undefined
    const newMsgs = await getChatMessages(roomData.value.id, undefined, 50)

    // 增量合并：找到新消息
    if (messages.value.length === 0) {
      messages.value = newMsgs
    } else {
      const lastIdx = newMsgs.findIndex((m) => m.id === latestId)
      if (lastIdx >= 0 && lastIdx < newMsgs.length - 1) {
        const appended = newMsgs.slice(lastIdx + 1)
        messages.value.push(...appended)
      } else if (lastIdx === -1) {
        // 本地最新消息不在服务器返回中，全量替换
        messages.value = newMsgs
      }
    }

    // 判断是否还有更早的消息
    hasMoreMessages.value = newMsgs.length >= 50

    // 自动滚动到底部（仅当用户已在底部附近时）
    await nextTick()
    scrollToBottomIfNear()
  } catch {
    // 静默忽略
  }
}

// 加载更早的消息
const loadOlderMessages = async () => {
  if (!roomData.value || messages.value.length === 0) return
  chatLoading.value = true
  try {
    const oldestId = messages.value[0].id
    const olderMsgs = await getChatMessages(roomData.value.id, oldestId, 50)
    if (olderMsgs.length > 0) {
      messages.value = [...olderMsgs, ...messages.value]
      hasMoreMessages.value = olderMsgs.length >= 50
    } else {
      hasMoreMessages.value = false
    }
  } catch {
    // 静默忽略
  } finally {
    chatLoading.value = false
  }
}

// 滚动到底部（仅当用户在底部附近时自动滚动）
const scrollToBottomIfNear = () => {
  const el = chatContainer.value
  if (!el) return
  const threshold = 150
  const distToBottom = el.scrollHeight - el.scrollTop - el.clientHeight
  if (distToBottom < threshold) {
    el.scrollTop = el.scrollHeight
  }
}

// 强制滚动到底部
const scrollToBottom = () => {
  const el = chatContainer.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

// 滚动事件（可选：用户手动上翻时不自动滚到底）
const onChatScroll = () => {
  // 预留：可在此检测滚动位置决定是否自动滚动
}

// 发送消息
const handleSendMessage = async () => {
  const content = chatInput.value.trim()
  if (!content || !roomData.value) return

  sendLoading.value = true
  try {
    await sendChatMessage(roomData.value.id, content)
    chatInput.value = ''
    // 立即拉取最新消息
    await fetchMessages()
    await nextTick()
    scrollToBottom()
  } catch (err: any) {
    const msg = err.response?.data?.detail || err.message || '发送失败'
    ElMessage.error(msg)
  } finally {
    sendLoading.value = false
  }
}

// 启动聊天轮询
const startChatPolling = () => {
  stopChatPolling()
  chatPollingTimer = setInterval(fetchMessages, 2000)
}

const stopChatPolling = () => {
  if (chatPollingTimer) {
    clearInterval(chatPollingTimer)
    chatPollingTimer = null
  }
}

// ─── 房间设置 ───

const showSettingsDialog = ref(false)
const settingsForm = ref<UpdateRoomData>({
  name: '',
  max_players: 8,
  map_id: 'classic',
  ai_count: 0,
  ai_difficulty: 'easy',
})

// 设置面板中 AI 最大数量（房主可自动变为观战者，所以 AI 数量可以等于 max_players）
const settingsMaxAi = computed(() => {
  // 非房主真人玩家占的位置不能被 AI 替代，但房主可以自动变为观战者
  const nonHostRealPlayers = roomData.value
    ? roomData.value.players.filter((p) => !p.is_ai && p.user_id !== roomData.value!.host_id).length
    : 0
  return (settingsForm.value.max_players ?? 8) - nonHostRealPlayers
})

// 打开设置时，用当前房间数据填充表单
watch(showSettingsDialog, (val) => {
  if (val && roomData.value) {
    settingsForm.value = {
      name: roomData.value.name,
      max_players: roomData.value.max_players,
      map_id: roomData.value.map_id,
      ai_count: roomData.value.ai_count,
      ai_difficulty: roomData.value.ai_difficulty,
    }
  }
})

// 最大人数变化时限制 AI 数量
watch(() => settingsForm.value.max_players, () => {
  if ((settingsForm.value.ai_count ?? 0) > settingsMaxAi.value) {
    settingsForm.value.ai_count = settingsMaxAi.value
  }
})

const handleSaveSettings = async () => {
  if (!roomData.value) return
  settingsLoading.value = true
  roomStore.stopPolling()
  try {
    const data = await updateRoomSettings(roomData.value.id, settingsForm.value)
    roomData.value = data
    roomStore.setRoom(data)
    showSettingsDialog.value = false
    ElMessage.success('房间设置已更新')
  } catch (err: any) {
    const status = err.response?.status
    const detail = err.response?.data?.detail
    if (status === 404) {
      ElMessage.error('房间不存在或已过期，请重新创建')
    } else if (status === 401) {
      ElMessage.error('登录已过期，请重新登录')
    } else {
      ElMessage.error(detail || err.message || '更新失败')
    }
    await fetchRoom()
  } finally {
    settingsLoading.value = false
    roomStore.startPolling(fetchRoom, 3000)
  }
}

// ─── 核心操作 ───

// 拉取房间数据
const fetchRoom = async () => {
  try {
    const data = await getRoomByCode(code)
    roomData.value = data
    roomStore.setRoom(data)

    // 如果游戏已开始，跳转到游戏页面
    if (data.status === 'playing') {
      roomStore.stopPolling()
      stopChatPolling()
      router.push(`/game/${data.id}`)
    }
  } catch (err: any) {
    const status = err.response?.status
    if (status === 404) {
      ElMessage.error('房间不存在或已过期')
      roomStore.stopPolling()
      stopChatPolling()
      roomStore.reset()
      router.push('/')
    }
  }
}

// 复制房间代码
const copyCode = () => {
  navigator.clipboard.writeText(code)
  ElMessage.success('已复制房间代码')
}

// 准备/取消
const handleToggleReady = async () => {
  if (!roomData.value) return
  readyLoading.value = true
  try {
    const data = await toggleReady(roomData.value.id)
    roomData.value = data
    roomStore.setRoom(data)
  } catch (err: any) {
    const msg = err.response?.data?.detail || err.message || '操作失败'
    ElMessage.error(msg)
  } finally {
    readyLoading.value = false
  }
}

// 开始游戏
const handleStart = async () => {
  if (!roomData.value) return
  startLoading.value = true
  try {
    const data = await startGame(roomData.value.id)
    roomData.value = data
    roomStore.setRoom(data)
    if (data.status === 'playing') {
      roomStore.stopPolling()
      stopChatPolling()
      router.push(`/game/${data.id}`)
    }
  } catch (err: any) {
    const msg = err.response?.data?.detail || err.message || '开始游戏失败'
    ElMessage.error(msg)
  } finally {
    startLoading.value = false
  }
}

// 切换为观战者
const handleSwitchToSpectator = async () => {
  if (!roomData.value) return
  switchRoleLoading.value = true
  try {
    const data = await switchRole(roomData.value.id, true)
    roomData.value = data
    roomStore.setRoom(data)
    ElMessage.success('已切换为观战者')
  } catch (err: any) {
    const msg = err.response?.data?.detail || err.message || '切换失败'
    ElMessage.error(msg)
  } finally {
    switchRoleLoading.value = false
  }
}

// 切换为玩家
const handleSwitchToPlayer = async () => {
  if (!roomData.value) return
  switchRoleLoading.value = true
  try {
    const data = await switchRole(roomData.value.id, false)
    roomData.value = data
    roomStore.setRoom(data)
    ElMessage.success('已切换为玩家')
  } catch (err: any) {
    const msg = err.response?.data?.detail || err.message || '切换失败'
    ElMessage.error(msg)
  } finally {
    switchRoleLoading.value = false
  }
}

// 返回（不离开房间，只是导航到上一页）
const handleBack = () => {
  router.back()
}

// 进入游戏（从房间页面手动进入）
const handleEnterGame = () => {
  if (!roomData.value) return
  roomStore.stopPolling()
  stopChatPolling()
  router.push(`/game/${roomData.value.id}`)
}

// 游戏结束后获胜者昵称
const winnerNickname = computed(() => {
  if (!roomStore.gameOverData?.rankings?.length) return '—'
  const winner = roomStore.gameOverData.rankings.find(r => r.rank === 1)
  return winner?.nickname ?? '—'
})

// 房主重置房间
const resetLoading = ref(false)
const handleResetRoom = async () => {
  if (!roomData.value) return
  resetLoading.value = true
  try {
    const data = await resetRoom(roomData.value.id)
    roomData.value = data
    roomStore.setRoom(data)
    ElMessage.success('房间已重置，可以重新开始')
  } catch (err: any) {
    const msg = err.response?.data?.detail || err.message || '重置失败'
    ElMessage.error(msg)
  } finally {
    resetLoading.value = false
  }
}

// 离开房间（真正退出）
const handleLeave = async () => {
  if (!roomData.value) {
    router.push('/')
    return
  }

  // 房主离开会销毁房间，二次确认
  if (isHost.value) {
    try {
      await ElMessageBox.confirm(
        '房主离开后房间将被销毁，其他玩家也会被移出。确定离开吗？',
        '离开房间',
        { confirmButtonText: '确定离开', cancelButtonText: '取消', type: 'warning' },
      )
    } catch {
      return
    }
  }

  try {
    await leaveRoom(roomData.value.id)
  } catch {
    // 忽略错误（可能房间已被销毁）
  }
  roomStore.reset()
  stopChatPolling()
  router.push('/')
}

onMounted(async () => {
  await fetchRoom()
  loading.value = false

  // 加载聊天历史
  await fetchMessages()
  await nextTick()
  scrollToBottom()

  // 轮询房间状态
  roomStore.startPolling(fetchRoom, 3000)
  // 轮询聊天消息
  startChatPolling()
})

onUnmounted(() => {
  roomStore.stopPolling()
  stopChatPolling()
})
</script>

<style scoped>
.room-page {
  width: 100%;
  height: 100%;
}

.room-body {
  height: calc(100vh - 80px);
}

.room-main {
  padding: 12px 0 0 0;
}

/* 覆盖 Element Plus .el-button+.el-button 的默认 margin-left: 12px，
   避免在 flex-col 布局中按钮错位 */
.flex-col > .el-button + .el-button {
  margin-left: 0;
}

/* 玩家列表卡片高度自适应 */
.player-card {
  max-height: 280px;
}
.player-card :deep(.el-card__body) {
  max-height: 200px;
  overflow-y: auto;
}

.player-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.player-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
}

.player-name {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100px;
}

/* 聊天区 */
.chat-card {
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
}
.chat-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chat-loading,
.chat-empty {
  text-align: center;
  color: #999;
  padding: 20px 0;
  font-size: 13px;
}

.load-more {
  text-align: center;
  color: #409eff;
  cursor: pointer;
  font-size: 12px;
  padding: 6px 0;
}
.load-more:hover {
  text-decoration: underline;
}

.chat-msg {
  max-width: 80%;
  padding: 6px 10px;
  border-radius: 8px;
  background: #f4f4f5;
  word-break: break-word;
}
.chat-msg-self {
  align-self: flex-end;
  background: #ecf5ff;
}
.chat-msg-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}
.chat-msg-nickname {
  font-size: 12px;
  font-weight: 600;
  color: #606266;
}
.chat-msg-time {
  font-size: 11px;
  color: #c0c4cc;
}
.chat-msg-content {
  font-size: 14px;
  color: #303133;
  line-height: 1.5;
}

.chat-input {
  padding: 10px 12px;
  border-top: 1px solid #ebeef5;
}

/* 观战者列表 */
.spectator-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.spectator-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 0;
}

.spectator-name {
  font-size: 13px;
  color: #909399;
}

/* 游戏结束回顾 */
.gameover-card :deep(.el-card__body) {
  padding: 12px 16px;
}

.gameover-rankings {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.gameover-rank-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  border-radius: 8px;
  background: #f5f7fa;
}

.gameover-rank-row.rank-row-me {
  background: #ecf5ff;
  border: 1px solid #409eff;
}

.rank-pos {
  font-size: 20px;
  min-width: 36px;
  text-align: center;
}

.rank-name {
  flex: 1;
  font-weight: 600;
  font-size: 14px;
}

.rank-assets {
  font-weight: 700;
  color: #e6a23c;
  font-size: 14px;
}

.gameover-summary {
  text-align: center;
  padding: 8px 0;
}

.gameover-winner {
  font-size: 16px;
  font-weight: 600;
  color: #e6a23c;
}
</style>
