<template>
  <div class="reader" :style="{ '--fs': fontSize + 'px' }">
    <div class="container layout">
      <!-- 章节目录 -->
      <aside class="toc" :class="{ open: tocOpen }">
        <div class="toc-head">
          <router-link to="/library" class="back"><el-icon><ArrowLeft /></el-icon>书阁</router-link>
          <el-button class="toc-close" text circle @click="tocOpen = false"><el-icon><Close /></el-icon></el-button>
        </div>
        <div v-if="doc" class="doc-title kai">{{ doc.title }}</div>
        <div v-if="doc" class="doc-meta">{{ doc.category }} · {{ doc.chapters.length }} 章 · {{ fmtNum(doc.word_count) }} 字</div>
        <el-input v-model="tocFilter" size="small" placeholder="筛选章节" clearable class="toc-filter" />
        <ol class="toc-list">
          <li v-for="(c, i) in tocItems" :key="c.id">
            <router-link :to="`/library/${slug}/${c.id}`" :class="{ active: c.id === chapter?.id }" @click="tocOpen = false">
              <span class="no">{{ i + 1 }}</span>{{ c.title }}
            </router-link>
          </li>
        </ol>
      </aside>
      <div v-if="tocOpen" class="mask" @click="tocOpen = false" />

      <!-- 正文 -->
      <article class="content paper-card" v-loading="loading">
        <div class="toolbar">
          <el-button class="toc-toggle" size="small" @click="tocOpen = true"><el-icon><Menu /></el-icon>目录</el-button>
          <div class="crumb" v-if="doc">
            <span>{{ doc.category }}</span><i>/</i><span>{{ doc.title }}</span>
          </div>
          <div class="tools">
            <el-button-group size="small">
              <el-button @click="fontSize = Math.max(14, fontSize - 1)">A-</el-button>
              <el-button @click="fontSize = Math.min(22, fontSize + 1)">A+</el-button>
            </el-button-group>
            <el-button size="small" :type="favorited ? 'primary' : 'default'" @click="toggleFav">
              <el-icon><component :is="favorited ? StarFilled : Star" /></el-icon>{{ favorited ? '已收藏' : '收藏' }}
            </el-button>
          </div>
        </div>

        <template v-if="chapter">
          <header class="ch-head">
            <span class="seal ch-seal">{{ chapterIndex + 1 }}</span>
            <h1 class="kai">{{ chapter.title }}</h1>
            <p class="ch-meta">{{ fmtNum(chapter.word_count) }} 字 · 更新于 {{ fmtTime(chapter.updated_at) }}</p>
          </header>
          <div ref="mdEl" class="md" v-html="rendered.html" />
          <nav class="pager">
            <router-link v-if="chapter.prev_id" :to="`/library/${slug}/${chapter.prev_id}`" class="prev">
              <small>上一章</small><span>{{ titleOf(chapter.prev_id) }}</span>
            </router-link>
            <span v-else />
            <router-link v-if="chapter.next_id" :to="`/library/${slug}/${chapter.next_id}`" class="next">
              <small>下一章</small><span>{{ titleOf(chapter.next_id) }}</span>
            </router-link>
          </nav>
        </template>
      </article>

      <!-- 本章纲目 -->
      <aside v-if="outline.length > 1" class="outline">
        <div class="outline-title kai">本章纲目</div>
        <a v-for="h in outline" :key="h.id" :href="`#${h.id}`" :class="`lv${h.level}`" @click.prevent="scrollTo(h.id)">{{ h.text }}</a>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Close, Menu, Star, StarFilled } from '@element-plus/icons-vue'
import { docApi, miscApi, type Chapter, type DocumentDetail } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { renderMarkdown } from '@/utils/markdown'
import { fmtNum, fmtTime } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const slug = computed(() => route.params.slug as string)
const doc = ref<DocumentDetail | null>(null)
const chapter = ref<Chapter | null>(null)
const loading = ref(false)
const tocOpen = ref(false)
const tocFilter = ref('')
const favorited = ref(false)
const mdEl = ref<HTMLElement>()
const fontSize = ref(Number(safeGet('nhx_fs')) || 17)

function safeGet(k: string) {
  try { return localStorage.getItem(k) } catch { return null }
}
watch(fontSize, (v) => { try { localStorage.setItem('nhx_fs', String(v)) } catch { /* ignore */ } })

const rendered = computed(() => renderMarkdown(chapter.value?.content ?? '', { headingPrefix: `c${chapter.value?.id}` }))
const outline = computed(() => rendered.value.headings.filter((h) => h.level <= 3).slice(0, 60))
const tocItems = computed(() => (doc.value?.chapters ?? []).filter((c) => !tocFilter.value || c.title.includes(tocFilter.value)))
const chapterIndex = computed(() => doc.value?.chapters.findIndex((c) => c.id === chapter.value?.id) ?? 0)
const titleOf = (id: number) => doc.value?.chapters.find((c) => c.id === id)?.title ?? ''

async function loadDoc() {
  doc.value = await docApi.get(slug.value)
  if (auth.user) favorited.value = (await miscApi.checkFavorite('document', doc.value.id)).favorited
}

async function loadChapter() {
  if (!doc.value) return
  const id = Number(route.params.chapterId) || doc.value.chapters[0]?.id
  if (!id) return
  loading.value = true
  try {
    chapter.value = await docApi.chapter(slug.value, id)
    await nextTick()
    const kw = route.query.kw as string | undefined
    if (kw && mdEl.value) markKeyword(mdEl.value, kw)
    else if (!route.hash) window.scrollTo({ top: 0 })
  } finally {
    loading.value = false
  }
}

/** 在正文中高亮检索关键词并滚动到第一个命中处 */
function markKeyword(root: HTMLElement, kw: string) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  const nodes: Text[] = []
  while (walker.nextNode()) {
    const n = walker.currentNode as Text
    if (n.data.includes(kw)) nodes.push(n)
  }
  for (const n of nodes) {
    const parts = n.data.split(kw)
    const frag = document.createDocumentFragment()
    parts.forEach((p, i) => {
      frag.append(p)
      if (i < parts.length - 1) {
        const m = document.createElement('mark')
        m.textContent = kw
        frag.append(m)
      }
    })
    n.replaceWith(frag)
  }
  root.querySelector('mark')?.scrollIntoView({ block: 'center' })
}

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function toggleFav() {
  if (!auth.user) {
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  if (!doc.value) return
  if (favorited.value) await miscApi.removeFavorite('document', doc.value.id)
  else await miscApi.addFavorite('document', doc.value.id)
  favorited.value = !favorited.value
  ElMessage.success(favorited.value ? '已加入收藏' : '已取消收藏')
}

watch(
  () => route.params.chapterId,
  () => loadChapter(),
)

;(async () => {
  try {
    await loadDoc()
    await loadChapter()
  } catch {
    router.replace({ name: 'not-found' })
  }
})()
</script>

<style scoped lang="scss">
.reader { padding-top: 24px; }
.layout { display: flex; gap: 24px; align-items: flex-start; max-width: 1400px; }
.toc {
  position: sticky;
  top: 84px;
  width: 260px;
  flex-shrink: 0;
  max-height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
}
.toc-head { display: flex; justify-content: space-between; align-items: center; }
.back { display: inline-flex; align-items: center; gap: 4px; color: var(--ink-3); font-size: 14px; }
.toc-close { display: none; }
.doc-title { font-size: 20px; line-height: 1.5; margin: 12px 0 4px; letter-spacing: 1px; }
.doc-meta { font-size: 12px; color: var(--ink-3); margin-bottom: 10px; }
.toc-filter { margin-bottom: 8px; }
.toc-list {
  list-style: none;
  margin: 0;
  padding: 0 4px 0 0;
  overflow-y: auto;
  flex: 1;
  border-left: 1px solid var(--line);
  a {
    display: flex;
    gap: 8px;
    padding: 6px 10px;
    font-size: 14px;
    line-height: 1.6;
    color: var(--ink-2);
    margin-left: -1px;
    border-left: 2px solid transparent;
    &:hover { color: var(--cinnabar); }
    &.active { color: var(--cinnabar); border-left-color: var(--cinnabar); background: var(--cinnabar-soft); font-weight: 600; }
  }
  .no { color: var(--ink-3); font-size: 12px; min-width: 18px; padding-top: 2px; }
}

.content { flex: 1; min-width: 0; padding: 20px 48px 40px; min-height: 60vh; }
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px dashed var(--line);
  .el-icon { margin-right: 4px; }
}
.toc-toggle { display: none; }
.crumb { font-size: 13px; color: var(--ink-3); flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; i { margin: 0 6px; font-style: normal; } }
.tools { display: flex; gap: 8px; }
.ch-head {
  text-align: center;
  padding: 32px 0 16px;
  h1 { font-size: 30px; letter-spacing: 3px; margin: 14px 0 6px; line-height: 1.5; }
}
.ch-seal { width: 40px; height: 40px; font-size: 18px; }
.ch-meta { color: var(--ink-3); font-size: 13px; margin: 0; }
.md { font-size: var(--fs); }
.md :deep(h2:first-child) { display: none; }

.pager {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 48px;
  padding-top: 20px;
  border-top: 1px solid var(--line);
  a {
    display: flex;
    flex-direction: column;
    max-width: 48%;
    padding: 10px 16px;
    border: 1px solid var(--line);
    border-radius: 3px;
    color: var(--ink);
    &:hover { border-color: var(--cinnabar); color: var(--cinnabar); }
    small { color: var(--ink-3); font-size: 12px; }
    span { font-family: var(--font-kai); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  }
  .next { text-align: right; margin-left: auto; }
}

.outline {
  position: sticky;
  top: 84px;
  width: 200px;
  flex-shrink: 0;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
  font-size: 13px;
  .outline-title { font-size: 15px; letter-spacing: 2px; margin-bottom: 8px; color: var(--ink); }
  a {
    display: block;
    padding: 3px 0 3px 10px;
    color: var(--ink-3);
    border-left: 1px solid var(--line);
    line-height: 1.6;
    &:hover { color: var(--cinnabar); border-left-color: var(--cinnabar); }
    &.lv3 { padding-left: 22px; font-size: 12.5px; }
  }
}

.mask { display: none; }

@media (max-width: 1280px) { .outline { display: none; } }
@media (max-width: 900px) {
  .toc {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    max-height: none;
    z-index: 100;
    background: var(--card);
    padding: 16px;
    width: 82%;
    max-width: 320px;
    transform: translateX(-105%);
    transition: transform 0.25s;
    box-shadow: var(--shadow-lg);
    &.open { transform: none; }
  }
  .toc-close, .toc-toggle { display: inline-flex; }
  .mask { display: block; position: fixed; inset: 0; background: rgba(0, 0, 0, 0.3); z-index: 99; }
  .content { padding: 14px 16px 30px; }
  .crumb { display: none; }
  .tools { margin-left: auto; }
  .ch-head h1 { font-size: 24px; }
}
</style>
