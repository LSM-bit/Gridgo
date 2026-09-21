<template>
  <DefaultLayout title="好友">
    <template #actions>
      <el-input v-model="targetId" placeholder="对方用户 ID" class="friends-page__id-input" />
      <el-button type="primary" :loading="adding" @click="handleAdd">添加好友</el-button>
      <el-button :loading="loading" @click="reload">刷新</el-button>
    </template>

    <div class="friends-page">
      <PageHeader title="好友" subtitle="管理好友与好友申请" icon="◎" />

      <div class="friends-summary">
        <div class="friends-summary__cell">
          <span class="friends-summary__num gg-num">{{ friends.length }}</span>
          <span class="friends-summary__label">好友总数</span>
        </div>
        <div class="friends-summary__cell">
          <span class="friends-summary__num gg-num">{{ requests.length }}</span>
          <span class="friends-summary__label">待处理申请</span>
        </div>
        <div class="friends-summary__cell">
          <span class="friends-summary__num gg-num">{{ acceptedCount }}</span>
          <span class="friends-summary__label">可直接交易</span>
        </div>
        <div class="friends-summary__hint">
          添加好友需要对方的用户 ID（可在个人中心查看自己的 ID）
        </div>
      </div>

      <div class="friends-grid">
        <!-- 好友列表 -->
        <section class="friends-panel">
          <header class="friends-panel__head">
            <span class="gg-kicker">FRIENDS · 好友列表</span>
            <el-tag size="small" type="info">{{ friends.length }}</el-tag>
          </header>

          <div class="friends-panel__body" v-loading="loading">
            <EmptyState
              v-if="!loading && friends.length === 0"
              description="还没有好友，在上方输入对方用户 ID 添加"
            />

            <div v-else class="friend-list">
              <div
                v-for="(friend, index) in friends"
                :key="friend.friendship_id"
                class="friend-row"
              >
                <span class="friend-row__idx">{{ pad(index + 1) }}</span>
                <span class="friend-row__info">
                  <span class="friend-row__name">{{ friend.nickname }}</span>
                  <span class="friend-row__meta">
                    @{{ friend.username }} · 积分 {{ friend.score }} · 胜率
                    {{ winRate(friend.total_games, friend.total_wins) }}
                  </span>
                </span>
                <el-button
                  type="danger"
                  plain
                  size="small"
                  :loading="removingId === friend.friendship_id"
                  @click="handleRemove(friend)"
                >
                  删除
                </el-button>
              </div>
            </div>
          </div>
        </section>

        <!-- 好友申请 -->
        <section class="friends-panel">
          <header class="friends-panel__head">
            <span class="gg-kicker">REQUESTS · 好友申请</span>
            <el-tag size="small" :type="requests.length ? 'warning' : 'info'">{{ requests.length }}</el-tag>
          </header>

          <div class="friends-panel__body" v-loading="loading">
            <EmptyState v-if="!loading && requests.length === 0" description="暂无待处理申请" />

            <div v-else class="friend-list">
              <div v-for="req in requests" :key="req.request_id" class="friend-row">
                <span class="friend-row__idx">{{ pad(req.user_id) }}</span>
                <span class="friend-row__info">
                  <span class="friend-row__name">{{ req.nickname }}</span>
                  <span class="friend-row__meta">@{{ req.username }} · 请求加你为好友</span>
                </span>
                <span class="friend-row__ops">
                  <el-button
                    type="primary"
                    size="small"
                    :loading="actingId === req.request_id"
                    @click="handleRespond(req, true)"
                  >
                    接受
                  </el-button>
                  <el-button
                    size="small"
                    :loading="actingId === req.request_id"
                    @click="handleRespond(req, false)"
                  >
                    拒绝
                  </el-button>
                </span>
              </div>
            </div>
          </div>
        </section>
      </div>

      <footer class="friends-foot">
        <span class="gg-stamp gg-stamp--ink">HOW TO</span>
        <ol class="friends-foot__steps">
          <li><span>01</span>在页面右上角输入对方的用户 ID</li>
          <li><span>02</span>点击「添加好友」发送申请</li>
          <li><span>03</span>对方接受后即可在对局中发起交易</li>
        </ol>
      </footer>
    </div>
  </DefaultLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { PageHeader, EmptyState } from '@/components/common'
import {
  getFriends,
  getFriendRequests,
  sendFriendRequest,
  respondFriendRequest,
  deleteFriend,
} from '@/api/friend'
import type { FriendItem, FriendRequestItem } from '@/api/friend'
import { winRate } from '@/utils/format'

const loading = ref(false)
const adding = ref(false)
const actingId = ref<number | null>(null)
const removingId = ref<number | null>(null)
const targetId = ref('')
const friends = ref<FriendItem[]>([])
const requests = ref<FriendRequestItem[]>([])

const acceptedCount = computed(() => friends.value.filter((friend) => friend.score >= 0).length)
const pad = (value: number) => String(value).padStart(2, '0')

const load = async () => {
  loading.value = true
  try {
    const [friendList, requestList] = await Promise.all([getFriends(), getFriendRequests()])
    friends.value = friendList ?? []
    requests.value = requestList ?? []
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || err.message || '加载好友数据失败')
  } finally {
    loading.value = false
  }
}

const reload = () => load()

const handleAdd = async () => {
  const id = Number(targetId.value.trim())
  if (!id) {
    ElMessage.warning('请输入有效的用户 ID')
    return
  }
  adding.value = true
  try {
    await sendFriendRequest(id)
    ElMessage.success('好友申请已发送')
    targetId.value = ''
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || err.message || '发送申请失败')
  } finally {
    adding.value = false
  }
}

const handleRespond = async (req: FriendRequestItem, accept: boolean) => {
  actingId.value = req.request_id
  try {
    await respondFriendRequest(req.request_id, accept)
    ElMessage.success(accept ? '已接受申请' : '已拒绝申请')
    await load()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || err.message || '处理申请失败')
  } finally {
    actingId.value = null
  }
}

const handleRemove = async (friend: FriendItem) => {
  try {
    await ElMessageBox.confirm(`确定删除好友「${friend.nickname}」吗？`, '删除好友', { type: 'warning' })
  } catch {
    return
  }
  removingId.value = friend.friendship_id
  try {
    await deleteFriend(friend.friendship_id)
    ElMessage.success('已删除好友')
    await load()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || err.message || '删除好友失败')
  } finally {
    removingId.value = null
  }
}

onMounted(load)
</script>

<style scoped>
.friends-page {
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

.friends-page__id-input {
  width: 132px;
}

/* ── 概览条 ── */
.friends-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 120px)) minmax(0, 1fr);
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border-strong);
}

.friends-summary__cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-right: 14px;
  border-right: 1px dotted var(--gg-border-strong);
}

.friends-summary__num {
  font-family: var(--gg-font-display);
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
  color: var(--gg-ink);
}

.friends-summary__label {
  font-family: var(--gg-font-mono);
  font-size: 9.5px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--gg-ink-3);
}

.friends-summary__hint {
  font-size: 12px;
  line-height: 1.6;
  color: var(--gg-ink-3);
  text-align: right;
}

/* ── 两栏面板 ── */
.friends-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
  gap: 14px;
  flex: 1 1 auto;
  min-height: 0;
}

.friends-panel {
  display: flex;
  flex-direction: column;
  min-height: 320px;
  background: var(--gg-surface);
  border: 1px solid var(--gg-border-strong);
  box-shadow: var(--gg-shadow-1);
}

.friends-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px dashed var(--gg-border-strong);
  background: var(--gg-surface-2);
}

.friends-panel__body {
  flex: 1 1 auto;
  padding: 12px 14px;
  min-height: 0;
}

.friend-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.friend-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border);
  border-left: 2px solid var(--gg-border-strong);
  transition: transform var(--gg-dur) var(--gg-ease), box-shadow var(--gg-dur) var(--gg-ease),
    border-color var(--gg-dur) var(--gg-ease), background-color var(--gg-dur) var(--gg-ease);
  animation: gg-fade-up var(--gg-dur) var(--gg-ease-out) both;
}

.friend-row:hover {
  transform: translateX(2px);
  background: var(--gg-surface);
  border-left-color: var(--gg-brand);
  box-shadow: var(--gg-shadow-1);
}

.friend-row__idx {
  flex: 0 0 auto;
  font-family: var(--gg-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.1em;
  color: var(--gg-ink-4);
}

.friend-row__info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex: 1 1 auto;
  min-width: 0;
}

.friend-row__name {
  font-size: 14px;
  font-weight: 700;
  color: var(--gg-ink);
}

.friend-row__meta {
  font-size: 11.5px;
  color: var(--gg-ink-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.friend-row__ops {
  display: flex;
  gap: 8px;
  flex: 0 0 auto;
}

/* ── 页脚指南 ── */
.friends-foot {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 16px;
  background: var(--gg-surface);
  border: 1px dashed var(--gg-border-strong);
}

.friends-foot__steps {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 22px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 12px;
  color: var(--gg-ink-2);
}

.friends-foot__steps li {
  display: flex;
  gap: 8px;
}

.friends-foot__steps span {
  font-family: var(--gg-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.14em;
  color: var(--gg-gold-strong);
}

@media (max-width: 960px) {
  .friends-page {
    padding: 16px 14px 20px;
    min-height: 0;
  }

  .friends-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .friends-summary {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .friends-summary__cell {
    padding-right: 10px;
  }

  .friends-summary__hint {
    grid-column: 1 / -1;
    text-align: left;
  }

  .friends-page__id-input {
    width: 118px;
  }
}

@media (max-width: 640px) {
  .friend-row {
    flex-wrap: wrap;
  }

  .friend-row__info {
    flex: 1 1 140px;
  }

  .friends-foot {
    flex-direction: column;
  }
}
</style>
