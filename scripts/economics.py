#!/usr/bin/env python3
"""Экономическая модель: стоимость вызова, затраты, окупаемость, чувствительность."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "economics.json"
CSV = ROOT / "reports" / "economics_table.csv"
FIG = ROOT / "reports" / "figures" / "fig_payback.png"

BLUE = "#0071e3"
GREEN = "#34c759"
RED = "#ff3b30"
GRAY = "#8e8e93"
TEXT = "#1d1d1f"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "text.color": TEXT})

A = {
    # Объём и труд
    "volume_per_year": 2247,
    "baseline_minutes": 35,
    "after_minutes": 12,
    "loaded_rate_rub_h": 1200,
    "returned_share_before": 0.147,
    "returned_share_after": 0.08,
    "rework_minutes": 20,
    "duplicate_share": 0.02,
    "duplicate_minutes": 30,
    # Модель
    "input_tokens": 1900,
    "output_tokens": 500,
    "input_price_rub_per_1m": 45,
    "output_price_rub_per_1m": 180,
    "calls_per_request": 1.7,
    "embedding_tokens": 600,
    "embedding_price_rub_per_1m": 8,
    # Затраты
    "dev_costs": {
        "AI-инженер, 200 ч × 2 500 ₽": 500_000,
        "Аналитик данных, 50 ч × 1 800 ₽": 90_000,
        "Эксперт по закупкам, 40 ч × 1 500 ₽": 60_000,
        "Проектный менеджер, 30 ч × 2 200 ₽": 66_000,
        "QA и пилот, 30 ч × 1 200 ₽": 36_000,
        "Обучение и управление изменениями, 20 ч × 1 400 ₽": 28_000,
    },
    "implementation_costs": {
        "Интеграция с 1С/ERP": 120_000,
        "ИБ и оценка воздействия на данные": 60_000,
        "Документация процессов": 40_000,
        "Резерв на непредвиденные работы": 100_000,
    },
    "annual_fixed_costs": {
        "Хостинг и вычислительные ресурсы": 36_000,
        "Мониторинг и observability": 24_000,
        "Поддержка и инциденты": 60_000,
        "Лицензии и инструменты": 60_000,
        "Сопровождение ИБ": 60_000,
    },
    "discount_rate": 0.20,
}


def calc(volume: float | None = None, saved_minutes: float | None = None) -> dict[str, float | int | None]:
    volume = A["volume_per_year"] if volume is None else volume
    saved_minutes = (A["baseline_minutes"] - A["after_minutes"]) if saved_minutes is None else saved_minutes

    cost_per_call = (
        A["input_tokens"] * A["input_price_rub_per_1m"]
        + A["output_tokens"] * A["output_price_rub_per_1m"]
    ) / 1_000_000
    cost_per_request = cost_per_call * A["calls_per_request"] + (
        A["embedding_tokens"] * A["embedding_price_rub_per_1m"] / 1_000_000
    )
    annual_api = cost_per_request * volume

    saving_time = volume * (saved_minutes / 60) * A["loaded_rate_rub_h"]
    reworks_before = volume * A["returned_share_before"]
    reworks_after = volume * A["returned_share_after"]
    saving_rework = (reworks_before - reworks_after) * (A["rework_minutes"] / 60) * A["loaded_rate_rub_h"]
    saving_duplicates = volume * A["duplicate_share"] * (A["duplicate_minutes"] / 60) * A["loaded_rate_rub_h"]
    annual_benefit = saving_time + saving_rework + saving_duplicates

    one_time = sum(A["dev_costs"].values()) + sum(A["implementation_costs"].values())
    annual_fixed = sum(A["annual_fixed_costs"].values()) + annual_api
    annual_net = annual_benefit - annual_fixed

    payback_months = (one_time / annual_net * 12) if annual_net > 0 else None
    contribution_per_request = annual_benefit / volume
    breakeven_requests = (one_time + annual_fixed) / contribution_per_request if contribution_per_request > 0 else None

    cashflows = [-one_time] + [annual_net / 12] * 36
    cumulative = np.cumsum(cashflows)
    monthly_rate = (1 + A["discount_rate"]) ** (1 / 12) - 1
    npv = sum(cf / ((1 + monthly_rate) ** t) for t, cf in enumerate(cashflows[:37]))
    roi_3y = (sum(cashflows[1:37]) - one_time) / one_time

    return {
        "volume": volume,
        "saved_minutes": saved_minutes,
        "cost_per_call": cost_per_call,
        "cost_per_request": cost_per_request,
        "annual_api": annual_api,
        "saving_time": saving_time,
        "saving_rework": saving_rework,
        "saving_duplicates": saving_duplicates,
        "annual_benefit": annual_benefit,
        "one_time": one_time,
        "annual_fixed": annual_fixed,
        "annual_net": annual_net,
        "payback_months": payback_months,
        "breakeven_requests": breakeven_requests,
        "roi_3y": roi_3y,
        "npv_3y": npv,
        "contribution_per_request": contribution_per_request,
        "cumulative_36m": cumulative.tolist(),
    }


def main() -> None:
    base = calc()
    sensitivity = []
    for volume in [1500, 2000, 2247, 3000, 4000]:
        for minutes in [15, 23, 30]:
            r = calc(volume=volume, saved_minutes=minutes)
            sensitivity.append({
                "volume": volume,
                "saved_minutes": minutes,
                "annual_net": round(r["annual_net"], 0),
                "payback_months": None if r["payback_months"] is None else round(r["payback_months"], 1),
            })

    result = {
        "assumptions": A,
        "base": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in base.items() if k != "cumulative_36m"},
        "dev_total": sum(A["dev_costs"].values()),
        "implementation_total": sum(A["implementation_costs"].values()),
        "annual_fixed_total": sum(A["annual_fixed_costs"].values()),
        "sensitivity": sensitivity,
        "payback_month": next(
            (i for i, v in enumerate(base["cumulative_36m"]) if v >= 0),
            None,
        ),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # CSV с ключевыми строками
    rows = [
        ("Стоимость одного вызова модели, ₽", round(base["cost_per_call"], 4)),
        ("Стоимость обработки заявки, ₽", round(base["cost_per_request"], 4)),
        ("Годовой объём заявок, шт.", A["volume_per_year"]),
        ("Экономия времени, ₽/год", round(base["saving_time"], 0)),
        ("Экономия на доработках, ₽/год", round(base["saving_rework"], 0)),
        ("Экономия на дубликатах, ₽/год", round(base["saving_duplicates"], 0)),
        ("Совокупный эффект, ₽/год", round(base["annual_benefit"], 0)),
        ("Разовые затраты, ₽", round(base["one_time"], 0)),
        ("Постоянные затраты, ₽/год", round(base["annual_fixed"], 0)),
        ("Чистый эффект, ₽/год", round(base["annual_net"], 0)),
        ("Окупаемость, мес.", round(base["payback_months"], 1) if base["payback_months"] else ""),
        ("Точка безубыточности, заявок", round(base["breakeven_requests"], 0)),
        ("ROI за 3 года, %", round(100 * base["roi_3y"], 1)),
        ("NPV за 3 года при 20%, ₽", round(base["npv_3y"], 0)),
    ]
    CSV.write_text("\n".join(f"{name};{value}" for name, value in rows), encoding="utf-8-sig")

    # График накопленного денежного потока
    months = np.arange(0, 37)
    cumulative = np.array(base["cumulative_36m"])
    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    ax.plot(months, cumulative / 1000, color=BLUE, linewidth=2.2, zorder=3)
    ax.axhline(0, color=GRAY, linewidth=1, linestyle="--", zorder=2)
    if result["payback_month"] is not None:
        m = result["payback_month"]
        ax.scatter([m], [cumulative[m] / 1000], color=GREEN, s=55, zorder=4)
        ax.annotate(
            f"окупаемость\n≈ {base['payback_months']:.1f} мес.",
            xy=(m, cumulative[m] / 1000),
            xytext=(m + 2, cumulative[m] / 1000 - 380),
            fontsize=9,
            color=GREEN,
            arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.2),
        )
    ax.fill_between(months, cumulative / 1000, 0, where=cumulative < 0, color=RED, alpha=0.08)
    ax.fill_between(months, cumulative / 1000, 0, where=cumulative >= 0, color=GREEN, alpha=0.10)
    ax.set_xlabel("Месяц")
    ax.set_ylabel("Накопленный поток, тыс. ₽")
    ax.set_title("Накопленный денежный поток и точка окупаемости", loc="left", fontsize=12, fontweight="bold", pad=12)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.grid(axis="y", color="#f2f2f7")
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(FIG, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"Стоимость вызова: {base['cost_per_call']:.4f} ₽")
    print(f"Стоимость заявки: {base['cost_per_request']:.4f} ₽")
    print(f"Эффект: {base['annual_benefit']:,.0f} ₽/год")
    print(f"Разовые: {base['one_time']:,.0f} ₽, постоянные: {base['annual_fixed']:,.0f} ₽/год")
    print(f"Чистый эффект: {base['annual_net']:,.0f} ₽/год")
    print(f"Окупаемость: {base['payback_months']:.1f} мес.")
    print(f"Точка безубыточности: {base['breakeven_requests']:,.0f} заявок")
    print(f"Сохранено: {OUT}")
    print(f"Сохранено: {FIG}")


if __name__ == "__main__":
    main()
