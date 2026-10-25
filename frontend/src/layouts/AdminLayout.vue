<template>
  <el-container class="admin">
    <el-aside :width="collapsed ? '64px' : '220px'" class="aside" :class="{ mobileOpen }">
      <router-link to="/" class="logo">
        <SealLogo :size="36" />
        <span v-show="!collapsed" class="kai">经方中医 · 后台</span>
      </router-link>
      <el-menu :default-active="$route.name as string" :collapse="collapsed" router class="menu" @select="mobileOpen = false">
        <el-menu-item v-for="r in menus" :key="r.name as string" :index="r.name as string" :route="{ name: r.name }">
          <el-icon><component :is="icons[r.meta!.icon as keyof typeof icons]" /></el-icon>
          <template #title>{{ r.meta!.title }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <div v-if="mobileOpen" class="mask" @click="mobileOpen = false" />

    <el-container class="right">
      <el-header class="header">
        <el-button text circle class="toggle" @click="toggle">
          <el-icon :size="18"><component :is="collapsed ? Expand : Fold" /></el-icon>
        </el-button>
        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ name: 'admin-dashboard' }">管理后台</el-breadcrumb-item>
          <el-breadcrumb-item>{{ $route.meta.title }}</el-breadcrumb-item>
        </el-breadcrumb>
        <div class="hdr-right">
          <router-link to="/" class="to-site"><el-icon><HomeFilled /></el-icon>返回前台</router-link>
          <el-dropdown @command="onCmd">
            <span class="user">
              <span class="avatar kai">{{ (auth.user?.nickname || auth.user?.username || '').slice(0, 1) }}</span>
              {{ auth.user?.nickname || auth.user?.username }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Expand, Fold, HomeFilled, Lock, Notebook, Odometer, Reading, Tickets, User } from '@element-plus/icons-vue'
import SealLogo from '@/components/SealLogo.vue'
import { adminRoutes } from '@/router'
import { useAuthStore } from '@/stores/auth'

const icons = { Odometer, User, Lock, Reading, Notebook, Tickets }
const auth = useAuthStore()
const router = useRouter()
const collapsed = ref(false)
const mobileOpen = ref(false)
const menus = computed(() => adminRoutes.filter((r) => !r.meta?.perm || auth.can(r.meta.perm)))

function toggle() {
  if (window.innerWidth < 768) mobileOpen.value = !mobileOpen.value
  else collapsed.value = !collapsed.value
}

function onCmd(c: string) {
  if (c === 'profile') router.push('/profile')
  else {
    auth.logout()
    router.push('/login')
  }
}
</script>

<style scoped lang="scss">
.admin { min-height: 100vh; }
.aside {
  background: #2b2420;
  background-image: linear-gradient(180deg, rgba(168, 50, 42, 0.12), transparent 40%);
  transition: width 0.2s;
  overflow-x: hidden;
  border-right: 3px solid var(--cinnabar);
}
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  color: #f1e6d0;
  font-size: 17px;
  letter-spacing: 2px;
  white-space: nowrap;
  border-bottom: 1px solid rgba(241, 230, 208, 0.1);
}
.menu {
  --el-menu-bg-color: transparent;
  --el-menu-text-color: #c9bba3;
  --el-menu-hover-bg-color: rgba(241, 230, 208, 0.08);
  --el-menu-active-color: #f1e6d0;
  margin-top: 8px;
  :deep(.el-menu-item) { letter-spacing: 2px; margin: 2px 8px; border-radius: 3px; height: 46px; }
  :deep(.el-menu-item.is-active) { background: var(--cinnabar); box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3); }
}
.menu.el-menu--collapse :deep(.el-menu-item) { margin: 2px 4px; }
.right { min-width: 0; }
.header {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--card);
  border-bottom: 1px solid var(--line);
  height: 64px;
}
.hdr-right { margin-left: auto; display: flex; align-items: center; gap: 20px; }
.to-site { display: inline-flex; align-items: center; gap: 4px; color: var(--ink-2); font-size: 14px; }
.user { display: flex; align-items: center; gap: 8px; cursor: pointer; color: var(--ink-2); }
.avatar { width: 30px; height: 30px; border-radius: 50%; background: var(--indigo); color: #f5eedf; display: inline-flex; align-items: center; justify-content: center; }
.main { padding: 20px; }
.mask { display: none; }
@media (max-width: 768px) {
  .aside { position: fixed; z-index: 100; height: 100vh; transform: translateX(-100%); width: 220px !important; transition: transform 0.2s; &.mobileOpen { transform: none; } }
  .mask { display: block; position: fixed; inset: 0; z-index: 99; background: rgba(0, 0, 0, 0.3); }
  .to-site { display: none; }
  .main { padding: 12px; }
}
</style>
