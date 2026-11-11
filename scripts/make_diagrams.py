#!/usr/bin/env python3
"""Схема архитектуры решения для отчёта."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "figures" / "fig_architecture.png"

BLUE = "#0071e3"
BLUE_L = "#e8f2ff"
GREEN = "#34c759"
GREEN_L = "#eaf8ee"
ORANGE = "#ff9f0a"
ORANGE_L = "#fff4e0"
GRAY = "#8e8e93"
GRAY_L = "#f5f5f7"
TEXT = "#1d1d1f"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "text.color": TEXT})


def box(ax, x, y, w, h, title, subtitle="", fc=BLUE_L, ec=BLUE, title_size=9.5):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.1, edgecolor=ec, facecolor=fc, zorder=3,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h - 0.22, title, ha="center", va="top", fontsize=title_size, fontweight="bold", zorder=4)
    if subtitle:
        ax.text(x + w / 2, y + h - 0.47, subtitle, ha="center", va="top", fontsize=7.4, color="#4a4a4f", zorder=4, linespacing=1.35)


def arrow(ax, x1, y1, x2, y2, color=GRAY, style="-|>", lw=1.2):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=11,
        linewidth=lw, color=color, zorder=2, shrinkA=2, shrinkB=2,
    ))


def main() -> None:
    fig, ax = plt.subplots(figsize=(12.2, 6.2))
    ax.set_xlim(0, 12.2)
    ax.set_ylim(0, 6.2)
    ax.axis("off")

    # Заголовки зон
    ax.text(0.35, 5.95, "Вход", fontsize=10, fontweight="bold", color=GRAY)
    ax.text(3.0, 5.95, "AI-агент «ЗакупКИ»", fontsize=10, fontweight="bold", color=BLUE)
    ax.text(9.75, 5.95, "Результат", fontsize=10, fontweight="bold", color=GRAY)

    # Вход
    box(ax, 0.25, 3.55, 1.85, 1.8, "Каналы заявок", "1С:Заявки\nE-mail\nExcel\nсвободный текст", fc=GRAY_L, ec=GRAY)

    # Контейнер агента
    ax.add_patch(FancyBboxPatch(
        (3.0, 1.35), 5.95, 4.05,
        boxstyle="round,pad=0.03,rounding_size=0.12",
        linewidth=1.2, edgecolor=BLUE, facecolor="#fbfdff", linestyle=(0, (4, 3)), zorder=1,
    ))

    # Внутренние блоки
    box(ax, 3.2, 3.85, 2.55, 1.25, "1. Извлечение полей", "regex + справочники\n(опционально LLM)", fc=BLUE_L, ec=BLUE)
    box(ax, 6.15, 3.85, 2.55, 1.25, "2. Категория", "TF-IDF + LogReg\nconfidence + fallback", fc=BLUE_L, ec=BLUE)
    box(ax, 3.2, 2.35, 2.55, 1.25, "3. Проверки", "полнота, бюджет,\nпорог, дубликаты", fc=GREEN_L, ec=GREEN)
    box(ax, 6.15, 2.35, 2.55, 1.25, "4. Риск и маршрут", "risk score 0–100\n4 маршрута", fc=GREEN_L, ec=GREEN)
    box(ax, 3.2, 1.55, 5.5, 0.62, "5. Генерация черновика сообщения и карточки", "", fc=ORANGE_L, ec=ORANGE, title_size=8.8)

    # Человек
    box(ax, 9.55, 3.55, 2.25, 1.8, "Человек-владелец", "подтверждает решение\nи внешнее действие", fc=ORANGE_L, ec=ORANGE)

    # Результаты
    box(ax, 9.55, 1.45, 2.25, 1.65, "Действия", "карточка в ERP\nписьмо заявителю\nзадача закупщику\nмеморандум", fc=GRAY_L, ec=GRAY)

    # Данные и аудит
    box(ax, 3.2, 0.35, 2.55, 0.72, "История заявок", "2 247 записей, цены,\nпоставщики, дубликаты", fc=GRAY_L, ec=GRAY, title_size=8.2)
    box(ax, 6.15, 0.35, 2.55, 0.72, "Правила и аудит", "пороги, роли,\nJSONL-журнал", fc=GRAY_L, ec=GRAY, title_size=8.2)

    # Стрелки
    arrow(ax, 2.10, 4.45, 3.18, 4.45, color=BLUE)
    arrow(ax, 5.75, 4.45, 6.13, 4.45, color=BLUE)
    arrow(ax, 7.45, 3.83, 7.45, 3.62, color=GREEN)
    arrow(ax, 6.15, 2.95, 5.77, 2.95, color=GREEN)
    arrow(ax, 5.75, 2.33, 5.75, 2.19, color=ORANGE)
    arrow(ax, 7.45, 2.33, 7.45, 2.19, color=ORANGE)
    arrow(ax, 8.72, 1.86, 9.53, 3.55, color=ORANGE)
    arrow(ax, 10.68, 3.53, 10.68, 3.12, color=ORANGE)
    arrow(ax, 3.75, 1.37, 3.75, 1.09, color=GRAY, style="<|-|>", lw=1.0)
    arrow(ax, 7.45, 1.37, 7.45, 1.09, color=GRAY, style="<|-|>", lw=1.0)

    # Легенда
    ax.plot([0.35, 0.75], [0.75, 0.75], color=BLUE, linewidth=2)
    ax.text(0.82, 0.75, "автоматически", va="center", fontsize=8)
    ax.plot([0.35, 0.75], [0.45, 0.45], color=ORANGE, linewidth=2)
    ax.text(0.82, 0.45, "решение человека", va="center", fontsize=8)

    fig.tight_layout()
    fig.savefig(OUT, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Сохранено: {OUT}")


if __name__ == "__main__":
    main()
