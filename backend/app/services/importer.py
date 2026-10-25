"""把原 nihaixia 仓库的 Markdown 知识库导入数据库。

- 典籍/讲义/叙事医案 -> documents + chapters（按 ## 分章，过长章节再按下级标题切分）
- cases/00_merged_table.md -> medical_cases（1257 例结构化医案）
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Chapter, Document, MedicalCase

log = logging.getLogger(__name__)

MAX_CHAPTER_CHARS = 40_000
TARGET_CHUNK_CHARS = 30_000


@dataclass(frozen=True)
class Entry:
    path: str
    slug: str
    category: str
    title: str | None = None


# 分类顺序即前台展示顺序
CATEGORIES = ["伤寒金匮", "黄帝内经", "针灸本草", "临床医案", "讲座心法", "精萃速查", "研究资料"]

MANIFEST: list[Entry] = [
    Entry("modules/01_shanghan_sun.md", "shanghan-taiyang", "伤寒金匮"),
    Entry("modules/13_shanghan_quebing.md", "shanghan-buqi", "伤寒金匮"),
    Entry("modules/02_shanghan_other.md", "shanghan-other", "伤寒金匮"),
    Entry("modules/04_jingui.md", "jingui", "伤寒金匮"),
    Entry("modules/05_huangdi_neijing.md", "jingui-5-7", "伤寒金匮"),
    Entry("modules/08_huangdi_detail.md", "huangdi-neijing", "黄帝内经"),
    Entry("modules/09_zhenjiu_bencao.md", "zhenjiu-bencao", "针灸本草"),
    Entry("references/distilled/02-acupuncture-quick-ref.md", "acupuncture-quick-ref", "针灸本草", "针灸速查手册"),
    Entry("references/distilled/04-acupuncture-highlights.md", "acupuncture-highlights", "针灸本草"),
    Entry("modules/03_yian.md", "yian", "临床医案"),
    Entry("cases/01_cancer.md", "cases-cancer", "临床医案"),
    Entry("cases/02_cardiovascular.md", "cases-cardiovascular", "临床医案"),
    Entry("cases/03_metabolic.md", "cases-metabolic", "临床医案"),
    Entry("cases/04_autoimmune.md", "cases-autoimmune", "临床医案"),
    Entry("cases/05_neurological.md", "cases-neurological", "临床医案"),
    Entry("cases/06_other.md", "cases-other", "临床医案"),
    Entry("distilled_cases.md", "distilled-cases", "临床医案"),
    Entry("modules/06_liangdong.md", "liangdong", "讲座心法"),
    Entry("modules/07_bimen_hantang.md", "bimen-hantang", "讲座心法"),
    Entry("modules/10_fuyang_luntan.md", "fuyang-luntan", "讲座心法"),
    Entry("modules/11_zhongjing_xinfa.md", "zhongjing-xinfa", "讲座心法"),
    Entry("modules/12_stanford_jingfang.md", "stanford-jingfang", "讲座心法"),
    Entry("modules/14_yijinjing_bidu.md", "yijinjing-bidu", "讲座心法"),
    Entry("references/distilled/01-six-meridian-formulas.md", "six-meridian-formulas", "精萃速查"),
    Entry("references/distilled/05-clinical-dose-quickref.md", "clinical-dose", "精萃速查"),
    Entry("references/distilled/06-clinical-dose-c99.md", "clinical-dose-c", "精萃速查"),
    Entry("references/distilled/03-clinical-experience.md", "clinical-experience", "精萃速查"),
    Entry("expression_style.md", "expression-style", "研究资料"),
    Entry("references/research/01-writings.md", "research-writings", "研究资料"),
    Entry("references/research/02-conversations.md", "research-conversations", "研究资料"),
    Entry("references/research/03-expression-dna.md", "research-expression", "研究资料"),
    Entry("references/research/04-external-views.md", "research-views", "研究资料"),
    Entry("references/research/05-decisions.md", "research-decisions", "研究资料"),
    Entry("references/research/06-timeline.md", "research-timeline", "研究资料"),
    Entry("references/research/07-teaching-methodology.md", "research-teaching", "研究资料"),
    Entry("references/research/08-clinical-cases.md", "research-clinical", "研究资料"),
]

CASES_TABLE = "cases/00_merged_table.md"

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")


def clean_inline(text: str) -> str:
    text = re.sub(r"[*_`]+", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return text.strip()


def count_words(text: str) -> int:
    # 中文按字计，英文按词计
    cjk = len(re.findall(r"[一-鿿]", text))
    latin = len(re.findall(r"[A-Za-z0-9]+", text))
    return cjk + latin


def _split_by_level(lines: list[str], level: int) -> list[tuple[str | None, list[str]]]:
    """按指定级别标题切块；返回 [(标题, 行列表)]，首块标题可能为 None。"""
    blocks: list[tuple[str | None, list[str]]] = [(None, [])]
    in_fence = False
    for line in lines:
        if _FENCE.match(line):
            in_fence = not in_fence
        m = None if in_fence else _HEADING.match(line)
        if m and len(m.group(1)) == level:
            blocks.append((clean_inline(m.group(2)), [line]))
        else:
            blocks[-1][1].append(line)
    if blocks[0][0] is None and not "".join(blocks[0][1]).strip():
        blocks.pop(0)
    return blocks


def _chunk(title: str, lines: list[str], level: int) -> list[tuple[str, str]]:
    text = "".join(lines)
    if len(text) <= MAX_CHAPTER_CHARS or level > 4:
        return [(title, text)]
    subs = _split_by_level(lines, level)
    if len(subs) <= 1:
        return _chunk(title, lines, level + 1)
    # 先递归把每个子块切到上限以内，再顺序合并成目标大小
    pieces: list[tuple[str | None, str]] = []
    for sub_title, sub_lines in subs:
        if sub_title is None:
            pieces.append((None, "".join(sub_lines)))
        else:
            pieces.extend(_chunk(sub_title, sub_lines, level + 1))
    groups: list[list[tuple[str | None, str]]] = [[]]
    size = 0
    for p in pieces:
        if groups[-1] and size + len(p[1]) > TARGET_CHUNK_CHARS:
            groups.append([])
            size = 0
        groups[-1].append(p)
        size += len(p[1])
    out = []
    for g in groups:
        names = [t for t, _ in g if t]
        if not names:
            label = title
        elif len(names) == 1:
            label = f"{title} · {names[0]}"
        else:
            label = f"{title} · {names[0]} 至 {names[-1]}"
        out.append((label[:300], "".join(c for _, c in g)))
    return out


def split_markdown(md: str) -> tuple[str | None, list[tuple[str, str]]]:
    """返回 (文档一级标题, [(章节标题, 章节 Markdown)])"""
    lines = md.splitlines(keepends=True)
    doc_title = None
    for i, line in enumerate(lines):
        m = _HEADING.match(line)
        if m and len(m.group(1)) == 1:
            doc_title = re.sub(r"^[\w-]+\.md\s*-\s*", "", clean_inline(m.group(2)))
            lines = lines[:i] + lines[i + 1 :]
            break
        if line.strip():
            break
    chapters: list[tuple[str, str]] = []
    for title, block in _split_by_level(lines, 2):
        content = "".join(block)
        if title is None:
            # 只有元信息引用块（> **内容**：…）的开篇已提取为文档简介，不单独成章
            body = [l for l in block if l.strip() and not re.match(r"^\s*(>|---|\*\*\*)", l)]
            if len("".join(body).strip()) < 20:
                continue
            title = "导读"
        chapters.extend(_chunk(title, block, 3))
    if not chapters:
        chapters = [("正文", "".join(lines))]
    return doc_title, chapters


def extract_summary(md: str) -> str:
    for line in md.splitlines()[:30]:
        m = re.match(r"^>\s*\*\*(内容|用途|来源)\*\*[:：]\s*(.+)", line)
        if m:
            return clean_inline(m.group(2))[:300]
    for line in md.splitlines()[:30]:
        if line.startswith(">") and len(line) > 6:
            return clean_inline(line.lstrip("> "))[:300]
    return ""


_EMPTY = {"", "---", "-", "未提及", "无", "/"}


def _cell(v: str) -> str:
    v = v.strip()
    return "" if v in _EMPTY else v


def parse_cases(md: str) -> list[dict]:
    rows = []
    for line in md.splitlines():
        if not re.match(r"^\|\s*\d+\s*\|", line):
            continue
        cells = [c for c in line.strip().strip("|").split("|")]
        if len(cells) < 12:
            continue
        cells = cells[:11] + ["|".join(cells[11:])]
        seq, date_text, patient, diagnosis, patho, western, rx, acu, principle, outcome, advice, comment = (
            _cell(c) for c in cells
        )
        if not (diagnosis or patho or rx or comment):
            continue
        diagnosis = diagnosis or "（未注明）"
        ym = re.search(r"(19|20)\d{2}", date_text)
        rows.append(
            dict(
                seq=int(seq),
                date_text=date_text[:100],
                year=int(ym.group(0)) if ym else None,
                patient=patient[:200],
                diagnosis=diagnosis,
                pathogenesis=patho,
                western_view=western,
                prescription=rx,
                acupuncture=acu,
                principle=principle,
                outcome=outcome,
                advice=advice,
                comment=comment,
            )
        )
    return rows


def import_documents(db: Session, content_dir: Path, *, replace: bool = False) -> int:
    n = 0
    for sort, entry in enumerate(MANIFEST):
        path = content_dir / entry.path
        if not path.exists():
            log.warning("内容文件缺失：%s", path)
            continue
        existing = db.scalar(select(Document).where(Document.slug == entry.slug))
        if existing and not replace:
            continue
        if existing:
            db.delete(existing)
            db.flush()
        md = path.read_text(encoding="utf-8")
        doc_title, chapters = split_markdown(md)
        title = entry.title or doc_title or path.stem
        doc = Document(
            slug=entry.slug,
            title=title[:200],
            category=entry.category,
            summary=extract_summary(md),
            source_path=entry.path,
            sort=sort,
        )
        total = 0
        for i, (ct, cc) in enumerate(chapters):
            wc = count_words(cc)
            total += wc
            doc.chapters.append(Chapter(title=ct, content=cc, word_count=wc, sort=i))
        doc.word_count = total
        db.add(doc)
        n += 1
    db.commit()
    return n


def import_cases(db: Session, content_dir: Path, *, replace: bool = False) -> int:
    path = content_dir / CASES_TABLE
    if not path.exists():
        return 0
    if db.scalar(select(func.count(MedicalCase.id))) and not replace:
        return 0
    if replace:
        db.query(MedicalCase).delete()
    rows = parse_cases(path.read_text(encoding="utf-8"))
    db.add_all(MedicalCase(**r) for r in rows)
    db.commit()
    return len(rows)


def import_all(db: Session, content_dir: Path, *, replace: bool = False) -> tuple[int, int]:
    docs = import_documents(db, content_dir, replace=replace)
    cases = import_cases(db, content_dir, replace=replace)
    log.info("内容导入完成：%d 篇典籍，%d 例医案", docs, cases)
    return docs, cases
