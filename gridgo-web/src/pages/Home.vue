<template>
  <DefaultLayout title="GridGo 大厅">
    <template #actions>
      <el-button size="small" :loading="listLoading" @click="loadRooms">刷新</el-button>
      <el-button size="small" type="primary" @click="openCreate">创建房间</el-button>
      <el-button size="small" @click="openJoin()">加入房间</el-button>
    </template>

    <div class="lobby">
      <!-- ── 主区：刊头 + 工具条 + 房间票券清单 ── -->
      <section class="lobby__main">
        <header class="lobby__masthead">
          <div class="lobby__masthead-text">
            <span class="gg-kicker">LOBBY · 大厅公告板</span>
            <h1 class="lobby__title">游戏大厅</h1>
            <p class="lobby__sub">创建或加入一局大富翁，2–8 人同场竞技</p>
          </div>
          <div class="lobby__masthead-stats">
            <div class="lobby__stat">
              <span class="lobby__stat-num gg-num">{{ rooms.length }}</span>
              <span class="lobby__stat-label">房间</span>
            </div>
            <div class="lobby__stat">
              <span class="lobby__stat-num gg-num">{{ waitingCount }}</span>
              <span class="lobby__stat-label">等待中</span>
            </div>
            <div class="lobby__stat">
              <span class="lobby__stat-num gg-num">{{ playingCount }}</span>
              <span class="lobby__stat-label">对局中</span>
            </div>
          </div>
        </header>

        <div class="lobby__toolbar">
          <span class="lobby__toolbar-label">房间列表</span>
          <div class="lobby__toolbar-actions">
            <el-button size="small" :loading="listLoading" @click="loadRooms">刷新列表</el-button>
            <el-button size="small" type="primary" @click="openCreate">创建房间</el-button>
            <el-button size="small" @click="openJoin()">输入房间号</el-button>
          </div>
        </div>

        <div class="lobby__list">
          <div v-if="listLoading && rooms.length === 0" class="lobby__skeleton">
            <div v-for="n in 3" :key="n" class="lobby__skeleton-row gg-shimmer"></div>
          </div>

          <div v-else-if="rooms.length === 0" class="lobby__empty">
            <span class="lobby__empty-mark">◈</span>
            <h3 class="lobby__empty-title">暂无可用房间</h3>
            <p class="lobby__empty-text">大厅现在很安静。创建第一间房，等对手入座。</p>
            <div class="lobby__empty-actions">
              <el-button type="primary" @click="openCreate">创建房间</el-button>
              <el-button @click="openJoin()">用房间号加入</el-button>
            </div>
            <ul class="lobby__empty-tips">
              <li><span>01</span>建好房后把 6 位房间号发给好友</li>
              <li><span>02</span>也可以创建时直接加 AI 对手练手</li>
            </ul>
          </div>

          <button
            v-for="row in rooms"
            v-else
            :key="row.id"
            type="button"
            class="room-ticket"
            :class="{ 'room-ticket--locked': row.status === 'playing' }"
            :disabled="row.status === 'playing'"
            @click="openJoin(row.code)"
          >
            <span class="room-ticket__code">{{ row.code }}</span>
            <span class="room-ticket__body">
              <span class="room-ticket__name">{{ row.name }}</span>
              <span class="room-ticket__meta">
                房主 {{ row.host_nickname }} · 玩家 {{ row.player_count }}/{{ row.max_players }} · AI
                {{ row.ai_count }} · 观战 {{ row.spectator_count }}
              </span>
            </span>
            <span class="room-ticket__status" :data-status="row.status">{{ statusText(row.status) }}</span>
            <span class="room-ticket__go">{{ row.status === 'playing' ? '进行中' : '加入' }}</span>
          </button>
        </div>
      </section>

      <!-- ── 侧栏：通行证 + 对局规则 ── -->
      <aside class="lobby__aside">
        <div class="pass">
          <span class="gg-kicker">PLAYER PASS</span>

          <template v-if="userStore.isLoggedIn">
            <div class="pass__id">
              <img v-if="userStore.avatar" class="pass__avatar" :src="userStore.avatar" alt="" />
              <span v-else class="pass__avatar">{{ avatarText }}</span>
              <div class="pass__id-text">
                <b class="pass__name">{{ displayName }}</b>
                <span class="pass__uid">UID {{ userStore.userId }}</span>
              </div>
            </div>
            <p class="pass__hint">已登录，可创建房间、邀请好友并保存战绩。</p>
            <div class="pass__actions">
              <el-button size="small" @click="router.push('/profile')">个人中心</el-button>
              <el-button size="small" type="danger" plain @click="handleLogout">退出登录</el-button>
            </div>
          </template>

          <template v-else>
            <div class="pass__guest">
              <span class="pass__guest-mark">?</span>
              <div class="pass__id-text">
                <b class="pass__name">未登录访客</b>
                <span class="pass__uid">仅可浏览房间列表</span>
              </div>
            </div>
            <p class="pass__hint">登录后即可创建房间、加入对局与保存战绩。</p>
            <div class="pass__actions">
              <el-button size="small" type="primary" @click="router.push('/login')">登录</el-button>
              <el-button size="small" @click="router.push('/register')">注册账号</el-button>
            </div>
          </template>
        </div>

        <div class="rules">
          <span class="gg-kicker">RULES · 对局说明</span>
          <ol class="rules__list">
            <li><span>01</span>开局每位玩家获得等额现金</li>
            <li><span>02</span>掷骰前进，落点可购买地块</li>
            <li><span>03</span>建造提升租金，抵押融资周转</li>
            <li><span>04</span>与对手自由交易、竞价拍卖</li>
            <li><span>05</span>其余玩家破产即获得胜利</li>
          </ol>
        </div>
      </aside>

      <footer class="lobby__foot">
        <span class="gg-stamp gg-stamp--gold">GRIDGO</span>
        <span class="lobby__foot-text">v0.1.0 · 在线大富翁对战平台</span>
        <span class="lobby__foot-note">房间状态每 5 秒自动刷新</span>
      </footer>
    </div>

    <el-dialog v-model="createVisible" title="创建房间" width="460px">
      <el-form :model="createForm" label-width="96px">
        <el-form-item label="房间名称">
          <el-input v-model="createForm.name" placeholder="留空则自动生成" />
        </el-form-item>
        <el-form-item label="地图">
          <el-select v-model="createForm.mapId">
            <el-option v-for="map in MAP_OPTIONS" :key="map.value" :label="map.label" :value="map.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="最大玩家">
          <el-input-number v-model="createForm.maxPlayers" :min="2" :max="8" />
        </el-form-item>
        <el-form-item label="AI 数量">
          <el-input-number v-model="createForm.aiCount" :min="0" :max="createForm.maxPlayers" />
        </el-form-item>
        <el-form-item label="AI 难度">
          <el-select v-model="createForm.aiDifficulty">
            <el-option v-for="item in AI_DIFFICULTY_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="房间密码">
          <el-switch v-model="createWithPassword" active-text="启用" />
        </el-form-item>
        <el-form-item v-if="createWithPassword" label="密码">
          <el-input v-model="createForm.password" type="password" show-password placeholder="加入房间时需要" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="joinVisible" title="加入房间" width="420px">
      <el-form :model="joinForm" label-width="96px">
        <el-form-item label="房间代码">
          <el-input v-model="joinForm.code" placeholder="6 位房间代码" />
        </el-form-item>
        <el-form-item label="房间密码">
          <el-input v-model="joinForm.password" type="password" show-password placeholder="无密码可留空" />
        </el-form-item>
        <el-form-item label="以观战加入">
          <el-switch v-model="joinForm.asSpectator" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="joinVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitJoin">加入</el-button>
      </template>
    </el-dialog>
  </DefaultLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { useUserStore } from '@/stores/user'
import {
  AI_DIFFICULTY_OPTIONS,
  MAP_OPTIONS,
  createRoom,
  getRooms,
  joinRoom,
  type RoomListItem,
} from '@/api/room'

const router = useRouter()
const userStore = useUserStore()

const rooms = ref<RoomListItem[]>([])
const listLoading = ref(false)
const submitting = ref(false)
const createVisible = ref(false)
const joinVisible = ref(false)
const createWithPassword = ref(false)

const createForm = reactive({
  name: '',
  mapId: 'classic',
  maxPlayers: 4,
  aiCount: 0,
  aiDifficulty: 'easy',
  password: '',
})

const joinForm = reactive({
  code: '',
  password: '',
  asSpectator: false,
})

const displayName = computed(() => userStore.nickname || userStore.username || '玩家')
const avatarText = computed(() => displayName.value.slice(0, 1).toUpperCase())
const waitingCount = computed(() => rooms.value.filter((room) => room.status === 'waiting').length)
const playingCount = computed(() => rooms.value.filter((room) => room.status === 'playing').length)

const statusText = (status: string) =>
  ({ waiting: '等待中', playing: '对局中', finished: '已结束' })[status] ?? status

const loadRooms = async () => {
  listLoading.value = true
  try {
    rooms.value = await getRooms()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || err.message || '房间列表加载失败')
  } finally {
    listLoading.value = false
  }
}

const handleLogout = () => {
  userStore.clearUserInfo()
  ElMessage.success('已退出登录')
  loadRooms()
}

const openCreate = () => {
  createWithPassword.value = false
  createForm.name = ''
  createForm.mapId = 'classic'
  createForm.maxPlayers = 4
  createForm.aiCount = 0
  createForm.aiDifficulty = 'easy'
  createForm.password = ''
  createVisible.value = true
}

const openJoin = (code = '') => {
  joinForm.code = code
  joinForm.password = ''
  joinForm.asSpectator = false
  joinVisible.value = true
}

const submitCreate = async () => {
  if (createWithPassword.value && !createForm.password.trim()) {
    ElMessage.warning('请输入房间密码或关闭密码开关')
    return
  }
  submitting.value = true
  try {
    const room = await createRoom({
      name: createForm.name || undefined,
      map_id: createForm.mapId,
      max_players: createForm.maxPlayers,
      ai_count: createForm.aiCount,
      ai_difficulty: createForm.aiDifficulty,
      password: createWithPassword.value ? createForm.password.trim() : null,
    })
    createVisible.value = false
    ElMessage.success(`房间已创建：${room.code}`)
    router.push(`/room/${room.code}`)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || err.message || '创建房间失败')
  } finally {
    submitting.value = false
  }
}

const submitJoin = async () => {
  const code = joinForm.code.trim()
  if (!code) {
    ElMessage.warning('请输入房间代码')
    return
  }
  submitting.value = true
  try {
    await joinRoom(code, joinForm.asSpectator, joinForm.password.trim() || undefined)
    joinVisible.value = false
    router.push(`/room/${code}`)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || err.message || '加入房间失败')
  } finally {
    submitting.value = false
  }
}

onMounted(loadRooms)
</script>

<style scoped>
.lobby {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 296px;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 16px;
  width: 100%;
  max-width: 1320px;
  min-height: calc(100vh - var(--gg-shell-bar));
  margin: 0 auto;
  padding: var(--gg-page-pad) var(--gg-page-pad) 14px;
  box-sizing: border-box;
  animation: gg-fade-up var(--gg-dur-slow) var(--gg-ease-out) both;
}

/* ── 主区 ── */
.lobby__main {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
  min-height: 0;
}

.lobby__masthead {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding-bottom: 14px;
  border-bottom: 2px solid var(--gg-ink);
}

.lobby__title {
  margin: 4px 0 2px;
  font-family: var(--gg-font-display);
  font-size: clamp(24px, 3.2vw, 34px);
  line-height: 1.15;
  letter-spacing: 0.02em;
  color: var(--gg-ink);
}

.lobby__sub {
  margin: 0;
  font-size: 12.5px;
  color: var(--gg-ink-3);
}

.lobby__masthead-stats {
  display: flex;
  gap: 18px;
  flex: 0 0 auto;
}

.lobby__stat {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.lobby__stat-num {
  font-family: var(--gg-font-display);
  font-size: 26px;
  font-weight: 700;
  line-height: 1;
  color: var(--gg-brand);
}

.lobby__stat-label {
  font-family: var(--gg-font-mono);
  font-size: 9.5px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--gg-ink-3);
}

.lobby__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 10px;
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border);
}

.lobby__toolbar-label {
  font-family: var(--gg-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--gg-ink-3);
}

.lobby__toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.lobby__list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1 1 auto;
  min-height: 240px;
}

/* 骨架 */
.lobby__skeleton {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.lobby__skeleton-row {
  height: 58px;
  border: 1px solid var(--gg-border);
}

/* 空态 */
.lobby__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex: 1 1 auto;
  padding: 30px 24px;
  text-align: center;
  background: var(--gg-surface);
  background-image: var(--gg-dotfield, radial-gradient(rgba(88, 68, 42, 0.12) 0.7px, transparent 0.8px));
  background-size: 8px 8px;
  border: 1px dashed var(--gg-border-strong);
}

.lobby__empty-mark {
  font-size: 26px;
  line-height: 1;
  color: var(--gg-gold);
}

.lobby__empty-title {
  margin: 2px 0 0;
  font-family: var(--gg-font-display);
  font-size: 17px;
  color: var(--gg-ink);
}

.lobby__empty-text {
  margin: 0;
  font-size: 12.5px;
  color: var(--gg-ink-3);
}

.lobby__empty-actions {
  display: flex;
  gap: 10px;
  margin-top: 6px;
}

.lobby__empty-tips {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin: 14px 0 0;
  padding: 12px 0 0;
  border-top: 1px dashed var(--gg-border-strong);
  list-style: none;
  font-size: 12px;
  color: var(--gg-ink-3);
  text-align: left;
}

.lobby__empty-tips li {
  display: flex;
  gap: 8px;
}

.lobby__empty-tips span {
  font-family: var(--gg-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.14em;
  color: var(--gg-gold-strong);
}

/* 房间票券行 */
.room-ticket {
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr) auto 74px;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 9px 12px;
  font: inherit;
  text-align: left;
  cursor: pointer;
  background: var(--gg-surface);
  border: 1px solid var(--gg-border-strong);
  border-left: 3px solid var(--gg-ink-4);
  color: var(--gg-ink);
  transition: transform var(--gg-dur) var(--gg-ease), border-color var(--gg-dur) var(--gg-ease),
    box-shadow var(--gg-dur) var(--gg-ease), background-color var(--gg-dur) var(--gg-ease);
}

.room-ticket:hover:not(:disabled) {
  transform: translateX(3px);
  background: #fffdf6;
  border-left-color: var(--gg-brand);
  box-shadow: var(--gg-shadow-1);
}

.room-ticket:focus-visible {
  outline: 2px solid var(--gg-brand);
  outline-offset: 1px;
}

.room-ticket--locked {
  cursor: not-allowed;
  opacity: 0.62;
  border-left-color: var(--gg-gold);
}

.room-ticket__code {
  font-family: var(--gg-font-mono);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-align: center;
  padding: 4px 6px;
  color: var(--gg-ink-2);
  border: 1px dashed var(--gg-border-strong);
  background: var(--gg-surface-2);
}

.room-ticket__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.room-ticket__name {
  font-size: 14px;
  font-weight: 700;
  color: var(--gg-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.room-ticket__meta {
  font-size: 11.5px;
  color: var(--gg-ink-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.room-ticket__status {
  font-family: var(--gg-font-mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  padding: 3px 7px;
  border: 1px solid var(--gg-border-strong);
  color: var(--gg-ink-3);
  background: var(--gg-surface-2);
  white-space: nowrap;
}

.room-ticket__status[data-status='waiting'] {
  color: var(--gg-green);
  border-color: rgba(63, 102, 78, 0.4);
  background: var(--gg-green-soft);
}

.room-ticket__status[data-status='playing'] {
  color: var(--gg-gold-strong);
  border-color: rgba(168, 121, 42, 0.45);
  background: var(--gg-gold-soft);
}

.room-ticket__go {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-align: right;
  color: var(--gg-brand);
}

.room-ticket--locked .room-ticket__go {
  color: var(--gg-ink-4);
}

/* ── 侧栏 ── */
.lobby__aside {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.pass,
.rules {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  background: var(--gg-surface);
  border: 1px solid var(--gg-border-strong);
  box-shadow: var(--gg-shadow-1);
}

.pass__id,
.pass__guest {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: var(--gg-grad-night);
  border: 1px solid #16130f;
  color: #f2ead9;
}

.pass__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  object-fit: cover;
  flex: 0 0 auto;
  background: var(--gg-surface);
  border: 1px solid var(--gg-border-strong);
  color: var(--gg-brand);
  font-family: var(--gg-font-display);
  font-size: 16px;
  font-weight: 700;
}

.pass__guest-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  border: 1px dashed rgba(242, 234, 217, 0.5);
  color: rgba(242, 234, 217, 0.7);
  font-family: var(--gg-font-display);
  font-size: 17px;
}

.pass__id-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.pass__name {
  font-size: 13.5px;
  color: #fdf7ea;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pass__uid {
  font-family: var(--gg-font-mono);
  font-size: 9.5px;
  letter-spacing: 0.14em;
  color: rgba(242, 234, 217, 0.5);
}

.pass__hint {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--gg-ink-3);
}

.pass__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pass__actions :deep(.el-button) {
  flex: 1 1 96px;
  margin-left: 0;
}

.rules__list {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.rules__list li {
  display: flex;
  gap: 9px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--gg-ink-2);
  padding-bottom: 7px;
  border-bottom: 1px dotted var(--gg-border);
}

.rules__list li:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.rules__list span {
  font-family: var(--gg-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.14em;
  color: var(--gg-gold-strong);
}

/* ── 页脚 ── */
.lobby__foot {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--gg-border-strong);
  font-size: 11.5px;
  color: var(--gg-ink-3);
}

.lobby__foot-note {
  margin-left: auto;
  font-family: var(--gg-font-mono);
  font-size: 10px;
  letter-spacing: 0.12em;
}

@media (max-width: 960px) {
  .lobby {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto;
    gap: 14px;
    padding: 16px 14px 20px;
    min-height: 0;
  }

  .lobby__masthead {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .lobby__masthead-stats {
    width: 100%;
    justify-content: space-between;
  }

  .lobby__stat {
    align-items: flex-start;
  }

  .lobby__toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .lobby__toolbar-actions :deep(.el-button) {
    flex: 1 1 auto;
    margin-left: 0;
  }

  .lobby__foot {
    flex-wrap: wrap;
  }

  .lobby__foot-note {
    margin-left: 0;
  }
}

@media (max-width: 640px) {
  .lobby__empty-actions {
    flex-direction: column;
    width: 100%;
  }

  .lobby__empty-actions :deep(.el-button) {
    width: 100%;
    margin-left: 0;
  }

  .room-ticket {
    grid-template-columns: 64px minmax(0, 1fr);
    row-gap: 6px;
  }

  .room-ticket__status,
  .room-ticket__go {
    grid-column: 2;
    justify-self: start;
    text-align: left;
  }
}
</style>
