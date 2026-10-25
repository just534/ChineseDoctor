export function fmtTime(v?: string | null) {
  if (!v) return '—'
  const d = new Date(v)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

export function fmtNum(n: number) {
  if (n >= 10000) return (n / 10000).toFixed(n >= 100000 ? 0 : 1) + ' 万'
  return n.toLocaleString('zh-CN')
}

export function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!)
}

export function highlight(text: string, kw: string) {
  const safe = escapeHtml(text)
  const words = kw.split(/\s+/).filter(Boolean).map((w) => escapeHtml(w).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  if (!words.length) return safe
  return safe.replace(new RegExp(`(${words.join('|')})`, 'gi'), '<mark>$1</mark>')
}

export const ACTION_LABELS: Record<string, string> = {
  login: '登录',
  register: '注册',
  change_password: '修改密码',
  logout_all: '退出所有设备',
  'user.create': '新增用户',
  'user.update': '编辑用户',
  'user.delete': '删除用户',
  'user.reset_password': '重置密码',
  'user.unlock': '解锁用户',
  'user.kick': '强制下线',
  'role.create': '新增角色',
  'role.update': '编辑角色',
  'role.delete': '删除角色',
  'document.create': '新增典籍',
  'document.update': '编辑典籍',
  'document.delete': '删除典籍',
  'chapter.create': '新增章节',
  'chapter.update': '编辑章节',
  'chapter.delete': '删除章节',
  'case.create': '新增医案',
  'case.update': '编辑医案',
  'case.delete': '删除医案',
  'ai.chat': 'AI 问诊',
}
