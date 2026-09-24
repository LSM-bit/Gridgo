<template>
  <GameLayout>
    <template #status>
      <span class="gg-chip gg-chip--phase">{{ phaseText }}</span>
      <!-- 回合 / 决策 / 拍卖倒计时：服务端不推送逐秒 tick，剩余秒数由前端本地递减 -->
      <span
        v-if="turnCountdownRunning"
        class="gg-chip gg-chip--timer"
        :data-on="turnSecondsLeft <= 5 ? 'no' : 'yes'"
      >
        {{ turnCountdownLabel }} {{ turnSecondsLeft }}s
      </span>
      <span class="game-status__wait">{{ waitText }}</span>
      <DicePanel :values="diceValues" :is-double="state?.dice.is_double ?? false" :rolling="isAnimating" />
      <span v-if="store.isSpectator" class="gg-chip">观战</span>
      <span v-if="syncing" class="gg-chip gg-chip--syncing">同步中…</span>
      <span class="gg-chip" :data-on="store.connected ? 'yes' : 'no'">
        {{ store.connected ? 'WS 已连接' : 'WS 已断开' }}
      </span>
    </template>

    <template #actions>
      <el-button size="small" @click="showLog = !showLog">{{ showLog ? '隐藏日志' : '显示日志' }}</el-button>
      <el-button
        size="small"
        type="warning"
        plain
        :disabled="store.isSpectator || store.isGameOver"
        @click="handleQuitGame"
      >
        退出本局（AI 接管）
      </el-button>
      <el-button size="small" type="danger" plain @click="handleLeave">离开对局</el-button>
    </template>

    <div class="game-page">
      <!-- ── 棋盘票面 ── -->
      <section class="game-page__board">
        <header class="game-page__board-head">
          <span class="gg-kicker">BOARD · 11 × 11</span>
          <span class="game-page__board-meta">
            第 <b class="gg-num">{{ state?.turn_number ?? 0 }}</b> 回合 ·
            <b class="gg-num">{{ (state?.players ?? []).length }}</b> 位玩家 ·
            地块 <b class="gg-num">{{ (state?.tiles ?? []).length }}</b>
          </span>
        </header>

        <div class="game-page__board-canvas">
          <GameBoard
            ref="boardRef"
            :state="state"
            :current-user-id="store.currentUserId"
            :highlight="highlight"
            :selected="selectedPosition"
            :center-lines="centerLines"
            @select="handleTileSelect"
            @select-player="handlePlayerSelect"
          />
        </div>

        <footer class="game-page__board-foot">
          <span class="gg-stamp gg-stamp--ink">GRIDGO</span>
          <span class="game-page__board-hint">点击地块查看地块详情 · 点击棋子查看玩家信息 · 建造 / 抵押 / 赎回</span>
          <span v-if="store.myPlayer" class="game-page__board-me">
            {{ store.myPlayer.nickname }} · {{ formatMoney(store.myPlayer.cash) }} · 地产
            <b class="gg-num">{{ store.myProperties.length }}</b> 处
          </span>
        </footer>
      </section>

      <!-- ── 侧栏票册 ── -->
      <aside class="game-page__side">
        <el-alert
          v-if="offline"
          class="game-page__alert"
          type="error"
          show-icon
          :closable="false"
          :title="offlineTitle"
          :description="offlineDescription"
        />

        <el-alert
          v-if="store.reconnectNotice"
          class="game-page__alert"
          type="warning"
          show-icon
          :closable="true"
          :title="`${playerName(store.reconnectNotice.playerId)} 已重连`"
          :description="`${store.reconnectNotice.modeText} · 离线 ${store.reconnectNotice.offlineSeconds}s`"
          @close="store.reconnectNotice = null"
        />

        <el-card shadow="never" class="action-card">
          <template #header>
            <div class="action-card__header">
              <span class="gg-kicker">01 · 我的操作</span>
              <span class="action-card__cash gg-num">{{ formatMoney(store.myPlayer?.cash ?? 0) }}</span>
            </div>
          </template>

          <div v-if="store.pendingDecision" class="action-card__decision">
            <span class="action-card__decision-title">待决事项</span>
            <p class="action-card__text">
              是否购买 {{ store.pendingDecision.tile_name }}（{{ formatMoney(store.pendingDecision.price) }}）？
            </p>
            <div class="action-card__row">
              <el-button type="primary" :disabled="offline || !store.canBuyProperty" @click="handleBuy">购买</el-button>
              <el-button :disabled="offline || !store.canBuyProperty" @click="handleDecline">放弃</el-button>
            </div>
          </div>

          <div class="action-card__row">
            <el-button type="primary" :disabled="offline || !store.canRoll" @click="store.sendRollDice()">掷骰子</el-button>
            <el-button :disabled="offline || !store.canAct" @click="store.sendEndTurn()">结束回合</el-button>
          </div>

          <div v-if="store.isInJail" class="action-card__row">
            <el-button size="small" :disabled="offline || !store.isMyTurn" @click="store.sendJailPayBail()">
              支付保释金 {{ formatMoney(state?.jail_bail ?? 0) }}
            </el-button>
            <el-button size="small" :disabled="offline || !store.hasJailCard" @click="store.sendJailUseCard()">使用免罪卡</el-button>
          </div>

          <template v-if="selectedTile">
            <div class="gg-perf action-card__sep"></div>
            <p class="action-card__text">
              已选地块：{{ selectedTile.name }}
              <span v-if="selectedTile.owner_id === store.currentUserId">（我的）</span>
            </p>
            <div class="action-card__row">
              <el-button size="small" :disabled="!canOperateTile" @click="store.sendBuild(selectedTile.position)">
                建造 {{ formatMoney(selectedTile.build_cost ?? 0) }}
              </el-button>
              <el-button size="small" :disabled="!canOperateTile || selectedTile.build_level === 0" @click="store.sendDemolish(selectedTile.position)">
                拆除
              </el-button>
            </div>
            <div class="action-card__row">
              <el-button size="small" :disabled="!canOperateTile || selectedTile.is_mortgaged" @click="store.sendMortgage(selectedTile.position)">
                抵押
              </el-button>
              <el-button size="small" :disabled="!canOperateTile || !selectedTile.is_mortgaged" @click="store.sendRedeem(selectedTile.position)">
                赎回
              </el-button>
            </div>
          </template>

          <p v-if="offline" class="action-card__idle action-card__idle--offline">
            连接已断开，掷骰子 / 结束回合 / 建造等操作已暂停，正在自动重连…
          </p>
          <p v-else-if="!store.canRoll && !store.canAct && !selectedTile" class="action-card__idle">
            等待对手行动中，可先查看地块与聊天
          </p>
        </el-card>

        <PlayerPanel
          :players="state?.players ?? []"
          :current-user-id="store.currentUserId"
          :current-player-index="state?.current_player_index ?? 0"
          :turn-number="state?.turn_number ?? 0"
          :disabled="store.isSpectator"
          @select="focusPlayer"
          @trade="openTradeWith"
        />

        <AuctionPanel
          :auction="store.activeAuction"
          :players="state?.players ?? []"
          :tiles="state?.tiles ?? []"
          :current-user-id="store.currentUserId"
          :is-spectator="store.isSpectator"
          :connected="!offline"
          @bid="handleBid"
        />

        <TradePanel
          :incoming="store.incomingTrades"
          :outgoing="store.outgoingTrades"
          :players="state?.players ?? []"
          :tiles="state?.tiles ?? []"
          :current-user-id="store.currentUserId"
          :connected="!offline"
          @accept="handleTradeAccept"
          @reject="handleTradeReject"
          @submit="handleTradeSubmit"
        />

        <ChatPanel :room-id="roomId" :current-user-id="store.currentUserId" />

        <LogPanel v-if="showLog" :logs="store.logs" />
      </aside>
    </div>

    <TileDetailDialog
      v-model="showTileDialog"
      :tile="selectedTile"
      :owner-name="selectedTileOwnerName"
      :max-build-level="state?.max_build_level ?? 5"
    />

    <!-- 点击棋子（或右侧玩家卡片）→ 展示玩家信息，而非棋子所在格子的地块信息 -->
    <PlayerDetailDialog
      v-model="showPlayerDialog"
      :player="selectedPlayer"
      :tiles="state?.tiles ?? []"
      :current-user-id="store.currentUserId"
      :current-player-id="store.currentPlayer?.user_id ?? null"
      @trade="openTradeWith"
    />

    <ChanceCard :card="store.activeCard" :player-name="cardPlayerName" @close="store.dismissCard()" />

    <GameOverDialog
      :model-value="showGameOver"
      :data="gameOver"
      :end-reason-text="endReasonText"
      :current-user-id="store.currentUserId"
      @update:model-value="showGameOver = $event"
      @view-replay="handleViewReplay"
      @back="handleLeave(true)"
    />
  </GameLayout>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import GameLayout from '@/layouts/GameLayout.vue'
import GameBoard from '@/components/board/GameBoard.vue'
import TileDetailDialog from '@/components/board/TileDetailDialog.vue'
import AuctionPanel from '@/components/card/AuctionPanel.vue'
import ChanceCard from '@/components/card/ChanceCard.vue'
import DicePanel from '@/components/card/DicePanel.vue'
import PlayerPanel from '@/components/player/PlayerPanel.vue'
import PlayerDetailDialog from '@/components/player/PlayerDetailDialog.vue'
import TradePanel from '@/components/player/TradePanel.vue'
import { ChatPanel, LogPanel, GameOverDialog } from '@/components/common'
import { useGame } from '@/composables/useGame'
import { useLocalCountdown } from '@/composables/useLocalCountdown'
import { countdownResetKey, phaseCountdownSeconds } from '@/utils/gameTimer'
import { formatMoney } from '@/utils/format'
import { leaveRoom } from '@/api/room'
import { quitFailText } from '@/stores/game'
import type { TradeOfferPayload } from '@/types/game'
import type { BoardRenderer } from '@/game/renderer'

const route = useRoute()
const router = useRouter()

const {
  store,
  roomStore,
  roomId,
  gameOver,
  showGameOver,
  endReasonText,
  phaseText,
  phaseTagType,
  waitText,
  playerName,
  anim,
  start,
  stop,
  syncing,
  sendTradeOffer,
} = useGame()

const { isAnimating, diceValues, bind } = anim

const boardRef = ref<InstanceType<typeof GameBoard> | null>(null)
const showLog = ref(false)
const showTileDialog = ref(false)
const selectedPosition = ref<number | null>(null)
const showPlayerDialog = ref(false)
const selectedPlayerId = ref<number | null>(null)

const state = computed(() => store.state)

/**
 * 连接异常保护：WS 断开 / 初始化失败时进入"只读保护"，
 * 掷骰子、结束回合、买卖建造、交易、出价等会改状态的按钮一律禁用，避免静默无效点击。
 */
const offline = computed(() => !store.connected)
const linkFailLabel = ref('')
const linkFailMessage = ref('')
const offlineTitle = computed(() => (linkFailLabel.value ? `${linkFailLabel.value}，操作已暂停` : '连接已断开，操作已暂停'))
const offlineDescription = computed(
  () => linkFailMessage.value || '正在自动重连，连接恢复后可继续操作',
)
const selectedTile = computed(() => (selectedPosition.value === null ? null : state.value?.tiles[selectedPosition.value] ?? null))
const selectedPlayer = computed(
  () => state.value?.players.find((p) => p.user_id === selectedPlayerId.value) ?? null,
)
const selectedTileOwnerName = computed(
  () => state.value?.players.find((p) => p.user_id === selectedTile.value?.owner_id)?.nickname ?? '',
)
const cardPlayerName = computed(() => (store.activeCard ? playerName(store.activeCard.player_id) : ''))
const highlight = computed(() => store.myProperties.map((tile) => tile.position))
const centerLines = computed(() =>
  (state.value?.players ?? []).map((player) => `${player.nickname} ${formatMoney(player.cash)}`),
)
const canOperateTile = computed(
  () => !offline.value && store.canAct && !!selectedTile.value && selectedTile.value.owner_id === store.currentUserId,
)

/**
 * 回合 / 决策 / 拍卖倒计时
 * 服务端只在状态快照里给出倒计时初值，不逐秒推送，所以剩余秒数在前端本地递减。
 */
const turnCountdownLabel = computed(() => {
  if (store.phase === 'WAIT_DECISION') return '决策剩余'
  if (store.phase === 'AUCTION') return '拍卖剩余'
  return '回合剩余'
})
const { secondsLeft: turnSecondsLeft, running: turnCountdownRunning } = useLocalCountdown(
  () => phaseCountdownSeconds(store.phase),
  () =>
    countdownResetKey({
      phase: store.phase,
      turnNumber: state.value?.turn_number ?? null,
      currentPlayerIndex: state.value?.current_player_index ?? null,
      auctionBid: store.activeAuction?.current_bid ?? null,
      auctionRounds: store.activeAuction?.bid_rounds ?? null,
    }),
)

const handleTileSelect = (position: number) => {
  selectedPosition.value = position
  showTileDialog.value = true
}

/** 点击棋子 / 玩家卡片：展示**玩家**信息（昵称、现金、资产等），而不是所在格子的地块信息 */
const handlePlayerSelect = (userId: number) => {
  if (!state.value?.players.some((p) => p.user_id === userId)) return
  selectedPlayerId.value = userId
  showPlayerDialog.value = true
}

const focusPlayer = (userId: number) => handlePlayerSelect(userId)

const openTradeWith = (userId: number) => {
  const partner = state.value?.players.find((p) => p.user_id === userId)
  ElMessage.info(`可在交易面板中向 ${partner?.nickname ?? '该玩家'} 发起交易`)
}

const handleBuy = () => {
  const decision = store.pendingDecision
  if (decision) store.sendBuyProperty(decision.tile_id)
}

const handleDecline = () => {
  const decision = store.pendingDecision
  if (decision) store.sendDeclineProperty(decision.tile_id)
}

/**
 * 所有会改状态的 WS 操作前置校验：断开时给出明确提示，而不是"点了没反应"。
 * 返回是否允许继续发送。
 */
const requireLink = (action: string): boolean => {
  if (store.connected) return true
  ElMessage.warning(`连接已断开，${action}未发送，请等待重连后重试`)
  return false
}

const handleBid = (amount: number) => {
  if (!requireLink('出价')) return
  if (!store.sendAuctionBid(amount)) ElMessage.error('出价发送失败，请稍后重试')
}

const handleTradeSubmit = (payload: TradeOfferPayload) => {
  if (!requireLink('交易提议')) return
  if (sendTradeOffer(payload)) ElMessage.success('交易提议已发送，等待对方回应')
  else ElMessage.error('交易提议发送失败，请稍后重试')
}

const handleTradeAccept = (tradeId: string) => {
  if (!requireLink('接受交易')) return
  if (store.sendTradeAccept(tradeId)) ElMessage.success('已接受该交易，等待服务端结算')
  else ElMessage.error('接受交易失败，请稍后重试')
}

const handleTradeReject = (tradeId: string) => {
  if (!requireLink('拒绝交易')) return
  if (store.sendTradeReject(tradeId)) ElMessage.success('已拒绝该交易')
  else ElMessage.error('拒绝交易失败，请稍后重试')
}

const handleViewReplay = (gameRecordId: number) => {
  router.push(`/replay/${gameRecordId}`)
}

const handleLeave = async (skipConfirm = false) => {
  if (!skipConfirm) {
    try {
      await ElMessageBox.confirm('确定离开当前对局吗？', '离开对局', { type: 'warning' })
    } catch {
      return
    }
  }
  // 通知后端：对局进行中离开时该席位交由 AI 托管，房间内无真人时后端自动解散房间
  try {
    await leaveRoom(roomId.value)
  } catch {
    // 房间可能已被解散或不存在，忽略后继续本地退出
  }
  stop()
  router.push('/')
}

/** 退出本局（保留在房间内）→ 回到房间等待页 */
const leaveToRoom = () => {
  const code = roomStore.roomCode
  stop()
  router.push(code ? `/room/${code}` : '/')
}

/** 强制退出本局：本局角色交由 AI 接管继续对局 */
const handleQuitGame = async () => {
  if (store.isSpectator) {
    ElMessage.info('观战中，无需退出本局')
    return
  }
  try {
    await ElMessageBox.confirm(
      '退出后本局你的角色将由 AI 接管继续对局，此操作无法撤销。确定退出本局吗？',
      '退出本局',
      { type: 'warning', confirmButtonText: '退出并由 AI 接管', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  if (!store.connected) {
    ElMessage.warning('连接已断开，请等待重连后再试')
    return
  }
  store.sendQuitGame()
}

// 退出本局结果
watch(
  () => store.quitResult,
  (result) => {
    if (!result) return
    store.clearQuitResult()
    if (result.ok) {
      ElMessage.success('已退出本局，你的角色现由 AI 接管继续对局')
      leaveToRoom()
    } else {
      ElMessage.warning(`退出本局失败：${quitFailText(result.reason)}`)
    }
  },
)

/**
 * 服务端拒绝类错误（操作不合法 / 非你的回合 / 状态不允许）→ 明确错误提示条，
 * 对应 D3「开局失败只显示 WS 已断开、无原因提示」的静默分支。
 */
watch(
  () => store.serverError,
  (notice) => {
    if (!notice) return
    store.clearServerError()
    ElMessage.error(`操作未生效：${notice.message}`)
  },
)

/** WS 断开 / 初始化失败（关闭码语义）→ 顶部提示条 + 弹窗提示，并冻结操作按钮 */
watch(
  () => store.connectionNotice,
  (notice) => {
    if (!notice) return
    store.clearConnectionNotice()
    linkFailLabel.value = notice.label
    linkFailMessage.value = notice.message
    if (notice.fatal) {
      ElMessageBox.alert(`${notice.message}（关闭码 ${notice.code}，已停止自动重连）`, notice.label || '连接异常', {
        type: 'error',
        confirmButtonText: '返回房间',
      })
        .catch(() => undefined)
        .finally(() => leaveToRoom())
    } else {
      ElMessage.error(`${notice.label}：${notice.message}`)
    }
  },
)

/** 连接恢复 → 复位异常文案，并明确告知已可继续操作 */
watch(
  () => store.connected,
  (isConnected, wasConnected) => {
    if (!isConnected) return
    if (!wasConnected && (linkFailLabel.value || linkFailMessage.value)) {
      ElMessage.success('连接已恢复，可继续操作')
    }
    linkFailLabel.value = ''
    linkFailMessage.value = ''
  },
)

/** 交易提示（收到报价 / 成交 / 被拒）→ 统一 toast，成功失败均有反馈 */
watch(
  () => store.tradeNotice,
  (notice) => {
    if (!notice) return
    store.clearTradeNotice()
    if (notice.kind === 'completed') ElMessage.success(notice.text)
    else if (notice.kind === 'rejected') ElMessage.warning(notice.text)
    else ElMessage.info(notice.text)
  },
)

/** 拍卖提示（出价成功 / 被超越 / 成交 / 流拍）→ 统一 toast */
watch(
  () => store.auctionNotice,
  (notice) => {
    if (!notice) return
    store.clearAuctionNotice()
    if (notice.kind === 'bid_accepted' || notice.kind === 'sold') ElMessage.success(notice.text)
    else ElMessage.warning(notice.text)
  },
)

// 房间解散（房间内已无真人玩家）
watch(
  () => store.roomDissolved,
  (notice) => {
    if (!notice) return
    ElMessageBox.alert('房间内已无真人玩家，该房间已自动解散。', '房间已解散', {
      type: 'info',
      confirmButtonText: '返回大厅',
    })
      .catch(() => undefined)
      .finally(() => {
        stop()
        router.push('/')
      })
  },
)

onMounted(() => {
  start(route.params.id as string)
  const instance = boardRef.value as unknown as { renderer?: BoardRenderer | null } | null
  bind(instance?.renderer ?? null)
})

onBeforeUnmount(() => {
  bind(null)
  stop()
})

defineExpose({ sendTradeOffer })
</script>

<style scoped>
/**
 * 对局页：棋盘列 + 侧栏票册。
 * 高度链严格为 100%（GameLayout 的 el-main 已确定高度），
 * 棋盘列由「头部 + 自适应画布 + 脚注」三段组成，画布 flex:1 + min-height:0
 * 保证棋盘永远按可用高度收缩，不会被裁切。
 */
.game-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 336px;
  gap: 14px;
  height: 100%;
  min-height: 0;
  animation: gg-fade-up var(--gg-dur-slow) var(--gg-ease-out) both;
}

.game-page__board {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.game-page__board-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 0 4px 8px;
  border-bottom: 1px dashed var(--gg-border-strong);
}

.game-page__board-meta {
  font-family: var(--gg-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.1em;
  color: var(--gg-ink-3);
}

.game-page__board-meta b {
  color: var(--gg-ink);
}

.game-page__board-canvas {
  position: relative;
  flex: 1 1 auto;
  min-height: 0;
  padding: 10px 0;
}

.game-page__board-canvas > :deep(*) {
  height: 100%;
}

.game-page__board-foot {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--gg-border-strong);
  font-size: 11.5px;
  color: var(--gg-ink-3);
}

.game-page__board-hint {
  letter-spacing: 0.04em;
}

.game-page__board-me {
  margin-left: auto;
  font-family: var(--gg-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.08em;
  color: var(--gg-ink-2);
}

/* ── 侧栏 ── */
.game-page__side {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-width: thin;
}

.game-page__side > * {
  flex: 0 0 auto;
  animation: gg-fade-up var(--gg-dur-slow) var(--gg-ease-out) both;
}

.game-page__alert {
  margin: 0;
}

.game-status__wait {
  font-size: 12.5px;
  color: rgba(242, 234, 217, 0.7);
}

.gg-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  font-family: var(--gg-font-mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  border: 1px solid rgba(242, 234, 217, 0.34);
  color: rgba(242, 234, 217, 0.88);
  white-space: nowrap;
}

.gg-chip--phase {
  background: var(--gg-brand);
  border-color: #6f1d13;
  color: #fdf3ea;
}

.gg-chip[data-on='no'] {
  color: #f0b7ab;
  border-color: rgba(240, 183, 171, 0.55);
}

/* 回合 / 决策 / 拍卖倒计时（本地递减，最后 5 秒转为告警色） */
.gg-chip--timer {
  font-variant-numeric: tabular-nums;
  border-color: rgba(226, 176, 96, 0.6);
  color: #f2d9a8;
}

.gg-chip--timer[data-on='no'] {
  color: #f0b7ab;
  border-color: rgba(240, 183, 171, 0.55);
}

.gg-chip--syncing {
  border-color: rgba(226, 176, 96, 0.4);
  color: rgba(242, 234, 217, 0.7);
}

/* ── 操作卡 ── */
.action-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.action-card__cash {
  font-family: var(--gg-font-mono);
  font-size: 12.5px;
  font-weight: 700;
  color: var(--gg-brand);
  letter-spacing: 0.04em;
}

.action-card__decision {
  margin-bottom: 10px;
  padding: 10px 12px;
  background: var(--gg-gold-soft);
  border: 1px dashed var(--gg-gold);
}

.action-card__decision-title {
  display: inline-block;
  margin-bottom: 6px;
  font-family: var(--gg-font-mono);
  font-size: 9.5px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--gg-gold-strong);
}

.action-card__text {
  margin: 0 0 8px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--gg-ink-2);
}

.action-card__row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.action-card__row:last-child {
  margin-bottom: 0;
}

.action-card__row :deep(.el-button) {
  flex: 1 1 118px;
  margin-left: 0;
}

.action-card__sep {
  margin: 10px 0;
}

.action-card__idle {
  margin: 8px 0 0;
  padding: 8px 10px;
  font-size: 12px;
  color: var(--gg-ink-3);
  background: var(--gg-surface-2);
  border: 1px dashed var(--gg-border-strong);
}

@media (max-width: 1100px) {
  .game-page {
    grid-template-columns: minmax(0, 1fr);
    height: auto;
    gap: 14px;
  }

  .game-page__board-canvas {
    height: min(88vw, 58vh);
  }

  .game-page__side {
    overflow: visible;
    padding-right: 0;
  }
}

@media (max-width: 640px) {
  .game-page__board-foot {
    flex-wrap: wrap;
  }

  .game-page__board-me {
    margin-left: 0;
  }

  .game-page__board-meta {
    display: none;
  }
}
</style>
