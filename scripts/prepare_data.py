#!/usr/bin/env python3
"""Очистка и подготовка синтетического набора заявок на закупку.

Запуск:
    python scripts/prepare_data.py

Результаты:
    data/processed/procurement_requests_clean.csv
    data/processed/quality_comparison.csv
    data/processed/data_quality_report.json
"""

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "procurement_requests_raw.csv"
CLEAN = ROOT / "data" / "processed" / "procurement_requests_clean.csv"
REPORT = ROOT / "data" / "processed" / "data_quality_report.json"
COMPARISON = ROOT / "data" / "processed" / "quality_comparison.csv"

RATES = {"RUB": 1.0, "USD": 92.5, "EUR": 100.5}

CATEGORY_CANON = [
    "IT-оборудование",
    "ПО и лицензии",
    "Канцелярия и расходники",
    "Услуги подрядчиков",
    "Транспорт и логистика",
    "Мебель и обустройство",
    "Маркетинг и реклама",
    "Обучение и развитие",
    "Ремонт и обслуживание",
    "Хозтовары",
]

CATEGORY_MAP = {
    "it": "IT-оборудование",
    "ит-оборудование": "IT-оборудование",
    "it оборудование": "IT-оборудование",
    "оборудование it": "IT-оборудование",
    "ит оборудование": "IT-оборудование",
    "по": "ПО и лицензии",
    "лицензии": "ПО и лицензии",
    "программное обеспечение": "ПО и лицензии",
    "канцелярия": "Канцелярия и расходники",
    "канцелярские товары": "Канцелярия и расходники",
    "расходники": "Канцелярия и расходники",
    "услуги": "Услуги подрядчиков",
    "подрядчики": "Услуги подрядчиков",
    "аутсорсинг": "Услуги подрядчиков",
    "транспорт": "Транспорт и логистика",
    "логистика": "Транспорт и логистика",
    "перевозки": "Транспорт и логистика",
    "мебель": "Мебель и обустройство",
    "обустройство": "Мебель и обустройство",
    "офисная мебель": "Мебель и обустройство",
    "маркетинг": "Маркетинг и реклама",
    "реклама": "Маркетинг и реклама",
    "pr": "Маркетинг и реклама",
    "обучение": "Обучение и развитие",
    "развитие": "Обучение и развитие",
    "курсы": "Обучение и развитие",
    "ремонт": "Ремонт и обслуживание",
    "обслуживание": "Ремонт и обслуживание",
    "то": "Ремонт и обслуживание",
    "хозтовары": "Хозтовары",
    "хозяйственные товары": "Хозтовары",
    "бытовая химия": "Хозтовары",
}

DEPT_MAP = {
    "ит-отдел": "ИТ-отдел",
    "it-отдел": "ИТ-отдел",
    "ит отдел": "ИТ-отдел",
    "отдел ит": "ИТ-отдел",
    "отдел продаж": "Отдел продаж",
    "продажи": "Отдел продаж",
    "отдел логистики": "Отдел логистики",
    "логистика": "Отдел логистики",
    "склад": "Складской комплекс",
    "складской комплекс": "Складской комплекс",
    "финансовый отдел": "Финансовый отдел",
    "фин. отдел": "Финансовый отдел",
    "финансы": "Финансовый отдел",
    "отдел кадров": "Отдел кадров",
    "hr": "Отдел кадров",
    "кадры": "Отдел кадров",
    "юридический отдел": "Юридический отдел",
    "юр. отдел": "Юридический отдел",
    "юристы": "Юридический отдел",
    "отдел маркетинга": "Отдел маркетинга",
    "маркетинг": "Отдел маркетинга",
    "административный отдел": "Административный отдел",
    "ахо": "Административный отдел",
    "админ. отдел": "Административный отдел",
    "отдел закупок": "Отдел закупок",
    "закупки": "Отдел закупок",
    "снабжение": "Отдел закупок",
    "служба безопасности": "Служба безопасности",
    "сб": "Служба безопасности",
    "транспортный отдел": "Транспортный отдел",
    "транспорт": "Транспортный отдел",
    "автопарк": "Транспортный отдел",
    "отдел обслуживания клиентов": "Отдел обслуживания клиентов",
    "поддержка клиентов": "Отдел обслуживания клиентов",
    "отдел обслуживания": "Отдел обслуживания клиентов",
    "клиентский сервис": "Отдел обслуживания клиентов",
    "руководство": "Руководство",
    "дирекция": "Руководство",
    "правление": "Руководство",
}

URGENCY_MAP = {
    "низкая": "низкая",
    "не срочно": "низкая",
    "плановая": "низкая",
    "средняя": "средняя",
    "обычная": "средняя",
    "стандартная": "средняя",
    "высокая": "высокая",
    "срочно": "высокая",
    "срочно!": "высокая",
    "asap": "высокая",
    "критично": "высокая",
}

UNIT_MAP = {
    "шт": "шт.",
    "шт.": "шт.",
    "ед.": "шт.",
    "уп": "уп.",
    "уп.": "уп.",
    "лиц": "лиц.",
    "лиц.": "лиц.",
    "мес": "мес.",
    "мес.": "мес.",
    "чел": "чел.",
    "чел.": "чел.",
}


def norm(value: str) -> str:
    value = (value or "").replace("\xa0", " ").replace("\u202f", " ")
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value


def parse_money(value: str) -> float:
    if value is None:
        return math.nan
    s = str(value).strip()
    if not s:
        return math.nan
    s = s.replace("\xa0", " ").replace("\u202f", " ")
    # Убираем обозначение валюты вместе с точкой/пробелами, иначе после
    # «220 337,33 руб.» остаётся лишняя точка и сумма вырастает в 100 раз.
    s = re.sub(r"(?i)(руб\.?|rub|₽)", "", s)
    s = s.replace(" ", "")
    s = re.sub(r"[^0-9,.\-]", "", s)
    s = s.replace(",", ".")
    if s.count(".") > 1:
        parts = s.split(".")
        if len(parts[-1]) <= 2:
            s = "".join(parts[:-1]) + "." + parts[-1]
        else:
            s = "".join(parts)
    try:
        return float(s)
    except ValueError:
        return math.nan


def parse_date(value: str) -> date | None:
    s = (value or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    try:
        serial = float(s)
        if 20000 < serial < 60000:
            return date.fromordinal(date(1899, 12, 30).toordinal() + int(serial))
    except ValueError:
        pass
    return None


def parse_attachment(value: str) -> str:
    v = norm(value)
    if v in {"да", "есть", "yes", "y", "1"}:
        return "да"
    return "нет"


def normalize_text(value: str) -> str:
    s = norm(value)
    s = re.sub(r"[^a-zа-яё0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def completeness(row: pd.Series) -> float:
    checks = [
        bool(row["quantity"] > 0),
        bool(row["unit_price"] > 0),
        row["budget_code"] != "НЕ УКАЗАН",
        len(str(row["justification"])) >= 30,
        row["supplier"] != "Не указан",
        bool(row["urgency"]),
        bool(row["attachment"]),
        bool(row["lead_time_days"] > 0),
    ]
    return sum(checks) / len(checks)


def main() -> None:
    raw = pd.read_csv(RAW, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    raw_rows = len(raw)
    df = raw.copy()

    report: dict[str, object] = {"source": str(RAW), "raw_rows": raw_rows}
    report["raw_columns"] = list(df.columns)

    # --- 1. Типы и форматы -------------------------------------------------
    bad_dates = 0
    parsed_dates = []
    for value in df["created_at"]:
        d = parse_date(value)
        if d is None:
            bad_dates += 1
            parsed_dates.append(pd.NaT)
        else:
            parsed_dates.append(pd.Timestamp(d))
    df["created_at"] = parsed_dates
    report["bad_dates"] = bad_dates

    for col in ["quantity", "unit_price", "total_amount", "lead_time_days"]:
        df[col] = df[col].map(parse_money)

    neg_qty = int((df["quantity"] <= 0).sum())
    neg_price = int((df["unit_price"] <= 0).sum())
    report["nonpositive_quantity"] = neg_qty
    report["nonpositive_price"] = neg_price

    df["currency"] = df["currency"].map(lambda x: norm(x).upper() or "RUB")
    report["currency_counts_raw"] = df["currency"].value_counts().to_dict()

    # --- 2. Справочники ---------------------------------------------------
    category_before = df["category"].map(norm)
    df["category_raw"] = df["category"]
    df["category"] = category_before.map(lambda x: CATEGORY_MAP.get(x, None))
    needs_fallback = int(df["category"].isna().sum())
    df.loc[df["category"].isna(), "category"] = df.loc[df["category"].isna(), "category_raw"].map(
        lambda x: next((c for c in CATEGORY_CANON if norm(c) == norm(x)), "Прочее")
    )
    report["category_variants_normalized"] = int((category_before != df["category"].map(norm)).sum())
    report["category_fallback_resolved"] = needs_fallback
    report["unknown_categories"] = int((df["category"] == "Прочее").sum())
    report["category_counts_before"] = category_before.value_counts().head(25).to_dict()
    report["category_counts_after"] = df["category"].value_counts().to_dict()

    dept_before = df["department"].map(norm)
    df["department_raw"] = df["department"]
    df["department"] = dept_before.map(lambda x: DEPT_MAP.get(x, None))
    unknown_depts = int(df["department"].isna().sum())
    df.loc[df["department"].isna(), "department"] = df.loc[df["department"].isna(), "department_raw"].str.strip()
    report["department_variants_normalized"] = int((dept_before != df["department"].map(norm)).sum())
    report["unknown_departments"] = unknown_depts

    urgency_before = df["urgency"].map(norm)
    df["urgency"] = urgency_before.map(lambda x: URGENCY_MAP.get(x, None))
    df["urgency_missing"] = df["urgency"].isna()
    missing_urgency = int(df["urgency"].isna().sum())
    report["missing_urgency"] = missing_urgency
    df["urgency"] = df["urgency"].fillna("средняя")

    df["unit"] = df["unit"].map(lambda x: UNIT_MAP.get(norm(x), norm(x) or "шт."))
    df["supplier"] = df["supplier"].map(lambda x: x.strip() if x.strip() else "Не указан")
    df["budget_code"] = df["budget_code"].map(lambda x: x.strip() if x.strip() else "НЕ УКАЗАН")
    df["justification"] = df["justification"].map(lambda x: re.sub(r"\s+", " ", x).strip())
    df["attachment"] = df["attachment"].map(parse_attachment)
    df["status"] = df["status"].map(lambda x: x.strip())

    # --- 3. Дубликаты -----------------------------------------------------
    # 3.1 Точные дубликаты по всем полям, кроме идентификатора.
    exact_cols = [c for c in df.columns if c != "request_id"]
    before_exact = len(df)
    df = df.drop_duplicates(subset=exact_cols, keep="first").copy()
    exact_removed = before_exact - len(df)

    # 3.2 Почти дубликаты: тот же отдел и категория, близкая сумма,
    #     близкий текст и дата в пределах 10 дней.
    df["_norm_text"] = df["request_text"].map(normalize_text)
    df = df.sort_values("created_at").reset_index(drop=True)
    drop_idx: set[int] = set()
    by_group = df.groupby(["department", "category"], dropna=False)
    for _, group in by_group:
        if len(group) < 2:
            continue
        idxs = list(group.index)
        for i in range(len(idxs)):
            a = idxs[i]
            if a in drop_idx:
                continue
            for j in range(i + 1, len(idxs)):
                b = idxs[j]
                if b in drop_idx:
                    continue
                ra, rb = df.loc[a], df.loc[b]
                if abs((ra["created_at"] - rb["created_at"]).days) > 10:
                    continue
                amount_a, amount_b = ra["total_amount"], rb["total_amount"]
                if not (np.isfinite(amount_a) and np.isfinite(amount_b)) or amount_a <= 0 or amount_b <= 0:
                    continue
                if abs(amount_a - amount_b) / max(amount_a, amount_b) > 0.05:
                    continue
                ta, tb = ra["_norm_text"], rb["_norm_text"]
                if not ta or not tb:
                    continue
                ratio = SequenceMatcher(None, ta, tb).ratio()
                if ratio >= 0.88:
                    drop_idx.add(b)
    near_removed = len(drop_idx)
    df = df.drop(index=list(drop_idx)).drop(columns=["_norm_text"]).reset_index(drop=True)
    report["exact_duplicates_removed"] = exact_removed
    report["near_duplicates_removed"] = near_removed
    report["duplicates_removed_total"] = exact_removed + near_removed
    report["rows_after_dedup"] = len(df)

    # 3.3 Остаточные близкие пары не удаляем автоматически: ложное удаление
    #     реальной заявки дороже, чем ручная проверка. Помечаем для человека.
    df["_norm_text"] = df["request_text"].map(normalize_text)
    possible: dict[int, str] = {}
    for _, group in df.groupby("category", dropna=False):
        idxs = list(group.index)
        for i in range(len(idxs)):
            a = idxs[i]
            for j in range(i + 1, len(idxs)):
                b = idxs[j]
                ra, rb = df.loc[a], df.loc[b]
                if abs((ra["created_at"] - rb["created_at"]).days) > 15:
                    continue
                amount_a, amount_b = ra["total_amount"], rb["total_amount"]
                if not (np.isfinite(amount_a) and np.isfinite(amount_b)) or amount_a <= 0 or amount_b <= 0:
                    continue
                if abs(amount_a - amount_b) / max(amount_a, amount_b) > 0.15:
                    continue
                ratio = SequenceMatcher(None, ra["_norm_text"], rb["_norm_text"]).ratio()
                if ratio >= 0.85:
                    possible[b] = ra["request_id"]
    df["possible_duplicate"] = df.index.isin(possible.keys())
    df["duplicate_of"] = df.index.map(lambda i: possible.get(i, ""))
    df = df.drop(columns=["_norm_text"])
    report["possible_duplicates_flagged"] = int(df["possible_duplicate"].sum())

    # Полнота на входе: считаем до импутации, иначе все заявки выглядят полными.
    def intake_completeness(row: pd.Series) -> float:
        checks = [
            pd.notna(row["quantity"]) and row["quantity"] > 0,
            pd.notna(row["unit_price"]) and row["unit_price"] > 0,
            str(row["budget_code"]).strip() not in {"", "НЕ УКАЗАН", "б/н", "нет", "TBD", "БЮДЖЕТ-1"},
            len(str(row["justification"]).strip()) >= 30,
            not bool(row["urgency_missing"]),
        ]
        return sum(checks) / len(checks)

    df["completeness_score"] = df.apply(intake_completeness, axis=1)

    # --- 4. Пропуски и некорректные значения ------------------------------
    missing_before = {
        col: int((raw[col].astype(str).str.strip() == "").sum())
        for col in ["quantity", "unit_price", "budget_code", "urgency", "supplier", "justification", "attachment", "lead_time_days"]
    }

    df["qty_imputed"] = df["quantity"].isna() | (df["quantity"] <= 0)
    df.loc[df["qty_imputed"], "quantity"] = np.nan
    qty_median = df.groupby("category")["quantity"].median()
    df["quantity"] = df.apply(
        lambda r: qty_median.get(r["category"], 1) if pd.isna(r["quantity"]) else r["quantity"], axis=1
    )
    df["quantity"] = df["quantity"].round().clip(lower=1).astype(int)

    # Валюта: приводим к рублям по фиксированным допущениям до импутации,
    # иначе медианная цена в рублях умножалась бы на курс ещё раз.
    df["currency"] = df["currency"].where(df["currency"].isin(RATES), "RUB")
    df["fx_rate"] = df["currency"].map(RATES)
    df["unit_price"] = df["unit_price"] * df["fx_rate"]
    df["total_amount"] = df["total_amount"] * df["fx_rate"]
    df["currency_original"] = raw["currency"].map(lambda x: norm(x).upper() or "RUB")
    df["currency"] = "RUB"

    df["price_imputed"] = df["unit_price"].isna() | (df["unit_price"] <= 0)
    df.loc[df["price_imputed"], "unit_price"] = np.nan
    price_median = df.groupby(["category", "unit"])["unit_price"].median()
    price_fallback = df.groupby("category")["unit_price"].median()
    df["unit_price"] = df.apply(
        lambda r: price_median.get((r["category"], r["unit"]),
                                   price_fallback.get(r["category"], 1.0))
        if pd.isna(r["unit_price"]) else r["unit_price"], axis=1
    )

    # Сумма: пересчитываем и фиксируем расхождения.
    df["total_calculated"] = (df["quantity"] * df["unit_price"]).round(2)
    mismatch = (
        df["total_amount"].isna()
        | (df["total_amount"] <= 0)
        | ((df["total_amount"] - df["total_calculated"]).abs() / df["total_calculated"].clip(lower=1) > 0.02)
    )
    df["total_recalculated"] = mismatch
    df["total_amount"] = df["total_calculated"]

    # Выбросы: флаги + винзоризованные версии для описательной статистики.
    df["price_outlier"] = False
    for _, idx in df.groupby("category").groups.items():
        s = df.loc[idx, "unit_price"]
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        df.loc[idx, "price_outlier"] = (s < lo) | (s > hi)
    df["unit_price_winsorized"] = df.groupby("category")["unit_price"].transform(
        lambda s: s.clip(s.quantile(0.01), s.quantile(0.99))
    )
    df["amount_winsorized"] = df["quantity"] * df["unit_price_winsorized"]

    df["justification"] = df["justification"].fillna("")
    df["justification_short"] = df["justification"].str.len() < 30
    df["lead_time_imputed"] = df["lead_time_days"].isna() | (df["lead_time_days"] <= 0)
    lead_median = df.groupby("category")["lead_time_days"].median()
    df["lead_time_days"] = df.apply(
        lambda r: lead_median.get(r["category"], 4.0) if pd.isna(r["lead_time_days"]) else r["lead_time_days"], axis=1
    )
    df["attachment"] = df["attachment"].fillna("нет")

    # --- 5. Производные признаки ------------------------------------------
    df["month"] = df["created_at"].dt.month
    df["quarter"] = df["created_at"].dt.quarter
    df["weekday"] = df["created_at"].dt.weekday
    df["text_len"] = df["request_text"].str.len()
    df["justification_len"] = df["justification"].str.len()
    df["amount_log"] = np.log1p(df["total_amount"])
    df["price_per_unit"] = df["total_amount"] / df["quantity"].clip(lower=1)
    df["is_high_value"] = df["total_amount"] >= 500_000
    df["is_urgent"] = df["urgency"] == "высокая"
    df["lead_time_bucket"] = pd.cut(
        df["lead_time_days"], bins=[0, 3, 5, 8, 100], labels=["до 3 дней", "3–5 дней", "5–8 дней", "более 8 дней"]
    ).astype(str)

    # --- 6. Сравнение до/после --------------------------------------------
    missing_after = {
        col: int((df[col].astype(str).str.strip() == "").sum())
        for col in ["quantity", "unit_price", "budget_code", "urgency", "supplier", "justification", "attachment", "lead_time_days"]
    }
    report["missing_before"] = missing_before
    report["missing_after"] = missing_after
    report["supplier_not_specified_before"] = int(
        raw["supplier"].map(lambda x: norm(x) in {"", "не указан"}).sum()
    )
    report["justification_short_before"] = int(
        raw["justification"].map(lambda x: len(str(x).strip()) < 30).sum()
    )
    report["rows_clean"] = len(df)
    report["columns_clean"] = len(df.columns)
    report["price_outliers_flagged"] = int(df["price_outlier"].sum())
    report["total_recalculated"] = int(df["total_recalculated"].sum())
    report["qty_imputed"] = int(df["qty_imputed"].sum())
    report["price_imputed"] = int(df["price_imputed"].sum())
    report["lead_time_imputed"] = int(df["lead_time_imputed"].sum())
    report["justification_short"] = int(df["justification_short"].sum())
    report["completeness_mean"] = float(df["completeness_score"].mean())
    report["amount_mean"] = float(df["total_amount"].mean())
    report["amount_median"] = float(df["total_amount"].median())
    report["amount_total"] = float(df["total_amount"].sum())
    report["lead_time_mean"] = float(df["lead_time_days"].mean())
    report["status_counts"] = df["status"].value_counts().to_dict()
    report["urgency_counts"] = df["urgency"].value_counts().to_dict()
    report["department_counts"] = df["department"].value_counts().to_dict()
    report["currency_original_counts"] = df["currency_original"].value_counts().to_dict()

    comparison_rows = []
    for col in missing_before:
        comparison_rows.append({
            "Признак": col,
            "Пропуски до, %": round(100 * missing_before[col] / raw_rows, 1),
            "Пропуски после, %": round(100 * missing_after[col] / len(df), 1),
        })
    pd.DataFrame(comparison_rows).to_csv(COMPARISON, index=False, encoding="utf-8-sig")

    # --- 7. Сохранение ----------------------------------------------------
    CLEAN.parent.mkdir(parents=True, exist_ok=True)
    out_cols = [
        "request_id", "created_at", "department", "department_raw", "requester",
        "request_text", "category", "category_raw", "quantity", "unit",
        "unit_price", "total_amount", "currency", "currency_original",
        "budget_code", "urgency", "supplier", "status", "lead_time_days",
        "attachment", "cost_center", "justification", "channel",
        "urgency_missing", "completeness_score",
        "qty_imputed", "price_imputed", "total_recalculated", "price_outlier",
        "unit_price_winsorized", "amount_winsorized", "justification_short",
        "lead_time_imputed", "possible_duplicate", "duplicate_of",
        "month", "quarter", "weekday", "text_len",
        "justification_len", "amount_log", "price_per_unit", "is_high_value",
        "is_urgent", "lead_time_bucket", "completeness_score",
    ]
    df[out_cols].to_csv(CLEAN, index=False, encoding="utf-8-sig")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Исходных строк: {raw_rows}")
    print(f"Удалено дубликатов: {exact_removed} точных + {near_removed} почти = {exact_removed + near_removed}")
    print(f"Очищенных строк: {len(df)}")
    print(f"Пропуски до: {missing_before}")
    print(f"Пропуски после: {missing_after}")
    print(f"Сохранено: {CLEAN}")
    print(f"Отчёт: {REPORT}")


if __name__ == "__main__":
    main()
