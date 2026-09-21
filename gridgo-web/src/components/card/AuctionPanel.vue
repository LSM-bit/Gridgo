<template>
  <el-card v-if="auction" shadow="never" class="auction-panel">
    <template #header>
      <div class="auction-panel__header">
        <span>拍卖 · {{ tileName }}</span>
        <el-tag size="small" type="danger">倒计时 {{ auction.countdown }}s</el-tag>
      </div>
    </template>

    <div class="auction-panel__row">
      <span>起拍价</span>
      <b>{{ formatMoney(auction.start_price) }}</b>
    </div>
    <div class="auction-panel__row">
      <span>当前出价</span>
      <b>{{ auction.current_bid ? formatMoney(auction.current_bid) : '暂无' }}</b>
    </div>
    <div class="auction-panel__row">
      <span>领先者</span>
      <b>{{ leaderName }}</b>
    </div>

    <div class="auction-panel__bidders">
      <el-tag v-for="id in auction.bidders" :key="id" size="small" :type="id === auction.current_bidder_id ? 'success' : 'info'">
        {{ playerNameOf(id) }}
      </el-tag>
    </div>

    <div v-if="canBid" class="auction-panel__actions">
      <el-input-number v-model="amount" :min="minAmount" :step="MIN_BID_INCREMENT" />
      <el-button type="primary" :disabled="amount < minAmount" @click="bid">出价</el-button>
      <el-button @click="amount = minAmount">最低价</el-button>
    </div>
    <p v-else-if="isSpectator" class="auction-panel__hint">观战中，无法参与竞价</p>
    <p v-else class="auction-panel__hint">等待其他玩家出价…</p>
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { formatMoney } from '@/utils/format'
import type { AuctionState, PlayerState, TileState } from '@/types/game'

/** 与后端 engine.MIN_BID_INCREMENT 对齐 */
const MIN_BID_INCREMENT = 10

const props = withDefaults(
  defineProps<{
    auction: AuctionState | null
    players: PlayerState[]
    tiles?: TileState[]
    currentUserId: number
    isSpectator?: boolean
  }>(),
  { tiles: () => [], isSpectator: false },
)

const emit = defineEmits<{ (e: 'bid', amount: number): void }>()

const amount = ref(0)

const minAmount = computed(() => (props.auction?.current_bid ? props.auction.current_bid + MIN_BID_INCREMENT : props.auction?.start_price ?? 0))
const tileName = computed(() => props.tiles[props.auction?.tile_position ?? 0]?.name ?? `#${props.auction?.tile_position}`)
const playerNameOf = (userId: number | null) => props.players.find((p) => p.user_id === userId)?.nickname ?? '未知'
const leaderName = computed(() => (props.auction?.current_bidder_id ? playerNameOf(props.auction.current_bidder_id) : '暂无'))
const canBid = computed(() => !props.isSpectator && (props.auction?.bidders.includes(props.currentUserId) ?? false))

watch(
  minAmount,
  (value) => {
    if (amount.value < value) amount.value = value
  },
  { immediate: true },
)

const bid = () => emit('bid', amount.value)
</script>

<style scoped>
.auction-panel {
  border-radius: 12px;
}

.auction-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.auction-panel__row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #5a6b7d;
  padding: 2px 0;
}

.auction-panel__bidders {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 8px 0;
}

.auction-panel__actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.auction-panel__hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: #9aa9b8;
}
/* ── 统一视觉（设计令牌） ── */
.auction-panel {
  border-radius: var(--gg-radius);
  border-color: #f0d9a8;
  background: linear-gradient(180deg, #fffdf7, var(--gg-surface));
}

.auction-panel :deep(.el-card__header) {
  background: var(--gg-gold-soft);
  border-bottom-color: #f4dfba;
}

.auction-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-weight: 600;
  color: var(--gg-gold-strong);
}

.auction-panel__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 5px 0;
  font-size: 13px;
  color: var(--gg-ink-2);
  border-bottom: 1px dashed var(--gg-border);
}

.auction-panel__row:last-of-type {
  border-bottom: none;
}

.auction-panel__row b {
  color: var(--gg-ink);
  font-variant-numeric: tabular-nums;
}

.auction-panel__bidders {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 8px 0 4px;
}

.auction-panel__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--gg-border);
}

.auction-panel__hint {
  margin: 10px 0 0;
  padding: 8px 10px;
  border-radius: var(--gg-radius-xs);
  background: var(--gg-surface-2);
  font-size: 12px;
  color: var(--gg-ink-3);
  text-align: center;
}

.auction-panel :deep(.el-tag--danger) {
  animation: gg-pulse 1.6s var(--gg-ease) infinite;
}
</style>
