<template>
  <el-card v-if="auction" shadow="never" class="auction-panel">
    <template #header>
      <div class="auction-panel__header">
        <span>拍卖 · {{ tileName }}</span>
        <el-tag size="small" :type="timerTagType">倒计时 {{ secondsLeft }}s</el-tag>
      </div>
    </template>

    <el-progress
      class="auction-panel__timer"
      :percentage="timerPercent"
      :stroke-width="6"
      :show-text="false"
      :status="secondsLeft <= 5 ? 'exception' : undefined"
    />

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
      <el-input-number v-model="amount" :min="minAmount" :step="MIN_BID_INCREMENT" :disabled="settling || !connected" />
      <el-button type="primary" :disabled="!canBidNow || amount < minAmount" @click="bid">出价</el-button>
      <el-button :disabled="!connected" @click="amount = minAmount">最低价</el-button>
    </div>
    <p v-else-if="isSpectator" class="auction-panel__hint">观战中，无法参与竞价 · 剩余 {{ secondsLeft }}s</p>
    <p v-else class="auction-panel__hint">等待其他玩家出价 · 剩余 {{ secondsLeft }}s</p>
    <p v-if="!connected" class="auction-panel__hint auction-panel__hint--offline">
      连接已断开，出价已暂停，正在自动重连…
    </p>
    <p v-if="settling" class="auction-panel__hint auction-panel__hint--settling">
      本轮倒计时结束，服务端结算中…（出价已暂停）
    </p>
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { formatMoney } from '@/utils/format'
import { useLocalCountdown } from '@/composables/useLocalCountdown'
import type { AuctionState, PlayerState, TileState } from '@/types/game'

/** 与后端 engine.MIN_BID_INCREMENT 对齐 */
const MIN_BID_INCREMENT = 10
/** 倒计时进入最后 5 秒时提醒一次，避免"倒计时结束才知道要结算" */
const FINAL_COUNTDOWN_WARN = 5

const props = withDefaults(
  defineProps<{
    auction: AuctionState | null
    players: PlayerState[]
    tiles?: TileState[]
    currentUserId: number
    isSpectator?: boolean
    /** WS 连接是否正常；断开时冻结出价入口 */
    connected?: boolean
  }>(),
  { tiles: () => [], isSpectator: false, connected: true },
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

// ─── 本地倒计时 ───
// 服务端只下发倒计时初值（每次出价重置为 auction.countdown），不推送逐秒 tick，
// 因此剩余秒数必须由前端本地递减；模板里也必须绑定这里的 secondsLeft，
// 否则界面永远停在初值上（历史缺陷：倒计时"不显示 / 不走"）。
const { secondsLeft } = useLocalCountdown(
  () => props.auction?.countdown ?? null,
  () => (props.auction ? `${props.auction.tile_position}:${props.auction.current_bid}:${props.auction.bid_rounds ?? 0}` : 'closed'),
)

/** 本轮倒计时归零：服务端即将结算，暂停出价避免无效请求 */
const settling = computed(() => !!props.auction && secondsLeft.value <= 0)
const canBidNow = computed(() => canBid.value && !settling.value && props.connected)
const timerTagType = computed(() => (secondsLeft.value <= 5 ? 'danger' : 'warning'))
const timerPercent = computed(() => {
  const total = props.auction?.countdown ?? 0
  if (!total) return 0
  return Math.max(0, Math.min(100, Math.round((secondsLeft.value / total) * 100)))
})

/**
 * 倒计时提醒：本轮（同一地块 + 同一出价 + 同一轮次）剩余 5 秒时提示一次，
 * 避免用户在倒计时归零后才发现"没来得及出价"。
 */
let warnedRoundKey = ''
watch(secondsLeft, (value) => {
  const auction = props.auction
  if (!auction) return
  const roundKey = `${auction.tile_position}:${auction.current_bid}:${auction.bid_rounds ?? 0}`
  if (value > FINAL_COUNTDOWN_WARN || value <= 0) return
  if (warnedRoundKey === roundKey || !canBid.value || !props.connected) return
  warnedRoundKey = roundKey
  ElMessage.warning(`拍卖倒计时不足 ${FINAL_COUNTDOWN_WARN} 秒，即将结算`)
})

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

.auction-panel__timer {
  margin-bottom: 8px;
}

.auction-panel__timer :deep(.el-progress-bar__outer) {
  background: var(--gg-surface-2);
}

.auction-panel__hint--settling {
  color: var(--gg-danger, #b3271e);
  border: 1px dashed rgba(179, 39, 30, 0.35);
  background: rgba(179, 39, 30, 0.06);
}

.auction-panel__hint--offline {
  color: var(--gg-danger, #b3271e);
  border: 1px dashed rgba(179, 39, 30, 0.35);
  background: rgba(179, 39, 30, 0.06);
}
</style>
