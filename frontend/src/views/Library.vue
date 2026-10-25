<template>
  <div class="container library">
    <div class="head">
      <div>
        <h2 class="sec-title">典籍书阁</h2>
        <p class="sec-sub">共 {{ docs.length }} 卷 · 点选书册开卷研读</p>
      </div>
      <el-input v-model="keyword" placeholder="书名 / 简介" clearable class="kw" :prefix-icon="Search" />
    </div>

    <div class="body">
      <aside class="cats">
        <button :class="{ active: !category }" @click="setCategory('')">全部典籍</button>
        <button v-for="c in categories" :key="c.name" :class="{ active: category === c.name }" @click="setCategory(c.name)">
          <span class="kai">{{ c.name }}</span><em>{{ c.count }}</em>
        </button>
      </aside>

      <div v-loading="loading" class="shelf">
        <router-link v-for="(d, i) in filtered" :key="d.id" :to="`/library/${d.slug}`" class="book">
          <div class="cover" :class="`c${i % 4}`">
            <div class="label kai">{{ shortTitle(d.title) }}</div>
            <div class="stitch" aria-hidden="true"><i v-for="n in 4" :key="n" /></div>
          </div>
          <div class="info">
            <span class="tag-ink">{{ d.category }}</span>
            <h3 class="kai">{{ d.title }}</h3>
            <p class="summary">{{ d.summary || '倪海厦讲义整理' }}</p>
            <div class="meta">
              <span>{{ d.chapter_count }} 章</span>
              <span>{{ fmtNum(d.word_count) }} 字</span>
              <span>{{ d.view_count }} 次研读</span>
            </div>
          </div>
        </router-link>
        <el-empty v-if="!loading && !filtered.length" description="暂无相关典籍" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { docApi, type DocumentItem } from '@/api'
import { fmtNum } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const docs = ref<DocumentItem[]>([])
const categories = ref<{ name: string; count: number }[]>([])
const category = ref((route.query.category as string) || '')
const keyword = ref('')
const loading = ref(true)

const filtered = computed(() => {
  const kw = keyword.value.trim()
  return docs.value.filter(
    (d) => (!category.value || d.category === category.value) && (!kw || d.title.includes(kw) || d.summary.includes(kw)),
  )
})

function setCategory(c: string) {
  category.value = c
  router.replace({ query: c ? { category: c } : {} })
}

function shortTitle(t: string) {
  const s = t.split(/[（(·+|]/)[0].trim()
  return s.length > 10 ? s.slice(0, 10) : s
}

onMounted(async () => {
  try {
    const [d, c] = await Promise.all([docApi.list(), docApi.categories()])
    docs.value = d
    categories.value = c
  } finally {
    loading.value = false
  }
})
</script>

<style scoped lang="scss">
.library { padding-top: 36px; }
.head { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; flex-wrap: wrap; }
.kw { width: 260px; }
.body { display: flex; gap: 28px; align-items: flex-start; }
.cats {
  position: sticky;
  top: 90px;
  width: 180px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-left: 2px solid var(--line);
  button {
    all: unset;
    cursor: pointer;
    padding: 10px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: var(--ink-2);
    font-size: 16px;
    letter-spacing: 2px;
    margin-left: -2px;
    border-left: 2px solid transparent;
    transition: all 0.2s;
    em { font-style: normal; font-size: 12px; color: var(--ink-3); }
    &:hover { color: var(--cinnabar); }
    &.active { color: var(--cinnabar); border-left-color: var(--cinnabar); background: var(--cinnabar-soft); }
  }
}
.shelf { flex: 1; display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; min-height: 300px; }
.book {
  display: flex;
  gap: 16px;
  padding: 14px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 4px;
  color: var(--ink);
  transition: all 0.2s;
  &:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); border-color: var(--gold); color: var(--ink); }
}
.cover {
  position: relative;
  width: 96px;
  height: 136px;
  flex-shrink: 0;
  border-radius: 2px 4px 4px 2px;
  box-shadow: 2px 3px 8px rgba(43, 36, 32, 0.3), inset -3px 0 6px rgba(0, 0, 0, 0.15);
  background-image: repeating-linear-gradient(45deg, rgba(255, 255, 255, 0.04) 0 2px, transparent 2px 5px);
  &.c0 { background-color: #2e5753; }
  &.c1 { background-color: #6b3a2a; }
  &.c2 { background-color: #3c4a5c; }
  &.c3 { background-color: #5a5236; }
}
.label {
  position: absolute;
  top: 12px;
  right: 14px;
  width: 26px;
  max-height: 112px;
  padding: 6px 0;
  background: #f5eedf;
  border: 1px solid #d8c8a8;
  writing-mode: vertical-rl;
  font-size: 13px;
  letter-spacing: 2px;
  color: var(--ink);
  display: flex;
  align-items: center;
  overflow: hidden;
}
.stitch {
  position: absolute;
  left: 7px;
  top: 10px;
  bottom: 10px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  i { width: 6px; height: 6px; border-radius: 50%; background: rgba(245, 238, 223, 0.6); }
}
.info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  h3 { margin: 6px 0 4px; font-size: 18px; letter-spacing: 1px; line-height: 1.5; }
  .summary {
    margin: 0;
    color: var(--ink-3);
    font-size: 13px;
    line-height: 1.7;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    flex: 1;
  }
  .meta { display: flex; gap: 14px; font-size: 12px; color: var(--ink-3); margin-top: 6px; }
}
.tag-ink { align-self: flex-start; }

@media (max-width: 860px) {
  .body { flex-direction: column; }
  .cats {
    position: static;
    width: 100%;
    flex-direction: row;
    overflow-x: auto;
    border-left: none;
    border-bottom: 2px solid var(--line);
    button { border-left: none; border-bottom: 2px solid transparent; margin: 0 0 -2px; white-space: nowrap; gap: 6px; &.active { border-bottom-color: var(--cinnabar); } }
  }
  .shelf { grid-template-columns: 1fr; width: 100%; }
  .kw { width: 100%; }
}
</style>
