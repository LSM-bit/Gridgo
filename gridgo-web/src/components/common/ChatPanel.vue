<template>
  <el-card shadow="never" class="chat-panel">
    <template #header>
      <div class="chat-panel__header">
        <span class="chat-panel__title">聊天</span>
        <span class="chat-panel__chan" :data-ws="lastSendViaWS ? 'on' : 'off'">
          {{ lastSendViaWS ? 'WS 通道' : 'REST 回退' }}
        </span>
      </div>
    </template>

    <div ref="listEl" class="chat-panel__list" :style="{ height: `${height}px` }" @scroll="onScroll">
      <div v-if="hasMore" class="chat-panel__more" @click="loadOlder()">加载更早的消息</div>

      <div v-if="loading && messages.length === 0" class="chat-panel__state">
        <span class="chat-panel__dots">···</span>
        <span>正在读取聊天记录</span>
      </div>

      <div v-else-if="messages.length === 0" class="chat-panel__state chat-panel__state--empty">
        <span class="chat-panel__empty-mark">✉</span>
        <span class="chat-panel__empty-title">还没有人说话</span>
        <span class="chat-panel__empty-hint">发条消息跟对手打个招呼</span>
      </div>

      <div
        v-for="msg in messages"
        :key="msg.id"
        class="chat-msg"
        :class="{ 'chat-msg--self': msg.user_id === currentUserId }"
      >
        <div class="chat-msg__meta">
          <span class="chat-msg__name">{{ msg.is_ai ? 'AI · ' : '' }}{{ msg.nickname }}</span>
          <span class="chat-msg__time">{{ formatTime(msg.created_at) }}</span>
        </div>
        <div class="chat-msg__content">{{ msg.content }}</div>
      </div>
    </div>

    <div class="chat-panel__input">
      <el-input
        v-model="draft"
        placeholder="输入消息…"
        maxlength="500"
        :disabled="!roomId"
        @keyup.enter="submit"
      >
        <template #append>
          <el-button :loading="sending" @click="submit">发送</el-button>
        </template>
      </el-input>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useChat } from '@/composables/useChat'
import { formatTime } from '@/utils/format'

const props = withDefaults(
  defineProps<{
    roomId: string
    currentUserId: number
    height?: number
  }>(),
  { height: 200 },
)

const { messages, loading, sending, hasMore, error: chatError, lastSendViaWS, loadInitial, loadOlder, send } = useChat({
  roomId: () => props.roomId,
})

const draft = ref('')
const listEl = ref<HTMLElement | null>(null)

const scrollToBottom = async () => {
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
}

const onScroll = () => {
  const el = listEl.value
  if (!el) return
  if (el.scrollTop < 40 && hasMore.value) loadOlder()
}

const submit = async () => {
  const content = draft.value.trim()
  if (!content) {
    ElMessage.warning('请输入消息内容')
    return
  }
  const ok = await send(content)
  if (!ok) {
    ElMessage.error(chatError.value || '消息发送失败，请稍后重试')
    return
  }
  draft.value = ''
  scrollToBottom()
  // 发送成功也给明确反馈：WS 断开时聊天自动走 REST 回退，需告知用户消息已送达
  ElMessage.success(lastSendViaWS.value ? '消息已发送' : '消息已发送（连接异常，已自动回退 REST 通道）')
}

watch(() => messages.value.length, scrollToBottom)

onMounted(async () => {
  if (props.roomId) await loadInitial()
  scrollToBottom()
})
</script>

<style scoped>
.chat-panel {
  border-radius: var(--gg-radius);
}

.chat-panel :deep(.el-card__header) {
  padding: 10px 14px;
  background: var(--gg-surface-2);
  border-bottom: 1px dashed var(--gg-border-strong);
}

.chat-panel :deep(.el-card__body) {
  padding: 12px 14px 14px;
}

.chat-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.chat-panel__title {
  font-family: var(--gg-font-display);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--gg-ink);
}

.chat-panel__chan {
  font-family: var(--gg-font-mono);
  font-size: 9.5px;
  letter-spacing: 0.16em;
  padding: 2px 6px;
  border: 1px solid var(--gg-border);
  color: var(--gg-ink-3);
  background: var(--gg-surface);
}

.chat-panel__chan[data-ws='on'] {
  color: var(--gg-green);
  border-color: var(--gg-green);
}

.chat-panel__list {
  overflow-y: auto;
  padding: 2px 4px 2px 2px;
}

/* ── 空态 / 加载态（不留白洞） ── */
.chat-panel__state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 100%;
  min-height: 120px;
  padding: 16px 12px;
  text-align: center;
  font-size: 12px;
  color: var(--gg-ink-3);
  border: 1px dashed var(--gg-border-strong);
  background: var(--gg-bg-deep);
}

.chat-panel__state--empty {
  border-style: dashed;
}

.chat-panel__empty-mark {
  font-size: 20px;
  color: var(--gg-gold-strong);
  line-height: 1;
}

.chat-panel__empty-title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--gg-ink-2);
}

.chat-panel__empty-hint {
  font-size: 11.5px;
  color: var(--gg-ink-4);
}

.chat-panel__dots {
  font-family: var(--gg-font-mono);
  letter-spacing: 0.3em;
  animation: gg-blink 1.4s linear infinite;
}

.chat-panel__more {
  display: block;
  margin-bottom: 8px;
  padding: 4px;
  font-size: 11.5px;
  color: var(--gg-brand);
  text-align: center;
  cursor: pointer;
  border: 1px dashed var(--gg-border-strong);
}

.chat-panel__more:hover {
  background: var(--gg-brand-soft);
}

/* ── 消息条目 ── */
.chat-msg {
  max-width: 90%;
  margin-bottom: 8px;
  padding: 7px 10px;
  background: var(--gg-surface-2);
  border: 1px solid var(--gg-border);
  border-left: 2px solid var(--gg-border-strong);
  animation: gg-fade-up var(--gg-dur) var(--gg-ease-out) both;
}

.chat-msg--self {
  margin-left: auto;
  background: var(--gg-brand-soft);
  border-color: var(--gg-border-strong);
  border-left-color: var(--gg-brand);
}

.chat-msg__meta {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 2px;
}

.chat-msg__name {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--gg-ink-2);
}

.chat-msg--self .chat-msg__name {
  color: var(--gg-brand);
}

.chat-msg__time {
  font-family: var(--gg-font-mono);
  font-size: 10px;
  color: var(--gg-ink-4);
  font-variant-numeric: tabular-nums;
}

.chat-msg__content {
  font-size: 13px;
  color: var(--gg-ink);
  line-height: 1.55;
  word-break: break-word;
}

.chat-panel__input {
  margin-top: 10px;
}
</style>
