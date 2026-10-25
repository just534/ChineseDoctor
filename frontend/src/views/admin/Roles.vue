<template>
  <div class="roles-page">
    <div class="admin-card role-list">
      <div class="admin-toolbar">
        <h3 class="admin-title" style="margin: 0">角色</h3>
        <span class="spacer" />
        <el-button v-perm="'role:manage'" type="primary" size="small" :icon="Plus" @click="openCreate">新增</el-button>
      </div>
      <div v-loading="loading">
        <div v-for="r in roles" :key="r.id" class="role" :class="{ active: current?.id === r.id }" @click="select(r)">
          <div class="role-head">
            <span class="kai role-name">{{ r.name }}</span>
            <el-tag v-if="r.is_system" size="small" effect="plain">内置</el-tag>
            <el-tag v-if="!r.is_active" size="small" type="info">停用</el-tag>
            <span class="spacer" />
            <span class="cell-muted">{{ r.user_count }} 人</span>
          </div>
          <div class="cell-muted code">{{ r.code }}</div>
          <div class="desc">{{ r.description || '—' }}</div>
        </div>
      </div>
    </div>

    <div class="admin-card perm-panel" v-if="current">
      <div class="admin-toolbar">
        <div>
          <h3 class="admin-title" style="margin: 0">{{ current.name }} · 权限配置</h3>
          <div class="cell-muted">已授予 {{ checked.length }} / {{ permissions.length }} 项权限</div>
        </div>
        <span class="spacer" />
        <template v-if="canManage">
          <el-button size="small" @click="openEdit(current)">编辑信息</el-button>
          <el-button v-if="!current.is_system" size="small" type="danger" plain @click="remove(current)">删除</el-button>
        </template>
      </div>

      <el-alert v-if="isSuper" type="info" :closable="false" show-icon title="超级管理员拥有系统全部权限，不可修改。" class="mb" />

      <div class="groups">
        <div v-for="g in groups" :key="g.name" class="group">
          <div class="group-head">
            <el-checkbox
              :model-value="g.items.every((p) => checked.includes(p.code))"
              :indeterminate="g.items.some((p) => checked.includes(p.code)) && !g.items.every((p) => checked.includes(p.code))"
              :disabled="readonly"
              @change="(v) => toggleGroup(g.items, v as boolean)"
            >
              <span class="kai g-name">{{ g.name }}</span>
            </el-checkbox>
          </div>
          <el-checkbox-group v-model="checked" :disabled="readonly" class="items">
            <el-checkbox v-for="p in g.items" :key="p.code" :value="p.code" class="item">
              {{ p.name }} <span class="cell-muted">{{ p.code }}</span>
            </el-checkbox>
          </el-checkbox-group>
        </div>
      </div>

      <div v-if="!readonly" class="save-bar">
        <el-button @click="checked = [...current.permissions]">还原</el-button>
        <el-button type="primary" :loading="saving" :disabled="!dirty" @click="savePerms">保存权限</el-button>
      </div>
    </div>

    <el-dialog v-model="dialog" :title="editing ? '编辑角色' : '新增角色'" width="480px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="角色编码" prop="code"><el-input v-model="form.code" :disabled="!!editing" placeholder="小写字母开头，如 reviewer" /></el-form-item>
        <el-form-item label="角色名称" prop="name"><el-input v-model="form.name" maxlength="50" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" maxlength="255" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort" :min="0" :max="999" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.is_active" :disabled="editing?.code === 'super_admin'" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveRole">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { roleApi, type Permission, type Role } from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const roles = ref<Role[]>([])
const permissions = ref<Permission[]>([])
const current = ref<Role | null>(null)
const checked = ref<string[]>([])
const loading = ref(false)
const saving = ref(false)
const dialog = ref(false)
const editing = ref<Role | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({ code: '', name: '', description: '', sort: 50, is_active: true })
const rules: FormRules = {
  code: [{ required: true, message: '请输入编码' }, { pattern: /^[a-z][a-z0-9_]{1,49}$/, message: '小写字母开头，可含数字与下划线' }],
  name: [{ required: true, message: '请输入名称' }],
}

const canManage = computed(() => auth.can('role:manage'))
const isSuper = computed(() => current.value?.code === 'super_admin')
const readonly = computed(() => !canManage.value || isSuper.value)
const dirty = computed(() => [...checked.value].sort().join() !== [...(current.value?.permissions ?? [])].sort().join())
const groups = computed(() => {
  const map = new Map<string, Permission[]>()
  for (const p of permissions.value) map.set(p.group, [...(map.get(p.group) ?? []), p])
  return [...map].map(([name, items]) => ({ name, items }))
})

function select(r: Role) {
  current.value = r
  checked.value = [...r.permissions]
}

function toggleGroup(items: Permission[], v: boolean) {
  const codes = items.map((p) => p.code)
  checked.value = v ? [...new Set([...checked.value, ...codes])] : checked.value.filter((c) => !codes.includes(c))
}

async function load(keepId?: number) {
  loading.value = true
  try {
    roles.value = await roleApi.list()
    const r = roles.value.find((x) => x.id === keepId) ?? roles.value[0]
    if (r) select(r)
  } finally {
    loading.value = false
  }
}

async function savePerms() {
  if (!current.value) return
  saving.value = true
  try {
    await roleApi.update(current.value.id, { permissions: checked.value })
    ElMessage.success('权限已更新，立即生效')
    await load(current.value.id)
  } finally {
    saving.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, { code: '', name: '', description: '', sort: 50, is_active: true })
  dialog.value = true
}

function openEdit(r: Role) {
  editing.value = r
  Object.assign(form, { code: r.code, name: r.name, description: r.description, sort: r.sort, is_active: r.is_active })
  dialog.value = true
}

async function saveRole() {
  if (!(await formRef.value?.validate().catch(() => false))) return
  saving.value = true
  try {
    let id: number
    if (editing.value) {
      const { code, ...rest } = form
      id = (await roleApi.update(editing.value.id, rest)).id
    } else {
      id = (await roleApi.create({ ...form, permissions: [] })).id
    }
    ElMessage.success('已保存')
    dialog.value = false
    await load(id)
  } finally {
    saving.value = false
  }
}

async function remove(r: Role) {
  await ElMessageBox.confirm(`确定删除角色「${r.name}」？`, '删除角色', { type: 'warning' })
  await roleApi.remove(r.id)
  ElMessage.success('已删除')
  load()
}

onMounted(async () => {
  permissions.value = await roleApi.permissions()
  load()
})
</script>

<style scoped lang="scss">
.roles-page { display: flex; gap: 16px; align-items: flex-start; }
.role-list { width: 320px; flex-shrink: 0; }
.role {
  padding: 12px 14px;
  border: 1px solid var(--line-soft);
  border-radius: 3px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s;
  &:hover { border-color: var(--gold); }
  &.active { border-color: var(--cinnabar); background: var(--cinnabar-soft); box-shadow: inset 3px 0 0 var(--cinnabar); }
}
.role-head { display: flex; align-items: center; gap: 6px; .spacer { flex: 1; } }
.role-name { font-size: 17px; letter-spacing: 1px; }
.code { font-family: monospace; }
.desc { font-size: 13px; color: var(--ink-2); margin-top: 2px; }
.perm-panel { flex: 1; min-width: 0; }
.mb { margin-bottom: 14px; }
.groups { display: flex; flex-direction: column; gap: 14px; }
.group { border: 1px solid var(--line-soft); border-radius: 3px; }
.group-head { background: #f1e8d5; padding: 6px 14px; border-bottom: 1px solid var(--line-soft); }
.g-name { font-size: 15px; letter-spacing: 2px; }
.items { padding: 10px 14px; display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 4px 12px; }
.item { margin-right: 0; }
.save-bar { display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; padding-top: 14px; border-top: 1px dashed var(--line); }
@media (max-width: 900px) {
  .roles-page { flex-direction: column; }
  .role-list, .perm-panel { width: 100%; }
}
</style>
