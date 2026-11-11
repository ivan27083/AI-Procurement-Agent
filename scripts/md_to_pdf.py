#!/usr/bin/env python3
"""Markdown → PDF converter for the Russian project report.

Adapted from the `huashu-md-to-pdf` skill converter:
  * Russian TOC heading and metadata labels
  * Cyrillic-friendly font stack
  * smaller cover title for long Russian titles
  * named pages so the cover/TOC carry no headers
  * wide tables and long console lines never overflow the page

Usage:
    python scripts/md_to_pdf.py reports/report.md -o reports/report.pdf
"""

from __future__ import annotations

import argparse
import html as html_mod
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import markdown2
from weasyprint import CSS, HTML

FONT_SANS = "'Segoe UI', 'DejaVu Sans', 'Arial', sans-serif"
FONT_MONO = "'Cascadia Mono', 'Consolas', 'DejaVu Sans Mono', monospace"


def extract_metadata(md_content: str) -> dict[str, object]:
    meta: dict[str, object] = {"title": None, "subtitle": None, "fields": []}

    h1 = re.search(r"^# (.+)$", md_content, re.MULTILINE)
    if h1:
        meta["title"] = h1.group(1).strip()

    # Metadata is the **Key**: value block before the first level-2 heading.
    head = md_content.split("\n## ", 1)[0]
    for match in re.finditer(r"^\*\*([^*]+)\*\*:\s*(.+?)\s*$", head, re.MULTILINE):
        key, value = match.group(1).strip(), match.group(2).strip()
        if key.lower() in {"подзаголовок", "subtitle"}:
            meta["subtitle"] = value
        else:
            meta["fields"].append((key, value))
    return meta


def strip_metadata(md_content: str) -> str:
    head, sep, tail = md_content.partition("\n## ")
    head = re.sub(r"^\*\*[^*]+\*\*:\s*.+?$", "", head, flags=re.MULTILINE)
    return head + sep + tail


def build_toc_and_headings(md_content: str) -> tuple[str, list[dict[str, object]]]:
    """Replace ## / ### headings with anchored HTML and collect the TOC."""
    toc: list[dict[str, object]] = []
    out: list[str] = []

    for line in md_content.splitlines():
        if line.startswith("## ") and not line.startswith("### "):
            title = line[3:].strip()
            anchor = f"sec-{len(toc) + 1}"
            toc.append({"level": 2, "title": title, "id": anchor})
            out.extend(["", f'<h2 id="{anchor}">{title}</h2>', ""])
        elif line.startswith("### "):
            title = line[4:].strip()
            anchor = f"sub-{len(toc) + 1}"
            toc.append({"level": 3, "title": title, "id": anchor})
            out.extend(["", f'<h3 id="{anchor}">{title}</h3>', ""])
        else:
            out.append(line)

    return "\n".join(out), toc


def toc_html(items: list[dict[str, object]]) -> str:
    if not items:
        return ""
    parts = []
    for item in items:
        css = "toc-h2" if item["level"] == 2 else "toc-h3"
        parts.append(
            f'<div class="toc-item {css}"><a class="toc-link" href="#{item["id"]}">'
            f'{item["title"]}</a></div>'
        )
    return "\n".join(parts)


def cover_html(meta: dict[str, object]) -> str:
    title = str(meta.get("title") or "Отчёт")
    subtitle = str(meta.get("subtitle") or "")
    fields = meta.get("fields") or []
    rows = "\n".join(
        f'<div class="meta-row"><span class="meta-key">{html_mod.escape(k)}</span>'
        f'<span class="meta-value">{html_mod.escape(v.replace("`", ""))}</span></div>'
        for k, v in fields
    )
    sub = f'<p class="cover-subtitle">{html_mod.escape(subtitle)}</p>' if subtitle else ""
    return f"""
    <section class="cover">
        <div class="cover-inner">
            <div class="cover-kicker">УЧЕБНЫЙ ПРОЕКТ · КОНЦЕПЦИЯ AI-РЕШЕНИЯ</div>
            <h1 class="cover-title">{html_mod.escape(title)}</h1>
            {sub}
            <div class="cover-rule"></div>
            <div class="cover-meta">{rows}</div>
            <div class="cover-foot">Отчёт содержит все шесть этапов проекта,
            декларацию использования ИИ и раздел «Решения и ограничения».</div>
        </div>
    </section>
    """


def css() -> str:
    return f"""
    @page {{
        size: A4;
        margin: 20mm 17mm 18mm 17mm;
        @top-left {{
            content: "AI-агент для первичной обработки заявок на закупку";
            font-family: {FONT_SANS};
            font-size: 7.8pt;
            color: #86868b;
            padding-bottom: 3mm;
        }}
        @top-right {{
            content: counter(page);
            font-family: {FONT_SANS};
            font-size: 7.8pt;
            color: #86868b;
            padding-bottom: 3mm;
        }}
    }}
    @page cover {{
        margin: 0;
        @top-left {{ content: none; }}
        @top-right {{ content: none; }}
    }}
    @page toc {{
        @top-left {{ content: none; }}
        @top-right {{ content: none; }}
    }}

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    html {{ font-family: {FONT_SANS}; }}

    body {{
        font-family: {FONT_SANS};
        font-size: 10.4pt;
        line-height: 1.62;
        color: #1d1d1f;
        text-align: left;
        hyphens: auto;
    }}

    /* ---------- Обложка ---------- */
    .cover {{
        page: cover;
        height: 297mm;
        background: linear-gradient(160deg, #f5f7fb 0%, #ffffff 55%, #eef4ff 100%);
        page-break-after: always;
    }}
    .cover-inner {{
        padding: 74mm 24mm 0 24mm;
        border-top: 6mm solid #0071e3;
        height: 100%;
    }}
    .cover-kicker {{
        font-size: 8.6pt;
        letter-spacing: 2.4px;
        color: #0071e3;
        font-weight: 600;
        margin-bottom: 12mm;
    }}
    .cover-title {{
        font-size: 31pt;
        line-height: 1.16;
        font-weight: 600;
        letter-spacing: -0.6px;
        color: #101114;
        margin-bottom: 7mm;
        max-width: 150mm;
    }}
    .cover-subtitle {{
        font-size: 13.5pt;
        line-height: 1.45;
        color: #4a4a4f;
        font-weight: 400;
        max-width: 140mm;
    }}
    .cover-rule {{
        width: 34mm;
        height: 2.4pt;
        background: #0071e3;
        margin: 11mm 0 9mm 0;
    }}
    .cover-meta {{ font-size: 9.6pt; line-height: 1.5; }}
    .meta-row {{ margin-bottom: 2.4mm; }}
    .meta-key {{
        display: inline-block;
        width: 40mm;
        color: #86868b;
        font-size: 8.8pt;
    }}
    .meta-value {{ color: #1d1d1f; }}
    .cover-foot {{
        position: absolute;
        bottom: 26mm;
        left: 24mm;
        right: 24mm;
        font-size: 8.6pt;
        color: #86868b;
        border-top: 0.6pt solid #d2d2d7;
        padding-top: 4mm;
    }}

    /* ---------- Оглавление ---------- */
    .toc-page {{
        page: toc;
        page-break-after: always;
    }}
    .toc-header {{
        font-size: 20pt;
        font-weight: 600;
        letter-spacing: -0.3px;
        margin-bottom: 7mm;
        padding-bottom: 3mm;
        border-bottom: 1.4pt solid #d2d2d7;
    }}
    .toc-item {{ break-inside: avoid; }}
    .toc-item a {{ text-decoration: none; color: inherit; }}
    .toc-content {{ column-count: 2; column-gap: 11mm; }}
    .toc-h2 {{ margin-top: 1.8mm; }}
    .toc-h2 .toc-link {{
        font-size: 9.6pt;
        font-weight: 600;
        color: #1d1d1f;
        line-height: 1.3;
    }}
    .toc-h3 {{ margin-left: 5mm; }}
    .toc-h3 .toc-link {{
        font-size: 8.4pt;
        color: #55555c;
        line-height: 1.32;
    }}

    /* ---------- Заголовки ---------- */
    h2 {{
        font-size: 19pt;
        line-height: 1.22;
        font-weight: 600;
        color: #101114;
        letter-spacing: -0.3px;
        margin: 10mm 0 5.5mm 0;
        padding-bottom: 2.6mm;
        border-bottom: 1.4pt solid #d2d2d7;
        page-break-inside: avoid;
        page-break-after: avoid;
    }}
    .content > h2:first-of-type {{ margin-top: 0; }}
    h3 {{
        font-size: 13.2pt;
        font-weight: 600;
        color: #1d1d1f;
        margin: 7mm 0 2.6mm 0;
        page-break-after: avoid;
    }}
    h4 {{
        font-size: 11pt;
        font-weight: 600;
        color: #424245;
        margin: 5mm 0 2mm 0;
        page-break-after: avoid;
    }}

    /* ---------- Текст ---------- */
    p {{ margin-bottom: 2.8mm; }}
    ul, ol {{ margin: 0 0 3mm 5.6mm; }}
    li {{ margin-bottom: 1.5mm; }}
    li > ul, li > ol {{ margin-top: 1.5mm; margin-bottom: 1.5mm; }}
    strong {{ font-weight: 600; color: #101114; }}
    em {{ color: #424245; }}
    a {{ color: #0066cc; text-decoration: none; }}
    hr {{ border: none; border-top: 0.6pt solid #d2d2d7; margin: 6mm 0; }}

    /* ---------- Таблицы ---------- */
    .table-caption {{
        page-break-after: avoid;
        break-after: avoid;
        margin-bottom: 1.2mm;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 4mm 0 5mm 0;
        font-size: 8.7pt;
        line-height: 1.38;
    }}
    thead {{ display: table-header-group; }}
    th {{
        background: #f2f4f8;
        text-align: left;
        font-weight: 600;
        padding: 2.2mm 2.4mm;
        border-bottom: 1pt solid #c9ccd3;
        color: #1d1d1f;
        vertical-align: bottom;
        hyphens: manual;
    }}
    td {{
        padding: 1.9mm 2.4mm;
        border-bottom: 0.5pt solid #e2e4e9;
        color: #333338;
        vertical-align: top;
        hyphens: manual;
    }}
    tbody tr:nth-child(even) td {{ background: #fafbfc; }}
    tr {{ page-break-inside: avoid; }}
    table code {{ font-size: 8pt; }}

    /* ---------- Изображения ---------- */
    p > img, img {{
        display: block;
        max-width: 100%;
        /* Высокие скриншоты не должны занимать всю страницу: иначе подпись
           уезжает на следующую и там остаётся почти пустой лист. */
        max-height: 232mm;
        height: auto;
        margin: 4mm auto 1.6mm auto;
        page-break-inside: avoid;
    }}
    .fig-caption {{
        text-align: center;
        font-size: 8.6pt;
        color: #6e6e73;
        margin: 0 0 5mm 0;
        page-break-before: avoid;
    }}

    /* ---------- Код ---------- */
    pre {{
        background: #f6f7f9;
        border: 0.6pt solid #dcdfe4;
        border-radius: 2.4mm;
        padding: 3.4mm 4mm;
        margin: 3mm 0 4mm 0;
        font-family: {FONT_MONO};
        font-size: 7.9pt;
        line-height: 1.42;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        page-break-inside: avoid;
    }}
    pre code {{ background: none; padding: 0; color: #1d1d1f; font-family: inherit; }}
    code {{
        background: #f2f4f8;
        padding: 0.3mm 1.2mm;
        border-radius: 1mm;
        font-family: {FONT_MONO};
        font-size: 8.8pt;
        color: #b00040;
    }}

    /* ---------- Цитаты / врезки ---------- */
    blockquote {{
        border-left: 2.6pt solid #0071e3;
        background: #f7faff;
        padding: 3mm 4mm;
        margin: 3.4mm 0 4mm 0;
        color: #333338;
        font-size: 9.8pt;
        page-break-inside: avoid;
    }}
    blockquote p:last-child {{ margin-bottom: 0; }}

    /* ---------- Печать ---------- */
    p, li, blockquote {{ orphans: 3; widows: 3; }}
    .cover, .toc-page {{ page-break-inside: avoid; }}
    """


def warn_missing_images(html: str, base_dir: Path) -> None:
    missing = []
    for raw in re.findall(r'<img[^>]+\bsrc=(?:"([^"]*)"|\'([^\']*)\')', html):
        src = html_mod.unescape(raw[0] or raw[1])
        parsed = urlparse(src)
        if parsed.scheme in ("http", "https", "data"):
            continue
        path = unquote(parsed.path)
        candidate = Path(path) if parsed.scheme == "file" else base_dir / path
        if not candidate.exists():
            missing.append(src)
    if missing:
        print(f"  [!] Не найдено изображений: {len(missing)}")
        for src in missing:
            print(f"      - {src}")


def convert(input_file: str, output_file: str | None = None) -> None:
    source = Path(input_file).resolve()
    md = source.read_text(encoding="utf-8")
    print(f"Чтение: {source}")

    meta = extract_metadata(md)
    md = strip_metadata(md)

    # Drop the leading h1: it becomes the cover title.
    md = re.sub(r"^# .+?\n", "", md, count=1, flags=re.MULTILINE)

    md, toc = build_toc_and_headings(md)
    print(f"Разделов: {sum(1 for t in toc if t['level'] == 2)}, "
          f"подразделов: {sum(1 for t in toc if t['level'] == 3)}")

    extras = [
        "fenced-code-blocks",
        "tables",
        "code-friendly",
        "cuddled-lists",
        "strike",
        "task_list",
        "header-ids",
    ]
    body = markdown2.markdown(md, extras=extras)
    body = body.replace("<table>", '<table class="content-table">')
    body = body.replace("<blockquote>", '<blockquote class="quote-block">')
    # Подпись таблицы не должна оставаться внизу страницы без самой таблицы.
    body = body.replace('<p><strong>Таблица ', '<p class="table-caption"><strong>Таблица ')

    toc_items = toc_html(toc)
    full_html = f"""<!DOCTYPE html>
<html lang="ru-RU">
<head>
<meta charset="utf-8">
<title>{html_mod.escape(str(meta.get("title") or "Отчёт"))}</title>
</head>
<body>
{cover_html(meta)}
<section class="toc-page">
    <h2 class="toc-header">Содержание</h2>
    <div class="toc-content">{toc_items}</div>
</section>
<div class="content">
{body}
</div>
</body>
</html>"""

    if not output_file:
        output_file = str(source.with_suffix(".pdf"))
    output = Path(output_file).resolve()

    warn_missing_images(full_html, source.parent)
    print("Рендеринг PDF…")
    HTML(string=full_html, base_url=source.as_uri()).write_pdf(
        str(output), stylesheets=[CSS(string=css())]
    )
    size = os.path.getsize(output) / (1024 * 1024)
    print(f"Готово: {output} ({size:.1f} МБ)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Markdown → PDF для русского отчёта")
    parser.add_argument("input")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()
    try:
        convert(args.input, args.output)
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"Ошибка конвертации: {exc}")
        import traceback

        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
