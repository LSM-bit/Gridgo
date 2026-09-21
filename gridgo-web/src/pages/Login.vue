<template>
  <div class="auth-page">
    <div class="auth-ticket">
      <!-- 票根 -->
      <aside class="auth-ticket__stub">
        <span class="gg-stamp gg-stamp--gold">GRIDGO</span>
        <h1 class="auth-ticket__brand">GridGo</h1>
        <p class="auth-ticket__slogan">在线大富翁对战平台</p>
        <ul class="auth-ticket__points">
          <li><span>01</span>实时掷骰 · 回合制对战</li>
          <li><span>02</span>买地建楼 · 拍卖与交易</li>
          <li><span>03</span>排行榜 · 对局回放</li>
        </ul>
        <p class="auth-ticket__foot">NO. 0001 / 入场券 · 凭票入座</p>
      </aside>

      <!-- 票面 -->
      <section class="auth-form">
        <span class="gg-kicker">SIGN IN · 登录</span>
        <h2 class="auth-form__title">欢迎回来</h2>
        <p class="auth-form__sub">登录后继续你的地产帝国</p>

        <el-form :model="form" label-position="top" size="large" class="auth-form__form" @submit.prevent="handleLogin">
          <el-form-item label="用户名">
            <el-input v-model="form.username" placeholder="请输入用户名" clearable />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-button type="primary" class="auth-form__submit" :loading="loading" @click="handleLogin">
            登录
          </el-button>

          <div class="auth-form__foot">
            还没有账号？
            <a class="auth-form__link" @click="router.push('/register')">立即注册</a>
          </div>
        </el-form>
      </section>
    </div>
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

<style scoped>
.auth-page {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 36px 20px;
  background-color: var(--gg-bg);
  background-image: var(--gg-grid), var(--gg-page-glow);
  background-size: 24px 24px, 24px 24px, auto, auto;
}

.auth-ticket {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 0.92fr) minmax(0, 1fr);
  width: min(920px, 100%);
  background: var(--gg-surface);
  border: 1px solid var(--gg-border-strong);
  box-shadow: var(--gg-shadow-3);
  animation: gg-pop-in var(--gg-dur-slow) var(--gg-ease-out) both;
}

.auth-ticket::before {
  content: '';
  position: absolute;
  inset: 5px;
  border: 1px solid var(--gg-border);
  pointer-events: none;
  z-index: 2;
}

/* ── 票根 ── */
.auth-ticket__stub {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
  padding: 40px 36px;
  background: var(--gg-grad-night);
  color: #f2ead9;
  border-right: 1px dashed rgba(242, 234, 217, 0.32);
}

.auth-ticket__brand {
  margin: 2px 0 0;
  font-family: var(--gg-font-display);
  font-size: clamp(28px, 3.6vw, 38px);
  letter-spacing: 0.04em;
  color: #fdf7ea;
}

.auth-ticket__slogan {
  margin: 0;
  font-size: 13px;
  letter-spacing: 0.08em;
  color: rgba(242, 234, 217, 0.68);
}

.auth-ticket__points {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 20px 0 0;
  padding: 16px 0 0;
  border-top: 1px dashed rgba(242, 234, 217, 0.26);
  list-style: none;
}

.auth-ticket__points li {
  display: flex;
  gap: 10px;
  font-size: 12.5px;
  color: rgba(242, 234, 217, 0.86);
}

.auth-ticket__points span {
  font-family: var(--gg-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.16em;
  color: var(--gg-gold);
}

.auth-ticket__foot {
  margin: 22px 0 0;
  font-family: var(--gg-font-mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(242, 234, 217, 0.45);
}

/* ── 票面（表单） ── */
.auth-form {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 40px 38px;
}

.auth-form__title {
  margin: 6px 0 0;
  font-family: var(--gg-font-display);
  font-size: 26px;
  letter-spacing: 0.02em;
  color: var(--gg-ink);
}

.auth-form__sub {
  margin: 4px 0 20px;
  font-size: 12.5px;
  color: var(--gg-ink-3);
}

.auth-form__submit {
  width: 100%;
  height: 44px;
  margin-top: 4px;
  font-size: 15px;
  letter-spacing: 0.22em;
}

.auth-form__foot {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  margin-top: 14px;
  font-size: 12.5px;
  color: var(--gg-ink-3);
}

/* 与 Register.vue 的「去登录」链接保持完全一致（同 token、同写法） */
.auth-form__link {
  color: var(--gg-brand);
  font-weight: 600;
  cursor: pointer;
  border-bottom: 1px solid rgba(176, 57, 44, 0.4);
}

.auth-form__link:hover {
  text-decoration: none;
  border-bottom-color: var(--gg-brand);
}

@media (max-width: 860px) {
  .auth-ticket {
    grid-template-columns: minmax(0, 1fr);
    width: min(430px, 100%);
  }

  .auth-ticket__stub {
    padding: 26px 24px 22px;
    border-right: 0;
    border-bottom: 1px dashed rgba(242, 234, 217, 0.32);
  }

  .auth-ticket__points {
    display: none;
  }

  .auth-ticket__foot {
    margin-top: 14px;
  }

  .auth-form {
    padding: 26px 24px 30px;
  }

  .auth-form__title {
    font-size: 22px;
  }
}

@media (max-width: 480px) {
  .auth-page {
    padding: 16px 12px;
  }

  .auth-ticket__stub {
    padding: 22px 18px 18px;
  }

  .auth-form {
    padding: 22px 18px 26px;
  }
}
</style>
