<template>
  <div class="home">
    <!-- 首屏 -->
    <section class="hero">
      <div class="mountains" aria-hidden="true"></div>
      <div class="container hero-inner">
        <div class="hero-text">
          <div class="vertical-title kai">
            <span>经方大道</span>
            <span class="sub">至简至真</span>
          </div>
          <div class="hero-main">
            <p class="eyebrow">倪海厦 · 人纪天纪 · 汉唐中医</p>
            <h1 class="kai">读懂<em>伤寒</em>，<br />一通百通</h1>
            <p class="lead">
              整理倪海厦先生伤寒论、金匮要略、黄帝内经、针灸本草讲义与上千例临床医案，
              以六经辨证为纲，经方为本，供中医学人研读查阅。
            </p>
            <div class="cta">
              <el-button type="primary" size="large" @click="$router.push('/library')">
                <el-icon><Reading /></el-icon><span>开卷研读</span>
              </el-button>
              <el-button size="large" @click="$router.push('/consult')">
                <el-icon><ChatDotRound /></el-icon><span>经方问诊</span>
              </el-button>
            </div>
          </div>
        </div>
        <div class="hero-art">
          <div class="ring">
            <span v-for="(m, i) in meridians" :key="m" class="ring-char kai" :style="{ transform: `rotate(${i * 60}deg) translateY(-150px) rotate(${-i * 60}deg)` }">{{ m }}</span>
          </div>
          <Taiji :size="200" class="taiji-spin" />
          <span class="seal hero-seal">经方<br />正宗</span>
        </div>
      </div>
      <div class="container counters">
        <div v-for="c in counters" :key="c.label" class="counter">
          <span class="num kai">{{ c.value }}</span>
          <span class="label">{{ c.label }}</span>
        </div>
      </div>
    </section>

    <!-- 开阖枢 -->
    <section class="container sec">
      <h2 class="sec-title">六经开阖枢</h2>
      <p class="sec-sub">三阳主外，三阴主内。辨六经，方能选经方。</p>
      <div class="six">
        <div v-for="g in sixGroups" :key="g.name" class="six-group">
          <div class="six-label kai">{{ g.name }}</div>
          <div class="six-row">
            <div v-for="m in g.items" :key="m.name" class="six-card paper-card framed">
              <div class="six-head">
                <span class="kai six-name">{{ m.name }}</span>
                <span class="six-role" :class="m.role">{{ m.roleLabel }}</span>
              </div>
              <p class="six-desc">{{ m.desc }}</p>
              <p class="six-fang"><span>代表方</span>{{ m.fang }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <div class="cloud-divider"></div>

    <!-- 典籍分类 -->
    <section class="container sec">
      <h2 class="sec-title">典籍书阁</h2>
      <p class="sec-sub">按门类收录讲义原文，章节分明，随读随查。</p>
      <div class="cats">
        <router-link
          v-for="(c, i) in categories"
          :key="c.name"
          :to="{ path: '/library', query: { category: c.name } }"
          class="cat paper-card"
        >
          <span class="cat-idx kai">{{ numerals[i] }}</span>
          <span class="cat-name kai">{{ c.name }}</span>
          <span class="cat-count">{{ c.count }} 卷</span>
          <span class="cat-desc">{{ catDesc[c.name] ?? '' }}</span>
        </router-link>
      </div>
    </section>

    <!-- 功能 -->
    <section class="container sec features">
      <div class="feature paper-card framed" @click="$router.push('/cases')">
        <span class="seal f-seal">案</span>
        <h3 class="kai">千例医案库</h3>
        <p>倪师 2005–2009 年临床医案结构化整理：诊断、病机、方剂剂量、针灸方案、疗效与医嘱，可按病名、方剂、年份检索。</p>
        <span class="more">进入医案库 →</span>
      </div>
      <div class="feature paper-card framed" @click="$router.push('/consult')">
        <span class="seal f-seal indigo">问</span>
        <h3 class="kai">经方问诊</h3>
        <p>以倪海厦经方思维为底本的 AI 助教，自动检索知识库原文作答，讲解六经辨证与方义，仅供学习参考。</p>
        <span class="more">开始问诊 →</span>
      </div>
      <div class="feature paper-card framed" @click="$router.push('/search')">
        <span class="seal f-seal ochre">检</span>
        <h3 class="kai">全文检索</h3>
        <p>一个关键词，贯通三百余章讲义与千例医案。输入方名、病名、穴位，即刻定位原文出处。</p>
        <span class="more">开始检索 →</span>
      </div>
    </section>

    <section class="container quote-sec">
      <blockquote class="kai">
        「张仲景怎么写的，你就怎么用。经方啊，你不要自己乱改。」
        <cite>—— 倪海厦</cite>
      </blockquote>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ChatDotRound, Reading } from '@element-plus/icons-vue'
import Taiji from '@/components/Taiji.vue'
import { docApi, miscApi } from '@/api'
import { fmtNum } from '@/utils/format'

const stats = ref({ documents: 0, chapters: 0, words: 0, cases: 0 })
const categories = ref<{ name: string; count: number }[]>([])

const counters = computed(() => [
  { label: '典籍卷册', value: stats.value.documents || '—' },
  { label: '章节篇目', value: stats.value.chapters || '—' },
  { label: '结构化医案', value: stats.value.cases || '—' },
  { label: '讲义字数', value: stats.value.words ? fmtNum(stats.value.words) : '—' },
])

const meridians = ['太阳', '阳明', '少阳', '太阴', '少阴', '厥阴']
const numerals = ['壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']

const sixGroups = [
  {
    name: '三阳',
    items: [
      { name: '太阳', role: 'open', roleLabel: '开', desc: '主表，体表防御。脉浮、头项强痛而恶寒。', fang: '桂枝汤 · 麻黄汤' },
      { name: '少阳', role: 'pivot', roleLabel: '枢', desc: '半表半里，枢纽调节。口苦、咽干、目眩。', fang: '小柴胡汤' },
      { name: '阳明', role: 'close', roleLabel: '阖', desc: '主里实热，消化吸收。胃家实，身热汗出。', fang: '白虎汤 · 承气汤' },
    ],
  },
  {
    name: '三阴',
    items: [
      { name: '太阴', role: 'open', roleLabel: '开', desc: '受纳精华。腹满而吐，食不下，自利益甚。', fang: '理中汤' },
      { name: '少阴', role: 'pivot', roleLabel: '枢', desc: '贯通能量，心肾阳气。脉微细，但欲寐。', fang: '四逆汤 · 真武汤' },
      { name: '厥阴', role: 'close', roleLabel: '阖', desc: '末端供血，寒热错杂。消渴，气上撞心。', fang: '乌梅丸' },
    ],
  },
]

const catDesc: Record<string, string> = {
  伤寒金匮: '伤寒论条文全解 · 金匮要略二十三篇',
  黄帝内经: '人纪·黄帝内经讲义详细篇目',
  针灸本草: '针灸教程 · 神农本草经 · 天纪',
  临床医案: '医案集 · 闭门课 · 分类叙事医案',
  讲座心法: '梁冬对话 · 扶阳论坛 · 仲景心法',
  精萃速查: '六经辨证公式 · 经方剂量速查',
  研究资料: '著作观点 · 表达方式 · 时间线',
}

onMounted(async () => {
  const [s, c] = await Promise.allSettled([miscApi.publicStats(), docApi.categories()])
  if (s.status === 'fulfilled') stats.value = s.value
  if (c.status === 'fulfilled') categories.value = c.value
})
</script>

<style scoped lang="scss">
.hero {
  position: relative;
  padding: 56px 0 40px;
  overflow: hidden;
}
.mountains {
  position: absolute;
  inset: auto 0 0 0;
  height: 260px;
  opacity: 0.55;
  pointer-events: none;
  background:
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 260' preserveAspectRatio='none'%3E%3Cpath d='M0 200 C120 150 200 170 300 120 S480 60 560 110 S720 190 820 140 S1000 70 1080 120 S1180 160 1200 150 V260 H0Z' fill='%232e5753' fill-opacity='.10'/%3E%3Cpath d='M0 230 C150 190 260 210 380 170 S600 130 700 180 S900 230 1020 190 S1160 170 1200 185 V260 H0Z' fill='%232b2420' fill-opacity='.08'/%3E%3C/svg%3E") bottom/100% 100% no-repeat;
}
.hero-inner { display: flex; align-items: center; justify-content: space-between; gap: 40px; position: relative; }
.hero-text { display: flex; gap: 36px; align-items: flex-start; }
.vertical-title {
  writing-mode: vertical-rl;
  font-size: 22px;
  letter-spacing: 10px;
  color: var(--ink-2);
  border-left: 1px solid var(--line);
  padding-left: 14px;
  display: flex;
  gap: 8px;
  .sub { color: var(--cinnabar); font-size: 16px; margin-top: 40px; }
}
.eyebrow { color: var(--indigo); letter-spacing: 4px; font-size: 14px; margin: 0 0 8px; }
h1 {
  font-size: clamp(40px, 6vw, 68px);
  line-height: 1.25;
  margin: 0 0 20px;
  letter-spacing: 6px;
  font-weight: 700;
  em { font-style: normal; color: var(--cinnabar); position: relative; }
}
.lead { max-width: 520px; color: var(--ink-2); font-size: 16px; line-height: 2; margin: 0 0 30px; }
.cta { display: flex; gap: 14px; flex-wrap: wrap; .el-icon { margin-right: 6px; } }

.hero-art {
  position: relative;
  width: 360px;
  height: 360px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--ink);
}
.ring {
  position: absolute;
  inset: 0;
  border: 1px dashed var(--gold);
  border-radius: 50%;
  &::before {
    content: '';
    position: absolute;
    inset: 40px;
    border: 1px solid var(--line);
    border-radius: 50%;
  }
}
.ring-char {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 46px;
  height: 46px;
  margin: -23px 0 0 -23px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 50%;
  font-size: 15px;
  color: var(--ink);
  box-shadow: var(--shadow);
}
.taiji-spin { animation: spin 60s linear infinite; filter: drop-shadow(0 6px 14px rgba(43, 36, 32, 0.2)); }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .taiji-spin { animation: none; } }
.hero-seal {
  position: absolute;
  right: 10px;
  bottom: 24px;
  padding: 8px 6px;
  font-size: 16px;
  line-height: 1.2;
  transform: rotate(6deg);
}

.counters {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  margin-top: 40px;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  position: relative;
}
.counter {
  text-align: center;
  padding: 18px 0;
  display: flex;
  flex-direction: column;
  & + .counter { border-left: 1px solid var(--line-soft); }
  .num { font-size: 34px; color: var(--cinnabar); font-weight: 700; line-height: 1.3; }
  .label { font-size: 13px; color: var(--ink-3); letter-spacing: 3px; }
}

.sec { padding: 48px 20px 8px; }

.six { display: flex; flex-direction: column; gap: 18px; }
.six-group { display: flex; gap: 18px; align-items: stretch; }
.six-label {
  writing-mode: vertical-rl;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  background: var(--ink);
  color: #f1e6d0;
  font-size: 20px;
  letter-spacing: 8px;
  border-radius: 3px;
  flex-shrink: 0;
}
.six-group:nth-child(2) .six-label { background: var(--indigo); }
.six-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; flex: 1; }
.six-card { padding: 18px 20px; transition: transform 0.2s, box-shadow 0.2s; &:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); } }
.six-head { display: flex; align-items: center; justify-content: space-between; }
.six-name { font-size: 24px; letter-spacing: 4px; }
.six-role {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-family: var(--font-kai);
  color: #fff;
  &.open { background: var(--cinnabar); }
  &.pivot { background: var(--gold); }
  &.close { background: var(--indigo); }
}
.six-desc { color: var(--ink-2); font-size: 14px; margin: 10px 0 8px; min-height: 50px; }
.six-fang {
  font-size: 14px;
  margin: 0;
  color: var(--ink);
  span { font-size: 12px; color: var(--ink-3); border: 1px solid var(--line); padding: 0 6px; margin-right: 8px; border-radius: 2px; }
}

.cats { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
.cat {
  display: grid;
  grid-template-columns: 52px 1fr auto;
  grid-template-rows: auto auto;
  align-items: center;
  column-gap: 12px;
  padding: 18px 20px;
  color: var(--ink);
  transition: all 0.2s;
  &:hover { border-color: var(--cinnabar); transform: translateY(-2px); box-shadow: var(--shadow-lg); color: var(--ink); }
}
.cat-idx {
  grid-row: span 2;
  width: 52px;
  height: 52px;
  border: 1px solid var(--cinnabar);
  color: var(--cinnabar);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  border-radius: 50%;
}
.cat-name { font-size: 20px; letter-spacing: 3px; }
.cat-count { font-size: 12px; color: var(--ink-3); }
.cat-desc { grid-column: 2 / span 2; font-size: 13px; color: var(--ink-3); }

.features { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; padding-top: 56px; }
.feature {
  padding: 28px 26px;
  cursor: pointer;
  transition: all 0.2s;
  &:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); .more { color: var(--cinnabar); } }
  h3 { font-size: 22px; letter-spacing: 3px; margin: 14px 0 8px; }
  p { color: var(--ink-2); font-size: 14.5px; margin: 0 0 14px; min-height: 76px; }
  .more { color: var(--ink-3); font-size: 14px; letter-spacing: 1px; }
}
.f-seal {
  width: 46px;
  height: 46px;
  font-size: 24px;
  &.indigo { background: var(--indigo); box-shadow: inset 0 0 0 2px var(--indigo), inset 0 0 0 3px rgba(251, 238, 230, 0.7); }
  &.ochre { background: var(--ochre); box-shadow: inset 0 0 0 2px var(--ochre), inset 0 0 0 3px rgba(251, 238, 230, 0.7); }
}

.quote-sec { padding: 56px 20px 0; text-align: center; }
.quote-sec blockquote {
  margin: 0 auto;
  max-width: 760px;
  font-size: 24px;
  letter-spacing: 3px;
  color: var(--ink);
  line-height: 1.9;
  cite { display: block; font-size: 15px; color: var(--ink-3); margin-top: 8px; font-style: normal; }
}

@media (max-width: 960px) {
  .hero-art { display: none; }
  .vertical-title { display: none; }
  .six-row, .features { grid-template-columns: 1fr; }
  .counters { grid-template-columns: repeat(2, 1fr); }
  .counter:nth-child(3) { border-left: none; }
}
</style>
