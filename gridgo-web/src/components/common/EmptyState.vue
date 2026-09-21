<template>
  <div class="empty-state">
    <span class="empty-state__icon">{{ icon || '◈' }}</span>
    <p class="empty-state__text">{{ text }}</p>
    <p v-if="description" class="empty-state__desc">{{ description }}</p>
    <div v-if="$slots.default" class="empty-state__slot">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ text?: string; description?: string; icon?: string }>(), {
  text: '暂无数据',
  description: '',
  icon: '',
})
</script>

<style scoped>
/* 票据式空态：虚线票框 + 标记 + 文案 + 可选行动区 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 168px;
  padding: 26px 18px;
  text-align: center;
  color: var(--gg-ink-3);
  border: 1px dashed var(--gg-border-strong);
  background-image: var(--gg-dotfield, radial-gradient(rgba(88, 68, 42, 0.12) 0.7px, transparent 0.8px));
  background-size: 8px 8px;
  animation: gg-fade-up var(--gg-dur-slow) var(--gg-ease-out) both;
}

.empty-state__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  margin-bottom: 2px;
  font-size: 17px;
  line-height: 1;
  color: var(--gg-gold);
  border: 1px solid var(--gg-border-strong);
  background: var(--gg-surface);
}

.empty-state__text {
  margin: 0;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--gg-ink-2);
}

.empty-state__desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--gg-ink-4);
}

.empty-state__slot {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-top: 10px;
}
</style>
