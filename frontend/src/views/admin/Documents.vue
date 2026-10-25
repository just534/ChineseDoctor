<template>
  <div class="admin-card">
    <div class="admin-toolbar">
      <el-input v-model="keyword" placeholder="书名 / 简介" clearable style="width: 220px" :prefix-icon="Search" />
      <el-select v-model="category" placeholder="分类" clearable style="width: 150px">
        <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
      </el-select>
      <span class="spacer" />
      <el-button type="primary" :icon="Plus" @click="openCreate">新增典籍</el-button>
    </div>

    <el-table v-loading="loading" :data="filtered" stripe>
      <el-table-column prop="sort" label="序" width="60" align="center" />
      <el-table-column label="书名" min-width="260">
        <template #default="{ row }: { row: any }">
          <div class="kai title">{{ row.title }}</div>
          <div class="cell-muted">{{ row.slug }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="category" label="分类" width="110" />
      <el-table-column label="章节 / 字数" width="130">
        <template #default="{ row }: { row: any }">{{ row.chapter_count }} 章 · {{ fmtNum(row.word_count) }}</template>
      </el-table-column>
      <el-table-column prop="view_count" label="阅读" width="80" align="center" />
      <el-table-column label="发布" width="80" align="center">
        <template #default="{ row }: { row: any }"><el-switch :model-value="row.is_published" @change="(v: string | number | boolean) => togglePublish(row, !!v)" /></template>
      </el-table-column>
      <el-table-column label="更新时间" width="150">
        <template #default="{ row }: { row: any }">{{ fmtTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="210" fixed="right">
        <template #default="{ row }: { row: any }">
          <el-button link type="primary" @click="openChapters(row)">章节</el-button>
          <el-button link type="primary" @click="openEdit(row)">信息</el-button>
          <el-button link type="primary" @click="$router.push(`/library/${row.slug}`)">预览</el-button>
          <el-button link type="danger" @click="removeDoc(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 典籍信息 -->
    <el-dialog v-model="metaDialog" :title="editing ? '编辑典籍信息' : '新增典籍'" width="560px" destroy-on-close>
      <el-form ref="metaRef" :model="meta" :rules="metaRules" label-width="80px">
        <el-form-item label="标识" prop="slug"><el-input v-model="meta.slug" :disabled="!!editing" placeholder="小写字母、数字、连字符，用于网址" /></el-form-item>
        <el-form-item label="书名" prop="title"><el-input v-model="meta.title" /></el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="meta.category" filterable allow-create style="width: 100%">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="简介"><el-input v-model="meta.summary" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="meta.sort" :min="0" /></el-form-item>
        <el-form-item label="发布"><el-switch v-model="meta.is_published" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="metaDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveMeta">保存</el-button>
      </template>
    </el-dialog>

    <!-- 章节编辑 -->
    <el-drawer v-model="chapterDrawer" size="92%" :title="doc ? `章节编辑 ·《${doc.title}》` : ''" destroy-on-close>
      <div v-if="doc" class="editor">
        <aside class="ch-list">
          <el-button type="primary" plain size="small" :icon="Plus" class="add" @click="newChapter">新增章节</el-button>
          <div v-for="(c, i) in doc.chapters" :key="c.id" class="ch" :class="{ active: chapter?.id === c.id }" @click="selectChapter(c.id)">
            <span class="no">{{ i + 1 }}</span><span class="t">{{ c.title }}</span>
          </div>
        </aside>
        <section class="ch-edit" v-loading="chLoading">
          <template v-if="chapter">
            <div class="ch-bar">
              <el-input v-model="chapter.title" placeholder="章节标题" class="ch-title" />
              <el-input-number v-model="chapter.sort" :min="0" controls-position="right" style="width: 110px" />
              <el-radio-group v-model="mode" size="small">
                <el-radio-button value="split">分栏</el-radio-button>
                <el-radio-button value="edit">编辑</el-radio-button>
                <el-radio-button value="preview">预览</el-radio-button>
              </el-radio-group>
              <span class="spacer" />
              <el-button v-if="chapter.id" type="danger" plain @click="removeChapter">删除</el-button>
              <el-button type="primary" :loading="saving" @click="saveChapter">保存章节</el-button>
            </div>
            <div class="panes" :class="mode">
              <textarea v-show="mode !== 'preview'" v-model="chapter.content" class="src" spellcheck="false" placeholder="使用 Markdown 编写章节内容" />
              <div v-show="mode !== 'edit'" class="preview md" v-html="renderSimple(chapter.content)" />
            </div>
            <div class="cell-muted">约 {{ chapter.content.length.toLocaleString() }} 字符 · 支持 Markdown（标题、表格、引用、加粗）</div>
          </template>
          <el-empty v-else description="选择左侧章节开始编辑" />
        </section>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { docApi, type DocumentDetail, type DocumentItem } from '@/api'
import { fmtNum, fmtTime } from '@/utils/format'
import { renderSimple } from '@/utils/markdown'

const docs = ref<DocumentItem[]>([])
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const category = ref('')
const categories = computed(() => [...new Set(docs.value.map((d) => d.category))])
const filtered = computed(() =>
  docs.value.filter((d) => (!category.value || d.category === category.value) && (!keyword.value || d.title.includes(keyword.value) || d.summary.includes(keyword.value))),
)

const metaDialog = ref(false)
const editing = ref<DocumentItem | null>(null)
const metaRef = ref<FormInstance>()
const meta = reactive({ slug: '', title: '', category: '', summary: '', sort: 100, is_published: false })
const metaRules: FormRules = {
  slug: [{ required: true, message: '请输入标识' }, { pattern: /^[a-z0-9][a-z0-9-]*$/, message: '小写字母、数字、连字符' }],
  title: [{ required: true, message: '请输入书名' }],
  category: [{ required: true, message: '请选择分类' }],
}

const chapterDrawer = ref(false)
const doc = ref<DocumentDetail | null>(null)
const chapter = ref<{ id: number | null; title: string; content: string; sort: number } | null>(null)
const chLoading = ref(false)
const mode = ref<'split' | 'edit' | 'preview'>('split')

async function load() {
  loading.value = true
  try {
    docs.value = await docApi.list({ include_unpublished: true })
  } finally {
    loading.value = false
  }
}

async function togglePublish(d: DocumentItem, v: boolean) {
  await docApi.update(d.id, { is_published: v })
  d.is_published = v
  ElMessage.success(v ? '已发布' : '已下架')
}

function openCreate() {
  editing.value = null
  Object.assign(meta, { slug: '', title: '', category: categories.value[0] ?? '', summary: '', sort: docs.value.length, is_published: false })
  metaDialog.value = true
}

function openEdit(d: DocumentItem) {
  editing.value = d
  Object.assign(meta, { slug: d.slug, title: d.title, category: d.category, summary: d.summary, sort: d.sort, is_published: d.is_published })
  metaDialog.value = true
}

async function saveMeta() {
  if (!(await metaRef.value?.validate().catch(() => false))) return
  saving.value = true
  try {
    if (editing.value) {
      const { slug, ...rest } = meta
      await docApi.update(editing.value.id, rest)
    } else {
      await docApi.create({ ...meta })
    }
    ElMessage.success('已保存')
    metaDialog.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function removeDoc(d: DocumentItem) {
  await ElMessageBox.confirm(`删除《${d.title}》及其全部 ${d.chapter_count} 个章节？此操作不可恢复。`, '删除典籍', { type: 'warning' })
  await docApi.remove(d.id)
  ElMessage.success('已删除')
  load()
}

async function openChapters(d: DocumentItem) {
  doc.value = await docApi.get(String(d.id))
  chapter.value = null
  chapterDrawer.value = true
  if (doc.value.chapters[0]) selectChapter(doc.value.chapters[0].id)
}

async function selectChapter(id: number) {
  if (!doc.value) return
  chLoading.value = true
  try {
    const c = await docApi.chapter(String(doc.value.id), id)
    chapter.value = { id: c.id, title: c.title, content: c.content, sort: c.sort }
  } finally {
    chLoading.value = false
  }
}

function newChapter() {
  const next = (doc.value?.chapters.at(-1)?.sort ?? -1) + 1
  chapter.value = { id: null, title: '新章节', content: '## 新章节\n\n', sort: next }
}

async function refreshDoc() {
  if (doc.value) doc.value = await docApi.get(String(doc.value.id))
}

async function saveChapter() {
  if (!doc.value || !chapter.value) return
  if (!chapter.value.title.trim()) return ElMessage.warning('请填写章节标题')
  saving.value = true
  try {
    const body = { title: chapter.value.title, content: chapter.value.content, sort: chapter.value.sort }
    if (chapter.value.id) await docApi.updateChapter(chapter.value.id, body)
    else chapter.value.id = (await docApi.createChapter(doc.value.id, body)).id
    ElMessage.success('章节已保存')
    await refreshDoc()
    load()
  } finally {
    saving.value = false
  }
}

async function removeChapter() {
  if (!chapter.value?.id) return
  await ElMessageBox.confirm(`删除章节「${chapter.value.title}」？`, '删除章节', { type: 'warning' })
  await docApi.removeChapter(chapter.value.id)
  chapter.value = null
  ElMessage.success('已删除')
  await refreshDoc()
  load()
}

onMounted(load)
</script>

<style scoped lang="scss">
.title { font-size: 15.5px; }
.editor { display: flex; gap: 16px; height: 100%; }
.ch-list {
  width: 260px;
  flex-shrink: 0;
  overflow-y: auto;
  border-right: 1px solid var(--line);
  padding-right: 10px;
  .add { width: 100%; margin-bottom: 10px; }
}
.ch {
  display: flex;
  gap: 8px;
  padding: 6px 8px;
  font-size: 13.5px;
  cursor: pointer;
  border-radius: 3px;
  line-height: 1.5;
  .no { color: var(--ink-3); min-width: 20px; }
  &:hover { background: var(--paper-2); }
  &.active { background: var(--cinnabar-soft); color: var(--cinnabar); }
}
.ch-edit { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px; }
.ch-bar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; .spacer { flex: 1; } }
.ch-title { width: 320px; }
.panes {
  flex: 1;
  display: grid;
  gap: 12px;
  min-height: 0;
  &.split { grid-template-columns: 1fr 1fr; }
  &.edit, &.preview { grid-template-columns: 1fr; }
}
.src {
  width: 100%;
  height: 100%;
  min-height: 60vh;
  resize: none;
  border: 1px solid var(--line);
  border-radius: 3px;
  padding: 12px 14px;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 13.5px;
  line-height: 1.7;
  background: #fffdf8;
  color: var(--ink);
  outline: none;
  &:focus { border-color: var(--cinnabar); }
}
.preview { overflow-y: auto; border: 1px solid var(--line); border-radius: 3px; padding: 12px 20px; background: var(--card); max-height: 75vh; font-size: 15px; }
</style>
