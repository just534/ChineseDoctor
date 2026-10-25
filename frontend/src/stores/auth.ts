import { defineStore } from 'pinia'
import { authApi, type Me, type Tokens } from '@/api'
import { tokenStore } from '@/utils/token'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as Me | null,
    loaded: false,
    config: { app_name: '倪海厦经方中医', allow_registration: true, ai_enabled: false },
  }),
  getters: {
    isLoggedIn: (s) => !!s.user,
    perms: (s) => new Set(s.user?.permissions ?? []),
  },
  actions: {
    can(code: string | string[]) {
      if (!this.user) return false
      if (this.user.is_superuser) return true
      const codes = Array.isArray(code) ? code : [code]
      return codes.every((c) => this.perms.has(c))
    },
    async init() {
      if (this.loaded) return
      const [cfg] = await Promise.allSettled([authApi.config(), this.fetchMe()])
      if (cfg.status === 'fulfilled') this.config = cfg.value
      this.loaded = true
    },
    async fetchMe() {
      if (!tokenStore.access) { this.user = null; return }
      try {
        this.user = await authApi.me()
      } catch {
        this.user = null
      }
    },
    async applyTokens(t: Tokens) {
      tokenStore.set(t.access_token, t.refresh_token)
      await this.fetchMe()
    },
    async login(username: string, password: string) {
      await this.applyTokens(await authApi.login(username, password))
    },
    async register(body: { username: string; password: string; email?: string; nickname?: string }) {
      await this.applyTokens(await authApi.register(body))
    },
    logout() {
      tokenStore.clear()
      this.user = null
    },
  },
})
