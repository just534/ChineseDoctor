<template>
  <div class="admin-card">
    <div class="admin-toolbar">
      <el-input v-model="q.keyword" placeholder="用户名 / 昵称 / 邮箱 / 手机" clearable style="width: 240px" :prefix-icon="Search" @keyup.enter="load(1)" @clear="load(1)" />
      <el-select v-model="q.role_id" placeholder="角色" clearable style="width: 150px" @change="load(1)">
        <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
      </el-select>
      <el-select v-model="q.is_active" placeholder="状态" clearable style="width: 120px" @change="load(1)">
        <el-option label="正常" :value="true" />
        <el-option label="禁用" :value="false" />
      </el-select>
      <el-button :icon="Search" @click="load(1)">查询</el-button>
      <span class="spacer" />
      <el-button v-perm="'user:create'" type="primary" :icon="Plus" @click="openCreate">新增用户</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column label="用户" min-width="180">
        <template #default="{ row }: { row: any }">
          <div class="u">
            <span class="avatar kai" :class="{ su: row.is_superuser }">{{ (row.nickname || row.username).slice(0, 1) }}</span>
            <div>
              <div>{{ row.nickname || row.username }}</div>
              <div class="cell-muted">@{{ row.username }}</div>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="联系方式" min-width="180">
        <template #default="{ row }: { row: any }">
          <div>{{ row.email || '—' }}</div>
          <div class="cell-muted">{{ row.phone || '' }}</div>
        </template>
      </el-table-column>
      <el-table-column label="角色" min-width="160">
        <template #default="{ row }: { row: any }">
          <el-tag v-for="r in row.roles" :key="r.id" size="small" :type="r.code === 'super_admin' ? 'danger' : r.code === 'admin' ? 'warning' : 'info'" effect="plain" class="role-tag">{{ r.name }}</el-tag>
          <span v-if="!row.roles.length" class="cell-muted">未分配</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }: { row: any }">
          <el-switch
            :model-value="row.is_active"
            :disabled="!auth.can('user:update') || row.id === auth.user?.id"
            @change="(v: string | number | boolean) => toggleActive(row, !!v)"
          />
        </template>
      </el-table-column>
      <el-table-column label="最近登录" width="170">
        <template #default="{ row }: { row: any }">
          <div>{{ fmtTime(row.last_login_at) }}</div>
          <div class="cell-muted">{{ row.last_login_ip || '' }}</div>
        </template>
      </el-table-column>
      <el-table-column label="注册时间" width="150">
        <template #default="{ row }: { row: any }">{{ fmtTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }: { row: any }">
          <el-button v-perm="'user:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-dropdown trigger="click" @command="(c: string) => onMore(c, row)">
            <el-button link type="primary">更多<el-icon><ArrowDown /></el-icon></el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-if="auth.can('user:reset_password')" command="reset">重置密码</el-dropdown-item>
                <el-dropdown-item v-if="auth.can('user:update')" command="unlock">解除锁定</el-dropdown-item>
                <el-dropdown-item v-if="auth.can('user:update')" command="kick">强制下线</el-dropdown-item>
                <el-dropdown-item v-if="auth.can('user:delete')" command="delete" divided :disabled="row.id === auth.user?.id">
                  <span style="color: var(--el-color-danger)">删除用户</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="q.page" v-model:page-size="q.size" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" background @current-change="load" @size-change="load(1)" />

    <el-dialog v-model="dialog" :title="editing ? '编辑用户' : '新增用户'" width="560px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="!!editing" placeholder="字母开头，3-30 位" />
        </el-form-item>
        <el-form-item v-if="!editing" label="初始密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 8 位，包含字母和数字">
            <template #append><el-button @click="genPwd">生成</el-button></template>
          </el-input>
        </el-form-item>
        <el-form-item label="昵称"><el-input v-model="form.nickname" maxlength="50" /></el-form-item>
        <el-form-item label="邮箱" prop="email"><el-input v-model="form.email" /></el-form-item>
        <el-form-item label="手机"><el-input v-model="form.phone" maxlength="30" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_ids" multiple placeholder="选择角色" style="width: 100%">
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id">
              <span>{{ r.name }}</span><span class="opt-desc">{{ r.description }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="状态"><el-switch v-model="form.is_active" active-text="正常" inactive-text="禁用" /></el-form-item>
        <el-form-item v-if="!editing" label="首次登录"><el-checkbox v-model="form.must_change_password">要求修改密码</el-checkbox></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" maxlength="255" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ArrowDown, Plus, Search } from '@element-plus/icons-vue'
import { roleApi, userApi, type Role, type User } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { fmtTime } from '@/utils/format'

const auth = useAuthStore()
const q = reactive({ keyword: '', role_id: undefined as number | undefined, is_active: undefined as boolean | undefined, page: 1, size: 20 })
const rows = ref<User[]>([])
const total = ref(0)
const loading = ref(false)
const roles = ref<Role[]>([])
const dialog = ref(false)
const editing = ref<User | null>(null)
const saving = ref(false)
const formRef = ref<FormInstance>()
const blank = () => ({ username: '', password: '', nickname: '', email: '', phone: '', role_ids: [] as number[], is_active: true, must_change_password: true, remark: '' })
const form = reactive(blank())
const pwdRule = /^(?=.*[A-Za-z])(?=.*\d).{8,72}$/
const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名' }, { pattern: /^[A-Za-z][A-Za-z0-9_]{2,29}$/, message: '字母开头，3-30 位字母数字下划线' }],
  password: [{ required: true, message: '请输入密码' }, { pattern: pwdRule, message: '至少 8 位，需包含字母和数字' }],
  email: [{ type: 'email', message: '邮箱格式不正确' }],
}

async function load(page = q.page) {
  q.page = page
  loading.value = true
  try {
    const res = await userApi.list({ ...q })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function genPwd() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
  const arr = crypto.getRandomValues(new Uint32Array(10))
  form.password = Array.from(arr, (n) => chars[n % chars.length]).join('') + Math.floor(Math.random() * 10) + 'a'
}

function openCreate() {
  editing.value = null
  Object.assign(form, blank())
  const member = roles.value.find((r) => r.code === 'member')
  if (member) form.role_ids = [member.id]
  dialog.value = true
}

function openEdit(u: User) {
  editing.value = u
  Object.assign(form, { ...blank(), ...u, email: u.email ?? '', phone: u.phone ?? '', role_ids: u.roles.map((r) => r.id) })
  dialog.value = true
}

async function save() {
  if (!(await formRef.value?.validate().catch(() => false))) return
  saving.value = true
  try {
    const body = { ...form, email: form.email || null, phone: form.phone || null }
    if (editing.value) {
      const { username, password, must_change_password, ...rest } = body
      await userApi.update(editing.value.id, rest)
    } else {
      await userApi.create(body)
    }
    ElMessage.success('已保存')
    dialog.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function toggleActive(u: User, v: boolean) {
  await userApi.update(u.id, { is_active: v })
  u.is_active = v
  ElMessage.success(v ? '已启用' : '已禁用，该用户已被强制下线')
}

async function onMore(cmd: string, u: User) {
  const name = u.nickname || u.username
  if (cmd === 'reset') {
    const { value } = await ElMessageBox.prompt(`为「${name}」设置新密码（用户下次登录需修改）`, '重置密码', {
      inputPattern: pwdRule,
      inputErrorMessage: '至少 8 位，需包含字母和数字',
      inputType: 'password',
    })
    await userApi.resetPassword(u.id, value)
    ElMessage.success('密码已重置')
  } else if (cmd === 'unlock') {
    await userApi.unlock(u.id)
    ElMessage.success('已解除登录锁定')
  } else if (cmd === 'kick') {
    await ElMessageBox.confirm(`确定让「${name}」在所有设备上下线？`, '强制下线', { type: 'warning' })
    await userApi.kick(u.id)
    ElMessage.success('已强制下线')
  } else if (cmd === 'delete') {
    await ElMessageBox.confirm(`删除后不可恢复，确定删除用户「${name}」？`, '删除用户', { type: 'warning', confirmButtonClass: 'el-button--danger' })
    await userApi.remove(u.id)
    ElMessage.success('已删除')
    load()
  }
}

onMounted(async () => {
  load(1)
  roles.value = await roleApi.options()
})
</script>

<style scoped lang="scss">
.u { display: flex; align-items: center; gap: 10px; }
.avatar {
  width: 34px; height: 34px; border-radius: 50%; background: var(--indigo); color: #f5eedf;
  display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
  &.su { background: var(--cinnabar); }
}
.role-tag { margin: 2px 4px 2px 0; }
.opt-desc { float: right; color: var(--ink-3); font-size: 12px; margin-left: 16px; }
</style>
