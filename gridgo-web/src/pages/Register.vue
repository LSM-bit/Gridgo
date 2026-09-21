<template>
  <div class="auth-page">
    <div class="auth-sheet">
      <!-- 票根：品牌侧 -->
      <aside class="auth-stub">
        <span class="auth-stub__no">NO. 0002</span>
        <div class="auth-stub__mark">GG</div>
        <h1 class="auth-stub__title">GridGo</h1>
        <p class="auth-stub__slogan">经典大富翁 · 多人在线对局平台</p>

        <ul class="auth-stub__points">
          <li><span class="auth-stub__idx">01</span>创建房间 · 邀请好友开局</li>
          <li><span class="auth-stub__idx">02</span>自由交易 · 竞价拍卖</li>
          <li><span class="auth-stub__idx">03</span>战绩统计 · 段位排行</li>
        </ul>

        <div class="auth-stub__foot">
          <span class="gg-stamp gg-stamp--gold">EST. 2026</span>
          <span class="auth-stub__note">BOARD GAME PARLOUR</span>
        </div>
      </aside>

      <!-- 票面：表单侧 -->
      <section class="auth-form">
        <header class="auth-form__head">
          <span class="gg-kicker">FORM 02 — NEW ACCOUNT</span>
          <h2 class="auth-form__title">注册</h2>
          <p class="auth-form__sub">创建账号，开启你的第一局</p>
        </header>

        <el-form :model="form" label-position="top" size="large" @submit.prevent="handleRegister">
          <div class="auth-form__grid">
            <el-form-item label="用户名">
              <el-input v-model="form.username" placeholder="字母和数字组合" clearable />
            </el-form-item>
            <el-form-item label="昵称">
              <el-input v-model="form.nickname" placeholder="对局中显示的名字" clearable />
            </el-form-item>
          </div>
          <el-form-item label="密码">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="至少 6 位"
              show-password
            />
          </el-form-item>
          <el-form-item label="确认密码">
            <el-input
              v-model="form.confirmPassword"
              type="password"
              placeholder="请再次输入密码"
              show-password
              @keyup.enter="handleRegister"
            />
          </el-form-item>

          <el-button
            type="primary"
            class="auth-form__submit"
            :loading="loading"
            @click="handleRegister"
          >
            注册并进入大厅
          </el-button>

          <p class="auth-form__foot">
            已有账号？
            <a class="auth-form__link" @click="$router.push('/login')">去登录</a>
          </p>
        </el-form>
      </section>
    </div>
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

<style scoped>
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 32px 20px;
}

.auth-sheet {
  position: relative;
  display: grid;
  grid-template-columns: 0.86fr 1fr;
  width: min(920px, 100%);
  background: var(--gg-surface);
  border: 1px solid var(--gg-border-strong);
  box-shadow: var(--gg-shadow-3);
  animation: gg-pop-in var(--gg-dur-slow) var(--gg-ease-out) both;
}

.auth-sheet::after {
  content: '';
  position: absolute;
  inset: -6px;
  border: 1px solid var(--gg-border);
  pointer-events: none;
}

/* ── 票根 ── */
.auth-stub {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 40px 34px;
  background: var(--gg-grad-night);
  color: #f2ead9;
  border-right: 1px dashed var(--gg-border-strong);
}

.auth-stub__no {
  font-family: var(--gg-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.24em;
  color: rgba(242, 234, 217, 0.5);
}

.auth-stub__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 50px;
  height: 50px;
  margin-top: 4px;
  background: var(--gg-brand);
  border: 1px solid #6f1d13;
  color: #fdf3ea;
  font-family: var(--gg-font-display);
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 0.08em;
  box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.35);
}

.auth-stub__title {
  margin: 0;
  font-family: var(--gg-font-display);
  font-size: 34px;
  letter-spacing: 0.03em;
  color: #fdf7ea;
}

.auth-stub__slogan {
  margin: 0;
  font-size: 12.5px;
  letter-spacing: 0.06em;
  color: rgba(242, 234, 217, 0.62);
}

.auth-stub__points {
  display: flex;
  flex-direction: column;
  gap: 9px;
  margin: 20px 0 0;
  padding: 16px 0 0;
  border-top: 1px dashed rgba(242, 234, 217, 0.24);
  list-style: none;
}

.auth-stub__points li {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: 12.5px;
  color: rgba(242, 234, 217, 0.86);
}

.auth-stub__idx {
  font-family: var(--gg-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.14em;
  color: var(--gg-gold);
}

.auth-stub__foot {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: auto;
  padding-top: 20px;
}

.auth-stub__note {
  font-family: var(--gg-font-mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  color: rgba(242, 234, 217, 0.42);
}

/* ── 票面表单 ── */
.auth-form {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 38px 36px;
}

.auth-form__head {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px dashed var(--gg-border-strong);
}

.auth-form__title {
  margin: 6px 0 0;
  font-family: var(--gg-font-display);
  font-size: 26px;
  letter-spacing: 0.04em;
  color: var(--gg-ink);
}

.auth-form__sub {
  margin: 4px 0 0;
  font-size: 12.5px;
  color: var(--gg-ink-3);
}

.auth-form__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 14px;
}

.auth-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.auth-form__submit {
  width: 100%;
  height: 44px;
  margin-top: 2px;
  font-size: 14px;
  letter-spacing: 0.18em;
}

.auth-form__foot {
  margin: 14px 0 0;
  font-size: 12.5px;
  color: var(--gg-ink-3);
  text-align: center;
}

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

@media (max-width: 880px) {
  .auth-sheet {
    grid-template-columns: 1fr;
    width: min(440px, 100%);
  }

  .auth-stub {
    padding: 26px 24px 22px;
    border-right: 0;
    border-bottom: 1px dashed var(--gg-border-strong);
  }

  .auth-stub__title {
    font-size: 26px;
  }

  .auth-stub__points {
    display: none;
  }

  .auth-stub__foot {
    margin-top: 6px;
    padding-top: 10px;
  }

  .auth-form {
    padding: 26px 24px 30px;
  }
}

@media (max-width: 520px) {
  .auth-page {
    padding: 16px 12px;
  }

  .auth-form__grid {
    grid-template-columns: 1fr;
  }

  .auth-form__title {
    font-size: 22px;
  }
}
</style>
