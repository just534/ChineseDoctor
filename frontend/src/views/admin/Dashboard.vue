<template>
  <div v-loading="!data" class="dash">
    <template v-if="data">
      <div class="stats">
        <div v-for="s in statCards" :key="s.label" class="stat admin-card">
          <span class="seal s-icon" :style="{ background: s.color, boxShadow: `inset 0 0 0 2px ${s.color}, inset 0 0 0 3px rgba(251,238,230,.7)` }">{{ s.char }}</span>
          <div>
            <div class="s-num kai">{{ s.value }}</div>
            <div class="s-label">{{ s.label }}</div>
          </div>
        </div>
      </div>
      <div class="grid">
        <div class="admin-card chart-card">
          <h3 class="admin-title">近七日活跃</h3>
          <div ref="trendEl" class="chart" />
        </div>
        <div class="admin-card chart-card">
          <h3 class="admin-title">角色分布</h3>
          <div ref="roleEl" class="chart" />
        </div>
      </div>
      <div class="grid">
        <div class="admin-card">
          <h3 class="admin-title">热门典籍</h3>
          <ol class="top">
            <li v-for="(d, i) in (data.top_documents as { title: string; views: number }[])" :key="d.title">
              <span class="rank" :class="{ hi: i < 3 }">{{ i + 1 }}</span>
              <span class="t">{{ d.title }}</span>
              <span class="v">{{ d.views }}</span>
            </li>
          </ol>
        </div>
        <div class="admin-card">
          <h3 class="admin-title">最近操作</h3>
          <el-timeline class="timeline">
            <el-timeline-item v-for="l in data.recent_logs" :key="l.id" :timestamp="fmtTime(l.created_at)" :type="l.success ? 'success' : 'danger'" size="normal">
              <b>{{ l.username || '匿名' }}</b> {{ ACTION_LABELS[l.action] || l.action }}
              <span v-if="l.target" class="cell-muted">· {{ l.target }}</span>
            </el-timeline-item>
          </el-timeline>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { miscApi } from '@/api'
import { ACTION_LABELS, fmtTime } from '@/utils/format'

const data = ref<any>(null)
const trendEl = ref<HTMLElement>()
const roleEl = ref<HTMLElement>()
const charts: { resize(): void; dispose(): void }[] = []

const statCards = computed(() => [
  { label: '注册用户', value: data.value.users, char: '人', color: '#2e5753' },
  { label: '本周新增', value: data.value.new_users_week, char: '新', color: '#a8322a' },
  { label: '典籍卷册', value: data.value.documents, char: '典', color: '#8b5a2b' },
  { label: '结构化医案', value: data.value.cases, char: '案', color: '#3c4a5c' },
  { label: '今日问诊', value: data.value.ai_calls_today, char: '问', color: '#b48d55' },
])

const onResize = () => charts.forEach((c) => c.resize())

onMounted(async () => {
  data.value = await miscApi.dashboard()
  await nextTick()
  const echarts = await import('@/utils/echarts')
  const font = { fontFamily: getComputedStyle(document.body).fontFamily }
  const trend = echarts.init(trendEl.value!)
  trend.setOption({
    textStyle: font,
    color: ['#a8322a', '#2e5753'],
    tooltip: { trigger: 'axis' },
    legend: { data: ['登录', '注册'], top: 0, right: 0 },
    grid: { left: 36, right: 16, top: 40, bottom: 28 },
    xAxis: { type: 'category', data: data.value.trend.days, axisLine: { lineStyle: { color: '#d8c8a8' } }, axisLabel: { color: '#85766a' } },
    yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: '#ebe1cc', type: 'dashed' } }, axisLabel: { color: '#85766a' } },
    series: [
      { name: '登录', type: 'line', smooth: true, data: data.value.trend.logins, areaStyle: { opacity: 0.12 }, symbolSize: 7 },
      { name: '注册', type: 'bar', barWidth: 14, data: data.value.trend.registrations, itemStyle: { borderRadius: [2, 2, 0, 0] } },
    ],
  })
  const role = echarts.init(roleEl.value!)
  role.setOption({
    textStyle: font,
    color: ['#a8322a', '#2e5753', '#b48d55', '#8b5a2b', '#3c4a5c', '#6b8f71'],
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: { color: '#4f4339' } },
    series: [{
      type: 'pie', radius: ['45%', '70%'], center: ['50%', '45%'],
      itemStyle: { borderColor: '#fbf7ee', borderWidth: 3 },
      label: { formatter: '{b}\n{c}', color: '#4f4339' },
      data: data.value.role_distribution.map((r: any) => ({ name: r.name, value: r.count })),
    }],
  })
  charts.push(trend, role)
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  charts.forEach((c) => c.dispose())
})
</script>

<style scoped lang="scss">
.dash { min-height: 400px; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 16px; margin-bottom: 16px; }
.stat { display: flex; align-items: center; gap: 16px; }
.s-icon { width: 48px; height: 48px; font-size: 24px; }
.s-num { font-size: 30px; font-weight: 700; line-height: 1.2; }
.s-label { font-size: 13px; color: var(--ink-3); letter-spacing: 2px; }
.grid { display: grid; grid-template-columns: 3fr 2fr; gap: 16px; margin-bottom: 16px; }
.chart { height: 280px; }
.top {
  list-style: none;
  padding: 0;
  margin: 0;
  li { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px dashed var(--line-soft); font-size: 14px; }
  .rank { width: 22px; height: 22px; border-radius: 50%; background: var(--paper-2); display: inline-flex; align-items: center; justify-content: center; font-size: 12px; &.hi { background: var(--cinnabar); color: #fff; } }
  .t { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .v { color: var(--ink-3); font-size: 12px; }
}
.timeline { max-height: 340px; overflow-y: auto; padding: 4px 4px 0 2px; font-size: 13.5px; }
@media (max-width: 1000px) { .grid { grid-template-columns: 1fr; } }
</style>
