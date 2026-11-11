#!/usr/bin/env python3
"""Рендер фрагментов консольного демо в PNG для отчёта."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CONSOLE = ROOT / "demo_output" / "demo_console.txt"
OUT_DIR = ROOT / "reports" / "figures"

BG = "#111318"
BAR = "#1c1f26"
TEXT = "#e8e8ed"
MUTED = "#9a9aa2"
GREEN = "#5dd39e"
ORANGE = "#ffb340"
RED = "#ff6b6b"
BLUE = "#6cb6ff"
CYAN = "#7ee0e0"

FONT = "C:/Windows/Fonts/consola.ttf"
FONT_BOLD = "C:/Windows/Fonts/consolab.ttf"


def color_for(line: str) -> str:
    if "[X]" in line:
        return RED
    if "[!]" in line:
        return ORANGE
    if "[OK]" in line:
        return GREEN
    if "REQ-DEMO" in line or "Аудит:" in line:
        return CYAN
    if "Маршрут:" in line or "Категория:" in line or "Сумма:" in line:
        return BLUE
    if line.strip().startswith(("╭", "╰", "├")):
        return MUTED
    return TEXT


def render(card: str, name: str, caption: str) -> None:
    lines = [f"PS C:\\AI-Procurement-Agent> {caption}", ""] + card.splitlines()
    font = ImageFont.truetype(FONT, 17)
    font_bold = ImageFont.truetype(FONT_BOLD, 16)
    line_h = 24
    pad = 28
    # Ширина по самой длинной строке: иначе справа остаётся чёрная полоса,
    # а текст на странице PDF выходит слишком мелким.
    text_width = max(font.getlength(line) for line in lines)
    width = max(760, int(text_width) + pad * 2)
    bar_h = 48
    height = bar_h + 26 + pad * 2 + line_h * len(lines)

    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, bar_h], fill=BAR)
    for i, color in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
        draw.ellipse([18 + i * 22, 17, 30 + i * 22, 29], fill=color)
    draw.text((100, 14), "demo — терминальный запуск прототипа", font=font_bold, fill=MUTED)

    y = bar_h + 26
    for line in lines:
        color = GREEN if line.startswith("PS ") else color_for(line)
        draw.text((pad, y), line, font=font, fill=color)
        y += line_h

    path = OUT_DIR / name
    img.save(path, optimize=True)
    print(f"Сохранено: {path} ({width}x{height})")


def main() -> None:
    text = CONSOLE.read_text(encoding="utf-8")
    cards = [c for c in re.split(r"\n\n(?=╭)", text) if c.strip()]
    render(cards[0], "fig_demo_review.png", "python -m agent.cli --demo")
    render(cards[2], "fig_demo_manager.png", "python -m agent.cli --demo")
    render(cards[4], "fig_demo_auto.png", "python -m agent.cli --demo")


if __name__ == "__main__":
    main()
