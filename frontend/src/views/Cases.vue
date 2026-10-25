<template>
  <div class="container cases">
    <h2 class="sec-title">倪师医案库</h2>
    <p class="sec-sub">2005–2009 年临床医案结构化整理 · 诊断 / 病机 / 方剂 / 针灸 / 疗效 / 医嘱</p>

    <div v-if="!auth.user" class="gate paper-card framed">
      <span class="seal gate-seal">案</span>
      <h3 class="kai">登录后查阅医案</h3>
      <p>医案库包含详细的方剂剂量与诊疗过程，仅向注册会员开放，供学习研究使用。</p>
      <div class="gate-btns">
        <el-button type="primary" @click="$router.push({ name: 'login', query: { redirect: '/cases' } })">登录</el-button>
        <el-button v-if="auth.config.allow_registration" @click="$router.push('/register')">免费注册</el-button>
      </div>
    </div>

    <div v-else-if="!auth.can('case:read')" class="gate paper-card framed">
      <h3 class="kai">暂无医案查阅权限</h3>
      <p>请联系管理员为您的账号分配「查阅医案库」权限。</p>
    </div>

    <template v-else>
      <div class="filters paper-card">
        <el-input v-model="q.keyword" placeholder="输入病名、方剂、穴位，多个词以空格分隔" clearable class="kw" @keyup.enter="search(1)">
          <template #prepend>
            <el-select v-model="q.field" style="width: 108px">
              <el-option v-for="f in fields" :key="f.value" :label="f.label" :value="f.value" />
            </el-select>
          </template>
        </el-input>
        <el-select v-model="q.year" placeholder="年份" clearable style="width: 140px" @change="search(1)">
          <el-option v-for="y in years" :key="y.year" :label="`${y.year} 年（${y.count}）`" :value="y.year" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="search(1)">检索</el-button>
        <div class="hot">
          <span>常用：</span>
          <a v-for="h in hots" :key="h" @click="quick(h)">{{ h }}</a>
        </div>
      </div>

      <div class="result-info">共检得 <b>{{ total }}</b> 例医案</div>

      <el-table v-loading="loading" :data="rows" stripe class="table" @row-click="open" row-class-name="clickable">
        <el-table-column prop="seq" label="序号" width="72" align="center" />
        <el-table-column prop="date_text" label="日期" width="120" show-overflow-tooltip />
        <el-table-column prop="patient" label="患者" width="130" show-overflow-tooltip />
        <el-table-column label="主要诊断" min-width="160">
          <template #default="{ row }"><span class="diag" v-html="highlight(row.diagnosis, q.keyword)" /></template>
        </el-table-column>
        <el-table-column label="方剂 / 治疗" min-width="260">
          <template #default="{ row }"><span class="clamp" v-html="highlight(strip(row.prescription) || '—', q.keyword)" /></template>
        </el-table-column>
        <el-table-column label="疗效" min-width="160">
          <template #default="{ row }"><span class="clamp muted">{{ strip(row.outcome) || '—' }}</span></template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="q.page"
        :page-size="q.size"
        :total="total"
        layout="total, prev, pager, next, jumper"
        background
        @current-change="search"
      />
    </template>

    <el-drawer v-model="drawer" :size="drawerSize" :title="current ? `医案 #${current.seq}` : ''">
      <template v-if="current">
        <div class="case-head">
          <h3 class="kai">{{ current.diagnosis }}</h3>
          <div class="case-meta">
            <span v-if="current.date_text"><el-icon><Calendar /></el-icon>{{ current.date_text }}</span>
            <span v-if="current.patient"><el-icon><User /></el-icon>{{ current.patient }}</span>
          </div>
          <el-button size="small" :type="caseFav ? 'primary' : 'default'" @click="toggleCaseFav">
            <el-icon><component :is="caseFav ? StarFilled : Star" /></el-icon>{{ caseFav ? '已收藏' : '收藏' }}
          </el-button>
        </div>
        <dl class="case-fields">
          <template v-for="f in detailFields" :key="f.key">
            <template v-if="current[f.key]">
              <dt><span class="dot" :style="{ background: f.color }" />{{ f.label }}</dt>
              <dd class="md" v-html="renderSimple(String(current[f.key]))" />
            </template>
          </template>
        </dl>
        <p class="case-note">⚠️ 医案为倪师个人临床记录，方药剂量因人而异，切勿自行照方服用。</p>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Calendar, Search, Star, StarFilled, User } from '@element-plus/icons-vue'
import { caseApi, miscApi, type MedicalCase } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { highlight } from '@/utils/format'
import { renderSimple } from '@/utils/markdown'

const auth = useAuthStore()
const route = useRoute()
const fields = [
  { value: 'all', label: '全部字段' },
  { value: 'diagnosis', label: '诊断' },
  { value: 'prescription', label: '方剂' },
  { value: 'pathogenesis', label: '病机' },
  { value: 'acupuncture', label: '针灸' },
  { value: 'comment', label: '倪师观点' },
]
const hots = ['肝癌', '乳癌', '失眠', '糖尿病', '十枣汤', '小柴胡汤', '四逆汤', '心脏病']
const detailFields: { key: keyof MedicalCase; label: string; color: string }[] = [
  { key: 'pathogenesis', label: '中医病机', color: '#a8322a' },
  { key: 'western_view', label: '西医背景', color: '#85766a' },
  { key: 'prescription', label: '方剂剂量 / 治疗组成', color: '#2e5753' },
  { key: 'acupuncture', label: '针灸方案', color: '#3f7069' },
  { key: 'principle', label: '治疗原则', color: '#8b5a2b' },
  { key: 'outcome', label: '疗程 / 结果', color: '#b48d55' },
  { key: 'advice', label: '生活医嘱', color: '#6b8f71' },
  { key: 'comment', label: '倪海厦观点', color: '#a8322a' },
]

const q = reactive({ keyword: (route.query.keyword as string) || '', field: 'all', year: undefined as number | undefined, page: 1, size: 20 })
const rows = ref<MedicalCase[]>([])
const total = ref(0)
const loading = ref(false)
const years = ref<{ year: number; count: number }[]>([])
const drawer = ref(false)
const current = ref<MedicalCase | null>(null)
const caseFav = ref(false)
const drawerSize = computed(() => (window.innerWidth < 768 ? '100%' : '640px'))

const strip = (s: string) => s.replace(/\*\*/g, '').replace(/<br\s*\/?>/g, ' ')

async function search(page = q.page) {
  q.page = page
  loading.value = true
  try {
    const res = await caseApi.list({ keyword: q.keyword, field: q.field, year: q.year, page: q.page, size: q.size })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function quick(h: string) {
  q.keyword = h
  search(1)
}

async function open(row: MedicalCase) {
  current.value = row
  drawer.value = true
  caseFav.value = (await miscApi.checkFavorite('case', row.id)).favorited
}

async function toggleCaseFav() {
  if (!current.value) return
  if (caseFav.value) await miscApi.removeFavorite('case', current.value.id)
  else await miscApi.addFavorite('case', current.value.id)
  caseFav.value = !caseFav.value
}

onMounted(async () => {
  if (!auth.can('case:read')) return
  search(1)
  years.value = await caseApi.years()
  const openId = Number(route.query.id)
  if (openId) open(await caseApi.get(openId))
})
</script>

<style scoped lang="scss">
.cases { padding-top: 36px; }
.gate {
  max-width: 560px;
  margin: 40px auto;
  padding: 40px;
  text-align: center;
  h3 { font-size: 24px; letter-spacing: 3px; margin: 16px 0 8px; }
  p { color: var(--ink-2); }
}
.gate-seal { width: 56px; height: 56px; font-size: 28px; }
.gate-btns { display: flex; justify-content: center; gap: 12px; margin-top: 16px; }
.filters { padding: 18px 20px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
.kw { flex: 1; min-width: 280px; }
.hot {
  width: 100%;
  font-size: 13px;
  color: var(--ink-3);
  a { margin-right: 14px; cursor: pointer; color: var(--indigo); &:hover { color: var(--cinnabar); } }
}
.result-info { margin: 18px 0 10px; color: var(--ink-3); font-size: 14px; b { color: var(--cinnabar); } }
.table { border: 1px solid var(--line); border-radius: 4px; }
:deep(.clickable) { cursor: pointer; }
.diag { font-weight: 600; color: var(--ink); }
.clamp { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; font-size: 13.5px; }
.muted { color: var(--ink-3); }
.case-head {
  border-bottom: 1px dashed var(--line);
  padding-bottom: 14px;
  margin-bottom: 8px;
  h3 { margin: 0 0 6px; font-size: 22px; letter-spacing: 1px; color: var(--cinnabar); }
  .el-icon { margin-right: 4px; }
}
.case-meta { display: flex; gap: 18px; color: var(--ink-3); font-size: 14px; margin-bottom: 10px; span { display: inline-flex; align-items: center; } }
.case-fields {
  margin: 0;
  dt { font-family: var(--font-kai); font-size: 16px; margin-top: 16px; display: flex; align-items: center; gap: 8px; color: var(--ink); }
  .dot { width: 8px; height: 8px; border-radius: 50%; }
  dd { margin: 4px 0 0 16px; font-size: 14.5px; line-height: 1.9; :deep(p) { margin: 2px 0; } }
}
.case-note { margin-top: 24px; font-size: 13px; color: var(--ochre); background: rgba(180, 141, 85, 0.12); padding: 8px 12px; border-radius: 3px; }
</style>
