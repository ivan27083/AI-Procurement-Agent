"""Классификатор категории закупки: TF-IDF + логистическая регрессия."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib

MODEL_PATH = Path(__file__).resolve().parent / "models" / "category_clf.joblib"

KEYWORDS: dict[str, tuple[str, ...]] = {
    "IT-оборудование": ("ноутбук", "монитор", "сервер", "мфу", "коммутатор", "ибп", "сканер", "гарнитура", "компьютер", "техника"),
    "ПО и лицензии": ("лицензи", "по ", "программ", "1с", "microsoft", "антивирус", "adobe", "bi-платформ", "подписк"),
    "Канцелярия и расходники": ("бумаг", "картридж", "тонер", "ручк", "папк", "блокнот", "канцеляр", "расходник"),
    "Услуги подрядчиков": ("клининг", "охрана", "грузчик", "переводчик", "аутсорсинг", "подрядчик", "услуг"),
    "Транспорт и логистика": ("топливо", "дизель", "аренда автомобил", "шины", "экспедирован", "перевозк", "рейс", "погрузчик"),
    "Мебель и обустройство": ("кресло", "стол", "шкаф", "стеллаж", "перегородк", "мебель"),
    "Маркетинг и реклама": ("сайт", "буклет", "реклам", "яндекс.директ", "ролик", "сувенир", "маркетинг"),
    "Обучение и развитие": ("курс", "тренинг", "обучени", "аттестаци", "повышения квалификации"),
    "Ремонт и обслуживание": ("ремонт", "обслуживан", "вентиляци", "кровл", "дизель-генератор", "то "),
    "Хозтовары": ("мыло", "мешк", "перчатк", "тряпк", "мытья полов", "хозтовар", "бытов"),
}


class CategoryClassifier:
    def __init__(self, model_path: Path | str = MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        self.model: Any | None = None
        self.mode = "keyword-fallback"
        if self.model_path.exists():
            try:
                self.model = joblib.load(self.model_path)
                self.mode = "tfidf-logreg"
            except Exception:
                self.model = None

    def predict(self, text: str) -> tuple[str, float]:
        keyword_label, keyword_conf = self._keyword_predict(text)
        if self.model is not None:
            try:
                proba = self.model.predict_proba([text])[0]
                idx = int(proba.argmax())
                label = str(self.model.classes_[idx])
                confidence = float(proba[idx])
                # Гибрид: сильный словарный сигнал страхует модель на коротких
                # и неоднозначных текстах, где TF-IDF ошибается уверенно.
                if confidence < 0.55 and keyword_label != "Не определено" and keyword_conf >= 0.5:
                    return keyword_label, max(confidence, min(0.65, keyword_conf))
                if confidence < 0.25 and keyword_label == "Не определено":
                    return "Не определено", confidence
                return label, confidence
            except Exception:
                pass
        return keyword_label, keyword_conf

    def _keyword_predict(self, text: str) -> tuple[str, float]:
        low = text.lower()
        scores: dict[str, int] = {}
        for category, words in KEYWORDS.items():
            score = sum(1 for word in words if word in low)
            if score:
                scores[category] = score
        if not scores:
            return "Не определено", 0.0
        best = max(scores, key=scores.get)
        total = sum(scores.values())
        return best, round(scores[best] / max(total, 1), 3)
