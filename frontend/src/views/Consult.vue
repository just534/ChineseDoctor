<template>
  <div class="container consult">
    <div class="consult-head">
      <div>
        <h2 class="sec-title">经方问诊</h2>
        <p class="sec-sub">以倪海厦经方思维为底本的 AI 助教 · 自动检索知识库原文作答 · 仅供学习参考</p>
      </div>
      <div v-if="quota" class="quota">
        今日已问 <b>{{ quota.used }}</b>{{ quota.limit ? ` / ${quota.limit}` : '' }} 次
      </div>
    </div>

    <div v-if="!auth.user" class="gate paper-card framed">
      <span class="seal gate-seal">问</span>
      <h3 class="kai">登录后开始问诊</h3>
      <p>问诊会调用大模型并检索知识库，需要登录会员账号。</p>
      <el-button type="primary" @click="$router.push({ name: 'login', query: { redirect: '/consult' } })">登录</el-button>
    </div>
    <div v-else-if="!auth.can('ai:chat')" class="gate paper-card framed">
      <h3 class="kai">暂无问诊权限</h3>
      <p>请联系管理员为您的账号分配「AI 问诊」权限。</p>
    </div>
    <div v-else-if="!auth.config.ai_enabled" class="gate paper-card framed">
      <h3 class="kai">问诊服务尚未开通</h3>
      <p>管理员配置 <code>ANTHROPIC_API_KEY</code> 后即可使用。</p>
    </div>

    <div v-else class="chat paper-card">
      <div ref="listEl" class="messages">
        <div v-if="!messages.length" class="welcome">
          <span class="seal w-seal">倪</span>
          <p class="kai">「我跟你说，中医很简单，就是阴阳气血。你有什么问题，尽管问。」</p>
          <div class="examples">
            <button v-for="e in examples" :key="e" @click="send(e)">{{ e }}</button>
          </div>
        </div>
        <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
          <div class="avatar">{{ m.role === 'user' ? (auth.user.nickname || auth.user.username).slice(0, 1) : '倪' }}</div>
          <div class="bubble">
            <div v-if="m.role === 'assistant'" class="md" v-html="renderSimple(m.content || '…')" />
            <div v-else class="plain">{{ m.content }}</div>
            <div v-if="m.refs?.length" class="refs">
              <span>参考原文：</span>
              <router-link v-for="r in m.refs" :key="r.chapter_id" :to="`/library/${r.slug}/${r.chapter_id}`" target="_blank">
                《{{ r.document }}》{{ r.title }}
              </router-link>
            </div>
            <div v-if="m.error" class="err">{{ m.error }}</div>
          </div>
        </div>
      </div>
      <div class="composer">
        <el-input
          v-model="input"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 6 }"
          resize="none"
          maxlength="2000"
          placeholder="描述症状或提问，例如：小建中汤和桂枝汤有什么区别？（Enter 发送，Shift+Enter 换行）"
          @keydown.enter.exact.prevent="send()"
        />
        <div class="composer-bar">
          <span class="hint">⚠️ AI 回答仅供中医学习交流，不构成诊疗建议。急重症请立即就医。</span>
          <div>
            <el-button v-if="messages.length && !streaming" text @click="messages = []">清空</el-button>
            <el-button v-if="streaming" @click="stop">停止</el-button>
            <el-button type="primary" :loading="streaming" :disabled="!input.trim()" @click="send()">发送</el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { miscApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { renderSimple } from '@/utils/markdown'
import { tokenStore } from '@/utils/token'

interface Ref { chapter_id: number; title: string; document: string; slug: string }
interface Msg { role: 'user' | 'assistant'; content: string; refs?: Ref[]; error?: string }

const auth = useAuthStore()
const messages = ref<Msg[]>([])
const input = ref('')
const streaming = ref(false)
const listEl = ref<HTMLElement>()
const quota = ref<{ used: number; limit: number | null } | null>(null)
let controller: AbortController | null = null

const examples = ['小建中汤和桂枝汤有什么区别？', '怎么判断是太阳病还是少阳病？', '脉结代为什么要用炙甘草汤？', '失眠在经方里怎么辨证？']

async function refreshQuota() {
  try { quota.value = await miscApi.aiQuota() } catch { /* ignore */ }
}

function scrollBottom() {
  nextTick(() => listEl.value?.scrollTo({ top: listEl.value.scrollHeight }))
}

async function send(text?: string) {
  const content = (text ?? input.value).trim()
  if (!content || streaming.value) return
  input.value = ''
  messages.value.push({ role: 'user', content })
  const history = messages.value.slice(-20).map(({ role, content }) => ({ role, content }))
  messages.value.push({ role: 'assistant', content: '' })
  const reply = messages.value[messages.value.length - 1]
  streaming.value = true
  scrollBottom()
  await refreshQuota() // 顺便刷新过期的 access token
  controller = new AbortController()
  try {
    const res = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tokenStore.access}` },
      body: JSON.stringify({ messages: history }),
      signal: controller.signal,
    })
    if (!res.ok || !res.body) {
      const err = await res.json().catch(() => ({}))
      reply.error = err.detail || `请求失败（${res.status}）`
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      let idx
      while ((idx = buf.indexOf('\n\n')) >= 0) {
        const raw = buf.slice(0, idx)
        buf = buf.slice(idx + 2)
        const ev = /^event: (.*)$/m.exec(raw)?.[1]
        const dataLine = /^data: (.*)$/m.exec(raw)?.[1]
        if (!ev || dataLine === undefined) continue
        const data = JSON.parse(dataLine)
        if (ev === 'delta') { reply.content += data; scrollBottom() }
        else if (ev === 'refs') reply.refs = data
        else if (ev === 'error') reply.error = data
      }
    }
  } catch (e) {
    if ((e as Error).name !== 'AbortError') reply.error = '网络异常，请稍后再试'
  } finally {
    streaming.value = false
    controller = null
    refreshQuota()
    scrollBottom()
  }
}

function stop() {
  controller?.abort()
}

onMounted(() => {
  if (auth.can('ai:chat') && auth.config.ai_enabled) refreshQuota()
})
</script>

<style scoped lang="scss">
.consult { padding-top: 36px; max-width: 980px; }
.consult-head { display: flex; justify-content: space-between; align-items: flex-start; }
.quota { font-size: 13px; color: var(--ink-3); padding-top: 8px; b { color: var(--cinnabar); } }
.gate {
  max-width: 560px;
  margin: 40px auto;
  padding: 40px;
  text-align: center;
  h3 { font-size: 24px; letter-spacing: 3px; margin: 16px 0 8px; }
  p { color: var(--ink-2); }
}
.gate-seal { width: 56px; height: 56px; font-size: 28px; }
.chat { display: flex; flex-direction: column; height: calc(100vh - 240px); min-height: 520px; overflow: hidden; }
.messages { flex: 1; overflow-y: auto; padding: 24px; }
.welcome {
  text-align: center;
  padding: 30px 0;
  p { font-size: 20px; color: var(--ink-2); letter-spacing: 1px; max-width: 520px; margin: 18px auto; line-height: 1.8; }
}
.w-seal { width: 60px; height: 60px; font-size: 32px; }
.examples {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  button {
    all: unset;
    cursor: pointer;
    padding: 8px 14px;
    border: 1px solid var(--line);
    border-radius: 18px;
    font-size: 14px;
    color: var(--ink-2);
    background: var(--paper);
    &:hover { border-color: var(--cinnabar); color: var(--cinnabar); }
  }
}
.msg {
  display: flex;
  gap: 12px;
  margin-bottom: 22px;
  &.user { flex-direction: row-reverse; .bubble { background: var(--indigo); color: #f5eedf; border-color: var(--indigo); } }
}
.avatar {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-kai);
  font-size: 17px;
  color: #fbeee6;
  background: var(--cinnabar);
}
.msg.user .avatar { background: var(--ink-2); }
.bubble {
  max-width: 78%;
  padding: 10px 16px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fffdf8;
  .md { font-size: 15px; line-height: 1.9; :deep(h2) { font-size: 19px; margin: 16px 0 10px; } :deep(h3) { font-size: 17px; } }
  .plain { white-space: pre-wrap; line-height: 1.8; }
}
.refs {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--line);
  font-size: 12.5px;
  color: var(--ink-3);
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  a { color: var(--indigo); }
}
.err { color: var(--el-color-danger); font-size: 13px; margin-top: 6px; }
.composer { border-top: 1px solid var(--line); padding: 14px 18px; background: var(--paper); }
.composer-bar { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; gap: 10px; }
.hint { font-size: 12px; color: var(--ink-3); }
@media (max-width: 640px) {
  .bubble { max-width: 88%; }
  .hint { display: none; }
  .messages { padding: 14px; }
}
</style>
