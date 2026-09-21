<template>
  <div class="dice-panel" :class="{ 'dice-panel--rolling': rolling }">
    <div class="dice-panel__dice">
      <span v-for="(value, index) in values" :key="index" class="die" :class="`die--${value}`">
        <i v-for="pip in pipMap[value] ?? []" :key="pip" class="die__pip" :class="`die__pip--${pip}`"></i>
      </span>
      <span v-if="values.length === 0" class="dice-panel__placeholder">--</span>
    </div>
    <div class="dice-panel__meta">
      <span v-if="total" class="dice-panel__total">合计 {{ total }}</span>
      <el-tag v-if="isDouble" size="small" type="warning">双数</el-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    values?: number[]
    isDouble?: boolean
    rolling?: boolean
  }>(),
  { values: () => [], isDouble: false, rolling: false },
)

const total = computed(() => props.values.reduce((sum, value) => sum + value, 0))

/** 1~6 骰面点位（3×3 宫格中的位置编号 1-9） */
const pipMap: Record<number, number[]> = {
  1: [5],
  2: [1, 9],
  3: [1, 5, 9],
  4: [1, 3, 7, 9],
  5: [1, 3, 5, 7, 9],
  6: [1, 3, 4, 6, 7, 9],
}
</script>

<style scoped>
.dice-panel {
  display: flex;
  align-items: center;
  gap: 10px;
}

.dice-panel__dice {
  display: flex;
  gap: 6px;
}

.die {
  position: relative;
  display: inline-block;
  width: 30px;
  height: 30px;
  border-radius: 6px;
  background: #fff;
  border: 1px solid #d7dee8;
  box-shadow: inset 0 -2px 0 rgba(0, 0, 0, 0.05);
  transition: transform 0.15s;
}

.die__pip {
  position: absolute;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #2c3e50;
}

/* 3×3 宫格：1 2 3 / 4 5 6 / 7 8 9 */
.die__pip--1 { top: 5px; left: 5px; }
.die__pip--2 { top: 5px; left: 12px; }
.die__pip--3 { top: 5px; right: 5px; }
.die__pip--4 { top: 12px; left: 5px; }
.die__pip--5 { top: 12px; left: 12px; }
.die__pip--6 { top: 12px; right: 5px; }
.die__pip--7 { bottom: 5px; left: 5px; }
.die__pip--8 { bottom: 5px; left: 12px; }
.die__pip--9 { bottom: 5px; right: 5px; }

.dice-panel--rolling .die {
  animation: dice-shake 0.4s infinite;
}

.dice-panel__placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 66px;
  height: 30px;
  border-radius: 6px;
  background: #f2f5f9;
  color: #9aa9b8;
  font-size: 12px;
}

.dice-panel__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #5a6b7d;
}

@keyframes dice-shake {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-3px) rotate(8deg); }
}
.dice-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: var(--gg-radius-sm);
  background: linear-gradient(180deg, var(--gg-surface), var(--gg-surface-2));
  border: 1px solid var(--gg-border);
}

.dice-panel__dice {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dice-panel__placeholder {
  color: var(--gg-ink-4);
  letter-spacing: 2px;
}

.dice-panel .die {
  box-shadow: 0 6px 16px rgba(22, 32, 44, 0.16), inset 0 -2px 0 rgba(22, 32, 44, 0.08);
  transition: transform var(--gg-dur) var(--gg-ease), box-shadow var(--gg-dur) var(--gg-ease);
}

.dice-panel--rolling .die {
  box-shadow: 0 8px 20px rgba(47, 111, 237, 0.28);
}

.dice-panel__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--gg-ink-2);
}

.dice-panel__total {
  font-weight: 700;
  color: var(--gg-brand-strong);
  font-variant-numeric: tabular-nums;
}
</style>
