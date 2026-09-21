<template>
  <div class="game-layout">
    <el-container class="game-layout__container">
      <el-header class="game-layout__header">
        <div class="game-layout__header-inner">
          <div class="game-layout__status">
            <slot name="status" />
          </div>
          <div class="game-layout__actions">
            <slot name="actions" />
          </div>
        </div>
      </el-header>
      <el-main class="game-layout__main">
        <slot />
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
defineProps<{ loading?: boolean }>()
</script>

<style scoped>
.game-layout {
  width: 100%;
  height: 100%;
  background: transparent;
}

.game-layout__container {
  height: 100vh;
}

/* ── 对局条：铅字 + 朱砂底线 ── */
.game-layout__header {
  height: var(--gg-shell-bar);
  padding: 0 var(--gg-page-pad);
  background: var(--gg-grad-night);
  color: #f2ead9;
  border-bottom: 1px solid #16130f;
  box-shadow: inset 0 -3px 0 var(--gg-gold), 0 6px 16px -8px rgba(40, 30, 18, 0.6);
}

.game-layout__header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  height: 100%;
}

.game-layout__status {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  font-size: 13px;
  color: rgba(242, 234, 217, 0.9);
  overflow-x: auto;
  scrollbar-width: none;
}

.game-layout__status::-webkit-scrollbar {
  display: none;
}

.game-layout__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.game-layout__actions :deep(.el-button) {
  border-color: rgba(242, 234, 217, 0.32);
  background: transparent;
  color: rgba(242, 234, 217, 0.9);
}

.game-layout__actions :deep(.el-button:not(.is-disabled):hover) {
  background: rgba(242, 234, 217, 0.14);
  border-color: rgba(242, 234, 217, 0.5);
  color: #fdf7ea;
}

.game-layout__actions :deep(.el-button--danger) {
  background: var(--gg-brand);
  border-color: #6f1d13;
  color: #fdf3ea;
}

/* ── 主体：严格按剩余高度约束，避免棋盘被裁 ── */
.game-layout__main {
  flex: 1 1 auto;
  min-height: 0;
  padding: 12px var(--gg-page-pad) 16px;
  overflow: hidden;
}

@media (max-width: 900px) {
  .game-layout__header {
    padding: 0 12px;
  }

  .game-layout__main {
    padding: 10px 12px 14px;
    overflow-y: auto;
  }
}
</style>
