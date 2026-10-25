<template>
  <div class="portal">
    <header class="header" :class="{ scrolled }">
      <div class="container bar">
        <router-link to="/" class="brand">
          <SealLogo :size="42" />
          <div class="brand-text">
            <strong class="kai">倪海厦 · 经方中医</strong>
            <small>伤寒 · 金匮 · 内经 · 针灸 · 医案</small>
          </div>
        </router-link>

        <nav class="nav" :class="{ open: menuOpen }" @click="menuOpen = false">
          <router-link v-for="n in navs" :key="n.to" :to="n.to" class="nav-item" :class="{ active: isActive(n.to) }">
            {{ n.label }}
          </router-link>
        </nav>

        <div class="right">
          <el-button class="search-btn" circle text @click="$router.push('/search')" aria-label="检索">
            <el-icon :size="18"><Search /></el-icon>
          </el-button>
          <template v-if="auth.user">
            <el-dropdown trigger="click" @command="onCommand">
              <span class="user">
                <span class="avatar">{{ (auth.user.nickname || auth.user.username).slice(0, 1) }}</span>
                <span class="uname">{{ auth.user.nickname || auth.user.username }}</span>
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile" :icon="UserIcon">个人中心</el-dropdown-item>
                  <el-dropdown-item v-if="hasAdmin" command="admin" :icon="Setting">管理后台</el-dropdown-item>
                  <el-dropdown-item command="logout" :icon="SwitchButton" divided>退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <router-link to="/login" class="login-link">登录</router-link>
            <el-button v-if="auth.config.allow_registration" type="primary" size="small" @click="$router.push('/register')">注册</el-button>
          </template>
          <el-button class="menu-btn" text circle @click="menuOpen = !menuOpen" aria-label="菜单">
            <el-icon :size="20"><Menu /></el-icon>
          </el-button>
        </div>
      </div>
    </header>

    <main class="main">
      <router-view v-slot="{ Component, route }">
        <component :is="Component" :key="route.name === 'reader' ? route.params.slug : route.fullPath" />
      </router-view>
    </main>

    <footer class="footer">
      <div class="container foot">
        <div class="foot-brand">
          <SealLogo :size="36" />
          <div>
            <div class="kai foot-title">倪海厦 · 经方中医知识平台</div>
            <div class="foot-quote">「中医很简单，就是阴阳气血。你搞懂了，一通百通。」</div>
          </div>
        </div>
        <p class="disclaimer">
          本站内容整理自倪海厦（1954–2012）公开讲义与医案，仅供中医学习交流，不构成任何诊疗建议。
          如有身体不适，请及时就医，并在执业中医师指导下用药。
        </p>
        <p class="copyright">
          知识库源自开源项目
          <a href="https://github.com/jangviktor-web/nihaixia" target="_blank" rel="noopener">jangviktor-web/nihaixia</a>
          （木兰宽松许可证 MulanPSL-2.0）
        </p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, Menu, Search, Setting, SwitchButton, User as UserIcon } from '@element-plus/icons-vue'
import SealLogo from '@/components/SealLogo.vue'
import { useAuthStore } from '@/stores/auth'
import { adminRoutes } from '@/router'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const menuOpen = ref(false)
const scrolled = ref(false)

const navs = [
  { to: '/', label: '首页' },
  { to: '/library', label: '典籍' },
  { to: '/cases', label: '医案' },
  { to: '/consult', label: '经方问诊' },
  { to: '/search', label: '检索' },
]

const isActive = (to: string) => (to === '/' ? route.path === '/' : route.path.startsWith(to))
const hasAdmin = computed(() => adminRoutes.some((r) => r.meta?.perm && auth.can(r.meta.perm)))

function onCommand(cmd: string) {
  if (cmd === 'profile') router.push('/profile')
  else if (cmd === 'admin') router.push('/admin')
  else if (cmd === 'logout') {
    auth.logout()
    ElMessage.success('已退出登录')
    router.push('/')
  }
}

const onScroll = () => (scrolled.value = window.scrollY > 10)
onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))
</script>

<style scoped lang="scss">
.portal { min-height: 100vh; display: flex; flex-direction: column; }
.header {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(245, 238, 223, 0.92);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid transparent;
  transition: all 0.25s;
  &.scrolled { border-bottom-color: var(--line); box-shadow: 0 2px 12px rgba(80, 55, 25, 0.06); }
}
.bar { display: flex; align-items: center; height: 68px; gap: 24px; }
.brand { display: flex; align-items: center; gap: 12px; color: var(--ink); }
.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
  strong { font-size: 20px; letter-spacing: 3px; }
  small { font-size: 11px; color: var(--ink-3); letter-spacing: 2px; }
}
.nav { display: flex; gap: 4px; margin-left: 24px; flex: 1; }
.nav-item {
  position: relative;
  padding: 6px 16px;
  color: var(--ink-2);
  font-size: 16px;
  letter-spacing: 2px;
  font-family: var(--font-kai);
  &:hover { color: var(--cinnabar); }
  &.active {
    color: var(--cinnabar);
    &::after {
      content: '';
      position: absolute;
      left: 50%;
      bottom: -2px;
      width: 6px;
      height: 6px;
      background: var(--cinnabar);
      transform: translateX(-50%) rotate(45deg);
    }
  }
}
.right { display: flex; align-items: center; gap: 12px; margin-left: auto; }
.login-link { color: var(--ink-2); letter-spacing: 1px; white-space: nowrap; }
.user { display: flex; align-items: center; gap: 8px; cursor: pointer; color: var(--ink-2); }
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--indigo);
  color: #f5eedf;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-kai);
  font-size: 15px;
}
.menu-btn { display: none; }
.main { flex: 1; }
.footer {
  margin-top: 60px;
  background: #2b2420;
  color: #c9bba3;
  padding: 40px 0 28px;
  border-top: 3px solid var(--cinnabar);
  a { color: #e3c08a; }
}
.foot-brand { display: flex; gap: 14px; align-items: center; margin-bottom: 16px; }
.foot-title { color: #f1e6d0; font-size: 18px; letter-spacing: 3px; }
.foot-quote { font-size: 13px; color: #a8987f; }
.disclaimer, .copyright { font-size: 13px; margin: 6px 0; color: #a8987f; }

@media (max-width: 900px) {
  .brand-text small, .uname, .search-btn { display: none; }
  .bar { gap: 10px; }
  .brand-text strong { font-size: 17px; letter-spacing: 1px; white-space: nowrap; }
  .right { gap: 6px; }
  .menu-btn { display: inline-flex; }
  .nav {
    display: none;
    position: absolute;
    top: 68px;
    left: 0;
    right: 0;
    flex-direction: column;
    background: var(--card);
    border-bottom: 1px solid var(--line);
    padding: 8px 20px;
    margin: 0;
    &.open { display: flex; }
  }
  .nav-item.active::after { display: none; }
}
</style>
