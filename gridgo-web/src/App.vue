<template>
  <router-view v-slot="{ Component }">
    <transition name="gg-route" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup lang="ts">
// GridGo - 大富翁游戏
</script>

<style>
#app {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  position: relative;
  isolation: isolate;
}

/* 路由切换统一过渡 */
.gg-route-enter-active,
.gg-route-leave-active {
  transition: opacity 0.22s cubic-bezier(0.16, 1, 0.3, 1),
    transform 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}

.gg-route-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.gg-route-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
