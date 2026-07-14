<template>
  <div class="login-page flex-center" style="height: 100vh">
    <el-card style="width: 400px">
      <template #header>
        <h2 class="text-center">🎲 GridGo 登录</h2>
      </template>
      <el-form :model="form" label-width="80px" @submit.prevent="handleLogin">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="w-full" :loading="loading" @click="handleLogin">登录</el-button>
        </el-form-item>
        <div class="text-center">
          还没有账号？<el-link type="primary" @click="$router.push('/register')">去注册</el-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const handleLogin = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  loading.value = true
  try {
    const res = await login({ username: form.username, password: form.password })
    userStore.setUserInfo({
      token: res.token.access_token,
      refreshToken: res.token.refresh_token,
      userId: res.user.id,
      username: res.user.username,
      nickname: res.user.nickname,
      avatar: res.user.avatar ?? undefined,
    })
    ElMessage.success('登录成功')
    router.push('/')
  } catch (err: any) {
    const msg = err.response?.data?.detail || err.message || '登录失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>
