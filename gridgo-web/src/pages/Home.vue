<template>
  <div class="home-page">
    <el-container>
      <el-header>
        <div class="flex-between w-full h-full">
          <h1>🎲 GridGo</h1>
          <div>
            <template v-if="userStore.isLoggedIn">
              <span class="mr-4">你好，{{ userStore.nickname }}</span>
              <el-button @click="$router.push('/profile')">👤 个人中心</el-button>
              <el-button @click="handleLogout">退出</el-button>
            </template>
            <template v-else>
              <el-button type="primary" @click="$router.push('/login')">登录</el-button>
              <el-button @click="$router.push('/register')">注册</el-button>
            </template>
          </div>
        </div>
      </el-header>
      <el-main>
        <div class="flex-col-center" style="height: 60vh">
          <h2>欢迎来到 GridGo 大富翁</h2>
          <p>经典大富翁，在线实时对战</p>
          <div v-if="userStore.isLoggedIn" class="mt-8 flex gap-4">
            <!-- 返回房间（用户已在房间中时显示） -->
            <el-button v-if="roomStore.inRoom" type="warning" size="large" @click="handleBackToRoom">
              🔙 返回房间
            </el-button>
            <template v-else>
              <el-button type="primary" size="large" @click="showCreateDialog = true">
                🏠 创建房间
              </el-button>
              <el-button size="large" @click="showJoinDialog = true">
                🚪 加入房间
              </el-button>
            </template>
          </div>
          <el-button v-else type="primary" size="large" class="mt-8" @click="$router.push('/login')">
            开始游戏
          </el-button>
        </div>
      </el-main>
    </el-container>

    <!-- 创建房间对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建房间" width="480px" :close-on-click-modal="false">
      <el-form :model="createForm" label-width="100px" label-position="left">
        <el-form-item label="房间名称">
          <el-input v-model="createForm.name" placeholder="给房间起个名字" maxlength="50" show-word-limit />
        </el-form-item>

        <el-form-item label="最大人数">
          <el-slider
            v-model="createForm.max_players"
            :min="2"
            :max="8"
            :step="1"
            show-stops
            :marks="{ 2: '2', 4: '4', 6: '6', 8: '8' }"
          />
        </el-form-item>

        <el-form-item label="选择地图">
          <el-radio-group v-model="createForm.map_id">
            <el-radio-button
              v-for="map in MAP_OPTIONS"
              :key="map.value"
              :value="map.value"
            >
              {{ map.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="AI 数量">
          <el-slider
            v-model="createForm.ai_count"
            :min="0"
            :max="maxAiCount"
            :step="1"
            show-stops
          />
        </el-form-item>

        <el-form-item v-if="(createForm.ai_count ?? 0) > 0" label="AI 难度">
          <el-radio-group v-model="createForm.ai_difficulty">
            <el-radio-button
              v-for="opt in AI_DIFFICULTY_OPTIONS"
              :key="opt.value"
              :value="opt.value"
            >
              {{ opt.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="handleCreateRoom">创建</el-button>
      </template>
    </el-dialog>

    <!-- 加入房间对话框 -->
    <el-dialog v-model="showJoinDialog" title="加入房间" width="400px">
      <el-form @submit.prevent="handleJoinRoom">
        <el-form-item label="房间代码">
          <el-input
            v-model="joinCode"
            placeholder="请输入6位房间代码"
            maxlength="6"
            style="text-transform: uppercase"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showJoinDialog = false">取消</el-button>
        <el-button :loading="joinLoading" @click="handleJoinRoom(false)">加入</el-button>
        <el-button type="info" :loading="spectateLoading" @click="handleJoinRoom(true)">👀 观战</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useRoomStore } from '@/stores/room'
import { logout } from '@/api/auth'
import { createRoom, joinRoom, MAP_OPTIONS, AI_DIFFICULTY_OPTIONS } from '@/api/room'
import type { CreateRoomData } from '@/api/room'

const router = useRouter()
const userStore = useUserStore()
const roomStore = useRoomStore()

// 创建房间
const showCreateDialog = ref(false)
const createLoading = ref(false)
const createForm = ref<CreateRoomData>({
  name: 'GridGo 房间',
  max_players: 8,
  map_id: 'classic',
  ai_count: 0,
  ai_difficulty: 'easy',
})

// AI 最大数量 = 最大人数（房主可自动变为观战者）
const maxAiCount = computed(() => createForm.value.max_players ?? 8)

// 当最大人数变化时，确保 AI 数量不超标
watch(() => createForm.value.max_players, () => {
  if ((createForm.value.ai_count ?? 0) > maxAiCount.value) {
    createForm.value.ai_count = maxAiCount.value
  }
})

// 加入房间
const showJoinDialog = ref(false)
const joinCode = ref('')
const joinLoading = ref(false)
const spectateLoading = ref(false)

// 返回房间
const handleBackToRoom = () => {
  if (roomStore.roomCode) {
    router.push(`/room/${roomStore.roomCode}`)
  }
}

const handleLogout = async () => {
  try {
    await logout()
  } catch {
    // 即使后端登出失败，前端也清除状态
  }
  userStore.clearUserInfo()
  ElMessage.success('已退出登录')
}

const handleCreateRoom = async () => {
  createLoading.value = true
  try {
    const room = await createRoom(createForm.value)
    ElMessage.success('房间创建成功')
    showCreateDialog.value = false
    router.push(`/room/${room.code}`)
  } catch (err: any) {
    const msg = err.response?.data?.detail || err.message || '创建房间失败'
    ElMessage.error(msg)
  } finally {
    createLoading.value = false
  }
}

const handleJoinRoom = async (asSpectator: boolean = false) => {
  const code = joinCode.value.trim().toUpperCase()
  if (code.length !== 6) {
    ElMessage.warning('请输入6位房间代码')
    return
  }

  if (asSpectator) {
    spectateLoading.value = true
  } else {
    joinLoading.value = true
  }
  try {
    const room = await joinRoom(code, asSpectator)
    ElMessage.success(asSpectator ? '已加入观战席' : '加入房间成功')
    showJoinDialog.value = false
    joinCode.value = ''
    router.push(`/room/${room.code}`)
  } catch (err: any) {
    const msg = err.response?.data?.detail || err.message || '加入房间失败'
    ElMessage.error(msg)
  } finally {
    joinLoading.value = false
    spectateLoading.value = false
  }
}
</script>

<style scoped>
.home-page {
  width: 100%;
  height: 100%;
}
</style>
