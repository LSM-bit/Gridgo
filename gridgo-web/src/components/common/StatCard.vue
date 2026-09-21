<template>
  <div class="stat-card" :class="`stat-card--${tone}`">
    <span class="stat-card__label">{{ label }}</span>
    <span class="stat-card__value">{{ value }}</span>
    <span v-if="hint" class="stat-card__hint">{{ hint }}</span>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ label: string; value: string | number; hint?: string; tone?: 'default' | 'gold' | 'green' | 'red' }>(), {
  hint: '',
  tone: 'default',
})
</script>

<style scoped>
.stat-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 12px 14px;
  border-radius: var(--gg-radius-sm);
  background: var(--gg-surface);
  border: 1px solid var(--gg-border);
  box-shadow: var(--gg-shadow-1);
  overflow: hidden;
  transition: transform var(--gg-dur) var(--gg-ease), box-shadow var(--gg-dur) var(--gg-ease),
    border-color var(--gg-dur) var(--gg-ease);
}

.stat-card::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 3px;
  background: var(--gg-grad-brand);
  opacity: 0.85;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--gg-shadow-2);
  border-color: var(--gg-border-strong);
}

.stat-card__label {
  font-size: 12px;
  color: var(--gg-ink-3);
  letter-spacing: 0.2px;
}

.stat-card__value {
  font-size: 20px;
  font-weight: 700;
  color: var(--gg-ink);
  font-variant-numeric: tabular-nums;
}

.stat-card__hint {
  font-size: 11px;
  color: var(--gg-ink-4);
}

.stat-card--gold::before {
  background: var(--gg-grad-gold);
}

.stat-card--gold .stat-card__value {
  color: var(--gg-gold-strong);
}

.stat-card--green::before {
  background: linear-gradient(135deg, #57c48d, #2b9c68);
}

.stat-card--green .stat-card__value {
  color: var(--gg-green);
}

.stat-card--red::before {
  background: linear-gradient(135deg, #ef8883, #d4514c);
}

.stat-card--red .stat-card__value {
  color: var(--gg-red);
}
</style>
