<template>
  <div class="register-page flex-center" style="height: 100vh">
    <el-card style="width: 400px">
      <template #header>
        <h2 class="text-center">🎲 GridGo 注册</h2>
      </template>
      <el-form :model="form" label-width="80px" @submit.prevent="handleRegister">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名（字母和数字）" />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码（至少6位）" show-password />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="form.confirmPassword" type="password" placeholder="请再次输入密码" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="w-full" :loading="loading" @click="handleRegister">注册</el-button>
        </el-form-item>
        <div class="text-center">
          已有账号？<el-link type="primary" @click="$router.push('/login')">去登录</el-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { register } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)

const form = reactive({
  username: '',
  nickname: '',
  password: '',
  confirmPassword: '',
})

const handleRegister = async () => {
  if (!form.username || !form.nickname || !form.password) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (form.password.length < 6 || form.password.length > 72) {
    ElMessage.warning('密码长度需在6-72位之间')
    return
  }
  if (form.password !== form.confirmPassword) {
    ElMessage.warning('两次密码输入不一致')
    return
  }

  loading.value = true
  try {
    const res = await register({
      username: form.username,
      password: form.password,
      nickname: form.nickname,
    })
    // 注册成功后自动登录
    userStore.setUserInfo({
      token: res.token.access_token,
      refreshToken: res.token.refresh_token,
      userId: res.user.id,
      username: res.user.username,
      nickname: res.user.nickname,
      avatar: res.user.avatar ?? undefined,
    })
    ElMessage.success('注册成功')
    router.push('/')
  } catch (err: any) {
    const msg = err.response?.data?.detail || err.message || '注册失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>
