<template>
  <div class="admin-card">
    <div class="admin-toolbar">
      <el-input v-model="q.keyword" placeholder="诊断 / 方剂 / 病机 / 患者" clearable style="width: 260px" :prefix-icon="Search" @keyup.enter="load(1)" @clear="load(1)" />
      <el-button :icon="Search" @click="load(1)">查询</el-button>
      <span class="spacer" />
      <el-button type="primary" :icon="Plus" @click="openEdit()">新增医案</el-button>
    </div>
    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column prop="seq" label="序号" width="76" align="center" />
      <el-table-column prop="date_text" label="日期" width="130" show-overflow-tooltip />
      <el-table-column prop="patient" label="患者" width="130" show-overflow-tooltip />
      <el-table-column prop="diagnosis" label="主要诊断" min-width="180" show-overflow-tooltip />
      <el-table-column prop="prescription" label="方剂" min-width="240" show-overflow-tooltip />
      <el-table-column label="发布" width="80" align="center">
        <template #default="{ row }: { row: any }"><el-switch :model-value="row.is_published" @change="(v: string | number | boolean) => togglePublish(row, !!v)" /></template>
      </el-table-column>
      <el-table-column label="操作" width="130" fixed="right">
        <template #default="{ row }: { row: any }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="q.page" :page-size="q.size" :total="total" layout="total, prev, pager, next, jumper" background @current-change="load" />

    <el-dialog v-model="dialog" :title="form.id ? `编辑医案 #${form.seq}` : '新增医案'" width="760px" destroy-on-close top="5vh">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" class="case-form">
        <div class="row3">
          <el-form-item label="序号"><el-input-number v-model="form.seq" :min="1" placeholder="自动" controls-position="right" /></el-form-item>
          <el-form-item label="日期"><el-input v-model="form.date_text" placeholder="如 2008-05-12" /></el-form-item>
          <el-form-item label="年份"><el-input-number v-model="form.year" :min="1900" :max="2100" controls-position="right" /></el-form-item>
        </div>
        <el-form-item label="患者"><el-input v-model="form.patient" placeholder="性别、年龄等" /></el-form-item>
        <el-form-item label="主要诊断" prop="diagnosis"><el-input v-model="form.diagnosis" /></el-form-item>
        <el-form-item v-for="f in textFields" :key="f.key" :label="f.label">
          <el-input v-model="(form as any)[f.key]" type="textarea" :autosize="{ minRows: 2, maxRows: 6 }" />
        </el-form-item>
        <el-form-item label="发布"><el-switch v-model="form.is_published" /></el-form-item>
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
import { Plus, Search } from '@element-plus/icons-vue'
import { caseApi, type MedicalCase } from '@/api'

const q = reactive({ keyword: '', page: 1, size: 20 })
const rows = ref<MedicalCase[]>([])
const total = ref(0)
const loading = ref(false)
const saving = ref(false)
const dialog = ref(false)
const formRef = ref<FormInstance>()
const textFields = [
  { key: 'pathogenesis', label: '中医病机' },
  { key: 'western_view', label: '西医背景' },
  { key: 'prescription', label: '方剂剂量' },
  { key: 'acupuncture', label: '针灸方案' },
  { key: 'principle', label: '治疗原则' },
  { key: 'outcome', label: '疗程结果' },
  { key: 'advice', label: '生活医嘱' },
  { key: 'comment', label: '倪师观点' },
]
const blank = (): Partial<MedicalCase> & { id?: number } => ({
  id: undefined, seq: undefined, date_text: '', year: null, patient: '', diagnosis: '', pathogenesis: '', western_view: '',
  prescription: '', acupuncture: '', principle: '', outcome: '', advice: '', comment: '', is_published: true,
})
const form = reactive(blank())
const rules: FormRules = { diagnosis: [{ required: true, message: '请填写主要诊断' }] }

async function load(page = q.page) {
  q.page = page
  loading.value = true
  try {
    const res = await caseApi.list({ ...q, include_unpublished: true })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function openEdit(row?: MedicalCase) {
  Object.assign(form, blank(), row ?? {})
  dialog.value = true
}

async function save() {
  if (!(await formRef.value?.validate().catch(() => false))) return
  saving.value = true
  try {
    const { id, ...body } = form
    if (id) await caseApi.update(id, body)
    else await caseApi.create(body)
    ElMessage.success('已保存')
    dialog.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function togglePublish(row: MedicalCase, v: boolean) {
  await caseApi.update(row.id, { ...row, is_published: v })
  row.is_published = v
}

async function remove(row: MedicalCase) {
  await ElMessageBox.confirm(`删除医案 #${row.seq}「${row.diagnosis.slice(0, 20)}」？`, '删除医案', { type: 'warning' })
  await caseApi.remove(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(() => load(1))
</script>

<style scoped lang="scss">
.row3 { display: grid; grid-template-columns: repeat(3, 1fr); }
.case-form { max-height: 68vh; overflow-y: auto; padding-right: 8px; }
</style>
