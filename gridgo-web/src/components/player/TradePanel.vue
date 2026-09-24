<template>
  <el-card shadow="never" class="trade-panel">
    <template #header>
      <div class="trade-panel__header">
        <span>交易</span>
        <el-button size="small" type="primary" :disabled="!connected" @click="openComposer">发起交易</el-button>
      </div>
    </template>

    <p v-if="!connected" class="trade-panel__offline">连接已断开，交易操作已暂停，正在自动重连…</p>

    <div v-if="incoming.length === 0 && outgoing.length === 0">
      <EmptyState text="暂无交易提议" icon="🤝" />
    </div>

    <div v-for="trade in incoming" :key="trade.trade_id" class="trade-item trade-item--incoming">
      <div class="trade-item__title">
        来自 {{ nicknameOf(trade.from_id) }}
        <el-tag size="small" type="warning">待我处理</el-tag>
      </div>
      <div class="trade-item__body">
        <p>对方付出：{{ formatMoney(trade.offer_cash) }} + 地产 {{ trade.offer_properties.length }} 处</p>
        <p>我方付出：{{ formatMoney(trade.request_cash) }} + 地产 {{ trade.request_properties.length }} 处</p>
        <p v-if="trade.request_properties.length" class="trade-item__tiles">
          涉及我的地产：{{ tileNames(trade.request_properties) }}
        </p>
        <p v-if="trade.offer_properties.length" class="trade-item__tiles">
          涉及对方地产：{{ tileNames(trade.offer_properties) }}
        </p>
      </div>
      <div class="trade-item__actions">
        <el-button size="small" type="success" :disabled="!connected" @click="emit('accept', trade.trade_id)">接受</el-button>
        <el-button size="small" :disabled="!connected" @click="emit('reject', trade.trade_id)">拒绝</el-button>
      </div>
    </div>

    <div v-for="trade in outgoing" :key="trade.trade_id" class="trade-item">
      <div class="trade-item__title">
        发给 {{ nicknameOf(trade.to_id) }}
        <el-tag size="small" type="info">等待回应</el-tag>
      </div>
      <div class="trade-item__body">
        <p>我方付出：{{ formatMoney(trade.offer_cash) }} + 地产 {{ trade.offer_properties.length }} 处</p>
        <p>对方付出：{{ formatMoney(trade.request_cash) }} + 地产 {{ trade.request_properties.length }} 处</p>
      </div>
      <div class="trade-item__actions">
        <el-button size="small" :disabled="!connected" @click="emit('reject', trade.trade_id)">撤回</el-button>
      </div>
    </div>
  </el-card>

  <el-dialog v-model="composerVisible" title="发起交易" width="440px">
    <el-form label-width="88px">
      <el-form-item label="交易对象">
        <el-select v-model="form.targetId" placeholder="选择玩家">
          <el-option
            v-for="player in partners"
            :key="player.user_id"
            :label="player.nickname"
            :value="player.user_id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="我付出">
        <el-input-number v-model="form.offerCash" :min="0" :max="myCash" />
      </el-form-item>
      <el-form-item label="我的地产">
        <el-select v-model="form.offerProperties" multiple placeholder="选择地产">
          <el-option v-for="tile in myTiles" :key="tile.position" :label="tile.name" :value="tile.position" />
        </el-select>
      </el-form-item>
      <el-form-item label="我索取">
        <el-input-number v-model="form.requestCash" :min="0" />
      </el-form-item>
      <el-form-item label="索取地产">
        <el-input v-model="form.requestProperties" placeholder="输入地块编号，逗号分隔，如 12,15" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="composerVisible = false">取消</el-button>
      <el-button type="primary" :disabled="!form.targetId || !connected" @click="submit">发送提议</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import EmptyState from '@/components/common/EmptyState.vue'
import { formatMoney } from '@/utils/format'
import type { PlayerState, TileState, TradeOffer, TradeOfferPayload } from '@/types/game'

const props = withDefaults(
  defineProps<{
    incoming: TradeOffer[]
    outgoing: TradeOffer[]
    players: PlayerState[]
    tiles?: TileState[]
    currentUserId: number
    /** WS 连接是否正常；断开时冻结交易发起 / 接受 / 拒绝入口 */
    connected?: boolean
  }>(),
  { tiles: () => [], connected: true },
)

const emit = defineEmits<{
  (e: 'accept', tradeId: string): void
  (e: 'reject', tradeId: string): void
  (e: 'submit', payload: TradeOfferPayload): void
}>()

const composerVisible = ref(false)
const form = reactive({
  targetId: null as number | null,
  offerCash: 0,
  offerProperties: [] as number[],
  requestCash: 0,
  requestProperties: '',
})

const partners = computed(() => props.players.filter((p) => p.user_id !== props.currentUserId && !p.is_bankrupt))
const myTiles = computed(() => {
  const me = props.players.find((p) => p.user_id === props.currentUserId)
  if (!me) return []
  return me.properties.map((pos) => props.tiles[pos]).filter(Boolean)
})
const myCash = computed(() => props.players.find((p) => p.user_id === props.currentUserId)?.cash ?? 0)

const nicknameOf = (userId: number) => props.players.find((p) => p.user_id === userId)?.nickname ?? `玩家${userId}`
const tileNames = (positions: number[]) =>
  positions.map((pos) => props.tiles[pos]?.name ?? `#${pos}`).join('、')

const openComposer = () => {
  form.targetId = null
  form.offerCash = 0
  form.offerProperties = []
  form.requestCash = 0
  form.requestProperties = ''
  composerVisible.value = true
}

const submit = () => {
  if (!props.connected) {
    ElMessage.warning('连接已断开，交易提议未发送，请等待重连后重试')
    return
  }
  if (!form.targetId) {
    ElMessage.warning('请选择交易对象')
    return
  }
  const requestProperties = form.requestProperties
    .split(/[,\s，]+/)
    .map((item) => Number(item))
    .filter((num) => Number.isFinite(num) && num >= 0)
  if (
    form.offerCash <= 0 &&
    form.requestCash <= 0 &&
    form.offerProperties.length === 0 &&
    requestProperties.length === 0
  ) {
    ElMessage.warning('请至少填写一项交易内容（现金或地产）')
    return
  }
  emit('submit', {
    target_id: form.targetId,
    offer: { cash: form.offerCash, properties: [...form.offerProperties] },
    request: { cash: form.requestCash, properties: requestProperties },
  })
  composerVisible.value = false
}
</script>

<style scoped>
.trade-panel {
  border-radius: 12px;
}

.trade-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.trade-panel__offline {
  margin: 0 0 8px;
  padding: 6px 8px;
  border-radius: 6px;
  border: 1px dashed rgba(179, 39, 30, 0.35);
  background: rgba(179, 39, 30, 0.06);
  font-size: 12px;
  color: var(--gg-danger, #b3271e);
  text-align: center;
}

.trade-item {
  padding: 8px;
  margin-bottom: 8px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.trade-item--incoming {
  border-color: #f0c36d;
  background: #fffaf0;
}

.trade-item__title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
}

.trade-item__body p {
  margin: 2px 0;
  font-size: 12px;
  color: #5a6b7d;
}

.trade-item__tiles {
  color: #7a8b9d;
}

.trade-item__actions {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}
.trade-panel {
  border-radius: var(--gg-radius);
}

.trade-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-weight: 600;
}

.trade-item {
  padding: 10px 12px;
  margin-bottom: 8px;
  border-radius: var(--gg-radius-sm);
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border);
  transition: box-shadow var(--gg-dur) var(--gg-ease), transform var(--gg-dur) var(--gg-ease);
  animation: gg-fade-up var(--gg-dur) var(--gg-ease-out) both;
}

.trade-item:last-child {
  margin-bottom: 0;
}

.trade-item:hover {
  transform: translateY(-1px);
  box-shadow: var(--gg-shadow-1);
}

.trade-item--incoming {
  background: linear-gradient(135deg, #fffaf0, #fff4e2);
  border-color: #f0d9a8;
}

.trade-item__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--gg-ink);
}

.trade-item__body {
  margin: 6px 0 0;
  font-size: 12.5px;
  color: var(--gg-ink-2);
  line-height: 1.6;
}

.trade-item__body p {
  margin: 0;
}

.trade-item__tiles {
  color: var(--gg-ink-3);
  font-size: 12px;
}

.trade-item__actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
</style>
