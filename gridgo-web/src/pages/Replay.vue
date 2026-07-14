<template>
  <div class="replay-page">
    <el-container style="height: 100vh">
      <!-- 顶栏 -->
      <el-header class="replay-header">
        <div class="flex-between w-full h-full">
          <div class="flex items-center gap-3">
            <el-button text @click="goBack">&larr; 返回</el-button>
            <el-tag type="info" size="large">回放</el-tag>
            <span>对局 #{{ replayStore.gameId }}</span>
            <span class="text-gray-400">第 {{ replayStore.currentTurn }} 回合</span>
          </div>
          <div class="flex items-center gap-2">
            <el-tag type="warning" size="small">{{ endReasonText }}</el-tag>
            <span class="text-gray-400 text-sm">{{ replayStore.totalTurns }} 回合</span>
          </div>
        </div>
      </el-header>

      <!-- 加载中 -->
      <el-main v-if="replayStore.loading" v-loading="true" style="height: calc(100vh - 60px)" />

      <!-- 错误 -->
      <el-main v-else-if="replayStore.error" style="height: calc(100vh - 60px)">
        <el-result icon="error" :title="replayStore.error">
          <template #extra>
            <el-button type="primary" @click="goBack">返回</el-button>
          </template>
        </el-result>
      </el-main>

      <!-- 主体 -->
      <el-main v-else-if="snapshot" class="replay-main">
        <el-row :gutter="16" class="replay-body">
          <!-- 左侧：棋盘 -->
          <el-col :span="16">
            <el-card class="board-card">
              <template #header>
                <div class="flex-between">
                  <span>棋盘</span>
                  <span class="text-sm text-gray-400">
                    步骤 {{ replayStore.currentStepIndex }} / {{ replayStore.totalSteps }}
                  </span>
                </div>
              </template>
              <div class="board-grid">
                <!-- 顶部行 -->
                <template v-for="i in 11" :key="'top-'+i">
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
                    <div class="tile-color-bar" v-if="snapshot.tiles[19 + i].group_color" :style="{ background: snapshot.tiles[19 + i].group_color as string }"></div>
                    <div class="tile-name">{{ snapshot.tiles[19 + i].name }}</div>
                    <div class="tile-info">
                      <span v-if="snapshot.tiles[19 + i].price">¥{{ snapshot.tiles[19 + i].price }}</span>
                      <span v-if="snapshot.tiles[19 + i].build_level" class="tile-houses">{{ snapshot.tiles[19 + i].build_level >= 5 ? '🏨' : '🏠'.repeat(snapshot.tiles[19 + i].build_level) }}</span>
                    </div>
                    <div class="tile-players" v-if="getPlayersOnTile(snapshot.tiles[19 + i].position).length">
                      <div v-for="p in getPlayersOnTile(snapshot.tiles[19 + i].position)" :key="p.user_id" class="player-token">{{ p.nickname.charAt(0) }}</div>
                    </div>
                  </div>
                </template>

                <!-- 左右列 + 中间区域 -->
                <template v-for="row in 9" :key="'mid-'+row">
                  <!-- 左列 -->
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
                    <div class="tile-color-bar" v-if="snapshot.tiles[20 - row].group_color" :style="{ background: snapshot.tiles[20 - row].group_color as string }"></div>
                    <div class="tile-name">{{ snapshot.tiles[20 - row].name }}</div>
                    <div class="tile-info">
                      <span v-if="snapshot.tiles[20 - row].price">¥{{ snapshot.tiles[20 - row].price }}</span>
                    </div>
                    <div class="tile-players" v-if="getPlayersOnTile(snapshot.tiles[20 - row].position).length">
                      <div v-for="p in getPlayersOnTile(snapshot.tiles[20 - row].position)" :key="p.user_id" class="player-token">{{ p.nickname.charAt(0) }}</div>
                    </div>
                  </div>

                  <!-- 中间区域 -->
                  <div v-if="row === 1" class="board-center" :style="{ gridRow: '2 / 11', gridColumn: '2 / 11' }">
                    <div class="board-center-content">
                      <!-- 游戏结束状态 -->
                      <template v-if="isGameOver">
                        <div class="gameover-title">游戏结束</div>
                        <div class="gameover-reason">{{ endReasonText }}</div>
                        <div class="gameover-winner" v-if="winnerPlayer">
                          🏆 {{ winnerPlayer.nickname }} 获胜！
                        </div>
                      </template>
                      <!-- 正常播放状态 -->
                      <template v-else>
                        <div v-if="snapshot.dice.total > 0" class="center-dice">
                          <span class="dice-big">{{ snapshot.dice.values[0] }}</span>
                          <span class="dice-plus">+</span>
                          <span class="dice-big">{{ snapshot.dice.values[1] }}</span>
                          <span class="dice-equals">= {{ snapshot.dice.total }}</span>
                        </div>
                        <div class="center-turn-info">第 {{ snapshot.turn_number }} 回合</div>
                        <div v-if="activePlayer" class="center-player">{{ activePlayer.nickname }} 的回合</div>
                      </template>
                      <!-- 当前操作描述 -->
                      <div v-if="replayStore.currentStep" class="center-action-desc">
                        {{ replayStore.currentStep.description }}
                      </div>
                    </div>
                  </div>

                  <!-- 右列 -->
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
                    <div class="tile-color-bar" v-if="snapshot.tiles[30 + row].group_color" :style="{ background: snapshot.tiles[30 + row].group_color as string }"></div>
                    <div class="tile-name">{{ snapshot.tiles[30 + row].name }}</div>
                    <div class="tile-info">
                      <span v-if="snapshot.tiles[30 + row].price">¥{{ snapshot.tiles[30 + row].price }}</span>
                    </div>
                    <div class="tile-players" v-if="getPlayersOnTile(snapshot.tiles[30 + row].position).length">
                      <div v-for="p in getPlayersOnTile(snapshot.tiles[30 + row].position)" :key="p.user_id" class="player-token">{{ p.nickname.charAt(0) }}</div>
                    </div>
                  </div>
                </template>

                <!-- 底部行 -->
                <template v-for="i in 11" :key="'bot-'+i">
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
                    <div class="tile-color-bar" v-if="snapshot.tiles[10 - i + 1].group_color" :style="{ background: snapshot.tiles[10 - i + 1].group_color as string }"></div>
                    <div class="tile-name">{{ snapshot.tiles[10 - i + 1].name }}</div>
                    <div class="tile-info">
                      <span v-if="snapshot.tiles[10 - i + 1].price">¥{{ snapshot.tiles[10 - i + 1].price }}</span>
                      <span v-if="snapshot.tiles[10 - i + 1].build_level" class="tile-houses">{{ snapshot.tiles[10 - i + 1].build_level >= 5 ? '🏨' : '🏠'.repeat(snapshot.tiles[10 - i + 1].build_level) }}</span>
                    </div>
                    <div class="tile-players" v-if="getPlayersOnTile(snapshot.tiles[10 - i + 1].position).length">
                      <div v-for="p in getPlayersOnTile(snapshot.tiles[10 - i + 1].position)" :key="p.user_id" class="player-token">{{ p.nickname.charAt(0) }}</div>
                    </div>
                  </div>
                </template>
              </div>
            </el-card>
          </el-col>

          <!-- 右侧：玩家 + 日志 + 控制 -->
          <el-col :span="8">
            <!-- 玩家列表 -->
            <el-card class="players-card">
              <template #header>{{ isGameOver ? '最终排名' : '玩家' }}</template>
              <div class="player-list">
                <div
                  v-for="(p, idx) in snapshot.players"
                  :key="p.user_id"
                  class="game-player-item"
                  :class="{
                    'player-active': !isGameOver && idx === snapshot.current_player_idx,
                    'player-bankrupt-row': p.is_bankrupt,
                    'player-winner': isGameOver && p.user_id === replayStore.winnerId,
                  }"
                >
                  <div class="flex items-center gap-2">
                    <div class="player-token-sm">
                      {{ p.is_ai ? '🤖' : p.nickname.charAt(0) }}
                    </div>
                    <span class="player-name">
                      <template v-if="isGameOver && replayStore.players.length">
                        {{ getPlayerRankBadge(p.user_id) }}
                      </template>
                      {{ p.nickname }}
                    </span>
                    <el-tag v-if="!isGameOver && idx === snapshot.current_player_idx" type="warning" size="small">行动中</el-tag>
                    <el-tag v-if="!isGameOver && p.is_in_jail" type="danger" size="small">监狱</el-tag>
                    <el-tag v-if="isGameOver && p.user_id === replayStore.winnerId" type="success" size="small">🏆</el-tag>
                  </div>
                  <div class="player-assets">
                    <span class="cash">¥{{ p.cash }}</span>
                    <el-tag v-if="p.is_bankrupt" type="danger" size="small">破产</el-tag>
                    <span v-if="isGameOver" class="player-props-count" :title="`持有 ${p.properties.length} 处地产`">
                      🏠{{ p.properties.length }}
                    </span>
                  </div>
                </div>
              </div>
            </el-card>

            <!-- 操作日志 -->
            <el-card class="log-card">
              <template #header>操作日志</template>
              <div class="log-list" ref="logListRef">
                <div
                  v-for="(log, idx) in displayLogs"
                  :key="idx"
                  class="log-item"
                  :class="{ 'log-current': idx === displayLogs.length - 1 }"
                >
                  {{ log }}
                </div>
                <div v-if="!displayLogs.length" class="text-gray-400 text-center py-4">
                  点击播放开始回放
                </div>
              </div>
            </el-card>

            <!-- 回放控制栏 -->
            <el-card class="control-card">
              <template #header>回放控制</template>

              <!-- 进度条 -->
              <div class="progress-area">
                <el-slider
                  v-model="stepSliderValue"
                  :min="0"
                  :max="replayStore.totalSteps"
                  :show-tooltip="false"
                  @change="onSliderChange"
                />
                <div class="progress-labels">
                  <span>步骤 {{ replayStore.currentStepIndex }}</span>
                  <span>{{ replayStore.totalSteps }}</span>
                </div>
              </div>

              <!-- 播放按钮 -->
              <div class="control-buttons">
                <el-button @click="replayStore.stepBackward()" :disabled="replayStore.currentStepIndex <= 0" circle>
                  ⏮
                </el-button>
                <el-button
                  :type="replayStore.isPlaying ? 'warning' : 'primary'"
                  @click="replayStore.togglePlay()"
                  size="large"
                  circle
                >
                  {{ replayStore.isPlaying ? '⏸' : '▶' }}
                </el-button>
                <el-button @click="replayStore.stepForward()" :disabled="replayStore.currentStepIndex >= replayStore.totalSteps" circle>
                  ⏭
                </el-button>
              </div>

              <!-- 速度控制 -->
              <div class="speed-area">
                <span class="text-sm text-gray-400">速度:</span>
                <el-radio-group v-model="speedValue" size="small" @change="onSpeedChange">
                  <el-radio-button :value="2000">0.5x</el-radio-button>
                  <el-radio-button :value="1000">1x</el-radio-button>
                  <el-radio-button :value="500">2x</el-radio-button>
                  <el-radio-button :value="250">4x</el-radio-button>
                </el-radio-group>
              </div>

              <!-- 回合跳转 -->
              <div class="turn-jump-area" v-if="replayStore.replayData">
                <span class="text-sm text-gray-400">跳转回合:</span>
                <el-select v-model="jumpTurn" size="small" @change="onJumpTurn" placeholder="选择回合" style="width: 120px">
                  <el-option
                    v-for="t in availableTurns"
                    :key="t"
                    :label="`第 ${t} 回合`"
                    :value="t"
                  />
                </el-select>
              </div>
            </el-card>

            <!-- 结算信息 -->
            <el-card v-if="replayStore.players.length" class="result-card">
              <template #header>最终排名</template>
              <div v-for="p in replayStore.players" :key="p.user_id" class="result-row">
                <span class="result-rank">#{{ p.rank }}</span>
                <span class="result-name">{{ p.nickname }}</span>
                <span class="result-amount" :class="p.settlement_amount >= 0 ? 'text-green-500' : 'text-red-500'">
                  {{ p.settlement_amount >= 0 ? '+' : '' }}¥{{ p.settlement_amount }}
                </span>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
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

function getPlayerRankBadge(userId: number): string {
  const player = replayStore.players.find((p) => p.user_id === userId)
  if (!player) return ''
  const badges: Record<number, string> = { 1: '🥇', 2: '🥈', 3: '🥉' }
  return badges[player.rank] || `#${player.rank} `
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

function tileStyle(tile: TileState): Record<string, string> {
  const style: Record<string, string> = {}
  if (tile.tile_type === 'START') style.background = '#f0f9eb'
  else if (tile.tile_type === 'JAIL') style.background = '#fdf6ec'
  else if (tile.tile_type === 'GO_TO_JAIL') style.background = '#fef0f0'
  else if (tile.tile_type === 'PARKING') style.background = '#f4f4f5'
  else if (tile.tile_type === 'CHANCE') style.background = '#ecf5ff'
  else if (tile.tile_type === 'FATE') style.background = '#fef0f0'
  else if (tile.tile_type === 'TAX') style.background = '#fafcff'
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
.replay-page {
  background: #f5f7fa;
  min-height: 100vh;
}

.replay-header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  height: 56px !important;
  padding: 0 16px;
}

.replay-main {
  padding: 16px;
  height: calc(100vh - 56px);
  overflow-y: auto;
}

.replay-body {
  height: 100%;
}

/* ─── 棋盘 ─── */

.board-card {
  height: 100%;
}

.board-card :deep(.el-card__body) {
  padding: 8px;
  overflow: auto;
}

.board-grid {
  display: grid;
  grid-template-columns: repeat(11, 1fr);
  grid-template-rows: repeat(11, 1fr);
  gap: 2px;
  width: 100%;
  aspect-ratio: 1;
  max-width: 660px;
  margin: 0 auto;
}

.tile-cell {
  border: 1px solid #ddd;
  border-radius: 3px;
  padding: 2px 4px;
  font-size: 10px;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: default;
  transition: all 0.2s;
  min-height: 40px;
}

.tile-cell.tile-current {
  border-color: #e6a23c;
  box-shadow: 0 0 4px #e6a23c88;
}

.tile-cell.tile-owned {
  border-color: #409eff66;
}

.tile-cell.tile-mortgaged {
  opacity: 0.6;
}

.tile-color-bar {
  width: 100%;
  height: 3px;
  border-radius: 2px;
  margin-bottom: 2px;
}

.tile-name {
  font-size: 9px;
  font-weight: 500;
  text-align: center;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.tile-info {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 8px;
  color: #999;
}

.tile-houses {
  font-size: 8px;
}

.tile-players {
  display: flex;
  gap: 1px;
  margin-top: 1px;
}

.player-token {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.board-center {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f9f9f9;
  border-radius: 8px;
  border: 1px dashed #ddd;
}

.board-center-content {
  text-align: center;
}

.center-dice {
  font-size: 24px;
  margin-bottom: 8px;
}

.dice-big {
  display: inline-block;
  width: 36px;
  height: 36px;
  line-height: 36px;
  text-align: center;
  background: #fff;
  border: 2px solid #409eff;
  border-radius: 6px;
  font-weight: bold;
  font-size: 18px;
  color: #409eff;
}

.dice-plus {
  margin: 0 4px;
  font-size: 16px;
  color: #999;
}

.dice-equals {
  margin-left: 4px;
  font-size: 14px;
  color: #666;
}

.center-turn-info {
  font-size: 14px;
  color: #666;
}

.center-player {
  font-size: 13px;
  color: #409eff;
  margin-top: 4px;
}

.center-action-desc {
  margin-top: 8px;
  padding: 4px 12px;
  background: #ecf5ff;
  border-radius: 4px;
  font-size: 12px;
  color: #409eff;
  font-weight: 500;
}

.gameover-title {
  font-size: 22px;
  font-weight: bold;
  color: #e6a23c;
  margin-bottom: 8px;
}

.gameover-reason {
  font-size: 13px;
  color: #999;
  margin-bottom: 6px;
}

.gameover-winner {
  font-size: 16px;
  font-weight: bold;
  color: #67c23a;
  margin-top: 4px;
}

/* ─── 玩家列表 ─── */

.players-card {
  margin-bottom: 12px;
}

.player-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.game-player-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  border-radius: 6px;
  transition: all 0.2s;
}

.game-player-item.player-active {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.game-player-item.player-bankrupt-row {
  opacity: 0.5;
  text-decoration: line-through;
}

.game-player-item.player-winner {
  background: #f0f9eb;
  border-left: 3px solid #67c23a;
}

.player-token-sm {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #909399;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

.player-name {
  font-size: 13px;
  font-weight: 500;
}

.player-assets {
  display: flex;
  align-items: center;
  gap: 4px;
}

.cash {
  font-weight: bold;
  color: #67c23a;
  font-size: 13px;
}

.player-props-count {
  font-size: 11px;
  color: #909399;
}

/* ─── 日志 ─── */

.log-card {
  margin-bottom: 12px;
}

.log-card :deep(.el-card__body) {
  padding: 8px;
}

.log-list {
  height: 200px;
  overflow-y: auto;
  font-size: 12px;
}

.log-item {
  padding: 4px 8px;
  border-bottom: 1px solid #f0f0f0;
  color: #666;
}

.log-item.log-current {
  color: #409eff;
  font-weight: 500;
  background: #ecf5ff;
  border-radius: 4px;
}

/* ─── 控制栏 ─── */

.control-card {
  margin-bottom: 12px;
}

.progress-area {
  margin-bottom: 12px;
}

.progress-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #999;
  margin-top: -4px;
}

.control-buttons {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin: 12px 0;
}

.speed-area {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  margin-bottom: 8px;
}

.turn-jump-area {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  margin-top: 8px;
}

/* ─── 结算信息 ─── */

.result-card {
  margin-bottom: 12px;
}

.result-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px solid #f5f5f5;
}

.result-rank {
  font-weight: bold;
  color: #e6a23c;
  min-width: 28px;
}

.result-name {
  flex: 1;
  font-size: 13px;
}

.result-amount {
  font-weight: bold;
  font-size: 13px;
}

.text-green-500 {
  color: #67c23a;
}

.text-red-500 {
  color: #f56c6c;
}

.text-gray-400 {
  color: #9ca3af;
}

.text-sm {
  font-size: 12px;
}

.flex {
  display: flex;
}

.items-center {
  align-items: center;
}

.gap-2 {
  gap: 8px;
}

.gap-3 {
  gap: 12px;
}

.flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.w-full {
  width: 100%;
}

.text-center {
  text-align: center;
}

.py-4 {
  padding-top: 16px;
  padding-bottom: 16px;
}
</style>
