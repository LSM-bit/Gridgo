<template>
  <div class="game-page">
    <el-container style="height: 100vh">
      <!-- 顶栏 -->
      <el-header class="game-header">
        <div class="flex-between w-full h-full">
          <div class="flex items-center gap-3">
            <el-tag :type="phaseTagType" size="large">{{ phaseText }}</el-tag>
            <span>第 {{ gameStore.state?.turn_number ?? 0 }} 回合</span>
            <span v-if="gameStore.currentPlayer" class="text-gray-400">
              当前：{{ gameStore.currentPlayer.nickname }}
              <el-tag v-if="gameStore.currentPlayer.is_ai" type="info" size="small">AI</el-tag>
            </span>
          </div>
          <div class="flex items-center gap-2">
            <el-tag :type="gameStore.connected ? 'success' : 'danger'" size="small">
              {{ gameStore.connected ? '已连接' : '未连接' }}
            </el-tag>
            <el-button size="small" @click="handleLeave">退出</el-button>
          </div>
        </div>
      </el-header>

      <!-- 主体 -->
      <el-main v-loading="!gameStore.state">
        <el-row :gutter="16" class="game-body" v-if="gameStore.state">
          <!-- 左侧：棋盘 -->
          <el-col :span="16">
            <el-card class="board-card">
              <template #header>
                <span>🗺️ 棋盘</span>
              </template>
              <div class="board-grid">
                <!-- 顶部行：位置 20→30，从左到右 -->
                <template v-for="i in 11" :key="'top-'+i">
                  <div
                    v-if="gameStore.state.tiles[19 + i]"
                    class="tile-cell"
                    :class="{
                      'tile-current': isPlayerOnTile(gameStore.state.tiles[19 + i].position),
                      'tile-owned-me': gameStore.state.tiles[19 + i].owner_id === gameStore.currentUserId,
                      'tile-owned-other': gameStore.state.tiles[19 + i].owner_id && gameStore.state.tiles[19 + i].owner_id !== gameStore.currentUserId,
                      'tile-mortgaged': gameStore.state.tiles[19 + i].is_mortgaged,
                    }"
                    :style="{ ...tileStyle(gameStore.state.tiles[19 + i]), gridRow: 1, gridColumn: i }"
                    @click="showTileInfo(gameStore.state.tiles[19 + i])"
                  >
                    <div class="tile-color-bar" v-if="gameStore.state.tiles[19 + i].group_color" :style="{ background: gameStore.state.tiles[19 + i].group_color as string }"></div>
                    <div class="tile-name">{{ gameStore.state.tiles[19 + i].name }}</div>
                    <div class="tile-info">
                      <span v-if="gameStore.state.tiles[19 + i].price">¥{{ gameStore.state.tiles[19 + i].price }}</span>
                      <span v-if="gameStore.state.tiles[19 + i].build_level" class="tile-houses">{{ gameStore.state.tiles[19 + i].build_level >= 5 ? '🏨' : '🏠'.repeat(gameStore.state.tiles[19 + i].build_level) }}</span>
                    </div>
                    <div class="tile-players" v-if="getPlayersOnTile(gameStore.state.tiles[19 + i].position).length">
                      <div v-for="p in getPlayersOnTile(gameStore.state.tiles[19 + i].position)" :key="p.user_id" class="player-token" :class="{ 'player-me': p.user_id === gameStore.currentUserId }">{{ p.nickname.charAt(0) }}</div>
                    </div>
                  </div>
                </template>

                <!-- 左右列 + 中间区域 -->
                <template v-for="row in 9" :key="'mid-'+row">
                  <!-- 左列：位置 19→11，从上到下 -->
                  <div
                    v-if="gameStore.state.tiles[20 - row]"
                    class="tile-cell"
                    :class="{
                      'tile-current': isPlayerOnTile(gameStore.state.tiles[20 - row].position),
                      'tile-owned-me': gameStore.state.tiles[20 - row].owner_id === gameStore.currentUserId,
                      'tile-owned-other': gameStore.state.tiles[20 - row].owner_id && gameStore.state.tiles[20 - row].owner_id !== gameStore.currentUserId,
                      'tile-mortgaged': gameStore.state.tiles[20 - row].is_mortgaged,
                    }"
                    :style="{ ...tileStyle(gameStore.state.tiles[20 - row]), gridRow: row + 1, gridColumn: 1 }"
                    @click="showTileInfo(gameStore.state.tiles[20 - row])"
                  >
                    <div class="tile-color-bar" v-if="gameStore.state.tiles[20 - row].group_color" :style="{ background: gameStore.state.tiles[20 - row].group_color as string }"></div>
                    <div class="tile-name">{{ gameStore.state.tiles[20 - row].name }}</div>
                    <div class="tile-info">
                      <span v-if="gameStore.state.tiles[20 - row].price">¥{{ gameStore.state.tiles[20 - row].price }}</span>
                    </div>
                    <div class="tile-players" v-if="getPlayersOnTile(gameStore.state.tiles[20 - row].position).length">
                      <div v-for="p in getPlayersOnTile(gameStore.state.tiles[20 - row].position)" :key="p.user_id" class="player-token" :class="{ 'player-me': p.user_id === gameStore.currentUserId }">{{ p.nickname.charAt(0) }}</div>
                    </div>
                  </div>

                  <!-- 中间区域 -->
                  <div v-if="row === 1" class="board-center" :style="{ gridRow: '2 / 11', gridColumn: '2 / 11' }">
                    <div class="board-center-content">
                      <div v-if="gameStore.state.dice.total > 0" class="center-dice">
                        <span class="dice-big">{{ gameStore.state.dice.values[0] }}</span>
                        <span class="dice-plus">+</span>
                        <span class="dice-big">{{ gameStore.state.dice.values[1] }}</span>
                        <span class="dice-equals">= {{ gameStore.state.dice.total }}</span>
                      </div>
                      <div class="center-turn-info">第 {{ gameStore.state.turn_number }} 回合</div>
                      <div v-if="gameStore.currentPlayer" class="center-player">{{ gameStore.currentPlayer.nickname }} 的回合</div>
                    </div>
                  </div>

                  <!-- 右列：位置 31→39，从上到下 -->
                  <div
                    v-if="gameStore.state.tiles[30 + row]"
                    class="tile-cell"
                    :class="{
                      'tile-current': isPlayerOnTile(gameStore.state.tiles[30 + row].position),
                      'tile-owned-me': gameStore.state.tiles[30 + row].owner_id === gameStore.currentUserId,
                      'tile-owned-other': gameStore.state.tiles[30 + row].owner_id && gameStore.state.tiles[30 + row].owner_id !== gameStore.currentUserId,
                      'tile-mortgaged': gameStore.state.tiles[30 + row].is_mortgaged,
                    }"
                    :style="{ ...tileStyle(gameStore.state.tiles[30 + row]), gridRow: row + 1, gridColumn: 11 }"
                    @click="showTileInfo(gameStore.state.tiles[30 + row])"
                  >
                    <div class="tile-color-bar" v-if="gameStore.state.tiles[30 + row].group_color" :style="{ background: gameStore.state.tiles[30 + row].group_color as string }"></div>
                    <div class="tile-name">{{ gameStore.state.tiles[30 + row].name }}</div>
                    <div class="tile-info">
                      <span v-if="gameStore.state.tiles[30 + row].price">¥{{ gameStore.state.tiles[30 + row].price }}</span>
                    </div>
                    <div class="tile-players" v-if="getPlayersOnTile(gameStore.state.tiles[30 + row].position).length">
                      <div v-for="p in getPlayersOnTile(gameStore.state.tiles[30 + row].position)" :key="p.user_id" class="player-token" :class="{ 'player-me': p.user_id === gameStore.currentUserId }">{{ p.nickname.charAt(0) }}</div>
                    </div>
                  </div>
                </template>

                <!-- 底部行：位置 10→0，从左到右 -->
                <template v-for="i in 11" :key="'bot-'+i">
                  <div
                    v-if="gameStore.state.tiles[10 - i + 1] !== undefined"
                    class="tile-cell"
                    :class="{
                      'tile-current': isPlayerOnTile(gameStore.state.tiles[10 - i + 1].position),
                      'tile-owned-me': gameStore.state.tiles[10 - i + 1].owner_id === gameStore.currentUserId,
                      'tile-owned-other': gameStore.state.tiles[10 - i + 1].owner_id && gameStore.state.tiles[10 - i + 1].owner_id !== gameStore.currentUserId,
                      'tile-mortgaged': gameStore.state.tiles[10 - i + 1].is_mortgaged,
                    }"
                    :style="{ ...tileStyle(gameStore.state.tiles[10 - i + 1]), gridRow: 11, gridColumn: i }"
                    @click="showTileInfo(gameStore.state.tiles[10 - i + 1])"
                  >
                    <div class="tile-color-bar" v-if="gameStore.state.tiles[10 - i + 1].group_color" :style="{ background: gameStore.state.tiles[10 - i + 1].group_color as string }"></div>
                    <div class="tile-name">{{ gameStore.state.tiles[10 - i + 1].name }}</div>
                    <div class="tile-info">
                      <span v-if="gameStore.state.tiles[10 - i + 1].price">¥{{ gameStore.state.tiles[10 - i + 1].price }}</span>
                      <span v-if="gameStore.state.tiles[10 - i + 1].build_level" class="tile-houses">{{ gameStore.state.tiles[10 - i + 1].build_level >= 5 ? '🏨' : '🏠'.repeat(gameStore.state.tiles[10 - i + 1].build_level) }}</span>
                    </div>
                    <div class="tile-players" v-if="getPlayersOnTile(gameStore.state.tiles[10 - i + 1].position).length">
                      <div v-for="p in getPlayersOnTile(gameStore.state.tiles[10 - i + 1].position)" :key="p.user_id" class="player-token" :class="{ 'player-me': p.user_id === gameStore.currentUserId }">{{ p.nickname.charAt(0) }}</div>
                    </div>
                  </div>
                </template>
              </div>
            </el-card>
          </el-col>

          <!-- 右侧：玩家 + 操作 + 日志 -->
          <el-col :span="8">
            <!-- 玩家列表 -->
            <el-card class="players-card">
              <template #header>👥 玩家</template>
              <div class="player-list">
                <div
                  v-for="p in gameStore.state.players"
                  :key="p.user_id"
                  class="game-player-item"
                  :class="{
                    'player-active': p.user_id === gameStore.currentPlayer?.user_id,
                    'player-bankrupt-row': p.is_bankrupt,
                    'player-me-row': p.user_id === gameStore.currentUserId,
                  }"
                >
                  <div class="flex items-center gap-2">
                    <div class="player-token-sm" :class="{ 'player-me': p.user_id === gameStore.currentUserId }">
                      {{ p.is_ai ? '🤖' : p.nickname.charAt(0) }}
                    </div>
                    <span class="player-name">{{ p.nickname }}</span>
                    <el-tag v-if="p.user_id === gameStore.currentPlayer?.user_id" type="warning" size="small">行动中</el-tag>
                    <el-tag v-if="p.is_in_jail" type="danger" size="small">监狱</el-tag>
                  </div>
                  <div class="player-assets">
                    <span class="cash">¥{{ p.cash }}</span>
                    <el-tag v-if="p.is_bankrupt" type="danger" size="small">破产</el-tag>
                  </div>
                </div>
              </div>
            </el-card>

            <!-- 操作面板 -->
            <el-card class="action-card">
              <template #header>🎮 操作</template>

              <!-- 骰子显示 -->
              <div v-if="gameStore.state.dice.total > 0" class="dice-display">
                <span class="dice">{{ gameStore.state.dice.values[0] }}</span>
                <span class="dice">{{ gameStore.state.dice.values[1] }}</span>
                <span class="dice-total">= {{ gameStore.state.dice.total }}</span>
                <el-tag v-if="gameStore.state.dice.is_double" type="warning" size="small">双数!</el-tag>
              </div>

              <!-- 监狱操作 -->
              <div v-if="gameStore.isInJail && gameStore.isMyTurn" class="action-buttons">
                <el-button type="primary" @click="gameStore.sendRollDice()">🎲 掷骰出狱</el-button>
                <el-button type="warning" @click="gameStore.sendJailPayBail()">
                  💰 保释金 ¥{{ gameStore.state.jail_bail }}
                </el-button>
                <el-button v-if="gameStore.hasJailCard" type="success" @click="gameStore.sendJailUseCard()">
                  🃏 使用免罪卡
                </el-button>
              </div>

              <!-- 掷骰子 -->
              <div v-else-if="gameStore.canRoll" class="action-buttons">
                <el-button type="primary" size="large" @click="gameStore.sendRollDice()">
                  🎲 掷骰子
                </el-button>
              </div>

              <!-- 购买决策 -->
              <div v-else-if="gameStore.canBuyProperty && gameStore.pendingDecision" class="action-buttons">
                <p class="decision-text">
                  停在 <strong>{{ gameStore.pendingDecision.tile_name }}</strong>，
                  购买价格 <strong>¥{{ gameStore.pendingDecision.price }}</strong>
                </p>
                <el-button type="primary" @click="gameStore.sendBuyProperty(gameStore.pendingDecision!.tile_id)">
                  💰 购买 (¥{{ gameStore.pendingDecision.price }})
                </el-button>
                <el-button @click="gameStore.sendDeclineProperty(gameStore.pendingDecision!.tile_id)">
                  ⏭️ 放弃
                </el-button>
              </div>

              <!-- 自由行动 -->
              <div v-else-if="gameStore.canAct" class="action-buttons">
                <el-button type="success" @click="gameStore.sendEndTurn()">✅ 结束回合</el-button>
                <el-divider content-position="left">建造</el-divider>
                <div class="build-list">
                  <div v-for="tile in buildableProperties" :key="tile.position" class="build-item">
                    <span>{{ tile.name }} (Lv.{{ tile.build_level }})</span>
                    <el-button size="small" @click="gameStore.sendBuild(tile.position)" :disabled="!canBuild(tile)">
                      建造 ¥{{ tile.build_cost }}
                    </el-button>
                  </div>
                </div>
              </div>

              <!-- 等待/非自己回合/观战 -->
              <div v-else class="action-waiting">
                <template v-if="gameStore.isSpectator">
                  <span>👀 观战模式</span>
                  <span class="text-gray-400 text-sm">你正在观战，无法操作</span>
                </template>
                <template v-else>
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>{{ waitText }}</span>
                </template>
              </div>
            </el-card>

            <!-- 日志 / 聊天 -->
            <el-card class="log-card">
              <template #header>
                <el-tabs v-model="rightTab" class="right-tabs">
                  <el-tab-pane label="📜 日志" name="log" />
                  <el-tab-pane label="💬 聊天" name="chat" />
                </el-tabs>
              </template>

              <!-- 日志面板 -->
              <div v-show="rightTab === 'log'" ref="logContainer" class="log-list">
                <div v-for="(log, i) in gameStore.logs" :key="i" class="log-item" :class="'log-' + log.type">
                  {{ log.message }}
                </div>
                <div v-if="gameStore.logs.length === 0" class="log-empty">暂无日志</div>
              </div>

              <!-- 聊天面板 -->
              <div v-show="rightTab === 'chat'" class="chat-panel">
                <div ref="chatContainer" class="chat-messages">
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
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 游戏结束弹窗 -->
        <el-dialog v-model="showGameOver" title="🏆 游戏结束" width="500px" :close-on-click-modal="false" :show-close="false">
          <div class="gameover-content">
            <p class="gameover-reason">{{ gameOverReason }}</p>
            <div class="gameover-rankings">
              <div v-for="(r, i) in gameOverRankings" :key="r.user_id" class="gameover-rank" :class="{ 'rank-me': r.user_id === gameStore.currentUserId }">
                <span class="rank-pos">{{ ['🥇', '🥈', '🥉'][i] || `#${r.rank}` }}</span>
                <span class="rank-name">{{ r.nickname }}</span>
                <span class="rank-assets">¥{{ r.total_assets }}</span>
              </div>
            </div>
          </div>
          <template #footer>
            <el-button @click="handleBackToRoom">留在房间</el-button>
            <el-button @click="goToReplay">查看回放</el-button>
            <el-button type="primary" @click="handleLeave">返回大厅</el-button>
          </template>
        </el-dialog>

        <!-- 机会/命运卡弹窗 -->
        <Transition name="card-pop">
          <div v-if="gameStore.activeCard" class="card-overlay" @click.self="dismissCard">
            <div class="card-container" :class="{ 'card-chance': gameStore.activeCard.card_type === 'CHANCE', 'card-fate': gameStore.activeCard.card_type === 'FATE' }">
              <!-- 卡片头部 -->
              <div class="card-header">
                <span class="card-type-badge">{{ gameStore.activeCard.card_type === 'CHANCE' ? '机会卡' : '命运卡' }}</span>
                <span class="card-id">{{ gameStore.activeCard.card_id }}</span>
              </div>
              <!-- 效果图标 -->
              <div class="card-effect-icon">
                {{ effectIcon(gameStore.activeCard.effect_type) }}
              </div>
              <!-- 卡片名称 -->
              <h2 class="card-title">{{ gameStore.activeCard.card_name }}</h2>
              <!-- 卡片描述 -->
              <p class="card-description">{{ gameStore.activeCard.description }}</p>
              <!-- 效果数值提示 -->
              <div class="card-effect-value" v-if="effectLabel(gameStore.activeCard)">
                {{ effectLabel(gameStore.activeCard) }}
              </div>
              <!-- 关闭按钮 -->
              <el-button type="primary" class="card-close-btn" @click="dismissCard">
                知道了
              </el-button>
            </div>
          </div>
        </Transition>

        <!-- 地块信息弹窗 -->
        <el-dialog v-model="showTileDialog" :title="selectedTile?.name ?? ''" width="360px">
          <div v-if="selectedTile" class="tile-detail">
            <p><strong>类型：</strong>{{ tileTypeText(selectedTile.tile_type) }}</p>
            <p v-if="selectedTile.tile_group"><strong>分组：</strong>{{ selectedTile.tile_group }}</p>
            <p v-if="selectedTile.price"><strong>价格：</strong>¥{{ selectedTile.price }}</p>
            <p v-if="selectedTile.build_cost"><strong>建造费：</strong>¥{{ selectedTile.build_cost }}</p>
            <p v-if="selectedTile.owner_id"><strong>拥有者：</strong>{{ getPlayerName(selectedTile.owner_id) }}</p>
            <p><strong>建筑等级：</strong>{{ selectedTile.build_level }} / {{ gameStore.state?.max_build_level ?? 5 }}</p>
            <p v-if="selectedTile.is_mortgaged"><el-tag type="warning">已抵押</el-tag></p>
            <div v-if="selectedTile.rent_0 !== null" class="rent-table">
              <strong>租金表：</strong>
              <table>
                <tr><td>空地</td><td>¥{{ selectedTile.rent_0 }}</td></tr>
                <tr><td>1房</td><td>¥{{ selectedTile.rent_1 }}</td></tr>
                <tr><td>2房</td><td>¥{{ selectedTile.rent_2 }}</td></tr>
                <tr><td>3房</td><td>¥{{ selectedTile.rent_3 }}</td></tr>
                <tr><td>4房</td><td>¥{{ selectedTile.rent_4 }}</td></tr>
                <tr><td>酒店</td><td>¥{{ selectedTile.rent_5 }}</td></tr>
              </table>
            </div>
          </div>
        </el-dialog>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useGameStore } from '@/stores/game'
import { useRoomStore } from '@/stores/room'
import { gameWS } from '@/api/ws'
import type { TileState } from '@/stores/game'
import { getChatMessages, sendChatMessage } from '@/api/chat'
import type { ChatMessage } from '@/api/chat'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const gameStore = useGameStore()
const roomStore = useRoomStore()

const roomId = route.params.id as string
const logContainer = ref<HTMLElement | null>(null)

// ─── 地块信息弹窗 ───

const showTileDialog = ref(false)
const selectedTile = ref<TileState | null>(null)

const showTileInfo = (tile: TileState) => {
  selectedTile.value = tile
  showTileDialog.value = true
}

// ─── 游戏结束弹窗 ───

const showGameOver = ref(false)
const gameOverRankings = ref<any[]>([])
const gameOverReason = ref('')
const gameRecordId = ref<number | null>(null)

// ─── 计算属性 ───

const phaseText = computed(() => {
  const map: Record<string, string> = {
    TURN_START: '回合开始',
    WAIT_ROLL: '等待掷骰',
    ROLLING: '掷骰中',
    MOVING: '移动中',
    TILE_EFFECT: '地块效果',
    WAIT_DECISION: '等待决策',
    FREE_ACTION: '自由行动',
    TURN_END: '回合结束',
    AUCTION: '拍卖中',
    BANKRUPTCY: '破产处理',
    GAME_OVER: '游戏结束',
  }
  return map[gameStore.phase] ?? gameStore.phase
})

const phaseTagType = computed(() => {
  if (gameStore.isMyTurn) return 'success'
  if (gameStore.phase === 'GAME_OVER') return 'danger'
  return 'info'
})

const waitText = computed(() => {
  if (gameStore.isSpectator) return `👀 观战中 · ${gameStore.currentPlayer?.nickname ?? ''} 的回合`
  if (gameStore.isGameOver) return '游戏已结束'
  if (!gameStore.isMyTurn) return `${gameStore.currentPlayer?.nickname ?? ''} 的回合...`
  return '等待中...'
})

const buildableProperties = computed(() => {
  if (!gameStore.state || !gameStore.myPlayer) return []
  return gameStore.myPlayer.properties
    .map((pos) => gameStore.state!.tiles[pos])
    .filter((t) => t.tile_type === 'PROPERTY' && t.build_level < (gameStore.state?.max_build_level ?? 5) && !t.is_mortgaged)
})


// ─── 辅助方法 ───

const canBuild = (tile: TileState) => {
  if (!gameStore.myPlayer || !gameStore.state) return false
  return (gameStore.myPlayer.cash >= (tile.build_cost ?? 0))
}

const isPlayerOnTile = (position: number) => {
  return gameStore.state?.players.some((p) => p.position === position && !p.is_bankrupt) ?? false
}

const getPlayersOnTile = (position: number) => {
  return gameStore.state?.players.filter((p) => p.position === position && !p.is_bankrupt) ?? []
}

const getPlayerName = (userId: number) => {
  const p = gameStore.state?.players.find((p) => p.user_id === userId)
  return p?.nickname ?? '未知'
}

const getTileName = (position: number) => {
  return gameStore.state?.tiles[position]?.name ?? `#${position}`
}

// ─── 卡片相关辅助方法 ───

const effectIcon = (effectType: string): string => {
  const iconMap: Record<string, string> = {
    move_to_position: '🚀',
    move_forward: '➡️',
    move_backward: '⬅️',
    move_to_nearest_station: '🚉',
    gain_money: '💰',
    lose_money: '💸',
    pay_per_house: '🏠',
    gain_from_all: '🎁',
    go_to_jail: '⛓️',
    get_out_of_jail: '🗝️',
  }
  return iconMap[effectType] ?? '🃏'
}

const effectLabel = (card: { effect_type: string; effect_value: number | null }): string => {
  const { effect_type, effect_value } = card
  if (effect_type === 'gain_money') return `+¥${effect_value}`
  if (effect_type === 'lose_money') return `-¥${effect_value}`
  if (effect_type === 'move_forward') return `前进 ${effect_value} 格`
  if (effect_type === 'move_backward') return `后退 ${effect_value} 格`
  if (effect_type === 'gain_from_all') return `每人支付 ¥${effect_value}`
  if (effect_type === 'pay_per_house') return `每房 ¥${effect_value}`
  if (effect_type === 'move_to_position') {
    const tileName = gameStore.state?.tiles[effect_value ?? 0]?.name
    return tileName ? `前往 ${tileName}` : ''
  }
  return ''
}

const dismissCard = () => {
  gameStore.dismissCard()
}

const tileStyle = (tile: TileState): { background: string } => {
  // 特殊地块背景色
  const bgMap: Record<string, string> = {
    START: '#e6f7e6',
    JAIL: '#f0f0f0',
    GO_TO_JAIL: '#fde6e6',
    PARKING: '#e6f0ff',
    CHANCE: '#fff7e6',
    FATE: '#f5e6ff',
    TAX: '#ffe6e6',
  }
  return { background: bgMap[tile.tile_type] ?? '#ffffff' }
}

const tileTypeText = (type: string) => {
  const map: Record<string, string> = {
    START: '起点', PROPERTY: '地产', STATION: '车站', UTILITY: '设施',
    CHANCE: '机会', FATE: '命运', TAX: '税收', JAIL: '监狱',
    PARKING: '停车场', GO_TO_JAIL: '去监狱',
  }
  return map[type] ?? type
}

// ─── WebSocket 事件处理 ───

const setupWSHandlers = () => {
  // 状态快照（连接时首次推送）
  gameWS.on('state.snapshot', (data: any) => {
    // 服务端可能在 snapshot 中附带 is_spectator 标识
    if (data.is_spectator !== undefined) {
      gameStore.isSpectator = data.is_spectator
      delete data.is_spectator
    }
    gameStore.applySnapshot(data)
    gameStore.connected = true
  })

  // 状态更新（每次 _save_state 后自动推送）
  gameWS.on('state.update', (data: any) => {
    gameStore.applySnapshot(data)
  })

  // 回合变更
  gameWS.on('game.turn_change', (data: any) => {
    gameStore.addLog('turn', `第 ${data.turn_number} 回合：${data.current_player_nickname}`)
  })

  // 骰子结果
  gameWS.on('game.dice_result', (data: any) => {
    gameStore.addLog('dice', `${getPlayerName(data.player_id)} 掷出 [${data.dice[0]}][${data.dice[1]}] = ${data.total}${data.is_double ? ' (双数!)' : ''}`)
  })

  // 棋子移动
  gameWS.on('game.player_moved', (data: any) => {
    if (data.passed_go) {
      gameStore.addLog('money', `${getPlayerName(data.player_id)} 经过起点，获得 ¥200`)
    }
  })

  // 地块事件
  gameWS.on('game.tile_event', (data: any) => {
    if (data.event_type === 'property_unowned') {
      gameStore.pendingDecision = {
        type: 'property_unowned',
        tile_id: data.tile_id,
        tile_name: data.tile_name,
        price: data.price,
      }
      gameStore.addLog('tile', `${getPlayerName(data.player_id)} 停在 ${data.tile_name}，可购买 (¥${data.price})`)
    }
  })

  // 地产购买
  gameWS.on('game.property_bought', (data: any) => {
    gameStore.addLog('buy', `${getPlayerName(data.player_id)} 购买了 ${data.tile_name} (¥${data.price})`)
    gameStore.clearPendingDecision()
  })

  // 租金支付
  gameWS.on('game.rent_paid', (data: any) => {
    gameStore.addLog('rent', `${getPlayerName(data.from_id)} 向 ${getPlayerName(data.to_id)} 支付租金 ¥${data.amount} (${data.tile_name})`)
  })

  // 卡片
  gameWS.on('game.card_drawn', (data: any) => {
    gameStore.addLog('card', `${getPlayerName(data.player_id)} 抽到${data.card_type === 'CHANCE' ? '机会' : '命运'}卡：${data.card_name}`)
    // 展示卡片弹窗
    gameStore.showCard({
      card_type: data.card_type,
      card_id: data.card_id,
      card_name: data.card_name,
      effect_type: data.effect_type,
      effect_value: data.effect_value,
      description: data.description,
      player_id: data.player_id,
    })
  })

  // 建造
  gameWS.on('game.building_built', (data: any) => {
    gameStore.addLog('build', `${getPlayerName(data.player_id)} 在 ${data.tile_name} 建造至 Lv.${data.level}`)
  })

  // 拆除
  gameWS.on('game.building_demolished', (data: any) => {
    gameStore.addLog('build', `${getPlayerName(data.player_id)} 拆除了 ${data.tile_name} 的房屋`)
  })

  // 抵押/赎回
  gameWS.on('game.property_mortgaged', (data: any) => {
    gameStore.addLog('mortgage', `${getPlayerName(data.player_id)} 抵押了 ${getTileName(data.tile_id)}`)
  })

  gameWS.on('game.property_redeemed', (data: any) => {
    gameStore.addLog('mortgage', `${getPlayerName(data.player_id)} 赎回了 ${getTileName(data.tile_id)}`)
  })

  // 放弃购买
  gameWS.on('game.property_declined', (data: any) => {
    gameStore.addLog('tile', `${getPlayerName(data.player_id)} 放弃了 ${getTileName(data.tile_id)}`)
    gameStore.clearPendingDecision()
  })

  // 监狱
  gameWS.on('game.jail_sent', (data: any) => {
    gameStore.addLog('jail', `${getPlayerName(data.player_id)} 入狱 (${data.reason})`)
  })

  gameWS.on('game.jail_released', (data: any) => {
    const methodMap: Record<string, string> = { double: '掷出双数', bail: '支付保释金', card: '使用免罪卡', forced_bail: '强制保释' }
    gameStore.addLog('jail', `${getPlayerName(data.player_id)} 出狱 (${methodMap[data.method] ?? data.method})`)
  })

  // 破产
  gameWS.on('game.player_bankrupt', (data: any) => {
    gameStore.addLog('bankrupt', `${getPlayerName(data.player_id)} 破产了！`)
  })

  // 金钱变化
  gameWS.on('game.money_change', (data: any) => {
    const sign = data.amount > 0 ? '+' : ''
    gameStore.addLog('money', `${getPlayerName(data.player_id)} ${sign}¥${data.amount} (${data.reason})`)
  })

  // 获得免罪卡
  gameWS.on('game.get_out_of_jail_card', (data: any) => {
    gameStore.addLog('card', `${getPlayerName(data.player_id)} 获得免罪卡（共 ${data.total_cards} 张）`)
  })

  // 税收
  gameWS.on('game.tax_paid', (data: any) => {
    gameStore.addLog('tax', `${getPlayerName(data.player_id)} 支付 ${data.tile_name} ¥${data.amount}`)
  })

  // 双数再掷
  gameWS.on('game.extra_roll', (data: any) => {
    gameStore.addLog('dice', `${getPlayerName(data.player_id)} 掷出双数，可以再掷一次！`)
  })

  // 游戏结束
  gameWS.on('game.over', (data: any) => {
    gameStore.addLog('over', `游戏结束！`)
    gameOverRankings.value = data.rankings
    gameRecordId.value = data.game_record_id
    const reasonMap: Record<string, string> = {
      last_standing: '仅剩一人',
      turn_limit: '达到回合上限',
      vote_end: '投票结束',
    }
    gameOverReason.value = reasonMap[data.end_reason] ?? data.end_reason
    showGameOver.value = true
    // 存储到 roomStore，供房间页面显示
    roomStore.setGameOverData({
      end_reason: data.end_reason,
      winner_id: data.winner_id,
      rankings: data.rankings,
      total_turns: data.total_turns,
    })
  })

  // 通用消息（更新内部状态）
  gameWS.on('*', (_msg: any) => {
    // 收到任何游戏消息后，请求最新快照保持同步
    // 这里用 debounce 避免频繁请求
  })

  // 连接/断线
  gameWS.on('system.player_connected', (data: any) => {
    gameStore.addLog('system', `${getPlayerName(data.player_id)} 重新连接`)
  })

  gameWS.on('system.player_disconnected', (data: any) => {
    gameStore.addLog('system', `${getPlayerName(data.player_id)} 断线`)
  })

  gameWS.on('system.pong', () => {
    gameStore.connected = true
  })
}

// ─── 生命周期 ───

onMounted(() => {
  console.log('[Game] ====== onMounted ======')
  console.log('[Game] isLoggedIn:', userStore.isLoggedIn, 'userId:', userStore.userId, 'roomId:', roomId)
  console.log('[Game] token:', userStore.token ? userStore.token.substring(0, 30) + '...' : 'EMPTY!')
  console.log('[Game] route.params:', JSON.stringify(route.params))
  console.log('[Game] full path:', route.fullPath)

  if (!userStore.isLoggedIn) {
    console.error('[Game] User not logged in! Redirecting to login.')
    router.push('/login')
    return
  }

  if (!roomId) {
    console.error('[Game] No roomId in route params!')
    return
  }

  if (!userStore.token) {
    console.error('[Game] No token available!')
    return
  }

  gameStore.setCurrentUserId(userStore.userId)
  setupWSHandlers()

  // 连接 WebSocket
  console.log('[Game] Calling gameWS.connect()...')
  gameWS.connect(userStore.token, roomId)
  console.log('[Game] gameWS.connect() called')

  // 启动聊天轮询
  startChatPolling()
})

onUnmounted(() => {
  gameWS.disconnect()
  gameStore.reset()
  stopChatPolling()
})

// 日志自动滚动
watch(() => gameStore.logs.length, async () => {
  await nextTick()
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
})

// ─── 操作 ───

const handleLeave = () => {
  gameWS.disconnect()
  gameStore.reset()
  roomStore.reset()
  stopChatPolling()
  router.push('/')
}

const handleBackToRoom = () => {
  gameWS.disconnect()
  gameStore.reset()
  stopChatPolling()
  // 跳转回房间页面，保留 roomStore 数据（包含 gameOverData）
  if (roomStore.roomCode) {
    router.push(`/room/${roomStore.roomCode}`)
  } else {
    router.push('/')
  }
}

const goToReplay = () => {
  if (gameRecordId.value) {
    gameWS.disconnect()
    gameStore.reset()
    stopChatPolling()
    router.push({ name: 'Replay', params: { id: gameRecordId.value } })
  }
}

// ─── 聊天功能 ───

const rightTab = ref('log')
const messages = ref<ChatMessage[]>([])
const chatInput = ref('')
const sendLoading = ref(false)
const chatLoading = ref(false)
const hasMoreMessages = ref(false)
const chatContainer = ref<HTMLElement | null>(null)
let chatPollingTimer: ReturnType<typeof setInterval> | null = null

const chatRoomId = computed(() => gameStore.state?.room_id ?? roomId)

const formatTime = (isoStr: string) => {
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

const fetchMessages = async () => {
  const rid = chatRoomId.value
  if (!rid) return
  try {
    const latestId = messages.value.length > 0 ? messages.value[messages.value.length - 1].id : undefined
    const newMsgs = await getChatMessages(rid, undefined, 50)

    if (messages.value.length === 0) {
      messages.value = newMsgs
    } else {
      const lastIdx = newMsgs.findIndex((m) => m.id === latestId)
      if (lastIdx >= 0 && lastIdx < newMsgs.length - 1) {
        const appended = newMsgs.slice(lastIdx + 1)
        messages.value.push(...appended)
      } else if (lastIdx === -1) {
        messages.value = newMsgs
      }
    }

    hasMoreMessages.value = newMsgs.length >= 50

    await nextTick()
    scrollToBottomIfNear()
  } catch {
    // 静默忽略
  }
}

const loadOlderMessages = async () => {
  const rid = chatRoomId.value
  if (!rid || messages.value.length === 0) return
  chatLoading.value = true
  try {
    const oldestId = messages.value[0].id
    const olderMsgs = await getChatMessages(rid, oldestId, 50)
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

const scrollToBottomIfNear = () => {
  const el = chatContainer.value
  if (!el) return
  const threshold = 150
  const distToBottom = el.scrollHeight - el.scrollTop - el.clientHeight
  if (distToBottom < threshold) {
    el.scrollTop = el.scrollHeight
  }
}

const scrollToBottom = () => {
  const el = chatContainer.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

const handleSendMessage = async () => {
  const content = chatInput.value.trim()
  const rid = chatRoomId.value
  if (!content || !rid) return

  sendLoading.value = true
  try {
    await sendChatMessage(rid, content)
    chatInput.value = ''
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

const startChatPolling = () => {
  stopChatPolling()
  chatPollingTimer = setInterval(fetchMessages, 3000)
}

const stopChatPolling = () => {
  if (chatPollingTimer) {
    clearInterval(chatPollingTimer)
    chatPollingTimer = null
  }
}

// 切换到聊天 Tab 时加载消息
watch(rightTab, (val) => {
  if (val === 'chat' && messages.value.length === 0) {
    fetchMessages().then(() => {
      nextTick(() => scrollToBottom())
    })
  }
})
</script>

<style scoped>
.game-page {
  width: 100%;
  height: 100%;
  background: #f5f7fa;
}

.game-header {
  border-bottom: 1px solid #ebeef5;
  background: #fff;
}

.game-body {
  height: calc(100vh - 80px);
}

/* 棋盘 */
.board-card {
  height: 100%;
}
.board-card :deep(.el-card__body) {
  height: calc(100% - 50px);
  overflow-y: auto;
}

.board-grid {
  display: grid;
  grid-template-columns: repeat(11, 1fr);
  grid-template-rows: repeat(11, 1fr);
  gap: 3px;
  aspect-ratio: 1 / 1;
  max-height: calc(100vh - 130px);
}

.board-center {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea33, #764ba233);
  border: 1px dashed #c0c4cc;
}

.board-center-content {
  text-align: center;
  color: #606266;
}

.center-dice {
  font-size: 24px;
  margin-bottom: 12px;
}

.dice-big {
  display: inline-block;
  width: 40px;
  height: 40px;
  line-height: 40px;
  text-align: center;
  background: #fff;
  border: 2px solid #409eff;
  border-radius: 8px;
  font-weight: bold;
  color: #409eff;
  margin: 0 4px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.dice-plus {
  font-size: 20px;
  color: #909399;
  margin: 0 2px;
}

.dice-equals {
  font-size: 16px;
  color: #909399;
  margin-left: 4px;
}

.center-turn-info {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.center-player {
  font-size: 14px;
  color: #409eff;
  font-weight: 500;
}

.tile-cell {
  position: relative;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 2px 1px;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
  overflow: hidden;
  min-height: 0;
  min-width: 0;
}
.tile-cell:hover {
  border-color: #409eff;
  box-shadow: 0 0 4px rgba(64, 158, 255, 0.3);
}
.tile-cell.tile-current {
  border-color: #e6a23c;
  box-shadow: 0 0 6px rgba(230, 162, 60, 0.4);
}
.tile-cell.tile-owned-me {
  border-color: #67c23a;
}
.tile-cell.tile-owned-other {
  border-color: #f56c6c;
}
.tile-cell.tile-mortgaged {
  opacity: 0.5;
}

.tile-color-bar {
  height: 4px;
  border-radius: 2px;
  margin-bottom: 2px;
}

.tile-name {
  font-size: 8px;
  font-weight: 600;
  line-height: 1.1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.tile-info {
  font-size: 7px;
  color: #666;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0px;
}

.tile-houses {
  font-size: 8px;
}

.tile-owner {
  font-size: 8px;
  color: #409eff;
}

.tile-players {
  position: absolute;
  bottom: 2px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 2px;
}

.player-token {
width: 14px;
height: 14px;
border-radius: 50%;
background: #409eff;
color: #fff;
font-size: 8px;
display: flex;
align-items: center;
justify-content: center;
font-weight: bold;
  border: 1px solid #fff;
}
.player-token.player-me {
  background: #67c23a;
}
.player-token.player-bankrupt {
  background: #999;
  text-decoration: line-through;
}

/* 右侧面板 */
.players-card, .action-card, .log-card {
  margin-bottom: 12px;
}

.player-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.game-player-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  border-radius: 6px;
  background: #f9f9f9;
  transition: background 0.2s;
}
.game-player-item.player-active {
  background: #fdf6ec;
  border: 1px solid #e6a23c;
}
.game-player-item.player-bankrupt-row {
  opacity: 0.4;
  text-decoration: line-through;
}
.game-player-item.player-me-row {
  border: 1px solid #67c23a;
}

.player-token-sm {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #909399;
  color: #fff;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}
.player-token-sm.player-me {
  background: #67c23a;
}

.player-name {
  font-size: 13px;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.player-assets .cash {
  font-weight: 600;
  color: #e6a23c;
  font-size: 13px;
}

/* 操作面板 */
.dice-display {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 12px;
}
.dice {
  display: inline-flex;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #fff;
  border: 2px solid #ddd;
  font-size: 20px;
  font-weight: bold;
  align-items: center;
  justify-content: center;
}
.dice-total {
  font-size: 18px;
  font-weight: bold;
  color: #409eff;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.decision-text {
  text-align: center;
  margin-bottom: 8px;
}

.build-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.build-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 13px;
}

.action-waiting {
  text-align: center;
  color: #999;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

/* 日志 / 聊天 */
.log-card :deep(.el-card__body) {
  max-height: 300px;
  overflow-y: auto;
  padding: 0;
}

/* Tab 样式 */
.right-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}
.right-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}
.right-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  padding: 0 12px;
  height: 36px;
  line-height: 36px;
}

/* 聊天面板 */
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 260px;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.chat-loading,
.chat-empty {
  text-align: center;
  color: #999;
  padding: 20px 0;
  font-size: 12px;
}
.load-more {
  text-align: center;
  color: #409eff;
  cursor: pointer;
  font-size: 11px;
  padding: 4px 0;
}
.load-more:hover {
  text-decoration: underline;
}
.chat-msg {
  max-width: 80%;
  padding: 4px 8px;
  border-radius: 6px;
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
  gap: 6px;
  margin-bottom: 1px;
}
.chat-msg-nickname {
  font-size: 11px;
  font-weight: 600;
  color: #606266;
}
.chat-msg-time {
  font-size: 10px;
  color: #c0c4cc;
}
.chat-msg-content {
  font-size: 12px;
  color: #303133;
  line-height: 1.4;
}
.chat-input {
  padding: 8px;
  border-top: 1px solid #ebeef5;
}
.chat-input :deep(.el-input__inner) {
  font-size: 12px;
}
.log-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 8px 12px;
}
.log-item {
  font-size: 12px;
  line-height: 1.4;
  padding: 2px 0;
  border-bottom: 1px solid #f5f5f5;
}
.log-item.log-turn { color: #409eff; font-weight: 600; }
.log-item.log-dice { color: #909399; }
.log-item.log-money { color: #e6a23c; }
.log-item.log-buy { color: #67c23a; }
.log-item.log-rent { color: #f56c6c; }
.log-item.log-card { color: #9c27b0; }
.log-item.log-jail { color: #795548; }
.log-item.log-over { color: #f56c6c; font-weight: bold; }
.log-empty { color: #ccc; text-align: center; padding: 20px; }

/* 游戏结束 */
.gameover-content { text-align: center; }
.gameover-reason { font-size: 16px; margin-bottom: 16px; color: #666; }
.gameover-rankings { display: flex; flex-direction: column; gap: 8px; }
.gameover-rank {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  border-radius: 8px;
  background: #f5f7fa;
}
.gameover-rank.rank-me { background: #ecf5ff; border: 1px solid #409eff; }
.rank-pos { font-size: 20px; }
.rank-name { flex: 1; text-align: left; font-weight: 600; }
.rank-assets { color: #e6a23c; font-weight: bold; }

/* 地块详情 */
.tile-detail p { margin: 4px 0; font-size: 14px; }
.rent-table table { width: 100%; margin-top: 8px; }
.rent-table td { padding: 2px 8px; font-size: 13px; }

/* ═══════════════════════════════════════════════════════════
   机会/命运卡弹窗
   ═══════════════════════════════════════════════════════════ */

.card-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.card-container {
  width: 320px;
  min-height: 420px;
  border-radius: 20px;
  padding: 32px 28px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  position: relative;
  overflow: hidden;
  box-shadow:
    0 20px 60px rgba(0, 0, 0, 0.35),
    0 0 0 2px rgba(255, 255, 255, 0.1);
}

/* 机会卡 — 橙黄渐变 */
.card-container.card-chance {
  background: linear-gradient(145deg, #ff9a3c, #ffcf48, #ff9a3c);
  color: #5a3000;
}

/* 命运卡 — 蓝紫渐变 */
.card-container.card-fate {
  background: linear-gradient(145deg, #6366f1, #a78bfa, #6366f1);
  color: #fff;
}

/* 卡片装饰圆 */
.card-container::before {
  content: '';
  position: absolute;
  top: -60px;
  right: -60px;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
}
.card-container::after {
  content: '';
  position: absolute;
  bottom: -40px;
  left: -40px;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 20px;
  position: relative;
  z-index: 1;
}

.card-type-badge {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  padding: 4px 14px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.25);
}

.card-id {
  font-size: 12px;
  opacity: 0.6;
  font-weight: 600;
}

.card-effect-icon {
  font-size: 56px;
  line-height: 1;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.15));
  animation: card-bounce-in 0.5s ease-out;
}

.card-title {
  font-size: 22px;
  font-weight: 800;
  margin: 0 0 12px;
  letter-spacing: 1px;
  position: relative;
  z-index: 1;
}

.card-description {
  font-size: 14px;
  line-height: 1.6;
  margin: 0 0 20px;
  opacity: 0.85;
  position: relative;
  z-index: 1;
}

.card-effect-value {
  font-size: 20px;
  font-weight: 800;
  padding: 8px 20px;
  border-radius: 12px;
  margin-bottom: 24px;
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, 0.2);
  letter-spacing: 0.5px;
}

.card-chance .card-effect-value {
  color: #a05000;
}

.card-fate .card-effect-value {
  color: #e0d0ff;
}

.card-close-btn {
  position: relative;
  z-index: 1;
  border-radius: 12px;
  padding: 10px 36px;
  font-weight: 600;
  font-size: 15px;
}

.card-chance .card-close-btn {
  background: #5a3000;
  border-color: #5a3000;
  color: #fff;
}
.card-chance .card-close-btn:hover {
  background: #7a4a10;
  border-color: #7a4a10;
}

.card-fate .card-close-btn {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.4);
  color: #fff;
}
.card-fate .card-close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
}

/* ─── 卡片弹出动画 ─── */

@keyframes card-bounce-in {
  0% { transform: scale(0.3) rotate(-15deg); opacity: 0; }
  50% { transform: scale(1.1) rotate(3deg); opacity: 1; }
  70% { transform: scale(0.95) rotate(-1deg); }
  100% { transform: scale(1) rotate(0deg); }
}

.card-pop-enter-active {
  transition: all 0.4s ease-out;
}
.card-pop-enter-active .card-container {
  animation: card-bounce-in 0.5s ease-out;
}

.card-pop-leave-active {
  transition: all 0.25s ease-in;
}
.card-pop-leave-to {
  opacity: 0;
}
.card-pop-leave-to .card-container {
  transform: scale(0.7) rotate(8deg);
  opacity: 0;
}
</style>
