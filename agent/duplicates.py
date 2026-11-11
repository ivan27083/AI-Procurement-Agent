"""Поиск дубликатов заявок по тексту и сумме."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .schema import DuplicateMatch

HISTORY_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "procurement_requests_clean.csv"


class DuplicateIndex:
    def __init__(self, history_path: Path | str = HISTORY_PATH) -> None:
        self.history_path = Path(history_path)
        self.ready = False
        self.df = pd.DataFrame()
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
        )
        self.matrix = None

        if self.history_path.exists():
            self.df = pd.read_csv(self.history_path, encoding="utf-8-sig")
            self.df["request_text"] = self.df["request_text"].fillna("").astype(str)
            if len(self.df):
                self.matrix = self.vectorizer.fit_transform(self.df["request_text"])
                self.ready = True

    def find(self, text: str, amount: float | None = None, request_id: str = "") -> DuplicateMatch:
        if not self.ready or not text.strip():
            return DuplicateMatch(is_duplicate=False, is_possible=False, reason="История недоступна")
        # Короткие общие формулировки («нужна закупка, детали позже») не
        # считаем дубликатами: сходства текста недостаточно для такого вывода.
        if len(text.split()) < 8 or len(text) < 45:
            return DuplicateMatch(is_duplicate=False, is_possible=False, reason="Текст слишком короткий для проверки дубликатов")

        query = self.vectorizer.transform([text])
        scores = cosine_similarity(query, self.matrix).ravel()
        order = np.argsort(scores)[::-1][:8]

        best: DuplicateMatch | None = None
        for idx in order:
            row = self.df.iloc[int(idx)]
            if request_id and str(row["request_id"]) == request_id:
                continue
            similarity = float(scores[int(idx)])
            candidate_amount = float(row["total_amount"]) if pd.notna(row["total_amount"]) else None
            amount_ratio = None
            if amount and candidate_amount and amount > 0 and candidate_amount > 0:
                amount_ratio = abs(amount - candidate_amount) / max(amount, candidate_amount)

            is_duplicate = (
                similarity >= 0.86
                and (amount_ratio is None or amount_ratio <= 0.20)
            )
            is_possible = (
                similarity >= 0.72
                or (similarity >= 0.62 and amount_ratio is not None and amount_ratio <= 0.10)
            )
            reason = ""
            if is_duplicate:
                reason = "Текст и сумма совпадают с исторической заявкой"
            elif is_possible:
                reason = "Похожий текст; требуется ручная проверка"

            candidate = DuplicateMatch(
                is_duplicate=is_duplicate,
                is_possible=is_possible or is_duplicate,
                request_id=str(row["request_id"]),
                similarity=similarity,
                amount=candidate_amount,
                created_at=str(row.get("created_at", "")),
                reason=reason,
            )
            if is_duplicate:
                return candidate
            if best is None or candidate.similarity > best.similarity:
                best = candidate

        return best or DuplicateMatch(is_duplicate=False, is_possible=False, reason="Совпадений не найдено")
