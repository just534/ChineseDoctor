import type { Directive } from 'vue'
import { useAuthStore } from '@/stores/auth'

/** v-perm="'user:create'" 或 v-perm="['a','b']"：无权限时移除元素 */
export const perm: Directive<HTMLElement, string | string[]> = {
  mounted(el, binding) {
    if (!useAuthStore().can(binding.value)) el.parentNode?.removeChild(el)
  },
}
