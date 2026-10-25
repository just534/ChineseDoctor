import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const md = new MarkdownIt({ html: false, linkify: true, breaks: false, typographer: false })

export interface Heading { level: number; text: string; id: string }

/** 渲染 Markdown 并为 h2-h4 生成锚点，返回 html 与目录 */
export function renderMarkdown(src: string, opts: { headingPrefix?: string } = {}) {
  const headings: Heading[] = []
  const tokens = md.parse(src, {})
  let i = 0
  for (let t = 0; t < tokens.length; t++) {
    const tok = tokens[t]
    if (tok.type === 'heading_open') {
      const level = Number(tok.tag.slice(1))
      const text = tokens[t + 1]?.children?.map((c) => c.content).join('') ?? ''
      const id = `${opts.headingPrefix ?? 'h'}-${i++}`
      tok.attrSet('id', id)
      if (level >= 2 && level <= 4) headings.push({ level, text: text.replace(/[*_`]/g, ''), id })
    }
  }
  const html = DOMPurify.sanitize(md.renderer.render(tokens, md.options, {}), { ADD_ATTR: ['id', 'target'] })
  return { html, headings }
}

export function renderSimple(src: string) {
  return DOMPurify.sanitize(md.render(src))
}
