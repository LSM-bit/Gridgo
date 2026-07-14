<template>
  <div class="profile-page">
    <el-container style="height: 100vh">
      <!-- 顶栏 -->
      <el-header>
        <div class="flex-between w-full h-full">
          <div class="flex items-center gap-3">
            <el-button text @click="$router.push('/')">
              <el-icon><ArrowLeft /></el-icon>
              返回
            </el-button>
            <span class="text-lg font-bold">👤 个人中心</span>
          </div>
        </div>
      </el-header>

      <el-main v-loading="loading">
        <el-row :gutter="20" class="profile-body">
          <!-- 左侧：个人信息卡片 -->
          <el-col :span="8">
            <el-card class="profile-card">
              <div class="profile-avatar-section">
                <el-avatar :size="80" :src="profile?.avatar || undefined">
                  {{ profile?.nickname?.charAt(0) || '?' }}
                </el-avatar>
                <h2 class="profile-nickname">{{ profile?.nickname || '—' }}</h2>
                <p class="profile-username">@{{ profile?.username || '—' }}</p>
                <el-tag v-if="profile?.status === 0" type="success" size="small">正常</el-tag>
                <el-tag v-else type="danger" size="small">已禁用</el-tag>
              </div>

              <el-divider />

              <!-- 统计数据 -->
              <div v-if="stats" class="stats-grid">
                <div class="stat-item">
                  <span class="stat-value">{{ stats.total_games }}</span>
                  <span class="stat-label">总局数</span>
                </div>
                <div class="stat-item">
                  <span class="stat-value stat-win">{{ stats.wins }}</span>
                  <span class="stat-label">胜场</span>
                </div>
                <div class="stat-item">
                  <span class="stat-value">{{ winRate }}%</span>
                  <span class="stat-label">胜率</span>
                </div>
                <div class="stat-item">
                  <span class="stat-value">{{ stats.avg_rank }}</span>
                  <span class="stat-label">平均排名</span>
                </div>
                <div class="stat-item">
                  <span class="stat-value stat-money">¥{{ formatNumber(stats.total_assets) }}</span>
                  <span class="stat-label">总资产</span>
                </div>
                <div class="stat-item">
                  <span class="stat-value" :class="{ 'stat-bankrupt': stats.bankruptcies > 0 }">{{ stats.bankruptcies }}</span>
                  <span class="stat-label">破产</span>
                </div>
              </div>
              <div v-else class="text-center text-gray-400 text-sm">暂无统计数据</div>

              <el-divider />

              <!-- 注册时间 -->
              <div class="profile-meta">
                <p>📅 注册时间：{{ formatDate(profile?.created_at) }}</p>
                <p>📧 邮箱：{{ profile?.email || '未设置' }}</p>
              </div>

              <el-divider />

              <!-- 操作按钮 -->
              <div class="flex-col gap-2">
                <el-button size="large" class="w-full" @click="showEditDialog = true">
                  ✏️ 修改资料
                </el-button>
                <el-button size="large" class="w-full" @click="showPasswordDialog = true">
                  🔒 修改密码
                </el-button>
              </div>
            </el-card>
          </el-col>

          <!-- 右侧：对局记录 -->
          <el-col :span="16">
            <el-card class="records-card">
              <template #header>
                <div class="flex-between">
                  <span>🏆 对局记录</span>
                  <el-tag v-if="stats" type="info" size="small">共 {{ stats.total_games }} 局</el-tag>
                </div>
              </template>

              <div v-if="records.length === 0 && !recordsLoading" class="records-empty">
                <p>🎮 还没有对局记录</p>
                <p class="text-gray-400 text-sm">快去开始一局游戏吧！</p>
              </div>

              <div v-else class="records-list">
                <div
                  v-for="record in records"
                  :key="record.id"
                  class="record-item"
                  :class="{ 'record-win': record.my_rank === 1, 'record-bankrupt': record.my_is_bankrupt }"
                  @click="handleViewDetail(record)"
                >
                  <div class="record-left">
                    <div class="record-rank">
                      <span v-if="record.my_rank === 1" class="rank-badge rank-1">🥇</span>
                      <span v-else-if="record.my_rank === 2" class="rank-badge rank-2">🥈</span>
                      <span v-else-if="record.my_rank === 3" class="rank-badge rank-3">🥉</span>
                      <span v-else class="rank-badge rank-other">#{{ record.my_rank }}</span>
                    </div>
                    <div class="record-info">
                      <div class="record-title">
                        <span>{{ mapLabel(record.map_id) }}</span>
                        <el-tag size="small" :type="endReasonType(record.end_reason)">{{ endReasonLabel(record.end_reason) }}</el-tag>
                      </div>
                      <div class="record-meta">
                        <span>{{ record.player_count }}人</span>
                        <span>·</span>
                        <span>{{ record.total_turns }}回合</span>
                        <span>·</span>
                        <span>🏆 {{ record.winner_nickname || '—' }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="record-right">
                    <div class="record-assets">¥{{ formatNumber(record.my_total_assets ?? 0) }}</div>
                    <div class="record-date">{{ formatDate(record.created_at) }}</div>
                    <el-tag v-if="record.my_is_bankrupt" type="danger" size="small">破产</el-tag>
                  </div>
                </div>

                <!-- 加载更多 -->
                <div v-if="hasMoreRecords" class="load-more-records">
                  <el-button text :loading="recordsLoading" @click="loadMoreRecords">加载更多</el-button>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>

    <!-- 修改资料对话框 -->
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

    <!-- 修改密码对话框 -->
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

    <!-- 对局详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="对局详情" width="560px">
      <div v-if="detailLoading" class="text-center py-8">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      </div>
      <div v-else-if="recordDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="地图">{{ mapLabel(recordDetail.map_id) }}</el-descriptions-item>
          <el-descriptions-item label="回合数">{{ recordDetail.total_turns }}</el-descriptions-item>
          <el-descriptions-item label="玩家数">{{ recordDetail.player_count }}</el-descriptions-item>
          <el-descriptions-item label="结束原因">{{ endReasonLabel(recordDetail.end_reason) }}</el-descriptions-item>
          <el-descriptions-item label="日期" :span="2">{{ formatDate(recordDetail.created_at) }}</el-descriptions-item>
        </el-descriptions>

        <h4 class="mt-4 mb-2">玩家排名</h4>
        <div class="detail-players">
          <div
            v-for="p in recordDetail.players"
            :key="p.user_id"
            class="detail-player-row"
            :class="{ 'detail-player-me': p.user_id === userStore.userId }"
          >
            <span class="detail-rank">
              {{ ['🥇', '🥈', '🥉'][p.rank - 1] || `#${p.rank}` }}
            </span>
            <span class="detail-name">
              {{ p.is_ai ? '🤖 ' : '' }}{{ p.nickname }}
              <el-tag v-if="p.user_id === userStore.userId" type="primary" size="small">我</el-tag>
            </span>
            <span class="detail-assets">¥{{ formatNumber(p.total_assets) }}</span>
            <el-tag v-if="p.is_bankrupt" type="danger" size="small">破产</el-tag>
          </div>
        </div>

        <!-- 查看回放按钮 -->
        <div class="mt-4 text-center">
          <el-button type="primary" @click="goToReplay(recordDetail!.id)">
            🎬 查看回放
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Loading } from '@element-plus/icons-vue'
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
  loading.value = true
  await Promise.all([fetchProfile(), fetchStats(), fetchRecords()])
  loading.value = false

  // 打开修改资料弹窗时预填数据
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
  width: 100%;
  height: 100%;
  background: #f5f7fa;
}

.profile-body {
  height: calc(100vh - 80px);
}

/* 覆盖 Element Plus .el-button+.el-button 的默认 margin-left: 12px，
   避免在 flex-col 布局中按钮错位 */
.flex-col > .el-button + .el-button {
  margin-left: 0;
}

/* 个人信息卡片 */
.profile-card {
  text-align: center;
}

.profile-avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 0;
}

.profile-nickname {
  font-size: 22px;
  font-weight: 700;
  margin: 4px 0 0;
  color: #303133;
}

.profile-username {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

/* 统计数据 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 4px;
  border-radius: 8px;
  background: #f5f7fa;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
}

.stat-win {
  color: #67c23a;
}

.stat-money {
  font-size: 14px;
  color: #e6a23c;
}

.stat-bankrupt {
  color: #f56c6c;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

/* 元信息 */
.profile-meta {
  text-align: left;
  font-size: 13px;
  color: #606266;
}

.profile-meta p {
  margin: 4px 0;
}

/* 对局记录 */
.records-card {
  height: 100%;
}

.records-card :deep(.el-card__body) {
  max-height: calc(100vh - 160px);
  overflow-y: auto;
}

.records-empty {
  text-align: center;
  padding: 60px 0;
  color: #909399;
  font-size: 16px;
}

.records-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.record-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: 10px;
  background: #f9f9f9;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.record-item:hover {
  background: #ecf5ff;
  border-color: #409eff;
}

.record-item.record-win {
  background: linear-gradient(135deg, #f0f9eb, #e1f3d8);
  border-left: 4px solid #67c23a;
}

.record-item.record-bankrupt {
  background: linear-gradient(135deg, #fef0f0, #fde2e2);
  border-left: 4px solid #f56c6c;
}

.record-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.record-rank {
  min-width: 36px;
  text-align: center;
}

.rank-badge {
  font-size: 20px;
  font-weight: 700;
}

.rank-badge.rank-other {
  font-size: 14px;
  color: #909399;
}

.record-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.record-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
}

.record-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 4px;
}

.record-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.record-assets {
  font-weight: 700;
  color: #e6a23c;
  font-size: 14px;
}

.record-date {
  font-size: 12px;
  color: #c0c4cc;
}

.load-more-records {
  text-align: center;
  padding: 12px 0;
}

/* 对局详情 */
.detail-players {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-player-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 6px;
  background: #f5f7fa;
}

.detail-player-row.detail-player-me {
  background: #ecf5ff;
  border: 1px solid #409eff;
}

.detail-rank {
  font-size: 18px;
  min-width: 28px;
  text-align: center;
}

.detail-name {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
}

.detail-assets {
  font-weight: 600;
  color: #e6a23c;
  font-size: 14px;
}
</style>
