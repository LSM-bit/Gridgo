<template>
  <div class="replay-page">
    <!-- 顶栏：票据刊头 -->
    <header class="replay-bar">
      <div class="replay-bar__left">
        <el-button text class="replay-bar__back" @click="goBack">&larr; 返回</el-button>
        <span class="gg-stamp gg-stamp--gold">回放</span>
        <span class="replay-bar__id gg-num">对局 #{{ replayStore.gameId }}</span>
        <span class="replay-bar__turn gg-num">第 {{ replayStore.currentTurn }} 回合</span>
      </div>
      <div class="replay-bar__right">
        <span class="replay-bar__reason">{{ endReasonText }}</span>
        <span class="replay-bar__total gg-num">{{ replayStore.totalTurns }} 回合</span>
      </div>
    </header>

    <!-- 加载 / 错误 -->
    <div v-if="replayStore.loading" class="replay-state">
      <span class="replay-state__mark">◌</span>
      <span>正在调阅对局档案…</span>
    </div>

    <div v-else-if="replayStore.error" class="replay-state replay-state--error">
      <span class="replay-state__mark">✕</span>
      <span class="replay-state__text">{{ replayStore.error }}</span>
      <el-button size="small" @click="goBack">返回</el-button>
    </div>

    <!-- 主体 -->
    <main v-else-if="snapshot" class="replay-main">
      <!-- 棋盘 -->
      <section class="replay-panel replay-panel--board">
        <header class="replay-panel__head">
          <span class="gg-kicker">BOARD · 棋盘</span>
          <span class="replay-panel__meta gg-num">
            步骤 {{ replayStore.currentStepIndex }} / {{ replayStore.totalSteps }}
          </span>
        </header>

        <div class="board-stage">
          <div class="board-grid">
            <!-- 顶部行 -->
            <template v-for="i in 11" :key="'top-' + i">
              <div
                v-if="snapshot.tiles[19 + i]"
                class="tile-cell"
                :class="{
                  'tile-current': isPlayerOnTile(snapshot.tiles[19 + i].position),
                  'tile-owned': snapshot.tiles[19 + i].owner_id != null,
                  'tile-mortgaged': snapshot.tiles[19 + i].is_mortgaged,
                }"
                :style="{ ...tileStyle(snapshot.tiles[19 + i]), gridRow: 1, gridColumn: i }"
              >
                <span
                  v-if="snapshot.tiles[19 + i].group_color"
                  class="tile-color-bar"
                  :style="{ background: snapshot.tiles[19 + i].group_color as string }"
                ></span>
                <span class="tile-name">{{ snapshot.tiles[19 + i].name }}</span>
                <span class="tile-info">
                  <span v-if="snapshot.tiles[19 + i].price">¥{{ snapshot.tiles[19 + i].price }}</span>
                  <span v-if="snapshot.tiles[19 + i].build_level" class="tile-houses">{{
                    houseLabel(snapshot.tiles[19 + i].build_level)
                  }}</span>
                </span>
                <span v-if="getPlayersOnTile(snapshot.tiles[19 + i].position).length" class="tile-players">
                  <span
                    v-for="p in getPlayersOnTile(snapshot.tiles[19 + i].position)"
                    :key="p.user_id"
                    class="player-token"
                    >{{ p.nickname.charAt(0) }}</span
                  >
                </span>
              </div>
            </template>

            <!-- 左右列 + 中央 -->
            <template v-for="row in 9" :key="'mid-' + row">
              <div
                v-if="snapshot.tiles[20 - row]"
                class="tile-cell"
                :class="{
                  'tile-current': isPlayerOnTile(snapshot.tiles[20 - row].position),
                  'tile-owned': snapshot.tiles[20 - row].owner_id != null,
                  'tile-mortgaged': snapshot.tiles[20 - row].is_mortgaged,
                }"
                :style="{ ...tileStyle(snapshot.tiles[20 - row]), gridRow: row + 1, gridColumn: 1 }"
              >
                <span
                  v-if="snapshot.tiles[20 - row].group_color"
                  class="tile-color-bar"
                  :style="{ background: snapshot.tiles[20 - row].group_color as string }"
                ></span>
                <span class="tile-name">{{ snapshot.tiles[20 - row].name }}</span>
                <span class="tile-info">
                  <span v-if="snapshot.tiles[20 - row].price">¥{{ snapshot.tiles[20 - row].price }}</span>
                </span>
                <span v-if="getPlayersOnTile(snapshot.tiles[20 - row].position).length" class="tile-players">
                  <span
                    v-for="p in getPlayersOnTile(snapshot.tiles[20 - row].position)"
                    :key="p.user_id"
                    class="player-token"
                    >{{ p.nickname.charAt(0) }}</span
                  >
                </span>
              </div>

              <div v-if="row === 1" class="board-center" :style="{ gridRow: '2 / 11', gridColumn: '2 / 11' }">
                <div class="board-center__inner">
                  <template v-if="isGameOver">
                    <span class="board-center__kicker">GAME OVER</span>
                    <span class="board-center__title">对局结束</span>
                    <span class="board-center__reason">{{ endReasonText }}</span>
                    <span v-if="winnerPlayer" class="board-center__winner">
                      冠军 · {{ winnerPlayer.nickname }}
                    </span>
                  </template>

                  <template v-else>
                    <span class="board-center__kicker">NOW PLAYING</span>
                    <div v-if="snapshot.dice.total > 0" class="center-dice">
                      <span class="dice-face gg-num">{{ snapshot.dice.values[0] }}</span>
                      <span class="dice-op">+</span>
                      <span class="dice-face gg-num">{{ snapshot.dice.values[1] }}</span>
                      <span class="dice-eq gg-num">= {{ snapshot.dice.total }}</span>
                    </div>
                    <span class="board-center__turn gg-num">第 {{ snapshot.turn_number }} 回合</span>
                    <span v-if="activePlayer" class="board-center__player">{{ activePlayer.nickname }} 的回合</span>
                  </template>

                  <p v-if="replayStore.currentStep" class="board-center__desc">
                    {{ replayStore.currentStep.description }}
                  </p>
                </div>
              </div>

              <div
                v-if="snapshot.tiles[30 + row]"
                class="tile-cell"
                :class="{
                  'tile-current': isPlayerOnTile(snapshot.tiles[30 + row].position),
                  'tile-owned': snapshot.tiles[30 + row].owner_id != null,
                  'tile-mortgaged': snapshot.tiles[30 + row].is_mortgaged,
                }"
                :style="{ ...tileStyle(snapshot.tiles[30 + row]), gridRow: row + 1, gridColumn: 11 }"
              >
                <span
                  v-if="snapshot.tiles[30 + row].group_color"
                  class="tile-color-bar"
                  :style="{ background: snapshot.tiles[30 + row].group_color as string }"
                ></span>
                <span class="tile-name">{{ snapshot.tiles[30 + row].name }}</span>
                <span class="tile-info">
                  <span v-if="snapshot.tiles[30 + row].price">¥{{ snapshot.tiles[30 + row].price }}</span>
                </span>
                <span v-if="getPlayersOnTile(snapshot.tiles[30 + row].position).length" class="tile-players">
                  <span
                    v-for="p in getPlayersOnTile(snapshot.tiles[30 + row].position)"
                    :key="p.user_id"
                    class="player-token"
                    >{{ p.nickname.charAt(0) }}</span
                  >
                </span>
              </div>
            </template>

            <!-- 底部行 -->
            <template v-for="i in 11" :key="'bot-' + i">
              <div
                v-if="snapshot.tiles[10 - i + 1] !== undefined"
                class="tile-cell"
                :class="{
                  'tile-current': isPlayerOnTile(snapshot.tiles[10 - i + 1].position),
                  'tile-owned': snapshot.tiles[10 - i + 1].owner_id != null,
                  'tile-mortgaged': snapshot.tiles[10 - i + 1].is_mortgaged,
                }"
                :style="{ ...tileStyle(snapshot.tiles[10 - i + 1]), gridRow: 11, gridColumn: i }"
              >
                <span
                  v-if="snapshot.tiles[10 - i + 1].group_color"
                  class="tile-color-bar"
                  :style="{ background: snapshot.tiles[10 - i + 1].group_color as string }"
                ></span>
                <span class="tile-name">{{ snapshot.tiles[10 - i + 1].name }}</span>
                <span class="tile-info">
                  <span v-if="snapshot.tiles[10 - i + 1].price">¥{{ snapshot.tiles[10 - i + 1].price }}</span>
                  <span v-if="snapshot.tiles[10 - i + 1].build_level" class="tile-houses">{{
                    houseLabel(snapshot.tiles[10 - i + 1].build_level)
                  }}</span>
                </span>
                <span v-if="getPlayersOnTile(snapshot.tiles[10 - i + 1].position).length" class="tile-players">
                  <span
                    v-for="p in getPlayersOnTile(snapshot.tiles[10 - i + 1].position)"
                    :key="p.user_id"
                    class="player-token"
                    >{{ p.nickname.charAt(0) }}</span
                  >
                </span>
              </div>
            </template>
          </div>
        </div>
      </section>

      <!-- 侧栏 -->
      <aside class="replay-side">
        <!-- 玩家 -->
        <section class="replay-panel">
          <header class="replay-panel__head">
            <span class="gg-kicker">{{ isGameOver ? 'RESULT · 最终排名' : 'PLAYERS · 玩家' }}</span>
            <span class="replay-panel__meta gg-num">{{ snapshot.players.length }} 人</span>
          </header>
          <div class="replay-panel__body">
            <div class="player-list">
              <div
                v-for="(p, idx) in snapshot.players"
                :key="p.user_id"
                class="player-row"
                :class="{
                  'player-row--active': !isGameOver && idx === snapshot.current_player_idx,
                  'player-row--bankrupt': p.is_bankrupt,
                  'player-row--winner': isGameOver && p.user_id === replayStore.winnerId,
                }"
              >
                <span class="player-row__token">{{ p.is_ai ? 'AI' : p.nickname.charAt(0) }}</span>
                <span class="player-row__main">
                  <span class="player-row__name">
                    <span v-if="isGameOver" class="player-row__rank gg-num">{{ rankLabel(p.user_id) }}</span>
                    {{ p.nickname }}
                    <em v-if="!isGameOver && idx === snapshot.current_player_idx" class="player-row__flag">行动中</em>
                    <em v-if="!isGameOver && p.is_in_jail" class="player-row__flag player-row__flag--jail">监狱</em>
                  </span>
                  <span class="player-row__sub gg-num">
                    ¥{{ p.cash }}
                    <span v-if="isGameOver"> · 地产 {{ p.properties.length }}</span>
                  </span>
                </span>
                <span v-if="p.is_bankrupt" class="player-row__bankrupt">破产</span>
              </div>
            </div>
          </div>
        </section>

        <!-- 操作日志 -->
        <section class="replay-panel replay-panel--log">
          <header class="replay-panel__head">
            <span class="gg-kicker">LOG · 操作日志</span>
            <span class="replay-panel__meta gg-num">{{ displayLogs.length }} 条</span>
          </header>
          <div ref="logListRef" class="log-list">
            <p v-for="(log, idx) in displayLogs" :key="idx" class="log-item" :class="{ 'log-item--current': idx === displayLogs.length - 1 }">
              {{ log }}
            </p>
            <p v-if="!displayLogs.length" class="log-empty">点击播放开始回放</p>
          </div>
        </section>

        <!-- 回放控制 -->
        <section class="replay-panel">
          <header class="replay-panel__head">
            <span class="gg-kicker">CONTROL · 回放控制</span>
            <span class="replay-panel__meta gg-num">{{ speedLabel }}</span>
          </header>
          <div class="replay-panel__body">
            <div class="progress-area">
              <el-slider
                v-model="stepSliderValue"
                :min="0"
                :max="replayStore.totalSteps"
                :show-tooltip="false"
                @change="onSliderChange"
              />
              <div class="progress-labels gg-num">
                <span>步骤 {{ replayStore.currentStepIndex }}</span>
                <span>{{ replayStore.totalSteps }}</span>
              </div>
            </div>

            <div class="control-buttons">
              <el-button class="ctrl-btn" :disabled="replayStore.currentStepIndex <= 0" @click="replayStore.stepBackward()">
                &laquo; 上一步
              </el-button>
              <el-button class="ctrl-btn ctrl-btn--play" type="primary" @click="replayStore.togglePlay()">
                {{ replayStore.isPlaying ? '暂停' : '播放' }}
              </el-button>
              <el-button
                class="ctrl-btn"
                :disabled="replayStore.currentStepIndex >= replayStore.totalSteps"
                @click="replayStore.stepForward()"
              >
                下一步 &raquo;
              </el-button>
            </div>

            <div class="ctrl-row">
              <span class="ctrl-row__label">速度</span>
              <el-radio-group v-model="speedValue" size="small" @change="onSpeedChange">
                <el-radio-button :value="2000">0.5x</el-radio-button>
                <el-radio-button :value="1000">1x</el-radio-button>
                <el-radio-button :value="500">2x</el-radio-button>
                <el-radio-button :value="250">4x</el-radio-button>
              </el-radio-group>
            </div>

            <div v-if="replayStore.replayData" class="ctrl-row">
              <span class="ctrl-row__label">跳转回合</span>
              <el-select v-model="jumpTurn" size="small" placeholder="选择回合" style="width: 130px" @change="onJumpTurn">
                <el-option v-for="t in availableTurns" :key="t" :label="`第 ${t} 回合`" :value="t" />
              </el-select>
            </div>
          </div>
        </section>

        <!-- 结算 -->
        <section v-if="replayStore.players.length" class="replay-panel">
          <header class="replay-panel__head">
            <span class="gg-kicker">SETTLEMENT · 结算</span>
          </header>
          <div class="replay-panel__body">
            <div v-for="p in replayStore.players" :key="p.user_id" class="settle-row">
              <span class="settle-row__rank gg-num">#{{ p.rank }}</span>
              <span class="settle-row__name">{{ p.nickname }}</span>
              <span
                class="settle-row__amount gg-num"
                :class="p.settlement_amount >= 0 ? 'settle-row__amount--plus' : 'settle-row__amount--minus'"
              >
                {{ p.settlement_amount >= 0 ? '+' : '' }}¥{{ p.settlement_amount }}
              </span>
            </div>
          </div>
        </section>
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useReplayStore } from '@/stores/replay'
import type { TileState, PlayerState } from '@/stores/game'

const route = useRoute()
const router = useRouter()
const replayStore = useReplayStore()

// ─── 数据 ───

const logListRef = ref<HTMLElement | null>(null)
const speedValue = ref(1000)
const jumpTurn = ref<number | null>(null)

const snapshot = computed(() => replayStore.currentSnapshot)
const isGameOver = computed(() => snapshot.value?.phase === 'GAME_OVER')
const activePlayer = computed(() => {
  if (!snapshot.value) return null
  return snapshot.value.players[snapshot.value.current_player_idx] || null
})

const winnerPlayer = computed(() => {
  if (!replayStore.winnerId || !snapshot.value) return null
  return snapshot.value.players.find((p) => p.user_id === replayStore.winnerId) || null
})

const endReasonText = computed(() => {
  const map: Record<string, string> = {
    last_standing: '最后幸存',
    turn_limit: '回合上限',
    vote_end: '投票结束',
  }
  return map[replayStore.endReason] || replayStore.endReason
})

const speedLabel = computed(() => {
  const map: Record<number, string> = { 2000: '0.5x', 1000: '1x', 500: '2x', 250: '4x' }
  return map[speedValue.value] ?? '1x'
})

function pad2(value: number): string {
  return String(value).padStart(2, '0')
}

/** 终局排名标记：01 / 02 / … 以编号式排版替代奖牌表情 */
function rankLabel(userId: number): string {
  const player = replayStore.players.find((p) => p.user_id === userId)
  if (!player) return ''
  return pad2(player.rank)
}

/** 建筑等级：以几何符号替代房屋/酒店表情 */
function houseLabel(level: number): string {
  if (level >= 5) return '★★'
  return '▲'.repeat(level)
}

const displayLogs = computed(() => {
  if (!snapshot.value) return []
  return snapshot.value.logs
})

const availableTurns = computed(() => {
  if (!replayStore.replayData) return []
  return replayStore.replayData.turns.map((t) => t.turn_number)
})

// 进度条双向绑定
const stepSliderValue = computed(() => replayStore.currentStepIndex)

// ─── 棋盘辅助 ───

function isPlayerOnTile(position: number): boolean {
  if (!snapshot.value) return false
  return snapshot.value.players.some((p) => !p.is_bankrupt && p.position === position)
}

function getPlayersOnTile(position: number): PlayerState[] {
  if (!snapshot.value) return []
  return snapshot.value.players.filter((p) => !p.is_bankrupt && p.position === position)
}

/** 格子底色：统一取票据色板，替代 Element 默认色 */
function tileStyle(tile: TileState): Record<string, string> {
  const style: Record<string, string> = {}
  if (tile.tile_type === 'START') style.background = 'var(--gg-green-soft)'
  else if (tile.tile_type === 'JAIL') style.background = 'var(--gg-gold-soft)'
  else if (tile.tile_type === 'GO_TO_JAIL') style.background = 'var(--gg-red-soft)'
  else if (tile.tile_type === 'PARKING') style.background = 'var(--gg-surface-3)'
  else if (tile.tile_type === 'CHANCE') style.background = '#e7e6d5'
  else if (tile.tile_type === 'FATE') style.background = 'var(--gg-brand-soft)'
  else if (tile.tile_type === 'TAX') style.background = 'var(--gg-surface-2)'
  if (tile.is_mortgaged) style.opacity = '0.6'
  return style
}

// ─── 事件处理 ───

function onSliderChange(val: number) {
  replayStore.goToStep(val)
}

function onSpeedChange(val: number) {
  replayStore.setSpeed(val)
}

function onJumpTurn(turnNumber: number) {
  replayStore.goToTurn(turnNumber)
}

function goBack() {
  replayStore.reset()
  router.back()
}

// 自动滚动日志到底部
watch(displayLogs, async () => {
  await nextTick()
  if (logListRef.value) {
    logListRef.value.scrollTop = logListRef.value.scrollHeight
  }
})

// ─── 生命周期 ───

onMounted(() => {
  const id = Number(route.params.id)
  if (id) {
    replayStore.fetchReplay(id)
  }
})

onUnmounted(() => {
  replayStore.reset()
})
</script>

<style scoped>
/* ═══ 页面骨架：桌板 + 侧册，撑满视口 ═══ */
.replay-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: var(--gg-bg);
  background-image: var(--gg-page-glow), var(--gg-grid);
}

/* ── 顶栏 ── */
.replay-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
  padding: 10px clamp(14px, 2.2vw, 26px);
  background: var(--gg-grad-night);
  border-bottom: 2px solid var(--gg-ink);
}

.replay-bar__left,
.replay-bar__right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.replay-bar__back {
  color: var(--gg-gold) !important;
  font-family: var(--gg-font-mono) !important;
  font-size: 12px !important;
  letter-spacing: 0.08em;
}

.replay-bar__id {
  font-family: var(--gg-font-mono);
  font-size: 12px;
  letter-spacing: 0.14em;
  color: #f4ecdc;
}

.replay-bar__turn {
  font-family: var(--gg-font-mono);
  font-size: 11px;
  letter-spacing: 0.12em;
  color: rgba(244, 236, 220, 0.6);
}

.replay-bar__reason {
  font-size: 11.5px;
  padding: 2px 8px;
  color: var(--gg-gold);
  border: 1px solid rgba(168, 121, 42, 0.55);
}

.replay-bar__total {
  font-family: var(--gg-font-mono);
  font-size: 11px;
  letter-spacing: 0.12em;
  color: rgba(244, 236, 220, 0.6);
}

/* ── 状态页 ── */
.replay-state {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 20px;
  font-size: 13px;
  color: var(--gg-ink-3);
}

.replay-state__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  color: var(--gg-gold);
  border: 1px solid var(--gg-border-strong);
  background: var(--gg-surface);
}

.replay-state--error .replay-state__mark {
  color: var(--gg-brand);
}

.replay-state__text {
  color: var(--gg-ink-2);
  font-weight: 600;
}

/* ── 主体：棋盘 + 侧栏 ── */
.replay-main {
  flex: 1 1 auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 356px);
  gap: 14px;
  align-items: start;
  width: 100%;
  max-width: 1560px;
  margin: 0 auto;
  padding: clamp(12px, 1.6vw, 20px) clamp(14px, 2.2vw, 26px) 22px;
  box-sizing: border-box;
  animation: gg-fade-up var(--gg-dur-slow) var(--gg-ease-out) both;
}

/* ── 面板通用 ── */
.replay-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--gg-surface);
  border: 1px solid var(--gg-border-strong);
  box-shadow: var(--gg-shadow-1);
}

.replay-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 9px 12px;
  background: var(--gg-surface-2);
  border-bottom: 1px dashed var(--gg-border-strong);
}

.replay-panel__meta {
  font-family: var(--gg-font-mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--gg-ink-3);
}

.replay-panel__body {
  padding: 12px;
}

/* ── 棋盘：按可用高度自适应，完整可见不裁切 ── */
.board-stage {
  display: flex;
  justify-content: center;
  padding: 12px;
}

.board-grid {
  display: grid;
  grid-template-columns: repeat(11, minmax(0, 1fr));
  grid-template-rows: repeat(11, minmax(0, 1fr));
  width: 100%;
  /* 关键：宽度取「容器宽」与「视口高预留后可用高」的较小值，保证整块棋盘完整可见 */
  max-width: min(100%, calc(100vh - 250px));
  aspect-ratio: 1 / 1;
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-ink);
  box-shadow: var(--gg-inset-line), var(--gg-shadow-2);
}

.tile-cell {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 3px;
  min-width: 0;
  overflow: hidden;
  background: var(--gg-surface);
  border: 1px solid var(--gg-border);
  color: var(--gg-ink-2);
  transition: background-color var(--gg-dur) var(--gg-ease);
}

.tile-color-bar {
  display: block;
  height: 4px;
  margin: -3px -3px 1px;
}

.tile-name {
  font-size: 8.5px;
  line-height: 1.15;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tile-info {
  display: flex;
  align-items: baseline;
  gap: 3px;
  margin-top: auto;
  font-family: var(--gg-font-mono);
  font-size: 7.5px;
  letter-spacing: 0.02em;
  color: var(--gg-ink-3);
}

.tile-houses {
  color: var(--gg-green);
  letter-spacing: -0.05em;
}

.tile-current {
  box-shadow: inset 0 0 0 2px var(--gg-brand);
}

.tile-owned {
  background: var(--gg-gold-soft);
}

.tile-mortgaged {
  opacity: 0.55;
}

.tile-players {
  position: absolute;
  right: 1px;
  bottom: 1px;
  display: flex;
  gap: 1px;
}

.player-token {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 12px;
  height: 12px;
  font-size: 8px;
  font-weight: 700;
  color: #fdf6e8;
  background: var(--gg-brand);
  border: 1px solid #6f1d13;
}

.board-center {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px;
  text-align: center;
  background-color: var(--gg-bg-deep);
  background-image: var(--gg-dotfield);
  background-size: 9px 9px;
  border: 1px solid var(--gg-border-strong);
}

.board-center__inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  max-width: 92%;
}

.board-center__kicker {
  font-family: var(--gg-font-mono);
  font-size: 9px;
  letter-spacing: 0.28em;
  color: var(--gg-ink-4);
}

.board-center__title {
  font-family: var(--gg-font-display);
  font-size: clamp(16px, 1.6vw, 22px);
  color: var(--gg-ink);
}

.board-center__reason,
.board-center__winner {
  font-size: 12px;
  color: var(--gg-brand);
  font-weight: 700;
}

.board-center__turn {
  font-family: var(--gg-font-mono);
  font-size: 11px;
  letter-spacing: 0.16em;
  color: var(--gg-ink-3);
}

.board-center__player {
  font-size: 13px;
  font-weight: 700;
  color: var(--gg-ink);
}

.center-dice {
  display: flex;
  align-items: baseline;
  gap: 6px;
  color: var(--gg-ink);
}

.dice-face {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  font-family: var(--gg-font-display);
  font-size: 17px;
  font-weight: 700;
  background: var(--gg-surface);
  border: 1px solid var(--gg-ink);
}

.dice-op,
.dice-eq {
  font-family: var(--gg-font-mono);
  font-size: 12px;
  color: var(--gg-ink-3);
}

.board-center__desc {
  margin: 6px 0 0;
  padding-top: 8px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--gg-ink-2);
  border-top: 1px dashed var(--gg-border-strong);
}

/* ── 侧栏 ── */
.replay-side {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

/* 玩家 */
.player-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.player-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 7px 9px;
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border);
  border-left: 2px solid var(--gg-border-strong);
}

.player-row--active {
  background: var(--gg-brand-soft);
  border-left-color: var(--gg-brand);
}

.player-row--bankrupt {
  opacity: 0.65;
}

.player-row--winner {
  border-left-color: var(--gg-gold-strong);
  background: var(--gg-gold-soft);
}

.player-row__token {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  flex: 0 0 auto;
  font-size: 11px;
  font-weight: 700;
  color: #fdf6e8;
  background: var(--gg-night);
  border: 1px solid #16130f;
}

.player-row__main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1 1 auto;
}

.player-row__name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--gg-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.player-row__rank {
  font-family: var(--gg-font-mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  color: var(--gg-brand);
}

.player-row__flag {
  font-style: normal;
  font-size: 10px;
  padding: 0 5px;
  color: var(--gg-brand);
  border: 1px solid rgba(176, 57, 44, 0.4);
}

.player-row__flag--jail {
  color: var(--gg-ink-3);
  border-color: var(--gg-border-strong);
}

.player-row__sub {
  font-family: var(--gg-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.06em;
  color: var(--gg-ink-3);
}

.player-row__bankrupt {
  font-size: 10px;
  padding: 1px 5px;
  color: var(--gg-red);
  border: 1px solid rgba(140, 38, 26, 0.4);
}

/* 日志 */
.log-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  max-height: 218px;
  overflow-y: auto;
  padding: 12px;
}

.log-item {
  margin: 0;
  padding: 5px 8px;
  font-size: 11.5px;
  line-height: 1.55;
  color: var(--gg-ink-2);
  background: var(--gg-surface-2);
  border-left: 2px solid var(--gg-border-strong);
}

.log-item--current {
  color: var(--gg-ink);
  font-weight: 600;
  border-left-color: var(--gg-brand);
  background: var(--gg-brand-soft);
}

.log-empty {
  margin: 0;
  padding: 18px 8px;
  text-align: center;
  font-size: 11.5px;
  color: var(--gg-ink-4);
  border: 1px dashed var(--gg-border-strong);
}

/* 控制 */
.progress-area {
  padding: 0 2px;
}

.progress-labels {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: -2px;
  font-family: var(--gg-font-mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  color: var(--gg-ink-3);
}

.control-buttons {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.ctrl-btn {
  flex: 1 1 0;
  margin-left: 0 !important;
  font-size: 12px;
}

.ctrl-btn--play {
  flex: 1.2 1 0;
  font-weight: 700;
}

.ctrl-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dotted var(--gg-border-strong);
}

.ctrl-row__label {
  font-family: var(--gg-font-mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--gg-ink-3);
  white-space: nowrap;
}

/* 结算 */
.settle-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px dotted var(--gg-border-strong);
}

.settle-row:last-child {
  border-bottom: 0;
}

.settle-row__rank {
  flex: 0 0 28px;
  font-family: var(--gg-font-mono);
  font-size: 11px;
  color: var(--gg-ink-3);
}

.settle-row__name {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 12.5px;
  color: var(--gg-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.settle-row__amount {
  font-family: var(--gg-font-mono);
  font-size: 12px;
  font-weight: 700;
}

.settle-row__amount--plus {
  color: var(--gg-green);
}

.settle-row__amount--minus {
  color: var(--gg-brand);
}

/* ── 响应式 ── */
@media (max-width: 1100px) {
  .replay-main {
    grid-template-columns: minmax(0, 1fr);
  }

  .board-grid {
    max-width: min(100%, 92vw);
  }

  .log-list {
    max-height: 180px;
  }
}

@media (max-width: 640px) {
  .replay-main {
    padding: 12px 12px 18px;
  }

  .board-stage {
    overflow-x: auto;
    justify-content: flex-start;
  }

  .board-grid {
    min-width: 540px;
  }

  .control-buttons {
    flex-wrap: wrap;
  }

  .ctrl-btn {
    flex: 1 1 40%;
  }
}
</style>
