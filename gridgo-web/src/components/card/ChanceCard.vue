<template>
  <el-dialog
    :model-value="!!card"
    :title="card?.card_type === 'CHANCE' ? '机会' : '命运'"
    width="360px"
    align-center
    :show-close="true"
    @update:model-value="emit('close')"
  >
    <div v-if="card" ref="cardRef" class="chance-card" :class="`chance-card--${(card.card_type || 'chance').toLowerCase()}`">
      <div class="chance-card__badge">{{ card.card_type === 'CHANCE' ? 'CHANCE' : 'FATE' }}</div>
      <h3 class="chance-card__name">{{ card.card_name }}</h3>
      <p class="chance-card__desc">{{ card.description }}</p>
      <div class="chance-card__meta">
        <el-tag size="small" type="info">{{ effectText(card.effect_type) }}</el-tag>
        <el-tag v-if="card.effect_value !== null" size="small" :type="card.effect_value >= 0 ? 'success' : 'danger'">
          {{ card.effect_value > 0 ? '+' : '' }}{{ card.effect_value }}
        </el-tag>
        <el-tag size="small">{{ playerName || `玩家${card.player_id}` }}</el-tag>
      </div>
    </div>
    <template #footer>
      <el-button type="primary" @click="emit('close')">知道了</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useAnimation } from '@/composables/useAnimation'
import { effectText } from '@/utils/format'
import type { CardDisplay } from '@/types/game'

const props = withDefaults(
  defineProps<{
    card: CardDisplay | null
    playerName?: string
  }>(),
  { playerName: '' },
)

const emit = defineEmits<{ (e: 'close'): void }>()

const cardRef = ref<Element | null>(null)
const { playCardReveal } = useAnimation()

const reveal = () => {
  if (props.card && cardRef.value) playCardReveal(cardRef.value)
}

watch(() => props.card, reveal)
onMounted(reveal)
</script>

<style scoped>
.chance-card {
  padding: 16px;
  border-radius: 12px;
  background: linear-gradient(160deg, #fffdf5, #fff3d6);
  border: 1px solid #f0d9a8;
  text-align: center;
}

.chance-card--fate {
  background: linear-gradient(160deg, #fbf7ff, #f0e6fb);
  border-color: #d9c6f0;
}

.chance-card__badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  background: #ffb300;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
}

.chance-card--fate .chance-card__badge {
  background: #9c27b0;
}

.chance-card__name {
  margin: 12px 0 6px;
  font-size: 18px;
}

.chance-card__desc {
  margin: 0 0 12px;
  color: #5a6b7d;
  font-size: 13px;
  line-height: 1.6;
}

.chance-card__meta {
  display: flex;
  justify-content: center;
  gap: 6px;
}
.chance-card {
  position: relative;
  padding: 18px 16px;
  border-radius: var(--gg-radius);
  background: linear-gradient(150deg, #fff8ec, #f2f6ff);
  border: 1px solid var(--gg-border);
  box-shadow: inset 0 1px 0 #fff;
  overflow: hidden;
  text-align: center;
}

.chance-card::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(320px 120px at 50% -20%, rgba(232, 138, 44, 0.18), transparent 70%);
  pointer-events: none;
}

.chance-card--fate {
  background: linear-gradient(150deg, #f5f0ff, #eef4ff);
}

.chance-card__badge {
  display: inline-block;
  padding: 3px 12px;
  border-radius: var(--gg-pill);
  background: var(--gg-grad-gold);
  color: #40260a;
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 2px;
  box-shadow: 0 6px 16px rgba(232, 138, 44, 0.3);
}

.chance-card--fate .chance-card__badge {
  background: linear-gradient(135deg, #a78bfa, #7c4dff);
  color: #fff;
  box-shadow: 0 6px 16px rgba(124, 77, 255, 0.3);
}

.chance-card__name {
  margin: 12px 0 6px;
  font-size: 19px;
  font-weight: 700;
  color: var(--gg-ink);
  letter-spacing: 0.2px;
}

.chance-card__desc {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.65;
  color: var(--gg-ink-2);
}

.chance-card__meta {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--gg-border);
}
</style>
