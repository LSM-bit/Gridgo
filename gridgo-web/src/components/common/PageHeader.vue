<template>
  <header class="page-header">
    <div class="page-header__left">
      <span v-if="icon" class="page-header__icon">{{ icon }}</span>
      <div class="page-header__text">
        <h1 class="page-header__title">{{ title }}</h1>
        <p v-if="subtitle" class="page-header__subtitle">{{ subtitle }}</p>
      </div>
    </div>
    <div class="page-header__right">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ title: string; subtitle?: string; icon?: string }>(), {
  subtitle: '',
  icon: '',
})
</script>

<style scoped>
/* 票据式刊头：粗底线 + 印章式图标 + 等宽小字副标题 */
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding-bottom: 12px;
  border-bottom: 2px solid var(--gg-ink);
  animation: gg-fade-up var(--gg-dur-slow) var(--gg-ease-out) both;
}

.page-header__left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.page-header__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  background: var(--gg-grad-night);
  border: 1px solid #16130f;
  color: var(--gg-gold);
  font-size: 15px;
  line-height: 1;
}

.page-header__text {
  min-width: 0;
}

.page-header__title {
  margin: 0;
  font-family: var(--gg-font-display);
  font-size: clamp(19px, 2.4vw, 25px);
  line-height: 1.2;
  letter-spacing: 0.02em;
  color: var(--gg-ink);
}

.page-header__subtitle {
  margin: 4px 0 0;
  font-family: var(--gg-font-mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--gg-ink-3);
}

.page-header__right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

@media (max-width: 640px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .page-header__right {
    width: 100%;
  }
}
</style>
