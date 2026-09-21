<template>
  <el-dialog
    :model-value="modelValue"
    title="对局结束"
    width="460px"
    :close-on-click-modal="false"
    :show-close="!immediateClose"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-if="data" class="game-over">
      <p class="game-over__reason">{{ endReasonText }}</p>
      <div class="game-over__rankings">
        <div
          v-for="item in data.rankings"
          :key="item.user_id"
          class="rank-row"
          :class="{ 'rank-row--me': item.user_id === currentUserId }"
        >
          <span class="rank-row__pos">{{ ['1', '2', '3'][item.rank - 1] ?? `#${item.rank}` }}</span>
          <span class="rank-row__name">{{ item.is_ai ? 'AI · ' : '' }}{{ item.nickname }}</span>
          <span class="rank-row__assets">{{ formatMoney(item.total_assets) }}</span>
          <el-tag v-if="item.is_bankrupt" size="small" type="danger">破产</el-tag>
        </div>
      </div>
      <p class="game-over__turns">共 {{ data.total_turns }} 回合</p>
    </div>
    <template #footer>
      <el-button v-if="data?.game_record_id" @click="emit('viewReplay', data!.game_record_id as number)">查看回放</el-button>
      <el-button type="primary" @click="emit('back')">返回大厅</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { formatMoney } from '@/utils/format'
import type { GameOverPayload } from '@/types/game'

withDefaults(
  defineProps<{
    modelValue: boolean
    data: GameOverPayload | null
    endReasonText?: string
    currentUserId: number
    immediateClose?: boolean
  }>(),
  { endReasonText: '', immediateClose: false },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'viewReplay', gameRecordId: number): void
  (e: 'back'): void
}>()
</script>

<style scoped>
.game-over {
  animation: gg-fade-up var(--gg-dur-slow) var(--gg-ease-out) both;
}

.game-over__reason {
  margin: 0 0 14px;
  padding: 8px 12px;
  text-align: center;
  border-radius: var(--gg-radius-sm);
  background: var(--gg-gold-soft);
  border: 1px solid #f4dfba;
  color: var(--gg-gold-strong);
  font-weight: 600;
  font-size: 13.5px;
}

.game-over__rankings {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rank-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: var(--gg-radius-sm);
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border);
  font-size: 13px;
  transition: transform var(--gg-dur) var(--gg-ease), box-shadow var(--gg-dur) var(--gg-ease);
}

.rank-row:hover {
  transform: translateX(2px);
  box-shadow: var(--gg-shadow-1);
}

.rank-row--me {
  background: var(--gg-brand-soft);
  border-color: #bcd2f8;
  box-shadow: 0 0 0 1px rgba(47, 111, 237, 0.16);
}

.rank-row:first-child {
  background: linear-gradient(120deg, #fff8e8, #fff2d6);
  border-color: #f0d9a8;
}

.rank-row__pos {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--gg-surface);
  border: 1px solid var(--gg-border);
  font-weight: 700;
  font-size: 12px;
  color: var(--gg-ink-2);
}

.rank-row:first-child .rank-row__pos {
  background: var(--gg-grad-gold);
  border-color: transparent;
  color: #40260a;
  box-shadow: 0 4px 12px rgba(232, 138, 44, 0.32);
}

.rank-row__name {
  flex: 1;
  font-weight: 500;
}

.rank-row__assets {
  color: var(--gg-gold-strong);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.game-over__turns {
  margin: 14px 0 0;
  text-align: center;
  font-size: 12px;
  color: var(--gg-ink-4);
}
</style>
