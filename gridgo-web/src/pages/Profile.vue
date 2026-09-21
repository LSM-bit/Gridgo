<template>
  <DefaultLayout title="个人中心">
    <template #actions>
      <el-button size="small" :loading="loading" @click="refreshAll">刷新</el-button>
      <el-button size="small" @click="openEditDialog">修改资料</el-button>
      <el-button size="small" @click="openPasswordDialog">修改密码</el-button>
    </template>

    <div class="profile-page">
      <PageHeader title="个人中心" subtitle="账号资料 · 战绩统计 · 对局记录" icon="◈" />

      <div class="profile-grid">
        <!-- 身份卡 -->
        <section class="profile-panel">
          <header class="profile-panel__head">
            <span class="gg-kicker">PLAYER · 身份卡</span>
            <span class="profile-panel__meta">{{ profile?.status === 0 ? '正常' : '已禁用' }}</span>
          </header>
          <div class="profile-panel__body">
            <div class="id-card">
              <span class="id-card__avatar">
                <img v-if="profile?.avatar" :src="profile.avatar" alt="" />
                <span v-else>{{ (profile?.nickname || '?').charAt(0) }}</span>
              </span>
              <span class="id-card__text">
                <b class="id-card__name">{{ profile?.nickname || '—' }}</b>
                <span class="id-card__username">@{{ profile?.username || '—' }}</span>
              </span>
            </div>

            <dl class="info-grid">
              <div class="info-grid__row">
                <dt>用户 ID</dt>
                <dd class="gg-num">{{ userStore.userId ?? '—' }}</dd>
              </div>
              <div class="info-grid__row">
                <dt>注册时间</dt>
                <dd>{{ formatDate(profile?.created_at) }}</dd>
              </div>
              <div class="info-grid__row">
                <dt>邮箱</dt>
                <dd>{{ profile?.email || '未设置' }}</dd>
              </div>
            </dl>

            <div class="id-card__ops">
              <el-button class="ops-btn" @click="openEditDialog">修改资料</el-button>
              <el-button class="ops-btn" @click="openPasswordDialog">修改密码</el-button>
            </div>
          </div>
        </section>

        <!-- 战绩统计 -->
        <section class="profile-panel">
          <header class="profile-panel__head">
            <span class="gg-kicker">STATS · 战绩统计</span>
            <span class="profile-panel__meta gg-num">{{ stats?.total_games ?? 0 }} 局</span>
          </header>
          <div class="profile-panel__body">
            <div v-if="stats" class="stat-grid">
              <div class="stat">
                <span class="stat__num gg-num">{{ stats.total_games }}</span>
                <span class="stat__label">总局数</span>
              </div>
              <div class="stat">
                <span class="stat__num gg-num">{{ stats.wins }}</span>
                <span class="stat__label">胜场</span>
              </div>
              <div class="stat">
                <span class="stat__num gg-num">{{ winRate }}%</span>
                <span class="stat__label">胜率</span>
              </div>
              <div class="stat">
                <span class="stat__num gg-num">{{ stats.avg_rank }}</span>
                <span class="stat__label">平均排名</span>
              </div>
              <div class="stat">
                <span class="stat__num gg-num">¥{{ formatNumber(stats.total_assets) }}</span>
                <span class="stat__label">总资产</span>
              </div>
              <div class="stat">
                <span class="stat__num gg-num">{{ stats.bankruptcies }}</span>
                <span class="stat__label">破产次数</span>
              </div>
            </div>
            <div v-else class="panel-empty">暂无统计数据，完成一局对局后生成</div>
          </div>
        </section>

        <!-- 对局记录 -->
        <section class="profile-panel profile-panel--wide">
          <header class="profile-panel__head">
            <span class="gg-kicker">RECORDS · 对局记录</span>
            <span class="profile-panel__meta gg-num">
              {{ records.length }}{{ hasMoreRecords ? '+' : '' }} 条
            </span>
          </header>

          <div class="profile-panel__body" v-loading="recordsLoading">
            <EmptyState
              v-if="records.length === 0 && !recordsLoading"
              description="还没有对局记录，去大厅开一局吧"
            >
              <el-button size="small" type="primary" @click="router.push('/')">前往大厅</el-button>
            </EmptyState>

            <div v-else class="record-list">
              <div
                v-for="record in records"
                :key="record.id"
                class="record-row"
                :class="{
                  'record-row--win': record.my_rank === 1,
                  'record-row--bankrupt': record.my_is_bankrupt,
                }"
                @click="handleViewDetail(record)"
              >
                <span class="record-row__rank gg-num">{{ pad(record.my_rank) }}</span>
                <span class="record-row__info">
                  <span class="record-row__title">
                    <b>{{ mapLabel(record.map_id) }}</b>
                    <el-tag size="small" :type="endReasonType(record.end_reason)">
                      {{ endReasonLabel(record.end_reason) }}
                    </el-tag>
                    <el-tag v-if="record.my_is_bankrupt" type="danger" size="small">破产</el-tag>
                  </span>
                  <span class="record-row__meta">
                    {{ record.player_count }} 人 · {{ record.total_turns }} 回合 · 冠军
                    {{ record.winner_nickname || '—' }}
                  </span>
                </span>
                <span class="record-row__right">
                  <span class="record-row__assets gg-num">¥{{ formatNumber(record.my_total_assets ?? 0) }}</span>
                  <span class="record-row__date gg-num">{{ formatDate(record.created_at) }}</span>
                </span>
              </div>

              <div v-if="hasMoreRecords" class="record-more">
                <el-button text :loading="recordsLoading" @click="loadMoreRecords">加载更多</el-button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- 修改资料 -->
    <el-dialog v-model="showEditDialog" title="修改资料" width="480px" :close-on-click-modal="false">
      <el-form :model="editForm" label-width="80px" label-position="left">
        <el-form-item label="昵称">
          <el-input v-model="editForm.nickname" placeholder="请输入昵称" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="头像URL">
          <el-input v-model="editForm.avatar" placeholder="请输入头像图片URL" maxlength="255" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" placeholder="请输入邮箱地址" maxlength="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="handleSaveProfile">保存</el-button>
      </template>
    </el-dialog>

    <!-- 修改密码 -->
    <el-dialog v-model="showPasswordDialog" title="修改密码" width="480px" :close-on-click-modal="false">
      <el-form :model="passwordForm" label-width="80px" label-position="left">
        <el-form-item label="旧密码">
          <el-input v-model="passwordForm.old_password" type="password" placeholder="请输入旧密码" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.new_password" type="password" placeholder="请输入新密码（至少6位）" show-password />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="passwordForm.confirm_password" type="password" placeholder="请再次输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPasswordDialog = false">取消</el-button>
        <el-button type="primary" :loading="passwordLoading" @click="handleChangePassword">确认修改</el-button>
      </template>
    </el-dialog>

    <!-- 对局详情 -->
    <el-dialog v-model="showDetailDialog" title="对局详情" width="560px">
      <div v-if="detailLoading" class="detail-loading">加载中…</div>
      <div v-else-if="recordDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="地图">{{ mapLabel(recordDetail.map_id) }}</el-descriptions-item>
          <el-descriptions-item label="回合数">{{ recordDetail.total_turns }}</el-descriptions-item>
          <el-descriptions-item label="玩家数">{{ recordDetail.player_count }}</el-descriptions-item>
          <el-descriptions-item label="结束原因">{{ endReasonLabel(recordDetail.end_reason) }}</el-descriptions-item>
          <el-descriptions-item label="日期" :span="2">{{ formatDate(recordDetail.created_at) }}</el-descriptions-item>
        </el-descriptions>

        <h4 class="detail-title">玩家排名</h4>
        <div class="detail-players">
          <div
            v-for="p in recordDetail.players"
            :key="p.user_id"
            class="detail-player-row"
            :class="{ 'detail-player-me': p.user_id === userStore.userId }"
          >
            <span class="detail-rank gg-num">{{ pad(p.rank) }}</span>
            <span class="detail-name">
              {{ p.is_ai ? 'AI · ' : '' }}{{ p.nickname }}
              <el-tag v-if="p.user_id === userStore.userId" type="primary" size="small">我</el-tag>
            </span>
            <span class="detail-assets gg-num">¥{{ formatNumber(p.total_assets) }}</span>
            <el-tag v-if="p.is_bankrupt" type="danger" size="small">破产</el-tag>
          </div>
        </div>

        <div class="detail-foot">
          <el-button type="primary" @click="goToReplay(recordDetail!.id)">查看回放</el-button>
        </div>
      </div>
    </el-dialog>
  </DefaultLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { PageHeader, EmptyState } from '@/components/common'
import { useUserStore } from '@/stores/user'
import {
  getMyProfile,
  updateMyProfile,
  changePassword,
  getMyStats,
  getMyRecords,
  getGameRecordDetail,
} from '@/api/user'
import type { UserProfile, UserStats, GameRecordItem, GameRecordDetail } from '@/api/user'
import { MAP_OPTIONS } from '@/api/room'

const userStore = useUserStore()
const router = useRouter()

const loading = ref(true)
const profile = ref<UserProfile | null>(null)
const stats = ref<UserStats | null>(null)

// ─── 对局记录 ───

const records = ref<GameRecordItem[]>([])
const recordsLoading = ref(false)
const recordsOffset = ref(0)
const hasMoreRecords = ref(true)
const RECORDS_PAGE_SIZE = 20

// ─── 修改资料 ───

const showEditDialog = ref(false)
const editLoading = ref(false)
const editForm = ref({
  nickname: '',
  avatar: '',
  email: '',
})

// ─── 修改密码 ───

const showPasswordDialog = ref(false)
const passwordLoading = ref(false)
const passwordForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

// ─── 对局详情 ───

const showDetailDialog = ref(false)
const detailLoading = ref(false)
const recordDetail = ref<GameRecordDetail | null>(null)

// ─── 计算属性 ───

const winRate = computed(() => {
  if (!stats.value || stats.value.total_games === 0) return 0
  return Math.round((stats.value.wins / stats.value.total_games) * 100)
})

// ─── 辅助方法 ───

const pad = (value: number) => String(value).padStart(2, '0')

const mapLabel = (mapId: string) => {
  const found = MAP_OPTIONS.find((m) => m.value === mapId)
  return found?.label ?? mapId
}

const endReasonLabel = (reason: string) => {
  const map: Record<string, string> = {
    last_standing: '仅剩一人',
    turn_limit: '回合上限',
    vote_end: '投票结束',
  }
  return map[reason] ?? reason
}

const endReasonType = (reason: string) => {
  const map: Record<string, string> = {
    last_standing: 'danger',
    turn_limit: 'warning',
    vote_end: 'info',
  }
  return (map[reason] ?? 'info') as any
}

const formatDate = (isoStr: string | null | undefined) => {
  if (!isoStr) return '—'
  try {
    const d = new Date(isoStr)
    return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
  } catch {
    return isoStr
  }
}

const formatNumber = (num: number) => {
  return num.toLocaleString('zh-CN')
}

// ─── 数据加载 ───

const fetchProfile = async () => {
  try {
    profile.value = await getMyProfile()
  } catch {
    ElMessage.error('获取用户信息失败')
  }
}

const fetchStats = async () => {
  try {
    stats.value = await getMyStats()
  } catch {
    // 静默
  }
}

const fetchRecords = async (append = false) => {
  recordsLoading.value = true
  try {
    const data = await getMyRecords(RECORDS_PAGE_SIZE, recordsOffset.value)
    if (append) {
      records.value.push(...data)
    } else {
      records.value = data
    }
    hasMoreRecords.value = data.length >= RECORDS_PAGE_SIZE
    recordsOffset.value += data.length
  } catch {
    // 静默
  } finally {
    recordsLoading.value = false
  }
}

const loadMoreRecords = () => {
  fetchRecords(true)
}

const refreshAll = async () => {
  loading.value = true
  await Promise.all([fetchProfile(), fetchStats(), fetchRecords()])
  loading.value = false
}

// ─── 弹窗入口 ───

const openEditDialog = () => {
  editForm.value = {
    nickname: profile.value?.nickname ?? '',
    avatar: profile.value?.avatar ?? '',
    email: profile.value?.email ?? '',
  }
  showEditDialog.value = true
}

const openPasswordDialog = () => {
  passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
  showPasswordDialog.value = true
}

// ─── 修改资料 ───

const handleSaveProfile = async () => {
  editLoading.value = true
  try {
    const data: Record<string, string> = {}
    if (editForm.value.nickname && editForm.value.nickname !== profile.value?.nickname) {
      data.nickname = editForm.value.nickname
    }
    if (editForm.value.avatar !== (profile.value?.avatar ?? '')) {
      data.avatar = editForm.value.avatar
    }
    if (editForm.value.email !== (profile.value?.email ?? '')) {
      data.email = editForm.value.email
    }

    if (Object.keys(data).length === 0) {
      ElMessage.info('没有修改')
      showEditDialog.value = false
      return
    }

    const updated = await updateMyProfile(data)
    profile.value = updated
    // 同步更新 userStore
    userStore.setUserInfo({
      token: userStore.token,
      refreshToken: userStore.refreshToken,
      userId: userStore.userId,
      username: userStore.username,
      nickname: updated.nickname,
      avatar: updated.avatar ?? '',
    })
    ElMessage.success('资料修改成功')
    showEditDialog.value = false
  } catch (err: any) {
    const msg = err.response?.data?.detail || err.message || '修改失败'
    ElMessage.error(msg)
  } finally {
    editLoading.value = false
  }
}

// ─── 修改密码 ───

const handleChangePassword = async () => {
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    ElMessage.error('两次输入的密码不一致')
    return
  }
  if (passwordForm.value.new_password.length < 6) {
    ElMessage.error('新密码至少6位')
    return
  }

  passwordLoading.value = true
  try {
    await changePassword({
      old_password: passwordForm.value.old_password,
      new_password: passwordForm.value.new_password,
    })
    ElMessage.success('密码修改成功')
    showPasswordDialog.value = false
    passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
  } catch (err: any) {
    const msg = err.response?.data?.detail || err.message || '修改密码失败'
    ElMessage.error(msg)
  } finally {
    passwordLoading.value = false
  }
}

// ─── 对局详情 ───

const handleViewDetail = async (record: GameRecordItem) => {
  showDetailDialog.value = true
  detailLoading.value = true
  recordDetail.value = null
  try {
    recordDetail.value = await getGameRecordDetail(record.id)
  } catch (err: any) {
    ElMessage.error('获取对局详情失败')
  } finally {
    detailLoading.value = false
  }
}

const goToReplay = (gameId: number) => {
  showDetailDialog.value = false
  router.push({ name: 'Replay', params: { id: gameId } })
}

// ─── 生命周期 ───

onMounted(async () => {
  await refreshAll()
  if (profile.value) {
    editForm.value = {
      nickname: profile.value.nickname,
      avatar: profile.value.avatar ?? '',
      email: profile.value.email ?? '',
    }
  }
})
</script>

<style scoped>
.profile-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 100%;
  max-width: 1240px;
  min-height: calc(100vh - var(--gg-shell-bar));
  margin: 0 auto;
  padding: var(--gg-page-pad) var(--gg-page-pad) 16px;
  box-sizing: border-box;
  animation: gg-fade-up var(--gg-dur-slow) var(--gg-ease-out) both;
}

.profile-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.25fr);
  gap: 14px;
  flex: 1 1 auto;
  min-height: 0;
}

.profile-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--gg-surface);
  border: 1px solid var(--gg-border-strong);
  box-shadow: var(--gg-shadow-1);
}

.profile-panel--wide {
  grid-column: 1 / -1;
}

.profile-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  background: var(--gg-surface-2);
  border-bottom: 1px dashed var(--gg-border-strong);
}

.profile-panel__meta {
  font-family: var(--gg-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.12em;
  color: var(--gg-ink-3);
}

.profile-panel__body {
  padding: 14px;
}

/* ── 身份卡 ── */
.id-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px;
  background: var(--gg-grad-night);
  color: #f2ead9;
  border: 1px solid #16130f;
}

.id-card__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 54px;
  height: 54px;
  flex: 0 0 auto;
  overflow: hidden;
  background: var(--gg-surface);
  border: 1px solid var(--gg-border-strong);
  color: var(--gg-brand);
  font-family: var(--gg-font-display);
  font-size: 22px;
  font-weight: 700;
}

.id-card__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.id-card__text {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.id-card__name {
  font-family: var(--gg-font-display);
  font-size: 18px;
  color: #fdf7ea;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.id-card__username {
  font-family: var(--gg-font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  color: rgba(242, 234, 217, 0.58);
}

.info-grid {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin: 14px 0 0;
}

.info-grid__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px dotted var(--gg-border-strong);
}

.info-grid__row dt {
  font-size: 11.5px;
  letter-spacing: 0.08em;
  color: var(--gg-ink-3);
  white-space: nowrap;
}

.info-grid__row dd {
  margin: 0;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--gg-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.id-card__ops {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

.ops-btn {
  flex: 1 1 0;
  margin-left: 0;
}

/* ── 统计 ── */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border);
}

.stat__num {
  font-family: var(--gg-font-display);
  font-size: 20px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--gg-ink);
}

.stat__label {
  font-family: var(--gg-font-mono);
  font-size: 9.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--gg-ink-3);
}

.panel-empty {
  padding: 26px 12px;
  text-align: center;
  font-size: 12.5px;
  color: var(--gg-ink-4);
  border: 1px dashed var(--gg-border-strong);
}

/* ── 记录 ── */
.record-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.record-row {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border);
  border-left: 2px solid var(--gg-border-strong);
  cursor: pointer;
  transition: transform var(--gg-dur) var(--gg-ease), box-shadow var(--gg-dur) var(--gg-ease),
    border-color var(--gg-dur) var(--gg-ease), background-color var(--gg-dur) var(--gg-ease);
  animation: gg-fade-up var(--gg-dur) var(--gg-ease-out) both;
}

.record-row:hover {
  transform: translateX(2px);
  background: var(--gg-surface);
  border-left-color: var(--gg-brand);
  box-shadow: var(--gg-shadow-1);
}

.record-row--win {
  border-left-color: var(--gg-gold-strong);
}

.record-row--bankrupt {
  opacity: 0.78;
}

.record-row__rank {
  font-family: var(--gg-font-mono);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--gg-ink-2);
  text-align: center;
}

.record-row__info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.record-row__title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  font-size: 13.5px;
  color: var(--gg-ink);
}

.record-row__meta {
  font-size: 11.5px;
  color: var(--gg-ink-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-row__right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 3px;
  flex: 0 0 auto;
}

.record-row__assets {
  font-size: 13px;
  font-weight: 700;
  color: var(--gg-gold-strong);
}

.record-row__date {
  font-size: 10.5px;
  color: var(--gg-ink-4);
}

.record-more {
  padding-top: 4px;
  text-align: center;
}

/* ── 详情弹窗 ── */
.detail-loading {
  padding: 26px 0;
  text-align: center;
  font-size: 12.5px;
  color: var(--gg-ink-3);
}

.detail-title {
  margin: 18px 0 8px;
  font-size: 13.5px;
  color: var(--gg-ink);
}

.detail-players {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.detail-player-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border);
}

.detail-player-me {
  background: var(--gg-brand-soft);
  border-color: rgba(176, 57, 44, 0.35);
}

.detail-rank {
  flex: 0 0 30px;
  font-family: var(--gg-font-mono);
  font-weight: 700;
  color: var(--gg-ink-2);
}

.detail-name {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--gg-ink);
}

.detail-assets {
  font-size: 13px;
  font-weight: 600;
  color: var(--gg-gold-strong);
}

.detail-foot {
  margin-top: 16px;
  text-align: center;
}

@media (max-width: 960px) {
  .profile-page {
    padding: 16px 14px 20px;
    min-height: 0;
  }

  .profile-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .profile-panel--wide {
    grid-column: auto;
  }
}

@media (max-width: 640px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .record-row {
    grid-template-columns: 34px minmax(0, 1fr);
    row-gap: 6px;
  }

  .record-row__right {
    grid-column: 2;
    align-items: flex-start;
    flex-direction: row;
    gap: 10px;
  }

  .id-card__ops {
    flex-direction: column;
  }
}
</style>
