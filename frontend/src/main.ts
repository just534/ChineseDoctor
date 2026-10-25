import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'element-plus/theme-chalk/el-message.css'
import 'element-plus/theme-chalk/el-message-box.css'
import 'element-plus/theme-chalk/el-loading.css'
import './styles/main.scss'
import App from './App.vue'
import router from './router'
import { perm } from './directives/perm'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.directive('perm', perm)
app.mount('#app')

window.addEventListener('auth:expired', () => {
  const auth = useAuthStore()
  if (!auth.user) return
  auth.logout()
  const cur = router.currentRoute.value
  if (cur.matched.some((r) => r.meta.auth)) router.replace({ name: 'login', query: { redirect: cur.fullPath } })
})
