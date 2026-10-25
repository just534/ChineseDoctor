import http from './http'

export interface Page<T> { items: T[]; total: number; page: number; size: number }
export interface RoleBrief { id: number; code: string; name: string }
export interface User {
  id: number; username: string; email: string | null; nickname: string; phone: string | null; avatar: string | null
  is_active: boolean; is_superuser: boolean; must_change_password: boolean; last_login_at: string | null
  last_login_ip: string | null; remark: string; created_at: string; roles: RoleBrief[]
}
export interface Me extends User { permissions: string[] }
export interface Role {
  id: number; code: string; name: string; description: string; is_system: boolean; is_active: boolean
  sort: number; created_at: string; permissions: string[]; user_count: number
}
export interface Permission { id: number; code: string; name: string; group: string; description: string }
export interface DocumentItem {
  id: number; slug: string; title: string; category: string; summary: string; word_count: number; sort: number
  is_published: boolean; view_count: number; updated_at: string; chapter_count: number
}
export interface ChapterBrief { id: number; title: string; word_count: number; sort: number }
export interface DocumentDetail extends DocumentItem { chapters: ChapterBrief[] }
export interface Chapter extends ChapterBrief {
  document_id: number; content: string; updated_at: string; prev_id?: number | null; next_id?: number | null
}
export interface MedicalCase {
  id: number; seq: number; date_text: string; year: number | null; patient: string; diagnosis: string
  pathogenesis: string; western_view: string; prescription: string; acupuncture: string; principle: string
  outcome: string; advice: string; comment: string; is_published: boolean
}
export interface SearchHit {
  type: 'chapter' | 'case'; id: number; title: string; subtitle: string; snippet: string
  document_slug: string | null; chapter_id: number | null
}
export interface Favorite { id: number; target_type: 'document' | 'case'; target_id: number; title: string; subtitle: string; created_at: string }
export interface AuditLog { id: number; user_id: number | null; username: string; action: string; target: string; detail: string; ip: string; success: boolean; created_at: string }
export interface Tokens { access_token: string; refresh_token: string }

const d = <T>(p: Promise<{ data: T }>) => p.then((r) => r.data)

export const authApi = {
  config: () => d<{ app_name: string; allow_registration: boolean; ai_enabled: boolean }>(http.get('/auth/config')),
  login: (username: string, password: string) => d<Tokens>(http.post('/auth/login', { username, password })),
  register: (body: { username: string; password: string; email?: string; nickname?: string }) => d<Tokens>(http.post('/auth/register', body)),
  me: () => d<Me>(http.get('/auth/me', { silent: true })),
  updateProfile: (body: Partial<Pick<User, 'nickname' | 'email' | 'phone'>>) => d<Me>(http.put('/auth/me', body)),
  changePassword: (old_password: string, new_password: string) => d<Tokens>(http.post('/auth/change-password', { old_password, new_password })),
  logoutAll: () => d(http.post('/auth/logout-all')),
}

export const userApi = {
  list: (params: Record<string, unknown>) => d<Page<User>>(http.get('/users', { params })),
  create: (body: Record<string, unknown>) => d<User>(http.post('/users', body)),
  update: (id: number, body: Record<string, unknown>) => d<User>(http.put(`/users/${id}`, body)),
  remove: (id: number) => d(http.delete(`/users/${id}`)),
  resetPassword: (id: number, new_password: string) => d(http.post(`/users/${id}/reset-password`, { new_password })),
  unlock: (id: number) => d(http.post(`/users/${id}/unlock`)),
  kick: (id: number) => d(http.post(`/users/${id}/kick`)),
}

export const roleApi = {
  list: () => d<Role[]>(http.get('/roles')),
  options: () => d<Role[]>(http.get('/roles/options')),
  permissions: () => d<Permission[]>(http.get('/permissions')),
  create: (body: Record<string, unknown>) => d<Role>(http.post('/roles', body)),
  update: (id: number, body: Record<string, unknown>) => d<Role>(http.put(`/roles/${id}`, body)),
  remove: (id: number) => d(http.delete(`/roles/${id}`)),
}

export const docApi = {
  categories: () => d<{ name: string; count: number }[]>(http.get('/documents/categories')),
  list: (params: Record<string, unknown> = {}) => d<DocumentItem[]>(http.get('/documents', { params })),
  get: (slug: string) => d<DocumentDetail>(http.get(`/documents/${slug}`)),
  chapter: (slug: string, id: number) => d<Chapter>(http.get(`/documents/${slug}/chapters/${id}`)),
  create: (body: Record<string, unknown>) => d<DocumentItem>(http.post('/documents', body)),
  update: (id: number, body: Record<string, unknown>) => d<DocumentItem>(http.put(`/documents/${id}`, body)),
  remove: (id: number) => d(http.delete(`/documents/${id}`)),
  createChapter: (docId: number, body: Record<string, unknown>) => d<Chapter>(http.post(`/documents/${docId}/chapters`, body)),
  updateChapter: (id: number, body: Record<string, unknown>) => d<Chapter>(http.put(`/chapters/${id}`, body)),
  removeChapter: (id: number) => d(http.delete(`/chapters/${id}`)),
}

export const caseApi = {
  list: (params: Record<string, unknown>) => d<Page<MedicalCase>>(http.get('/cases', { params })),
  years: () => d<{ year: number; count: number }[]>(http.get('/cases/years')),
  get: (id: number) => d<MedicalCase>(http.get(`/cases/${id}`)),
  create: (body: Partial<MedicalCase>) => d<MedicalCase>(http.post('/cases', body)),
  update: (id: number, body: Partial<MedicalCase>) => d<MedicalCase>(http.put(`/cases/${id}`, body)),
  remove: (id: number) => d(http.delete(`/cases/${id}`)),
}

export const miscApi = {
  search: (q: string, scope = 'all') => d<SearchHit[]>(http.get('/search', { params: { q, scope, limit: 50 } })),
  publicStats: () => d<{ documents: number; chapters: number; words: number; cases: number }>(http.get('/stats/public')),
  dashboard: () => d<any>(http.get('/stats/dashboard')),
  auditLogs: (params: Record<string, unknown>) => d<Page<AuditLog>>(http.get('/audit-logs', { params })),
  favorites: () => d<Favorite[]>(http.get('/favorites')),
  addFavorite: (target_type: string, target_id: number) => d(http.post('/favorites', { target_type, target_id })),
  removeFavorite: (target_type: string, target_id: number) => d(http.delete('/favorites', { params: { target_type, target_id } })),
  checkFavorite: (target_type: string, target_id: number) =>
    d<{ favorited: boolean }>(http.get('/favorites/check', { params: { target_type, target_id }, silent: true })),
  aiQuota: () => d<{ enabled: boolean; used: number; limit: number | null }>(http.get('/ai/quota', { silent: true })),
}
