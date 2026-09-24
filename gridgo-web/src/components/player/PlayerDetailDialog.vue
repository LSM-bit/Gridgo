<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    width="420px"
    append-to-body
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-if="player" class="player-detail">
      <div class="player-detail__tags">
        <el-tag size="small" :type="isMe ? 'success' : 'info'">{{ isMe ? '我' : '玩家' }}</el-tag>
        <el-tag v-if="player.is_ai" size="small" type="warning">{{ aiDifficultyText(player.ai_difficulty) || 'AI' }}</el-tag>
        <el-tag v-if="isCurrentPlayer" size="small" type="primary">当前回合</el-tag>
        <el-tag v-if="player.is_bankrupt" size="small" type="danger">已破产</el-tag>
        <el-tag v-if="!player.is_connected" size="small" type="info">断线中</el-tag>
      </div>

      <div class="player-detail__row">
        <span>现金</span>
        <b>{{ formatMoney(player.cash) }}</b>
      </div>
      <div class="player-detail__row">
        <span>净资产（现金 + 地价估值）</span>
        <b>{{ formatMoney(netWorth) }}</b>
      </div>
      <div class="player-detail__row">
        <span>持有地产</span>
        <b>{{ properties.length }} 处</b>
      </div>
      <div class="player-detail__row">
        <span>所在位置</span>
        <b>{{ currentTileName }}</b>
      </div>
      <div class="player-detail__row">
        <span>监狱状态</span>
        <b>{{ player.is_in_jail ? `在狱中（剩余 ${player.jail_turns} 回合）` : '自由身' }}</b>
      </div>
      <div class="player-detail__row">
        <span>免罪卡</span>
        <b>{{ player.get_out_of_jail_cards }} 张</b>
      </div>

      <div class="player-detail__section">
        <span class="gg-kicker">地产持有</span>
        <p v-if="!properties.length" class="player-detail__empty">暂未持有地产</p>
        <ul v-else class="player-detail__list">
          <li v-for="tile in properties" :key="tile.position">
            <span class="player-detail__list-name">{{ tile.name }}</span>
            <span class="player-detail__list-meta">
              <template v-if="tile.build_level > 0">Lv.{{ tile.build_level }} · </template>
              <template v-if="tile.is_mortgaged">已抵押</template>
              <template v-else>地价 {{ formatMoney(tile.price ?? 0) }}</template>
            </span>
          </li>
        </ul>
      </div>
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">关闭</el-button>
      <el-button
        type="primary"
        :disabled="isMe || player?.is_bankrupt || !player"
        @click="emit('trade', player?.user_id ?? 0)"
      >
        发起交易
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 玩家信息弹窗
 *
 * 点击棋盘上的棋子（或右侧玩家卡片）时展示**玩家**信息：现金、净资产、
 * 持有地产、监狱与连接状态等，而不是棋子所在格子的地块信息。
 */
import { computed } from 'vue'
import { aiDifficultyText, formatMoney } from '@/utils/format'
import type { PlayerState, TileState } from '@/types/game'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    player: PlayerState | null
    tiles?: TileState[]
    currentUserId: number
    currentPlayerId?: number | null
  }>(),
  { tiles: () => [], currentPlayerId: null },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'trade', userId: number): void
}>()

const isMe = computed(() => !!props.player && props.player.user_id === props.currentUserId)
const isCurrentPlayer = computed(() => !!props.player && props.player.user_id === props.currentPlayerId)
const title = computed(() => (props.player ? `${props.player.nickname} · 玩家信息` : '玩家信息'))

const properties = computed(() =>
  props.player ? props.tiles.filter((tile) => tile.owner_id === props.player?.user_id) : [],
)
const netWorth = computed(() =>
  props.player ? props.player.cash + properties.value.reduce((sum, tile) => sum + (tile.price ?? 0), 0) : 0,
)
const currentTileName = computed(() => {
  if (!props.player) return '-'
  return props.tiles[props.player.position]?.name ?? `#${props.player.position}`
})
</script>

<style scoped>
.player-detail__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.player-detail__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 5px 0;
  font-size: 13px;
  color: var(--gg-ink-2);
  border-bottom: 1px dashed var(--gg-border);
}

.player-detail__row b {
  color: var(--gg-ink);
  font-variant-numeric: tabular-nums;
}

.player-detail__section {
  margin-top: 12px;
}

.player-detail__empty {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--gg-ink-3);
}

.player-detail__list {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
  max-height: 180px;
  overflow-y: auto;
}

.player-detail__list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 4px 0;
  font-size: 12.5px;
  border-bottom: 1px dashed var(--gg-border);
}

.player-detail__list-name {
  color: var(--gg-ink);
}

.player-detail__list-meta {
  font-family: var(--gg-font-mono);
  font-size: 11px;
  color: var(--gg-ink-3);
}
</style>
