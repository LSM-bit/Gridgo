<template>
  <div class="room-page">
    <!-- 顶栏：房间票头 -->
    <header class="room-bar">
      <el-button text class="room-bar__back" @click="handleBack">← 返回</el-button>
      <span class="room-bar__title">{{ roomData?.name || '房间' }}</span>
      <span class="room-bar__code" :title="'房间代码 ' + code">{{ code }}</span>
      <el-button size="small" @click="copyCode">复制代码</el-button>
      <span class="room-bar__status" :data-status="roomData?.status">{{ statusText }}</span>
      <span class="room-bar__spacer"></span>
      <span class="room-bar__meta">
        {{ roomData?.players.length || 0 }}/{{ roomData?.max_players || 8 }} 玩家 ·
        观战 {{ roomData?.spectators?.length || 0 }}/{{ roomData?.max_spectators || 10 }}
      </span>
      <el-button size="small" type="danger" plain @click="handleLeave">离开房间</el-button>
    </header>

    <!-- 主体 -->
    <main class="room-main" v-loading="loading">
      <section class="room-col room-col--main">
        <!-- 玩家席位 -->
        <div class="room-panel room-panel--wide">
          <header class="room-panel__head">
            <span class="gg-kicker">SEATS · 玩家席位</span>
            <span class="room-panel__meta gg-num">
              {{ roomData?.players.length || 0 }}/{{ roomData?.max_players || 8 }}
            </span>
          </header>
          <div class="room-panel__body">
            <div class="seat-grid">
              <div
                v-for="n in seatCount"
                :key="'seat-' + n"
                class="seat"
                :class="{ 'seat--empty': !playerAt(n - 1), 'seat--me': playerAt(n - 1)?.user_id === userStore.userId }"
              >
                <template v-if="playerAt(n - 1)">
                  <span class="seat__no">{{ pad(n) }}</span>
                  <span class="seat__avatar">
                    <img v-if="playerAt(n - 1)?.avatar" :src="playerAt(n - 1)!.avatar!" alt="" />
                    <span v-else>{{ playerAt(n - 1)!.is_ai ? 'AI' : playerAt(n - 1)!.nickname.charAt(0) }}</span>
                  </span>
                  <span class="seat__info">
                    <span class="seat__name">{{ playerAt(n - 1)!.nickname }}</span>
                    <span class="seat__tags">
                      <el-tag v-if="playerAt(n - 1)!.is_host" type="warning" size="small">房主</el-tag>
                      <el-tag v-if="playerAt(n - 1)!.is_ai" type="info" size="small">
                        AI · {{ difficultyText(playerAt(n - 1)!.ai_difficulty) }}
                      </el-tag>
                      <el-tag
                        v-else-if="!playerAt(n - 1)!.is_host"
                        :type="playerAt(n - 1)!.is_ready ? 'success' : 'info'"
                        size="small"
                      >
                        {{ playerAt(n - 1)!.is_ready ? '已准备' : '未准备' }}
                      </el-tag>
                      <el-tag v-if="playerAt(n - 1)!.user_id === userStore.userId" size="small">我</el-tag>
                    </span>
                  </span>
                </template>
                <template v-else>
                  <span class="seat__no">{{ pad(n) }}</span>
                  <span class="seat__empty">空席 · 等待玩家</span>
                </template>
              </div>
            </div>

            <p class="room-panel__hint">
              把房间代码 <b class="gg-num">{{ code }}</b> 发给好友即可邀请入座
            </p>
          </div>
        </div>

        <!-- 观战席 -->
        <div class="room-panel">
          <header class="room-panel__head">
            <span class="gg-kicker">SPECTATE · 观战席</span>
            <span class="room-panel__meta gg-num">
              {{ roomData?.spectators?.length || 0 }}/{{ roomData?.max_spectators || 10 }}
            </span>
          </header>
          <div class="room-panel__body">
            <div v-if="(roomData?.spectators?.length ?? 0) > 0" class="watch-list">
              <div v-for="s in roomData?.spectators || []" :key="s.user_id" class="watch-row">
                <span class="watch-row__name">{{ s.nickname }}</span>
                <el-tag v-if="s.is_host" type="warning" size="small">房主</el-tag>
                <el-tag v-if="s.user_id === userStore.userId" size="small">我</el-tag>
              </div>
            </div>
            <div v-else class="room-empty">
              <span class="room-empty__mark">◌</span>
              <span>暂无观战者</span>
            </div>
          </div>
        </div>

        <!-- 操作台 -->
        <div class="room-panel">
          <header class="room-panel__head">
            <span class="gg-kicker">ACTIONS · 操作台</span>
            <span class="room-panel__meta">{{ roleText }}</span>
          </header>
          <div class="room-panel__body room-panel__body--ops">
            <!-- 已结束 -->
            <template v-if="roomData?.status === 'finished'">
              <div class="ops-note ops-note--danger">本局已结束 · 获胜者 {{ winnerNickname }}</div>
              <el-button v-if="isHost" type="primary" class="ops-btn" :loading="resetLoading" @click="handleResetRoom">
                返回准备阶段
              </el-button>
              <p v-else class="ops-hint">等待房主重置房间</p>
            </template>

            <!-- 进行中 -->
            <template v-else-if="roomData?.status === 'playing'">
              <div class="ops-note ops-note--ok">对局进行中</div>
              <el-button type="primary" class="ops-btn" @click="handleEnterGame">进入游戏</el-button>
            </template>

            <!-- 等待中 -->
            <template v-else>
              <template v-if="isHost">
                <el-button
                  type="primary"
                  class="ops-btn"
                  :disabled="!canStart"
                  :loading="startLoading"
                  @click="handleStart"
                >
                  开始游戏
                </el-button>
                <p v-if="!canStart" class="ops-hint">{{ startHint }}</p>
                <el-button class="ops-btn" @click="showSettingsDialog = true">房间设置</el-button>
              </template>

              <template v-if="isSpectator">
                <div class="ops-note">观战模式 · 无法参与对局操作</div>
                <el-button
                  v-if="(roomData?.players.length ?? 0) < (roomData?.max_players ?? 8)"
                  type="primary"
                  plain
                  class="ops-btn"
                  :loading="switchRoleLoading"
                  @click="handleSwitchToPlayer"
                >
                  加入玩家席
                </el-button>
              </template>

              <template v-if="!isHost && !isSpectator">
                <el-button
                  :type="amReady ? 'success' : 'primary'"
                  class="ops-btn"
                  :loading="readyLoading"
                  @click="handleToggleReady"
                >
                  {{ amReady ? '已准备（点击取消）' : '点击准备' }}
                </el-button>
              </template>

              <el-button
                v-if="!isSpectator"
                plain
                class="ops-btn"
                :loading="switchRoleLoading"
                @click="handleSwitchToSpectator"
              >
                切换为观战
              </el-button>
            </template>
          </div>
        </div>

        <!-- 房间信息 -->
        <div class="room-panel room-panel--wide">
          <header class="room-panel__head">
            <span class="gg-kicker">ROOM INFO · 房间信息</span>
          </header>
          <div class="room-panel__body">
            <dl class="info-grid">
              <div class="info-grid__row"><dt>房间名称</dt><dd>{{ roomData?.name || '—' }}</dd></div>
              <div class="info-grid__row"><dt>房间代码</dt><dd class="gg-num">{{ code }}</dd></div>
              <div class="info-grid__row"><dt>地图</dt><dd>{{ mapLabel }}</dd></div>
              <div class="info-grid__row"><dt>最大人数</dt><dd class="gg-num">{{ roomData?.max_players ?? '—' }}</dd></div>
              <div class="info-grid__row"><dt>AI 数量</dt><dd class="gg-num">{{ roomData?.ai_count ?? 0 }}</dd></div>
              <div class="info-grid__row">
                <dt>AI 难度</dt>
                <dd>{{ (roomData?.ai_count ?? 0) > 0 ? difficultyText(roomData?.ai_difficulty) : '—' }}</dd>
              </div>
              <div class="info-grid__row">
                <dt>房间密码</dt>
                <dd>{{ roomData?.has_password ? '已设置' : '无密码' }}</dd>
              </div>
              <div class="info-grid__row"><dt>房主</dt><dd>{{ hostNickname }}</dd></div>
            </dl>
          </div>
        </div>
      </section>

      <!-- 聊天列 -->
      <aside class="room-col room-col--side">
        <div v-if="roomData?.status === 'finished' && roomStore.gameOverData" class="room-panel room-panel--result">
          <header class="room-panel__head">
            <span class="gg-kicker">RESULT · 对局结果</span>
            <span class="room-panel__meta gg-num">{{ roomStore.gameOverData.total_turns }} 回合</span>
          </header>
          <div class="room-panel__body">
            <div class="result-list">
              <div
                v-for="(r, i) in roomStore.gameOverData.rankings"
                :key="r.user_id"
                class="result-row"
                :class="{ 'result-row--me': r.user_id === userStore.userId }"
              >
                <span class="result-row__pos">{{ ['01', '02', '03'][i] || `#${r.rank}` }}</span>
                <span class="result-row__name">{{ r.is_ai ? 'AI · ' : '' }}{{ r.nickname }}</span>
                <span class="result-row__assets gg-num">¥{{ r.total_assets.toLocaleString() }}</span>
                <el-tag v-if="r.is_bankrupt" type="danger" size="small">破产</el-tag>
              </div>
            </div>
          </div>
        </div>

        <div class="room-panel room-panel--chat">
          <header class="room-panel__head">
            <span class="gg-kicker">CHAT · 房间聊天</span>
            <span class="room-panel__meta gg-num">{{ messages.length }} 条</span>
          </header>

          <div ref="chatContainer" class="chat-messages" @scroll="onChatScroll">
            <div v-if="chatLoading" class="chat-state">加载更早的消息…</div>
            <div v-if="hasMoreMessages" class="chat-more" @click="loadOlderMessages">↑ 加载更早的消息</div>
            <div v-if="!chatLoading && messages.length === 0" class="chat-state chat-state--empty">
              <span class="chat-state__mark">✉</span>
              <span class="chat-state__title">房间里还没有人说话</span>
              <span class="chat-state__hint">发条消息，约对手开一局</span>
            </div>
            <div
              v-for="msg in messages"
              :key="msg.id"
              class="chat-msg"
              :class="{ 'chat-msg--self': msg.user_id === userStore.userId }"
            >
              <div class="chat-msg__meta">
                <span class="chat-msg__name">{{ msg.is_ai ? 'AI · ' : '' }}{{ msg.nickname }}</span>
                <span class="chat-msg__time gg-num">{{ formatTime(msg.created_at) }}</span>
              </div>
              <div class="chat-msg__content">{{ msg.content }}</div>
            </div>
          </div>

          <div class="chat-input">
            <el-input v-model="chatInput" placeholder="输入消息…" maxlength="500" @keyup.enter="handleSendMessage">
              <template #append>
                <el-button :loading="sendLoading" @click="handleSendMessage">发送</el-button>
              </template>
            </el-input>
          </div>
        </div>
      </aside>
    </main>

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
            <el-radio-button v-for="m in MAP_OPTIONS" :key="m.value" :value="m.value">
              {{ m.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="AI 数量">
          <el-slider v-model="settingsForm.ai_count" :min="0" :max="settingsMaxAi" :step="1" show-stops />
        </el-form-item>

        <el-form-item v-if="(settingsForm.ai_count ?? 0) > 0" label="AI 难度">
          <el-radio-group v-model="settingsForm.ai_difficulty">
            <el-radio-button v-for="opt in AI_DIFFICULTY_OPTIONS" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="房间密码">
          <el-switch v-model="settingsPasswordEnabled" active-text="启用密码" inline-prompt />
          <span class="settings-hint">
            {{ roomData?.has_password ? '当前房间已设置密码' : '当前房间无密码' }}
          </span>
        </el-form-item>

        <el-form-item v-if="settingsPasswordEnabled" label="新密码">
          <el-input
            v-model="settingsPassword"
            type="password"
            show-password
            maxlength="32"
            placeholder="留空则保持原密码不变"
          />
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
  if (roomData.value.players.length < 2) return '至少需要 2 名玩家才能开始'
  if (!roomData.value.players.every((p) => p.is_ready || p.is_host || p.is_ai)) return '还有玩家未准备'
  return ''
})

// 席位数量（至少 2 个，最多 8 个）
const seatCount = computed(() => Math.max(2, roomData.value?.max_players ?? 4))

const playerAt = (index: number) => roomData.value?.players[index] ?? null

const pad = (value: number) => String(value).padStart(2, '0')

const hostNickname = computed(() => {
  if (!roomData.value) return '—'
  const host = roomData.value.players.find((p) => p.user_id === roomData.value!.host_id)
  return host?.nickname ?? '—'
})

const roleText = computed(() => {
  if (roomData.value?.status === 'waiting') {
    if (isHost.value) return '房主'
    if (isSpectator.value) return '观战者'
    return '玩家'
  }
  return roomData.value?.status === 'playing' ? '对局中' : '已结束'
})

const statusText = computed(
  () =>
    ({ waiting: '等待中', playing: '对局中', finished: '已结束' })[roomData.value?.status ?? ''] ??
    '未知状态',
)

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

// 滚动事件（预留：用户手动上翻时不自动滚到底）
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

// 房间密码（对齐后端 UpdateRoomData.password / clear_password）
const settingsPasswordEnabled = ref(false)
const settingsPassword = ref('')

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
    settingsPasswordEnabled.value = !!roomData.value.has_password
    settingsPassword.value = ''
  }
})

// 最大人数变化时限制 AI 数量
watch(
  () => settingsForm.value.max_players,
  () => {
    if ((settingsForm.value.ai_count ?? 0) > settingsMaxAi.value) {
      settingsForm.value.ai_count = settingsMaxAi.value
    }
  },
)

const handleSaveSettings = async () => {
  if (!roomData.value) return
  settingsLoading.value = true
  roomStore.stopPolling()
  try {
    const payload: UpdateRoomData = { ...settingsForm.value }
    const nextPassword = settingsPassword.value.trim()
    if (settingsPasswordEnabled.value) {
      if (nextPassword) payload.password = nextPassword
    } else if (roomData.value.has_password) {
      payload.clear_password = true
    }
    const data = await updateRoomSettings(roomData.value.id, payload)
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
  const winner = roomStore.gameOverData.rankings.find((r) => r.rank === 1)
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
/**
 * 房间页：票据式顶栏 + 主列（席位/观战/操作台/房间信息）+ 聊天列。
 * 主列两栏网格铺满宽度，聊天列撑满视口高度，消除右侧与下半部留白。
 */
.room-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  width: 100%;
  background-color: var(--gg-bg);
  background-image: var(--gg-grid);
  background-size: 24px 24px, 24px 24px;
}

/* ── 顶栏 ── */
.room-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 10px 22px;
  background: var(--gg-grad-night);
  border-bottom: 3px double #16130f;
  color: #f2ead9;
  position: sticky;
  top: 0;
  z-index: 10;
}

.room-bar__back {
  color: rgba(242, 234, 217, 0.78);
}

.room-bar__back:hover {
  color: #fdf7ea;
  background: rgba(255, 255, 255, 0.08);
}

.room-bar__title {
  font-family: var(--gg-font-display);
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.03em;
  color: #fdf7ea;
}

.room-bar__code {
  font-family: var(--gg-font-mono);
  font-size: 12px;
  letter-spacing: 0.18em;
  padding: 3px 9px;
  border: 1px dashed rgba(242, 234, 217, 0.42);
  color: var(--gg-gold);
}

.room-bar__status {
  font-family: var(--gg-font-mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  padding: 3px 8px;
  border: 1px solid rgba(242, 234, 217, 0.34);
}

.room-bar__status[data-status='waiting'] {
  color: #9fd3b1;
  border-color: rgba(159, 211, 177, 0.5);
}

.room-bar__status[data-status='playing'] {
  background: var(--gg-brand);
  border-color: #6f1d13;
  color: #fdf3ea;
}

.room-bar__status[data-status='finished'] {
  color: #f0b7ab;
  border-color: rgba(240, 183, 171, 0.5);
}

.room-bar__spacer {
  flex: 1 1 auto;
}

.room-bar__meta {
  font-family: var(--gg-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.1em;
  color: rgba(242, 234, 217, 0.64);
}

/* ── 主体 ── */
.room-main {
  flex: 1 1 auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 360px);
  gap: 14px;
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 16px 22px 20px;
  box-sizing: border-box;
  min-height: calc(100vh - 62px);
  animation: gg-fade-up var(--gg-dur-slow) var(--gg-ease-out) both;
}

.room-col {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
  min-height: 0;
}

.room-col--main {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-auto-rows: auto;
  gap: 14px;
  align-content: start;
}

.room-col--side {
  min-height: 0;
}

.room-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--gg-surface);
  border: 1px solid var(--gg-border-strong);
  box-shadow: var(--gg-shadow-1);
}

.room-panel--wide {
  grid-column: 1 / -1;
}

.room-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 9px 14px;
  background: var(--gg-surface-2);
  border-bottom: 1px dashed var(--gg-border-strong);
}

.room-panel__meta {
  font-family: var(--gg-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.12em;
  color: var(--gg-ink-3);
}

.room-panel__body {
  padding: 13px 14px;
}

.room-panel__body--ops {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.room-panel__hint {
  margin: 12px 0 0;
  font-size: 11.5px;
  color: var(--gg-ink-3);
}

.room-panel__hint b {
  color: var(--gg-brand);
  letter-spacing: 0.14em;
}

/* ── 席位 ── */
.seat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
}

.seat {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 11px;
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border);
  border-left: 2px solid var(--gg-border-strong);
  min-width: 0;
  transition: border-color var(--gg-dur) var(--gg-ease), background-color var(--gg-dur) var(--gg-ease);
}

.seat--me {
  border-left-color: var(--gg-brand);
  background: var(--gg-brand-soft);
}

.seat--empty {
  border-style: dashed;
  background: transparent;
}

.seat__no {
  flex: 0 0 auto;
  font-family: var(--gg-font-mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--gg-ink-4);
}

.seat__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
  overflow: hidden;
  font-family: var(--gg-font-display);
  font-size: 12px;
  font-weight: 700;
  color: var(--gg-ink-2);
  background: var(--gg-surface);
  border: 1px solid var(--gg-border-strong);
}

.seat__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.seat__info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.seat__name {
  font-size: 13px;
  font-weight: 700;
  color: var(--gg-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.seat__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.seat__empty {
  font-size: 12px;
  color: var(--gg-ink-4);
}

/* ── 观战 ── */
.watch-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.watch-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border);
}

.watch-row__name {
  font-size: 12.5px;
  color: var(--gg-ink-2);
}

.room-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 20px 12px;
  font-size: 12px;
  color: var(--gg-ink-4);
  border: 1px dashed var(--gg-border-strong);
}

.room-empty__mark {
  font-size: 18px;
  color: var(--gg-gold);
}

/* ── 操作台 ── */
.ops-btn {
  width: 100%;
}

.ops-note {
  padding: 8px 10px;
  font-size: 12px;
  color: var(--gg-ink-2);
  background: var(--gg-surface-2);
  border: 1px dashed var(--gg-border-strong);
}

.ops-note--ok {
  color: var(--gg-green);
  border-color: rgba(63, 102, 78, 0.45);
  background: var(--gg-green-soft);
}

.ops-note--danger {
  color: var(--gg-brand-strong);
  border-color: rgba(176, 57, 44, 0.45);
  background: var(--gg-brand-soft);
}

.ops-hint {
  margin: 0;
  font-size: 11.5px;
  color: var(--gg-ink-3);
  text-align: center;
}

/* ── 房间信息 ── */
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px 18px;
  margin: 0;
}

.info-grid__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 6px;
  border-bottom: 1px dotted var(--gg-border);
}

.info-grid__row dt {
  font-size: 11.5px;
  letter-spacing: 0.08em;
  color: var(--gg-ink-3);
  white-space: nowrap;
}

.info-grid__row dd {
  margin: 0;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--gg-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── 结果面板 ── */
.room-panel--result {
  flex: 0 0 auto;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.result-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 10px;
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border);
}

.result-row--me {
  background: var(--gg-brand-soft);
  border-color: rgba(176, 57, 44, 0.35);
}

.result-row__pos {
  font-family: var(--gg-font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--gg-gold-strong);
}

.result-row__name {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--gg-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-row__assets {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--gg-gold-strong);
}

/* ── 聊天 ── */
.room-panel--chat {
  flex: 1 1 auto;
  min-height: 380px;
}

.room-panel--chat .room-panel__body,
.chat-messages {
  min-height: 0;
}

.chat-messages {
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 13px 14px;
  display: flex;
  flex-direction: column;
  gap: 9px;
  scrollbar-width: thin;
}

.chat-state {
  padding: 14px 10px;
  text-align: center;
  font-size: 11.5px;
  color: var(--gg-ink-4);
}

.chat-state--empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  flex: 1 1 auto;
  min-height: 150px;
  border: 1px dashed var(--gg-border-strong);
  background: var(--gg-bg-deep);
}

.chat-state__mark {
  font-size: 20px;
  color: var(--gg-gold);
}

.chat-state__title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--gg-ink-2);
}

.chat-state__hint {
  font-size: 11.5px;
  color: var(--gg-ink-4);
}

.chat-more {
  padding: 4px;
  font-size: 11.5px;
  text-align: center;
  color: var(--gg-brand);
  border: 1px dashed var(--gg-border-strong);
  cursor: pointer;
}

.chat-more:hover {
  background: var(--gg-brand-soft);
}

.chat-msg {
  max-width: 88%;
  padding: 7px 10px;
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border);
  border-left: 2px solid var(--gg-border-strong);
  animation: gg-fade-up var(--gg-dur) var(--gg-ease-out) both;
}

.chat-msg--self {
  margin-left: auto;
  background: var(--gg-brand-soft);
  border-left-color: var(--gg-brand);
}

.chat-msg__meta {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 3px;
}

.chat-msg__name {
  font-size: 11px;
  font-weight: 600;
  color: var(--gg-ink-2);
}

.chat-msg--self .chat-msg__name {
  color: var(--gg-brand);
}

.chat-msg__time {
  font-size: 10px;
  color: var(--gg-ink-4);
}

.chat-msg__content {
  font-size: 13px;
  line-height: 1.55;
  color: var(--gg-ink);
  word-break: break-word;
}

.chat-input {
  padding: 11px 14px;
  border-top: 1px dashed var(--gg-border-strong);
  background: var(--gg-surface-2);
}

.settings-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--gg-ink-3);
  line-height: 1.6;
}

@media (max-width: 1080px) {
  .room-main {
    grid-template-columns: minmax(0, 1fr);
    min-height: 0;
  }

  .room-col--main {
    grid-template-columns: minmax(0, 1fr);
  }

  .room-panel--wide {
    grid-column: auto;
  }

  .room-panel--chat {
    min-height: 320px;
  }
}

@media (max-width: 640px) {
  .room-bar {
    padding: 10px 14px;
    gap: 8px;
  }

  .room-main {
    padding: 14px 12px 18px;
  }

  .seat-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .info-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .room-bar__meta {
    width: 100%;
  }
}
</style>
