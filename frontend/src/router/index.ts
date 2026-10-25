import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    auth?: boolean
    perm?: string | string[]
    guestOnly?: boolean
    icon?: string
  }
}

export const adminRoutes: RouteRecordRaw[] = [
  { path: '', name: 'admin-dashboard', component: () => import('@/views/admin/Dashboard.vue'), meta: { title: '控制台', perm: 'dashboard:view', icon: 'Odometer' } },
  { path: 'users', name: 'admin-users', component: () => import('@/views/admin/Users.vue'), meta: { title: '用户管理', perm: 'user:read', icon: 'User' } },
  { path: 'roles', name: 'admin-roles', component: () => import('@/views/admin/Roles.vue'), meta: { title: '角色权限', perm: 'role:read', icon: 'Lock' } },
  { path: 'documents', name: 'admin-documents', component: () => import('@/views/admin/Documents.vue'), meta: { title: '典籍管理', perm: 'document:manage', icon: 'Reading' } },
  { path: 'cases', name: 'admin-cases', component: () => import('@/views/admin/Cases.vue'), meta: { title: '医案管理', perm: 'case:manage', icon: 'Notebook' } },
  { path: 'audit', name: 'admin-audit', component: () => import('@/views/admin/AuditLogs.vue'), meta: { title: '操作日志', perm: 'audit:read', icon: 'Tickets' } },
]

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layouts/PortalLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('@/views/Home.vue'), meta: { title: '首页' } },
      { path: 'library', name: 'library', component: () => import('@/views/Library.vue'), meta: { title: '典籍' } },
      { path: 'library/:slug/:chapterId?', name: 'reader', component: () => import('@/views/Reader.vue'), meta: { title: '阅读' } },
      { path: 'cases', name: 'cases', component: () => import('@/views/Cases.vue'), meta: { title: '医案' } },
      { path: 'search', name: 'search', component: () => import('@/views/Search.vue'), meta: { title: '检索' } },
      { path: 'consult', name: 'consult', component: () => import('@/views/Consult.vue'), meta: { title: '经方问诊' } },
      { path: 'profile', name: 'profile', component: () => import('@/views/Profile.vue'), meta: { title: '个人中心', auth: true } },
      { path: '403', name: 'forbidden', component: () => import('@/views/Forbidden.vue'), meta: { title: '无权访问' } },
    ],
  },
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue'), meta: { title: '登录', guestOnly: true } },
  { path: '/register', name: 'register', component: () => import('@/views/Login.vue'), meta: { title: '注册', guestOnly: true } },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { auth: true },
    children: adminRoutes,
  },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFound.vue'), meta: { title: '页面不存在' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, _from, saved) {
    if (saved) return saved
    if (to.hash) return { el: to.hash, top: 90 }
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.init()
  if (to.meta.guestOnly && auth.isLoggedIn) return { name: 'home' }
  const needAuth = to.matched.some((r) => r.meta.auth)
  if (needAuth && !auth.isLoggedIn) return { name: 'login', query: { redirect: to.fullPath } }
  if (auth.user?.must_change_password && to.name !== 'profile') {
    return { name: 'profile', query: { tab: 'password', force: '1' } }
  }
  if (to.meta.perm && !auth.can(to.meta.perm)) {
    // 后台首页无权限时跳到第一个有权限的菜单
    if (to.name === 'admin-dashboard') {
      const first = adminRoutes.find((r) => r.meta?.perm && auth.can(r.meta.perm))
      if (first) return { name: first.name as string }
    }
    return { name: 'forbidden' }
  }
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 倪海厦经方中医` : '倪海厦 · 经方中医'
})

export default router
