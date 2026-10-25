const A = 'nhx_access'
const R = 'nhx_refresh'

function safeGet(k: string) {
  try { return localStorage.getItem(k) } catch { return null }
}

export const tokenStore = {
  get access() { return safeGet(A) },
  get refresh() { return safeGet(R) },
  set(access: string, refresh: string) {
    try { localStorage.setItem(A, access); localStorage.setItem(R, refresh) } catch { /* ignore */ }
  },
  clear() {
    try { localStorage.removeItem(A); localStorage.removeItem(R) } catch { /* ignore */ }
  },
}
