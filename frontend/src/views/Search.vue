<template>
  <div class="container search-page">
    <div class="search-hero">
      <h2 class="kai">一字入门，贯通典籍</h2>
      <div class="box">
        <el-input v-model="kw" size="large" placeholder="方名、病名、穴位、条文……如：小柴胡汤、少阴病、足三里" clearable @keyup.enter="go">
          <template #append><el-button :icon="Search" @click="go">检索</el-button></template>
        </el-input>
      </div>
      <div class="hot">
        <a v-for="h in hots" :key="h" @click="kw = h; go()">{{ h }}</a>
      </div>
    </div>

    <template v-if="searched">
      <el-tabs v-model="tab" class="tabs">
        <el-tab-pane :label="`全部（${hits.length}）`" name="all" />
        <el-tab-pane :label="`典籍（${chapterHits.length}）`" name="chapter" />
        <el-tab-pane :label="`医案（${caseHits.length}）`" name="case" />
      </el-tabs>
      <p v-if="!auth.can('case:read')" class="tip">登录会员后可同时检索医案库。</p>
      <div v-loading="loading" class="results">
        <article v-for="h in shown" :key="h.type + h.id" class="hit paper-card" @click="openHit(h)">
          <div class="hit-head">
            <span class="hit-type" :class="h.type">{{ h.type === 'chapter' ? '典籍' : '医案' }}</span>
            <h3 class="kai" v-html="highlight(h.title, query)" />
          </div>
          <div class="hit-sub">{{ h.subtitle }}</div>
          <p class="hit-snippet" v-html="highlight(h.snippet, query)" />
        </article>
        <el-empty v-if="!loading && !shown.length" description="未检得相关内容，换个关键词试试" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { miscApi, type SearchHit } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { highlight } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const kw = ref((route.query.q as string) || '')
const query = ref('')
const tab = ref('all')
const hits = ref<SearchHit[]>([])
const loading = ref(false)
const searched = ref(false)
const hots = ['桂枝汤', '小柴胡汤', '少阴病', '炙甘草汤', '足三里', '十枣汤', '失眠', '脉结代']

const chapterHits = computed(() => hits.value.filter((h) => h.type === 'chapter'))
const caseHits = computed(() => hits.value.filter((h) => h.type === 'case'))
const shown = computed(() => (tab.value === 'all' ? hits.value : tab.value === 'chapter' ? chapterHits.value : caseHits.value))

function go() {
  const v = kw.value.trim()
  if (!v) return
  router.replace({ query: { q: v } })
}

async function run(q: string) {
  query.value = q
  loading.value = true
  searched.value = true
  try {
    hits.value = await miscApi.search(q)
  } finally {
    loading.value = false
  }
}

function openHit(h: SearchHit) {
  if (h.type === 'chapter') router.push({ path: `/library/${h.document_slug}/${h.chapter_id}`, query: { kw: query.value.split(/\s+/)[0] } })
  else router.push({ path: '/cases', query: { id: h.id } })
}

watch(
  () => route.query.q,
  (q) => {
    if (typeof q === 'string' && q.trim()) {
      kw.value = q
      run(q.trim())
    }
  },
  { immediate: true },
)
</script>

<style scoped lang="scss">
.search-page { padding-top: 40px; max-width: 960px; }
.search-hero {
  text-align: center;
  padding: 30px 0 10px;
  h2 { font-size: 32px; letter-spacing: 6px; margin: 0 0 20px; }
}
.box { max-width: 680px; margin: 0 auto; }
.hot {
  margin-top: 14px;
  a { margin: 0 8px; font-size: 14px; color: var(--indigo); cursor: pointer; &:hover { color: var(--cinnabar); } }
}
.tabs { margin-top: 30px; }
.tip { font-size: 13px; color: var(--ink-3); margin: -6px 0 12px; }
.results { display: flex; flex-direction: column; gap: 14px; min-height: 200px; }
.hit {
  padding: 16px 20px;
  cursor: pointer;
  transition: all 0.2s;
  &:hover { border-color: var(--cinnabar); box-shadow: var(--shadow-lg); }
  h3 { margin: 0; font-size: 18px; letter-spacing: 1px; }
}
.hit-head { display: flex; align-items: center; gap: 10px; }
.hit-type {
  font-size: 12px;
  padding: 0 6px;
  border-radius: 2px;
  color: #fff;
  flex-shrink: 0;
  &.chapter { background: var(--indigo); }
  &.case { background: var(--cinnabar); }
}
.hit-sub { font-size: 12px; color: var(--ink-3); margin: 4px 0; }
.hit-snippet { margin: 0; font-size: 14px; color: var(--ink-2); line-height: 1.8; }
:deep(mark) { background: rgba(168, 50, 42, 0.15); color: var(--cinnabar); padding: 0 1px; }
</style>
