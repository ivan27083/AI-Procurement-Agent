#!/usr/bin/env python3
"""Разведочный анализ и графики для отчёта."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "procurement_requests_raw.csv"
CLEAN = ROOT / "data" / "processed" / "procurement_requests_clean.csv"
QUALITY = ROOT / "data" / "processed" / "data_quality_report.json"
FIG = ROOT / "reports" / "figures"
METRICS = ROOT / "reports" / "eda_metrics.json"

FIG.mkdir(parents=True, exist_ok=True)

BLUE = "#0071e3"
GREEN = "#34c759"
ORANGE = "#ff9f0a"
RED = "#ff3b30"
GRAY = "#8e8e93"
LIGHT = "#e5e5ea"
TEXT = "#1d1d1f"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": LIGHT,
    "axes.labelcolor": TEXT,
    "text.color": TEXT,
    "xtick.color": "#6e6e73",
    "ytick.color": "#6e6e73",
    "axes.grid": True,
    "grid.color": "#f2f2f7",
    "grid.linewidth": 0.8,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def save(fig: plt.Figure, name: str) -> None:
    path = FIG / name
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {path.name}")


def style_axes(ax: plt.Axes, grid_axis: str = "y") -> None:
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.grid(axis=grid_axis, color="#f2f2f7", linewidth=0.9)
    ax.set_axisbelow(True)


def main() -> None:
    raw = pd.read_csv(RAW, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    clean = pd.read_csv(CLEAN, encoding="utf-8-sig")
    quality = json.loads(QUALITY.read_text(encoding="utf-8"))
    clean["created_at"] = pd.to_datetime(clean["created_at"])

    metrics: dict[str, object] = {}
    metrics["n_raw"] = len(raw)
    metrics["n_clean"] = len(clean)
    metrics["duplicates_removed"] = quality["duplicates_removed_total"]
    metrics["exact_duplicates"] = quality["exact_duplicates_removed"]
    metrics["near_duplicates"] = quality["near_duplicates_removed"]
    metrics["possible_duplicates_flagged"] = quality["possible_duplicates_flagged"]
    metrics["duplicate_share_raw"] = round(100 * quality["duplicates_removed_total"] / len(raw), 1)
    metrics["missing_before"] = quality["missing_before"]
    metrics["missing_after"] = quality["missing_after"]
    metrics["supplier_not_specified_before"] = quality["supplier_not_specified_before"]
    metrics["justification_short_before"] = quality["justification_short_before"]

    cat_counts = clean["category"].value_counts()
    metrics["category_counts"] = cat_counts.to_dict()
    metrics["category_share"] = (100 * cat_counts / len(clean)).round(1).to_dict()
    metrics["category_spend_mrub"] = (clean.groupby("category")["total_amount"].sum() / 1e6).round(1).sort_values(ascending=False).to_dict()

    status_counts = clean["status"].value_counts()
    metrics["status_counts"] = status_counts.to_dict()
    metrics["status_share"] = (100 * status_counts / len(clean)).round(1).to_dict()
    metrics["returned_share"] = round(100 * (clean["status"] == "Возвращена на доработку").mean(), 1)

    urgency_counts = clean["urgency"].value_counts()
    metrics["urgency_counts"] = urgency_counts.to_dict()
    metrics["urgency_share"] = (100 * urgency_counts / len(clean)).round(1).to_dict()

    dept_counts = clean["department"].value_counts()
    metrics["department_counts"] = dept_counts.to_dict()

    monthly = clean.groupby(clean["created_at"].dt.to_period("M")).size()
    metrics["monthly_counts"] = {str(k): int(v) for k, v in monthly.items()}
    metrics["monthly_mean"] = round(float(monthly.mean()), 1)
    metrics["monthly_min"] = int(monthly.min())
    metrics["monthly_max"] = int(monthly.max())

    amounts = clean["total_amount"]
    metrics["amount_total_mrub"] = round(float(amounts.sum() / 1e6), 1)
    metrics["amount_mean"] = round(float(amounts.mean()), 0)
    metrics["amount_median"] = round(float(amounts.median()), 0)
    metrics["amount_p90"] = round(float(amounts.quantile(0.90)), 0)
    metrics["amount_p95"] = round(float(amounts.quantile(0.95)), 0)
    metrics["amount_max"] = round(float(amounts.max()), 0)
    metrics["share_over_500k"] = round(100 * (amounts >= 500_000).mean(), 1)
    metrics["share_over_1m"] = round(100 * (amounts >= 1_000_000).mean(), 1)

    lead = clean["lead_time_days"]
    metrics["lead_time_mean"] = round(float(lead.mean()), 2)
    metrics["lead_time_median"] = round(float(lead.median()), 2)
    metrics["lead_time_p90"] = round(float(lead.quantile(0.90)), 2)
    metrics["lead_time_by_urgency"] = clean.groupby("urgency")["lead_time_days"].mean().round(2).to_dict()
    metrics["lead_time_by_status"] = clean.groupby("status")["lead_time_days"].mean().round(2).to_dict()

    metrics["completeness_mean"] = round(float(clean["completeness_score"].mean()), 3)
    metrics["completeness_low_share"] = round(100 * (clean["completeness_score"] < 0.7).mean(), 1)
    metrics["completeness_by_status"] = clean.groupby("status")["completeness_score"].mean().round(3).to_dict()
    metrics["spearman_completeness_lead"] = round(float(clean["completeness_score"].corr(lead, method="spearman")), 3)
    metrics["spearman_completeness_returned"] = round(float(
        clean["completeness_score"].corr((clean["status"] == "Возвращена на доработку").astype(int), method="spearman")
    ), 3)

    metrics["high_value_count"] = int((amounts >= 500_000).sum())
    metrics["urgent_count"] = int((clean["urgency"] == "высокая").sum())
    metrics["supplier_not_specified_clean"] = int((clean["supplier"] == "Не указан").sum())
    metrics["supplier_not_specified_share"] = round(100 * (clean["supplier"] == "Не указан").mean(), 1)
    metrics["currency_original_counts"] = clean["currency_original"].value_counts().to_dict()

    # --- График 1: динамика по месяцам -----------------------------------
    fig, ax = plt.subplots(figsize=(8.4, 3.4))
    x = np.arange(len(monthly))
    ax.bar(x, monthly.values, color=BLUE, width=0.68, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([p.strftime("%b") for p in monthly.index], fontsize=9)
    ax.set_ylabel("Заявок, шт.")
    ax.set_title("Динамика заявок по месяцам, 2025 год", loc="left", fontsize=13, fontweight="bold", pad=12)
    ax.set_ylim(0, monthly.max() * 1.18)
    for i, v in enumerate(monthly.values):
        ax.text(i, v + monthly.max() * 0.02, str(v), ha="center", va="bottom", fontsize=8, color="#6e6e73")
    style_axes(ax)
    save(fig, "fig_monthly.png")

    # --- График 2: категории ---------------------------------------------
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    cats = cat_counts.sort_values()
    ax.barh(cats.index, cats.values, color=BLUE, height=0.65, zorder=3)
    for i, v in enumerate(cats.values):
        ax.text(v + len(clean) * 0.004, i, f"{v}  ({100*v/len(clean):.1f}%)", va="center", fontsize=8, color="#6e6e73")
    ax.set_xlabel("Заявок, шт.")
    ax.set_title("Структура заявок по категориям", loc="left", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlim(0, cats.max() * 1.28)
    style_axes(ax, "x")
    save(fig, "fig_categories.png")

    # --- График 3: статусы ------------------------------------------------
    fig, ax = plt.subplots(figsize=(7.6, 3.1))
    order = ["Одобрена", "В работе", "Возвращена на доработку", "Отклонена", "Отменена"]
    vals = [status_counts.get(s, 0) for s in order]
    colors = [GREEN, BLUE, ORANGE, RED, GRAY]
    bars = ax.barh(order[::-1], vals[::-1], color=colors[::-1], height=0.6, zorder=3)
    for bar, v in zip(bars, vals[::-1]):
        ax.text(v + len(clean) * 0.004, bar.get_y() + bar.get_height() / 2, f"{v} ({100*v/len(clean):.1f}%)", va="center", fontsize=8.5, color="#6e6e73")
    ax.set_xlabel("Заявок, шт.")
    ax.set_title("Текущие статусы заявок", loc="left", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlim(0, max(vals) * 1.3)
    style_axes(ax, "x")
    save(fig, "fig_status.png")

    # --- График 4: пропуски до/после -------------------------------------
    fields = ["quantity", "unit_price", "budget_code", "urgency", "justification", "attachment"]
    labels = ["Количество", "Цена", "Бюджетный код", "Срочность", "Обоснование", "Вложение"]
    before = [100 * quality["missing_before"][f] / len(raw) for f in fields]
    after = [100 * quality["missing_after"][f] / len(clean) for f in fields]
    fig, ax = plt.subplots(figsize=(8.4, 3.6))
    y = np.arange(len(fields))
    h = 0.36
    ax.barh(y + h/2, before, height=h, color=ORANGE, label="До очистки", zorder=3)
    ax.barh(y - h/2, after, height=h, color=GREEN, label="После очистки", zorder=3)
    for i, (b, a) in enumerate(zip(before, after)):
        ax.text(b + 0.4, i + h/2, f"{b:.1f}%", va="center", fontsize=8, color="#6e6e73")
        ax.text(a + 0.4, i - h/2, f"{a:.1f}%", va="center", fontsize=8, color="#6e6e73")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Доля пропусков, %")
    ax.set_title("Пропуски в ключевых полях до и после очистки", loc="left", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlim(0, max(before) * 1.25)
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    style_axes(ax, "x")
    save(fig, "fig_missing.png")

    # --- График 5: распределение сумм ------------------------------------
    fig, ax = plt.subplots(figsize=(8.0, 3.5))
    log_amounts = np.log10(amounts.clip(lower=1))
    ax.hist(log_amounts, bins=45, color=BLUE, alpha=0.85, zorder=3)
    med = np.log10(amounts.median())
    ax.axvline(med, color=RED, linestyle="--", linewidth=1.4, zorder=4)
    ax.text(med + 0.05, ax.get_ylim()[1] * 0.9, f"медиана\n{amounts.median()/1000:.0f} тыс. ₽", color=RED, fontsize=8.5)
    ticks = [3, 4, 5, 6, 7]
    ax.set_xticks(ticks)
    ax.set_xticklabels(["1 тыс.", "10 тыс.", "100 тыс.", "1 млн", "10 млн"])
    ax.set_xlabel("Сумма заявки (логарифмическая шкала)")
    ax.set_ylabel("Заявок, шт.")
    ax.set_title("Распределение сумм заявок", loc="left", fontsize=13, fontweight="bold", pad=12)
    style_axes(ax)
    save(fig, "fig_amounts.png")

    # --- График 6: срок обработки по срочности ---------------------------
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    data = [clean.loc[clean["urgency"] == u, "lead_time_days"].values for u in ["низкая", "средняя", "высокая"]]
    bp = ax.boxplot(data, patch_artist=True, widths=0.45, medianprops=dict(color=TEXT, linewidth=1.6), flierprops=dict(marker="o", markersize=2.5, markerfacecolor=GRAY, markeredgecolor=GRAY, alpha=0.4))
    for patch, color in zip(bp["boxes"], [GRAY, BLUE, ORANGE]):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)
        patch.set_edgecolor(color)
    ax.set_xticklabels(["Низкая", "Средняя", "Высокая"])
    ax.set_ylabel("Срок обработки, дней")
    ax.set_title("Срок обработки по уровню срочности", loc="left", fontsize=13, fontweight="bold", pad=12)
    style_axes(ax)
    save(fig, "fig_lead_time.png")

    # --- График 7: полнота заявок ----------------------------------------
    fig, ax = plt.subplots(figsize=(7.6, 3.2))
    ax.hist(clean["completeness_score"], bins=np.linspace(0, 1, 11), color=GREEN, alpha=0.85, zorder=3, rwidth=0.9)
    ax.axvline(clean["completeness_score"].mean(), color=RED, linestyle="--", linewidth=1.3)
    ax.text(clean["completeness_score"].mean() - 0.02, ax.get_ylim()[1] * 0.9, f"среднее {clean['completeness_score'].mean():.2f}", ha="right", color=RED, fontsize=8.5)
    ax.set_xlabel("Индекс полноты заявки (0–1)")
    ax.set_ylabel("Заявок, шт.")
    ax.set_title("Распределение полноты заявок после очистки", loc="left", fontsize=13, fontweight="bold", pad=12)
    style_axes(ax)
    save(fig, "fig_completeness.png")

    # --- График 8: затраты по категориям ---------------------------------
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    spend = (clean.groupby("category")["total_amount"].sum() / 1e6).sort_values()
    ax.barh(spend.index, spend.values, color=BLUE, height=0.65, zorder=3)
    for i, v in enumerate(spend.values):
        ax.text(v + spend.max() * 0.015, i, f"{v:.1f} млн ₽", va="center", fontsize=8, color="#6e6e73")
    ax.set_xlabel("Сумма заявок, млн ₽")
    ax.set_title("Суммарный объём заявок по категориям", loc="left", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlim(0, spend.max() * 1.25)
    style_axes(ax, "x")
    save(fig, "fig_spend.png")

    METRICS.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Метрики: {METRICS}")
    print(f"Строк: {len(clean)}, объём: {metrics['amount_total_mrub']} млн ₽")


if __name__ == "__main__":
    main()
