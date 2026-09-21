<template>
  <el-card shadow="never" class="log-panel">
    <template #header>
      <div class="log-panel__header">
        <span>对局日志</span>
        <el-tag size="small" type="info">{{ logs.length }}</el-tag>
      </div>
    </template>
    <div ref="listEl" class="log-panel__list" :style="{ maxHeight: `${maxHeight}px` }">
      <p v-if="logs.length === 0" class="log-panel__empty">暂无日志</p>
      <div v-for="(log, index) in logs" :key="`${log.timestamp}-${index}`" class="log-row" :class="`log-row--${log.type}`">
        <span class="log-row__time">{{ formatLogTime(log.timestamp) }}</span>
        <span class="log-row__text">{{ log.message }}</span>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { formatLogTime } from '@/utils/format'
import type { GameLog } from '@/types/game'

const props = withDefaults(
  defineProps<{
    logs: GameLog[]
    maxHeight?: number
    autoScroll?: boolean
  }>(),
  { maxHeight: 220, autoScroll: true },
)

const listEl = ref<HTMLElement | null>(null)

const scrollToBottom = async () => {
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
}

watch(
  () => props.logs.length,
  () => {
    if (props.autoScroll) scrollToBottom()
  },
)
</script>

<style scoped>
.log-panel {
  border-radius: var(--gg-radius);
}

.log-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-weight: 600;
}

.log-panel__list {
  overflow-y: auto;
  padding-right: 4px;
  scroll-behavior: smooth;
}

.log-panel__empty {
  margin: 0;
  padding: 10px 0;
  font-size: 12px;
  color: var(--gg-ink-4);
  text-align: center;
}

.log-row {
  position: relative;
  display: flex;
  gap: 8px;
  padding: 4px 8px 4px 10px;
  margin-bottom: 2px;
  font-size: 12px;
  color: var(--gg-ink-2);
  line-height: 1.55;
  border-radius: var(--gg-radius-xs);
  transition: background var(--gg-dur) var(--gg-ease);
}

.log-row::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  border-radius: var(--gg-pill);
  background: var(--gg-border-strong);
}

.log-row:hover {
  background: var(--gg-surface-2);
}

.log-row__time {
  flex: 0 0 auto;
  color: var(--gg-ink-4);
  font-variant-numeric: tabular-nums;
  font-size: 11px;
}

.log-row__text {
  flex: 1;
  word-break: break-word;
}

.log-row--money::before,
.log-row--rent::before {
  background: var(--gg-gold);
}

.log-row--money .log-row__text,
.log-row--rent .log-row__text {
  color: var(--gg-gold-strong);
}

.log-row--bankrupt::before,
.log-row--jail::before {
  background: var(--gg-red);
}

.log-row--bankrupt .log-row__text,
.log-row--jail .log-row__text {
  color: var(--gg-red);
}

.log-row--trade::before,
.log-row--auction::before {
  background: var(--gg-brand);
}

.log-row--trade .log-row__text,
.log-row--auction .log-row__text {
  color: var(--gg-brand-strong);
}

.log-row--system .log-row__text {
  color: var(--gg-ink-3);
}
/* 事件类型配色（type 取自 useGame 事件映射） */
.log-row--buy::before,
.log-row--build::before,
.log-row--mortgage::before,
.log-row--tile::before {
  background: var(--gg-green);
}

.log-row--buy .log-row__text,
.log-row--build .log-row__text,
.log-row--mortgage .log-row__text {
  color: var(--gg-green);
}

.log-row--trade::before,
.log-row--auction::before,
.log-row--card::before {
  background: var(--gg-purple);
}

.log-row--trade .log-row__text,
.log-row--auction .log-row__text,
.log-row--card .log-row__text {
  color: #6d3fd6;
}

.log-row--tax::before {
  background: var(--gg-red);
}

.log-row--tax .log-row__text {
  color: var(--gg-red);
}

.log-row--turn {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed var(--gg-border);
  font-weight: 600;
}

.log-row--turn::before,
.log-row--dice::before {
  background: var(--gg-border-strong);
}

.log-row--dice .log-row__text {
  color: var(--gg-ink);
}

.log-row--over {
  justify-content: center;
  font-weight: 700;
  color: var(--gg-gold-strong);
  background: var(--gg-gold-soft);
}

.log-row--over::before {
  background: var(--gg-grad-gold);
}
</style>
