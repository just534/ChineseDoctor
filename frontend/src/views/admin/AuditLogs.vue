<template>
  <div class="admin-card">
    <div class="admin-toolbar">
      <el-input v-model="q.keyword" placeholder="用户 / 对象 / IP / 详情" clearable style="width: 240px" :prefix-icon="Search" @keyup.enter="load(1)" @clear="load(1)" />
      <el-select v-model="q.action" placeholder="操作类型" clearable style="width: 150px" @change="load(1)">
        <el-option v-for="a in actionGroups" :key="a.value" :label="a.label" :value="a.value" />
      </el-select>
      <el-select v-model="q.success" placeholder="结果" clearable style="width: 110px" @change="load(1)">
        <el-option label="成功" :value="true" />
        <el-option label="失败" :value="false" />
      </el-select>
      <el-button :icon="Search" @click="load(1)">查询</el-button>
    </div>
    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column label="时间" width="160"><template #default="{ row }: { row: any }">{{ fmtTime(row.created_at) }}</template></el-table-column>
      <el-table-column label="用户" width="130"><template #default="{ row }: { row: any }">{{ row.username || '—' }}</template></el-table-column>
      <el-table-column label="操作" width="130">
        <template #default="{ row }: { row: any }"><el-tag size="small" effect="plain" :type="tagType(row.action)">{{ ACTION_LABELS[row.action] || row.action }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="target" label="对象" min-width="180" show-overflow-tooltip />
      <el-table-column prop="detail" label="详情" min-width="220" show-overflow-tooltip />
      <el-table-column prop="ip" label="IP" width="130" />
      <el-table-column label="结果" width="80" align="center">
        <template #default="{ row }: { row: any }">
          <el-icon :color="row.success ? 'var(--el-color-success)' : 'var(--el-color-danger)'"><component :is="row.success ? CircleCheck : CircleClose" /></el-icon>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="q.page" v-model:page-size="q.size" :total="total" :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next" background @current-change="load" @size-change="load(1)" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { CircleCheck, CircleClose, Search } from '@element-plus/icons-vue'
import { miscApi, type AuditLog } from '@/api'
import { ACTION_LABELS, fmtTime } from '@/utils/format'

const q = reactive({ keyword: '', action: '', success: undefined as boolean | undefined, page: 1, size: 20 })
const rows = ref<AuditLog[]>([])
const total = ref(0)
const loading = ref(false)
const actionGroups = [
  { value: 'login', label: '登录' },
  { value: 'register', label: '注册' },
  { value: 'user.', label: '用户管理' },
  { value: 'role.', label: '角色权限' },
  { value: 'document.', label: '典籍' },
  { value: 'chapter.', label: '章节' },
  { value: 'case.', label: '医案' },
  { value: 'ai.', label: 'AI 问诊' },
]

const tagType = (a: string) => (a.endsWith('delete') ? 'danger' : a.startsWith('role') || a.startsWith('user') ? 'warning' : a === 'login' ? 'success' : 'info')

async function load(page = q.page) {
  q.page = page
  loading.value = true
  try {
    const res = await miscApi.auditLogs({ ...q })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

onMounted(() => load(1))
</script>
