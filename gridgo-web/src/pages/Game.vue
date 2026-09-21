<template>
  <GameLayout>
    <template #status>
      <span class="gg-chip gg-chip--phase">{{ phaseText }}</span>
      <span class="game-status__wait">{{ waitText }}</span>
      <DicePanel :values="diceValues" :is-double="state?.dice.is_double ?? false" :rolling="isAnimating" />
      <span v-if="store.isSpectator" class="gg-chip">观战</span>
      <span class="gg-chip" :data-on="store.connected ? 'yes' : 'no'">
        {{ store.connected ? 'WS 已连接' : 'WS 已断开' }}
      </span>
    </template>

    <template #actions>
      <el-button size="small" @click="showLog = !showLog">{{ showLog ? '隐藏日志' : '显示日志' }}</el-button>
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
          />
        </div>

        <footer class="game-page__board-foot">
          <span class="gg-stamp gg-stamp--ink">GRIDGO</span>
          <span class="game-page__board-hint">点击地块查看详情 · 建造 / 抵押 / 赎回</span>
          <span v-if="store.myPlayer" class="game-page__board-me">
            {{ store.myPlayer.nickname }} · {{ formatMoney(store.myPlayer.cash) }} · 地产
            <b class="gg-num">{{ store.myProperties.length }}</b> 处
          </span>
        </footer>
      </section>

      <!-- ── 侧栏票册 ── -->
      <aside class="game-page__side">
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
              <el-button type="primary" :disabled="!store.canBuyProperty" @click="handleBuy">购买</el-button>
              <el-button :disabled="!store.canBuyProperty" @click="handleDecline">放弃</el-button>
            </div>
          </div>

          <div class="action-card__row">
            <el-button type="primary" :disabled="!store.canRoll" @click="store.sendRollDice()">掷骰子</el-button>
            <el-button :disabled="!store.canAct" @click="store.sendEndTurn()">结束回合</el-button>
          </div>

          <div v-if="store.isInJail" class="action-card__row">
            <el-button size="small" :disabled="!store.isMyTurn" @click="store.sendJailPayBail()">
              支付保释金 {{ formatMoney(state?.jail_bail ?? 0) }}
            </el-button>
            <el-button size="small" :disabled="!store.hasJailCard" @click="store.sendJailUseCard()">使用免罪卡</el-button>
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

          <p v-if="!store.canRoll && !store.canAct && !selectedTile" class="action-card__idle">
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
          @bid="handleBid"
        />

        <TradePanel
          :incoming="store.incomingTrades"
          :outgoing="store.outgoingTrades"
          :players="state?.players ?? []"
          :tiles="state?.tiles ?? []"
          :current-user-id="store.currentUserId"
          @accept="store.sendTradeAccept"
          @reject="store.sendTradeReject"
          @submit="sendTradeOffer"
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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import GameLayout from '@/layouts/GameLayout.vue'
import GameBoard from '@/components/board/GameBoard.vue'
import TileDetailDialog from '@/components/board/TileDetailDialog.vue'
import AuctionPanel from '@/components/card/AuctionPanel.vue'
import ChanceCard from '@/components/card/ChanceCard.vue'
import DicePanel from '@/components/card/DicePanel.vue'
import PlayerPanel from '@/components/player/PlayerPanel.vue'
import TradePanel from '@/components/player/TradePanel.vue'
import { ChatPanel, LogPanel, GameOverDialog } from '@/components/common'
import { useGame } from '@/composables/useGame'
import { formatMoney } from '@/utils/format'
import type { BoardRenderer } from '@/game/renderer'

const route = useRoute()
const router = useRouter()

const {
  store,
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
  sendTradeOffer,
} = useGame()

const { isAnimating, diceValues, bind } = anim

const boardRef = ref<InstanceType<typeof GameBoard> | null>(null)
const showLog = ref(false)
const showTileDialog = ref(false)
const selectedPosition = ref<number | null>(null)

const state = computed(() => store.state)
const selectedTile = computed(() => (selectedPosition.value === null ? null : state.value?.tiles[selectedPosition.value] ?? null))
const selectedTileOwnerName = computed(
  () => state.value?.players.find((p) => p.user_id === selectedTile.value?.owner_id)?.nickname ?? '',
)
const cardPlayerName = computed(() => (store.activeCard ? playerName(store.activeCard.player_id) : ''))
const highlight = computed(() => store.myProperties.map((tile) => tile.position))
const centerLines = computed(() =>
  (state.value?.players ?? []).map((player) => `${player.nickname} ${formatMoney(player.cash)}`),
)
const canOperateTile = computed(
  () => store.canAct && !!selectedTile.value && selectedTile.value.owner_id === store.currentUserId,
)

const handleTileSelect = (position: number) => {
  selectedPosition.value = position
  showTileDialog.value = true
}

const focusPlayer = (userId: number) => {
  const player = state.value?.players.find((p) => p.user_id === userId)
  if (!player) return
  selectedPosition.value = player.position
  showTileDialog.value = true
}

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

const handleBid = (amount: number) => store.sendAuctionBid(amount)

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
  stop()
  router.push('/')
}

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
