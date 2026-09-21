<template>
  <DefaultLayout title="排行榜">
    <template #actions>
      <el-button size="small" :loading="loading" @click="reload">刷新</el-button>
    </template>

    <div class="board-page">
      <PageHeader title="排行榜" subtitle="按积分排序的全局榜单" icon="◆" />

      <!-- 我的排名条 -->
      <div class="board-me">
        <template v-if="myEntry">
          <div class="board-me__cell">
            <span class="board-me__num gg-num">#{{ myEntry.rank }}</span>
            <span class="board-me__label">我的排名</span>
          </div>
          <div class="board-me__cell">
            <span class="board-me__num gg-num">{{ myEntry.score }}</span>
            <span class="board-me__label">积分</span>
          </div>
          <div class="board-me__cell">
            <span class="board-me__num gg-num">{{ myEntry.total_games }}</span>
            <span class="board-me__label">总对局</span>
          </div>
          <div class="board-me__cell">
            <span class="board-me__num gg-num">{{ myEntry.total_wins }}</span>
            <span class="board-me__label">胜场</span>
          </div>
          <div class="board-me__cell">
            <span class="board-me__num gg-num">{{ myEntry.win_streak }}</span>
            <span class="board-me__label">连胜</span>
          </div>
        </template>

        <div v-else class="board-me__empty">
          <span class="board-me__mark">◇</span>
          <span class="board-me__empty-text">你还没有上榜记录，完成一局对局即可进入榜单</span>
          <el-button size="small" type="primary" @click="router.push('/')">前往大厅</el-button>
        </div>
      </div>

      <!-- 榜单 -->
      <section class="board-panel">
        <header class="board-panel__head">
          <span class="gg-kicker">RANKING · 积分榜</span>
          <span class="board-panel__meta gg-num">
            第 {{ page }} 页 · 共 {{ totalCount }} 名玩家
          </span>
        </header>

        <div class="board-panel__body" v-loading="loading">
          <EmptyState
            v-if="!loading && items.length === 0"
            description="暂无榜单数据，完成对局后即可上榜"
          />

          <div v-else class="rank-table">
            <div class="rank-table__head">
              <span>名次</span>
              <span>玩家</span>
              <span>积分</span>
              <span>对局</span>
              <span>胜场</span>
              <span>胜率</span>
              <span>连胜</span>
            </div>

            <div
              v-for="row in items"
              :key="row.user_id"
              class="rank-table__row"
              :class="{ 'rank-table__row--me': row.user_id === userStore.userId }"
            >
              <span class="rank-table__pos gg-num" :class="{ 'rank-table__pos--top': row.rank <= 3 }">
                {{ pad(row.rank) }}
              </span>
              <span class="rank-table__player">
                <b class="rank-table__name">{{ row.nickname }}</b>
                <small class="rank-table__username">@{{ row.username }}</small>
              </span>
              <span class="rank-table__cell rank-table__cell--strong gg-num">{{ row.score }}</span>
              <span class="rank-table__cell gg-num">{{ row.total_games }}</span>
              <span class="rank-table__cell gg-num">{{ row.total_wins }}</span>
              <span class="rank-table__cell gg-num">{{ winRate(row.total_games, row.total_wins) }}</span>
              <span class="rank-table__cell gg-num">{{ row.win_streak }}</span>
            </div>
          </div>
        </div>

        <footer class="board-pager">
          <el-button size="small" :disabled="offset === 0" @click="prevPage">上一页</el-button>
          <span class="board-pager__info gg-num">
            {{ rangeText }}
          </span>
          <el-button size="small" :disabled="!hasNext" @click="nextPage">下一页</el-button>
        </footer>
      </section>
    </div>
  </DefaultLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { PageHeader, EmptyState } from '@/components/common'
import { getLeaderboard } from '@/api/leaderboard'
import type { LeaderboardEntry } from '@/api/leaderboard'
import { useUserStore } from '@/stores/user'
import { winRate } from '@/utils/format'

const PAGE_SIZE = 20

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const items = ref<LeaderboardEntry[]>([])
const totalCount = ref(0)
const offset = ref(0)

const page = computed(() => Math.floor(offset.value / PAGE_SIZE) + 1)
const hasNext = computed(() => offset.value + PAGE_SIZE < totalCount.value)
const myEntry = computed(() => items.value.find((item) => item.user_id === userStore.userId) ?? null)
const rangeText = computed(() => {
  if (totalCount.value === 0) return '暂无排名数据'
  const from = offset.value + 1
  const to = offset.value + items.value.length
  return `${from}–${to} / ${totalCount.value}`
})

const pad = (value: number) => String(value).padStart(2, '0')

const load = async () => {
  loading.value = true
  try {
    const res = await getLeaderboard({ limit: PAGE_SIZE, offset: offset.value })
    items.value = res.items ?? []
    totalCount.value = res.total ?? 0
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || err.message || '加载排行榜失败')
  } finally {
    loading.value = false
  }
}

const reload = () => {
  offset.value = 0
  load()
}

const prevPage = () => {
  offset.value = Math.max(0, offset.value - PAGE_SIZE)
  load()
}

const nextPage = () => {
  if (!hasNext.value) return
  offset.value += PAGE_SIZE
  load()
}

onMounted(load)
</script>

<style scoped>
.board-page {
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

/* ── 我的排名条 ── */
.board-me {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0;
  background: var(--gg-surface);
  border: 1px solid var(--gg-border-strong);
  box-shadow: var(--gg-shadow-1);
}

.board-me__cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 12px 14px;
  border-right: 1px dotted var(--gg-border-strong);
}

.board-me__cell:last-child {
  border-right: 0;
}

.board-me__num {
  font-family: var(--gg-font-display);
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
  color: var(--gg-brand);
}

.board-me__label {
  font-family: var(--gg-font-mono);
  font-size: 9.5px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--gg-ink-3);
}

.board-me__empty {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 14px;
  background: var(--gg-surface-2);
}

.board-me__mark {
  color: var(--gg-gold);
  font-size: 16px;
}

.board-me__empty-text {
  font-size: 12.5px;
  color: var(--gg-ink-3);
}

/* ── 榜单面板 ── */
.board-panel {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 300px;
  background: var(--gg-surface);
  border: 1px solid var(--gg-border-strong);
  box-shadow: var(--gg-shadow-1);
}

.board-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  background: var(--gg-surface-2);
  border-bottom: 1px dashed var(--gg-border-strong);
}

.board-panel__meta {
  font-family: var(--gg-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.12em;
  color: var(--gg-ink-3);
}

.board-panel__body {
  flex: 1 1 auto;
  padding: 12px 14px;
  min-height: 0;
}

/* ── 榜单行 ── */
.rank-table {
  display: flex;
  flex-direction: column;
}

.rank-table__head,
.rank-table__row {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr) 78px 62px 62px 70px 62px;
  align-items: center;
  gap: 8px;
}

.rank-table__head {
  padding: 0 10px 8px;
  border-bottom: 2px solid var(--gg-ink);
  font-family: var(--gg-font-mono);
  font-size: 9.5px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--gg-ink-3);
}

.rank-table__row {
  padding: 9px 10px;
  border-bottom: 1px dotted var(--gg-border-strong);
  transition: background-color var(--gg-dur) var(--gg-ease), transform var(--gg-dur) var(--gg-ease);
  animation: gg-fade-up var(--gg-dur) var(--gg-ease-out) both;
}

.rank-table__row:hover {
  background: var(--gg-surface-2);
  transform: translateX(2px);
}

.rank-table__row--me {
  background: var(--gg-brand-soft);
  border-bottom-color: rgba(176, 57, 44, 0.4);
}

.rank-table__pos {
  font-family: var(--gg-font-mono);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--gg-ink-3);
}

.rank-table__pos--top {
  color: var(--gg-brand);
}

.rank-table__player {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.rank-table__name {
  font-size: 13.5px;
  color: var(--gg-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank-table__username {
  font-size: 11px;
  color: var(--gg-ink-4);
  white-space: nowrap;
}

.rank-table__cell {
  font-size: 12.5px;
  color: var(--gg-ink-2);
  text-align: right;
}

.rank-table__cell--strong {
  font-weight: 700;
  color: var(--gg-ink);
}

/* ── 分页 ── */
.board-pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 12px 14px;
  border-top: 1px dashed var(--gg-border-strong);
  background: var(--gg-surface-2);
}

.board-pager__info {
  font-family: var(--gg-font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  color: var(--gg-ink-3);
}

@media (max-width: 960px) {
  .board-page {
    padding: 16px 14px 20px;
    min-height: 0;
  }

  .board-me {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .board-me__cell {
    border-bottom: 1px dotted var(--gg-border-strong);
  }
}

@media (max-width: 760px) {
  .rank-table__head {
    display: none;
  }

  .rank-table__row {
    grid-template-columns: 46px minmax(0, 1fr) auto;
    grid-template-areas:
      'pos player player'
      'pos metrics metrics';
    row-gap: 6px;
  }

  .rank-table__pos {
    grid-area: pos;
    align-self: start;
    padding-top: 2px;
  }

  .rank-table__player {
    grid-area: player;
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }

  .rank-table__cell {
    text-align: left;
  }

  .rank-table__row > .rank-table__cell {
    grid-area: metrics;
  }

  .rank-table__row > .rank-table__cell:nth-of-type(n + 2) {
    display: inline-block;
    margin-right: 12px;
  }
}

@media (max-width: 640px) {
  .board-me {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .board-me__empty {
    flex-direction: column;
    text-align: center;
  }
}
</style>
