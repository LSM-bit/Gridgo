import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { getMyRoom } from '@/api/room'
import type { RoomInfo } from '@/api/room'

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
    path: '/friends',
    name: 'Friends',
    component: () => import('@/pages/Friends.vue'),
    meta: { title: '好友', requiresAuth: true },
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
router.beforeEach(async (to, _from, next) => {
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

  // 房间页 → 校验当前用户确实已加入该房间（防止未加入直接访问 /room/:code）
  if (to.name === 'Room' && loggedIn) {
    const code = String(to.params.code ?? '')
    let myRoom: RoomInfo | null = null
    let checked = false
    try {
      myRoom = await getMyRoom()
      checked = true
    } catch (err) {
      // 接口异常（网络/服务未就绪）不拦截，避免误伤正常访问
      console.warn('[Router] 获取当前活跃房间失败，跳过房间守卫校验', err)
    }

    if (checked) {
      if (!myRoom) {
        ElMessage.warning('你尚未加入任何房间，请先在大厅创建或加入房间')
        next({ name: 'Home' })
        return
      }
      // 已加入其他房间 → 直接带回自己所在的房间
      if (myRoom.code !== code) {
        next({ name: 'Room', params: { code: myRoom.code }, replace: true })
        return
      }
    }
  }

  next()
})

export default router
