import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/pages/Home.vue'),
    meta: { title: 'GridGo - 大富翁' },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/Login.vue'),
    meta: { title: '登录', guestOnly: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/pages/Register.vue'),
    meta: { title: '注册', guestOnly: true },
  },
  {
    path: '/room/:code',
    name: 'Room',
    component: () => import('@/pages/Room.vue'),
    meta: { title: '房间', requiresAuth: true },
  },
  {
    path: '/game/:id',
    name: 'Game',
    component: () => import('@/pages/Game.vue'),
    meta: { title: '游戏', requiresAuth: true },
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/pages/Profile.vue'),
    meta: { title: '个人中心', requiresAuth: true },
  },
  {
    path: '/leaderboard',
    name: 'Leaderboard',
    component: () => import('@/pages/Leaderboard.vue'),
    meta: { title: '排行榜' },
  },
  {
    path: '/replay/:id',
    name: 'Replay',
    component: () => import('@/pages/Replay.vue'),
    meta: { title: '对局回放', requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  document.title = (to.meta.title as string) || 'GridGo - 大富翁'

  const userStore = useUserStore()
  const loggedIn = userStore.isLoggedIn

  // 需要认证的页面 → 未登录则跳转登录
  if (to.meta.requiresAuth && !loggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  // 仅游客可访问的页面（登录/注册）→ 已登录则跳转首页
  if (to.meta.guestOnly && loggedIn) {
    next({ name: 'Home' })
    return
  }

  next()
})

export default router
