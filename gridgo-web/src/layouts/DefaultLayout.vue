<template>
  <div class="app-shell">
    <header class="app-shell__bar">
      <div class="app-shell__brand" @click="router.push('/')">
        <span class="app-shell__logo">GG</span>
        <span class="app-shell__titles">
          <span class="app-shell__title">{{ title }}</span>
          <span class="app-shell__tagline">BOARD GAME PARLOUR</span>
        </span>
      </div>

      <!-- 桌面导航（≤760px 隐藏，改由抽屉承载） -->
      <nav class="app-shell__nav" aria-label="主导航">
        <slot name="nav">
          <router-link
            v-for="(item, i) in navItems"
            :key="item.path"
            :to="item.path"
            class="app-shell__link"
          >
            <span class="app-shell__link-idx">{{ String(i + 1).padStart(2, '0') }}</span>
            <span class="app-shell__link-text">{{ item.label }}</span>
          </router-link>
        </slot>
      </nav>

      <!-- 桌面操作区 + 用户票据（≤760px 隐藏，内容移入抽屉） -->
      <div class="app-shell__actions">
        <slot name="actions" />

        <!-- 返回房间入口：已加入房间且不在房间页时显示 -->
        <button
          v-if="canReturnToRoom"
          class="app-shell__btn app-shell__btn--room"
          type="button"
          @click="goBackToRoom"
        >
          返回房间
        </button>

        <!-- 登录态：用户票据（仅头像与昵称，不展示 UID） -->
        <div v-if="userStore.isLoggedIn" class="app-shell__user">
          <img v-if="userStore.avatar" class="app-shell__avatar" :src="userStore.avatar" alt="" />
          <span v-else class="app-shell__avatar">{{ avatarText }}</span>
          <span class="app-shell__user-meta">
            <span class="app-shell__user-name">{{ displayName }}</span>
          </span>
          <button class="app-shell__btn app-shell__btn--ghost" type="button" @click="handleLogout">
            退出
          </button>
        </div>

        <!-- 未登录态：登录入口 -->
        <div v-else class="app-shell__guest">
          <button class="app-shell__btn app-shell__btn--ghost" type="button" @click="router.push('/login')">
            登录
          </button>
          <button class="app-shell__btn app-shell__btn--solid" type="button" @click="router.push('/register')">
            注册
          </button>
        </div>
      </div>

      <!-- 窄屏折叠入口 -->
      <button
        ref="burgerRef"
        class="app-shell__burger"
        type="button"
        aria-label="打开导航菜单"
        aria-controls="app-shell-drawer"
        :aria-expanded="mobileNavOpen ? 'true' : 'false'"
        @click="openMobileNav"
      >
        <span class="app-shell__burger-bars" aria-hidden="true">
          <i></i><i></i><i></i>
        </span>
        <span class="app-shell__burger-text">菜单</span>
      </button>
    </header>

    <!-- 窄屏抽屉 -->
    <Transition name="gg-scrim">
      <div v-if="mobileNavOpen" class="app-shell__scrim" @click="closeMobileNav"></div>
    </Transition>

    <Transition name="gg-panel">
      <aside
        v-if="mobileNavOpen"
        id="app-shell-drawer"
        ref="drawerRef"
        class="app-shell__drawer"
        role="dialog"
        aria-modal="true"
        aria-label="导航菜单"
        tabindex="-1"
      >
        <header class="app-shell__drawer-head">
          <span class="app-shell__drawer-title">
            <span class="gg-kicker">MENU</span>
            <span class="app-shell__drawer-title-text">菜单</span>
          </span>
          <button
            class="app-shell__drawer-close"
            type="button"
            aria-label="关闭导航菜单"
            @click="closeMobileNav"
          >
            <span aria-hidden="true">×</span>
          </button>
        </header>

        <nav class="app-shell__drawer-nav" aria-label="导航">
          <router-link
            v-for="(item, i) in navItems"
            :key="item.path"
            :to="item.path"
            class="app-shell__drawer-link"
          >
            <span class="app-shell__drawer-link-idx">{{ String(i + 1).padStart(2, '0') }}</span>
            <span class="app-shell__drawer-link-text">{{ item.label }}</span>
            <span class="app-shell__drawer-link-arrow" aria-hidden="true">→</span>
          </router-link>
        </nav>

        <!-- 页面操作（承接桌面 #actions 插槽内容） -->
        <section class="app-shell__drawer-block">
          <span class="gg-kicker">ACTIONS · 操作</span>
          <div class="app-shell__drawer-actions">
            <slot name="actions" />
          </div>
        </section>

        <!-- 返回房间入口（已加入房间且不在房间页时显示） -->
        <section v-if="canReturnToRoom" class="app-shell__drawer-block">
          <span class="gg-kicker">ROOM · 房间</span>
          <button
            class="app-shell__drawer-btn app-shell__drawer-btn--solid"
            type="button"
            @click="goBackToRoom"
          >
            返回房间
          </button>
        </section>

        <!-- 用户票据 / 访客入口 -->
        <section class="app-shell__drawer-block app-shell__drawer-block--user">
          <template v-if="userStore.isLoggedIn">
            <span class="gg-kicker">ACCOUNT · 账户</span>
            <div class="app-shell__drawer-user">
              <img v-if="userStore.avatar" class="app-shell__drawer-avatar" :src="userStore.avatar" alt="" />
              <span v-else class="app-shell__drawer-avatar">{{ avatarText }}</span>
              <span class="app-shell__drawer-user-meta">
                <span class="app-shell__drawer-user-name">{{ displayName }}</span>
              </span>
            </div>
            <button
              class="app-shell__drawer-btn app-shell__drawer-btn--ghost"
              type="button"
              @click="handleLogout"
            >
              退出登录
            </button>
          </template>

          <template v-else>
            <span class="gg-kicker">ACCOUNT · 账户</span>
            <div class="app-shell__drawer-guest">
              <span class="app-shell__drawer-guest-text">尚未登录，登录后可保存战绩与好友</span>
            </div>
            <button
              class="app-shell__drawer-btn app-shell__drawer-btn--solid"
              type="button"
              @click="goTo('/login')"
            >
              登录
            </button>
            <button
              class="app-shell__drawer-btn app-shell__drawer-btn--ghost"
              type="button"
              @click="goTo('/register')"
            >
              注册
            </button>
          </template>
        </section>
      </aside>
    </Transition>

    <main class="app-shell__main">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getMyRoom } from '@/api/room'
import type { RoomInfo } from '@/api/room'

withDefaults(defineProps<{ title?: string }>(), { title: 'GridGo' })

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const navItems = [
  { path: '/', label: '大厅' },
  { path: '/leaderboard', label: '排行榜' },
  { path: '/friends', label: '好友' },
  { path: '/profile', label: '个人中心' },
]

const displayName = computed(() => userStore.nickname || userStore.username || '玩家')

const avatarText = computed(() => displayName.value.slice(0, 1).toUpperCase())

// ── 返回房间入口（依据后端活跃房间索引，不在房间页时展示） ──
const activeRoom = ref<RoomInfo | null>(null)

const canReturnToRoom = computed(() => !!activeRoom.value && route.name !== 'Room')

const refreshActiveRoom = async () => {
  if (!userStore.isLoggedIn) {
    activeRoom.value = null
    return
  }
  try {
    activeRoom.value = await getMyRoom()
  } catch {
    activeRoom.value = null
  }
}

const goBackToRoom = () => {
  closeMobileNav(false)
  if (activeRoom.value) {
    router.push(`/room/${activeRoom.value.code}`)
  }
}

const handleLogout = () => {
  closeMobileNav(false)
  userStore.clearUserInfo()
  router.push('/login')
}

// ── 窄屏折叠导航（≤760px） ──
const mobileNavOpen = ref(false)
const burgerRef = ref<HTMLButtonElement | null>(null)
const drawerRef = ref<HTMLElement | null>(null)
let previousBodyOverflow = ''

const openMobileNav = () => {
  mobileNavOpen.value = true
}

function closeMobileNav(restoreFocus = true) {
  if (!mobileNavOpen.value) return
  mobileNavOpen.value = false
  if (restoreFocus) {
    burgerRef.value?.focus()
  }
}

function goTo(path: string) {
  closeMobileNav(false)
  router.push(path)
}

const onKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape' && mobileNavOpen.value) {
    closeMobileNav()
  }
}

watch(mobileNavOpen, async (open) => {
  if (open) {
    previousBodyOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    await nextTick()
    drawerRef.value?.focus()
  } else {
    document.body.style.overflow = previousBodyOverflow
  }
})

// 路由切换后自动收起抽屉，并同步活跃房间
watch(
  () => route.fullPath,
  () => {
    closeMobileNav(false)
    refreshActiveRoom()
  },
)

// 登录态变化时刷新活跃房间
watch(
  () => userStore.isLoggedIn,
  () => {
    refreshActiveRoom()
  },
)

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  refreshActiveRoom()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = previousBodyOverflow
})
</script>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  max-width: 100%;
  background: transparent;
}

/* ── 顶部铅字条 ── */
.app-shell__bar {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: var(--gg-gap-lg);
  height: var(--gg-shell-bar);
  padding: 0 var(--gg-page-pad);
  background: var(--gg-grad-night);
  color: #f2ead9;
  border-bottom: 1px solid #16130f;
  box-shadow: inset 0 -3px 0 var(--gg-brand), 0 6px 16px -8px rgba(40, 30, 18, 0.6);
}

.app-shell__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  cursor: pointer;
  user-select: none;
  flex: 0 1 auto;
}

.app-shell__logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  background: var(--gg-brand);
  border: 1px solid #6f1d13;
  color: #fdf3ea;
  font-family: var(--gg-font-display);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.06em;
  box-shadow: 2px 2px 0 rgba(0, 0, 0, 0.4);
  transition: transform var(--gg-dur) var(--gg-ease);
}

.app-shell__brand:hover .app-shell__logo {
  transform: translate(-1px, -1px);
}

.app-shell__titles {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  min-width: 0;
}

.app-shell__title {
  font-family: var(--gg-font-display);
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.05em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-shell__tagline {
  font-family: var(--gg-font-mono);
  font-size: 9px;
  letter-spacing: 0.2em;
  color: rgba(242, 234, 217, 0.42);
}

.app-shell__nav {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 1 1 auto;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}

.app-shell__nav::-webkit-scrollbar {
  display: none;
}

.app-shell__link {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  padding: 8px 12px;
  color: rgba(242, 234, 217, 0.68);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-decoration: none;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
  transition: color var(--gg-dur-fast) linear, border-color var(--gg-dur-fast) linear,
    background-color var(--gg-dur-fast) linear;
}

.app-shell__link-idx {
  font-family: var(--gg-font-mono);
  font-size: 9.5px;
  letter-spacing: 0.12em;
  color: rgba(242, 234, 217, 0.36);
}

.app-shell__link:hover {
  color: #fdf7ea;
  background: rgba(255, 255, 255, 0.05);
  text-decoration: none;
}

.app-shell__link.router-link-active {
  color: #fdf7ea;
  border-bottom-color: var(--gg-brand);
}

.app-shell__link.router-link-active .app-shell__link-idx {
  color: var(--gg-gold);
}

.app-shell__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

/* ── 用户票据 / 访客入口 ── */
.app-shell__user,
.app-shell__guest {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 10px;
  margin-left: 2px;
  border-left: 1px dashed rgba(242, 234, 217, 0.22);
}

.app-shell__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  object-fit: cover;
  background: var(--gg-surface);
  border: 1px solid var(--gg-border-strong);
  color: var(--gg-brand);
  font-family: var(--gg-font-display);
  font-size: 13px;
  font-weight: 700;
}

.app-shell__user-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  min-width: 0;
}

.app-shell__user-name {
  font-size: 12.5px;
  font-weight: 600;
  color: #fdf7ea;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-shell__btn {
  padding: 6px 12px;
  font-family: var(--gg-font-body);
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.08em;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background-color var(--gg-dur-fast) linear, color var(--gg-dur-fast) linear,
    border-color var(--gg-dur-fast) linear;
}

.app-shell__btn--ghost {
  background: transparent;
  border-color: rgba(242, 234, 217, 0.3);
  color: rgba(242, 234, 217, 0.86);
}

.app-shell__btn--ghost:hover {
  background: rgba(242, 234, 217, 0.12);
  color: #fdf7ea;
}

.app-shell__btn--solid {
  background: var(--gg-brand);
  border-color: #6f1d13;
  color: #fdf3ea;
  box-shadow: 2px 2px 0 rgba(0, 0, 0, 0.35);
}

.app-shell__btn--solid:hover {
  background: #bd4433;
}

/* 返回房间按钮（金色强调，区别于退出/登录） */
.app-shell__btn--room {
  background: rgba(201, 162, 39, 0.16);
  border-color: rgba(201, 162, 39, 0.75);
  color: #f0d79a;
}

.app-shell__btn--room:hover {
  background: rgba(201, 162, 39, 0.3);
  color: #fdf7ea;
}

.app-shell__main {
  flex: 1 1 auto;
  min-height: 0;
}

/* ═══ 窄屏折叠入口（桌面隐藏） ═══ */
.app-shell__burger {
  display: none;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 0 12px;
  margin-left: auto;
  background: transparent;
  border: 1px solid rgba(242, 234, 217, 0.32);
  color: rgba(242, 234, 217, 0.9);
  font-family: var(--gg-font-body);
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.1em;
  cursor: pointer;
  flex: 0 0 auto;
  transition: background-color var(--gg-dur-fast) linear, border-color var(--gg-dur-fast) linear;
}

.app-shell__burger:hover {
  background: rgba(242, 234, 217, 0.12);
  border-color: rgba(242, 234, 217, 0.5);
  color: #fdf7ea;
}

.app-shell__burger-bars {
  display: inline-flex;
  flex-direction: column;
  justify-content: space-between;
  width: 18px;
  height: 12px;
}

.app-shell__burger-bars i {
  display: block;
  height: 2px;
  background: currentColor;
}

/* ═══ 抽屉 ═══ */
.app-shell__scrim {
  position: fixed;
  inset: 0;
  z-index: 60;
  background: rgba(22, 19, 15, 0.58);
}

.app-shell__drawer {
  position: fixed;
  top: 0;
  right: 0;
  z-index: 61;
  display: flex;
  flex-direction: column;
  width: min(86vw, 340px);
  max-width: 100%;
  height: 100vh;
  height: 100dvh;
  background-color: var(--gg-surface);
  background-image: var(--gg-paper-lines);
  border-left: 2px solid var(--gg-ink);
  box-shadow: -10px 0 30px -14px rgba(30, 22, 12, 0.7);
  overflow-y: auto;
  overscroll-behavior: contain;
}

.app-shell__drawer:focus {
  outline: none;
}

.app-shell__drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 16px;
  background: var(--gg-grad-night);
  color: #f2ead9;
  border-bottom: 2px solid var(--gg-brand);
}

.app-shell__drawer-title {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
}

.app-shell__drawer-title .gg-kicker {
  color: rgba(242, 234, 217, 0.5);
}

.app-shell__drawer-title-text {
  font-family: var(--gg-font-display);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.app-shell__drawer-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  margin-right: -8px;
  background: transparent;
  border: 1px solid rgba(242, 234, 217, 0.32);
  color: rgba(242, 234, 217, 0.9);
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  transition: background-color var(--gg-dur-fast) linear, color var(--gg-dur-fast) linear;
}

.app-shell__drawer-close:hover {
  background: rgba(242, 234, 217, 0.14);
  color: #fdf7ea;
}

.app-shell__drawer-nav {
  display: flex;
  flex-direction: column;
  border-bottom: 1px solid var(--gg-border-strong);
}

.app-shell__drawer-link {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 48px;
  padding: 0 16px;
  color: var(--gg-ink);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-decoration: none;
  border-bottom: 1px dotted var(--gg-border-strong);
  transition: background-color var(--gg-dur-fast) linear, color var(--gg-dur-fast) linear;
}

.app-shell__drawer-link:last-child {
  border-bottom: 0;
}

.app-shell__drawer-link:hover {
  background: var(--gg-surface-2);
  text-decoration: none;
}

.app-shell__drawer-link.router-link-active {
  color: var(--gg-brand);
  background: var(--gg-brand-soft);
  box-shadow: inset 3px 0 0 var(--gg-brand);
}

.app-shell__drawer-link-idx {
  font-family: var(--gg-font-mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--gg-ink-4);
}

.app-shell__drawer-link-text {
  flex: 1 1 auto;
  min-width: 0;
}

.app-shell__drawer-link-arrow {
  font-family: var(--gg-font-mono);
  font-size: 13px;
  color: var(--gg-ink-4);
}

.app-shell__drawer-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px dotted var(--gg-border-strong);
}

.app-shell__drawer-block:last-child {
  border-bottom: 0;
}

.app-shell__drawer-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.app-shell__drawer-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.app-shell__drawer-actions :deep(.el-button) {
  width: 100%;
  min-height: 44px;
  font-size: 13.5px;
}

.app-shell__drawer-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border-strong);
}

.app-shell__drawer-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  object-fit: cover;
  background: var(--gg-surface);
  border: 1px solid var(--gg-border-strong);
  color: var(--gg-brand);
  font-family: var(--gg-font-display);
  font-size: 15px;
  font-weight: 700;
}

.app-shell__drawer-user-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.app-shell__drawer-user-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--gg-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-shell__drawer-guest {
  padding: 10px;
  background: var(--gg-surface-2);
  border: 1px dashed var(--gg-border-strong);
}

.app-shell__drawer-guest-text {
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--gg-ink-2);
}

.app-shell__drawer-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 46px;
  font-family: var(--gg-font-body);
  font-size: 13.5px;
  font-weight: 600;
  letter-spacing: 0.1em;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background-color var(--gg-dur-fast) linear, color var(--gg-dur-fast) linear,
    border-color var(--gg-dur-fast) linear;
}

.app-shell__drawer-btn--solid {
  background: var(--gg-brand);
  border-color: #6f1d13;
  color: #fdf3ea;
  box-shadow: 2px 2px 0 rgba(0, 0, 0, 0.3);
}

.app-shell__drawer-btn--solid:hover {
  background: #bd4433;
}

.app-shell__drawer-btn--ghost {
  background: transparent;
  border-color: var(--gg-border-strong);
  color: var(--gg-ink-2);
}

.app-shell__drawer-btn--ghost:hover {
  background: var(--gg-surface-2);
  color: var(--gg-ink);
}

/* 焦点可见（键盘） */
.app-shell__burger:focus-visible,
.app-shell__drawer-close:focus-visible,
.app-shell__drawer-btn:focus-visible,
.app-shell__drawer-link:focus-visible,
.app-shell__btn:focus-visible {
  outline: 2px solid var(--gg-gold);
  outline-offset: 2px;
}

/* 过渡 */
.gg-scrim-enter-active,
.gg-scrim-leave-active {
  transition: opacity var(--gg-dur) linear;
}

.gg-scrim-enter-from,
.gg-scrim-leave-to {
  opacity: 0;
}

.gg-panel-enter-active,
.gg-panel-leave-active {
  transition: transform var(--gg-dur-slow) var(--gg-ease-out);
}

.gg-panel-enter-from,
.gg-panel-leave-to {
  transform: translateX(100%);
}

@media (prefers-reduced-motion: reduce) {
  .gg-scrim-enter-active,
  .gg-scrim-leave-active,
  .gg-panel-enter-active,
  .gg-panel-leave-active {
    transition: none;
  }
}

@media (max-width: 900px) {
  .app-shell__bar {
    gap: 10px;
    padding: 0 12px;
  }

  .app-shell__tagline {
    display: none;
  }

  .app-shell__user-name {
    max-width: 78px;
  }
}

/* ═══ ≤760px：折叠式导航，顶栏无横向溢出 ═══ */
@media (max-width: 760px) {
  .app-shell__nav,
  .app-shell__actions {
    display: none;
  }

  .app-shell__burger {
    display: inline-flex;
  }

  .app-shell__bar {
    gap: 8px;
    padding: 0 12px;
  }

  .app-shell__title {
    font-size: 14px;
  }
}

@media (max-width: 640px) {
  .app-shell__bar {
    height: 52px;
  }

  .app-shell__logo {
    width: 28px;
    height: 28px;
    font-size: 11px;
  }

  .app-shell__link {
    padding: 7px 8px;
    font-size: 12px;
  }

  .app-shell__link-idx {
    display: none;
  }

  .app-shell__user-meta {
    display: none;
  }

  .app-shell__btn {
    padding: 5px 9px;
    font-size: 12px;
  }

  .app-shell__burger {
    padding: 0 10px;
    font-size: 12px;
  }
}
</style>
