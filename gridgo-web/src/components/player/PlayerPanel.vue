<template>
  <el-card shadow="never" class="player-panel">
    <template #header>
      <div class="player-panel__header">
        <span>玩家</span>
        <el-tag size="small" type="info">第 {{ turnNumber }} 回合</el-tag>
      </div>
    </template>

    <div v-if="players.length === 0">
      <EmptyState text="等待玩家加入" icon="👥" />
    </div>

    <div
      v-for="(player, index) in players"
      :key="player.user_id"
      class="player-row"
      :class="{
        'player-row--current': index === currentPlayerIndex,
        'player-row--me': player.user_id === currentUserId,
        'player-row--bankrupt': player.is_bankrupt,
      }"
      @click="emit('select', player.user_id)"
    >
      <span class="player-row__dot" :style="{ background: tokenColor(index) }"></span>
      <div class="player-row__main">
        <div class="player-row__name">
          {{ player.nickname }}
          <el-tag v-if="player.is_ai" size="small" type="warning">{{ aiDifficultyText(player.ai_difficulty) || 'AI' }}</el-tag>
          <el-tag v-if="player.user_id === currentUserId" size="small">我</el-tag>
          <el-tag v-if="index === currentPlayerIndex" size="small" type="success">行动中</el-tag>
        </div>
        <div class="player-row__meta">
          <span>{{ formatMoney(player.cash) }}</span>
          <span>地产 {{ player.properties.length }}</span>
          <span v-if="player.is_in_jail"><el-tag size="small" type="danger">监狱</el-tag></span>
          <span v-if="player.get_out_of_jail_cards > 0">免罪卡 {{ player.get_out_of_jail_cards }}</span>
          <span v-if="!player.is_connected" class="player-row__offline">离线</span>
          <span v-if="player.is_bankrupt" class="player-row__offline">已破产</span>
        </div>
      </div>
      <el-button
        v-if="tradable(player)"
        size="small"
        text
        type="primary"
        @click.stop="emit('trade', player.user_id)"
      >
        交易
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { tokenColor } from '@/game/board'
import { aiDifficultyText, formatMoney } from '@/utils/format'
import EmptyState from '@/components/common/EmptyState.vue'
import type { PlayerState } from '@/types/game'

const props = withDefaults(
  defineProps<{
    players: PlayerState[]
    currentUserId: number
    currentPlayerIndex: number
    turnNumber?: number
    disabled?: boolean
  }>(),
  { turnNumber: 0, disabled: false },
)

const emit = defineEmits<{
  (e: 'select', userId: number): void
  (e: 'trade', userId: number): void
}>()

const tradable = (player: PlayerState) =>
  !props.disabled && player.user_id !== props.currentUserId && !player.is_bankrupt
</script>

<style scoped>
.player-panel {
  border-radius: 12px;
}

.player-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.player-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.player-row:hover {
  background: #f2f6fb;
}

.player-row--current {
  background: #eef7ee;
}

.player-row--me .player-row__name {
  font-weight: 700;
}

.player-row--bankrupt {
  opacity: 0.55;
}

.player-row__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex: 0 0 auto;
}

.player-row__main {
  flex: 1;
  min-width: 0;
}

.player-row__name {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
}

.player-row__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: #7a8b9d;
}

.player-row__offline {
  color: #c62828;
}
.player-panel {
  border-radius: var(--gg-radius);
}

.player-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-weight: 600;
}

.player-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  margin-bottom: 6px;
  border-radius: var(--gg-radius-sm);
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border);
  cursor: pointer;
  transition: transform var(--gg-dur) var(--gg-ease), box-shadow var(--gg-dur) var(--gg-ease),
    background var(--gg-dur) var(--gg-ease), border-color var(--gg-dur) var(--gg-ease);
}

.player-row:last-child {
  margin-bottom: 0;
}

.player-row:hover {
  transform: translateX(2px);
  background: var(--gg-surface);
  border-color: var(--gg-border-strong);
  box-shadow: var(--gg-shadow-1);
}

.player-row--current {
  background: var(--gg-brand-soft);
  border-color: #bcd2f8;
}

.player-row--current::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: var(--gg-pill);
  background: var(--gg-grad-brand);
}

.player-row--me {
  box-shadow: 0 0 0 1px rgba(47, 111, 237, 0.18);
}

.player-row--bankrupt {
  opacity: 0.55;
  filter: grayscale(0.4);
}

.player-row__dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex: 0 0 auto;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.9), 0 2px 6px rgba(22, 32, 44, 0.18);
}

.player-row__main {
  flex: 1;
  min-width: 0;
}

.player-row__name {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--gg-ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.player-row__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 3px;
  font-size: 11.5px;
  color: var(--gg-ink-3);
  font-variant-numeric: tabular-nums;
}

.player-row__offline {
  color: var(--gg-red);
}
</style>
