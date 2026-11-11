"""Правила закупочного контроля, оценка риска и маршрутизация."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from .schema import DuplicateMatch, PolicyCheck

QUOTE_THRESHOLD = 100_000
TENDER_THRESHOLD = 500_000
COMMITTEE_THRESHOLD = 1_000_000

CATEGORY_REQUIREMENTS = {
    "IT-оборудование": "Согласование ИБ для сетевого оборудования и проверка совместимости.",
    "ПО и лицензии": "Проверка лицензионной чистоты и способа поставки.",
    "Услуги подрядчиков": "Юридическая проверка договора при сумме от 300 000 ₽.",
    "Ремонт и обслуживание": "Техническая экспертиза при сумме от 300 000 ₽.",
    "Транспорт и логистика": "Проверка тарифов и наличия топливных карт.",
}


class PolicyEngine:
    def __init__(self, history_path: Path | str | None = None) -> None:
        self.price_medians: dict[str, float] = {}
        if history_path:
            path = Path(history_path)
            if path.exists():
                df = pd.read_csv(path, encoding="utf-8-sig")
                self.price_medians = (
                    df.groupby("category")["unit_price_winsorized"].median().to_dict()
                )

    def evaluate(
        self,
        extracted: dict[str, object],
        category: str,
        confidence: float,
        amount: float | None,
        duplicate: DuplicateMatch,
        today: date | None = None,
    ) -> list[PolicyCheck]:
        today = today or date.today()
        checks: list[PolicyCheck] = []

        # 1. Полнота
        missing = extracted.get("_missing_fields", [])
        if missing:
            checks.append(PolicyCheck(
                "REQ-01", "fail", "Полнота заявки",
                "Не заполнены: " + ", ".join(missing) + ".",
                "Запросить у заявителя",
            ))
        else:
            checks.append(PolicyCheck("REQ-01", "pass", "Полнота заявки", "Все обязательные поля заполнены."))

        # 2. Бюджетный код
        budget = str(extracted.get("budget_code") or "")
        if re.fullmatch(r"[A-ZА-Я]{2,4}-\d{4}-\d{2}", budget):
            checks.append(PolicyCheck("BUD-01", "pass", "Бюджетный код", f"Код {budget} корректен."))
        elif budget:
            checks.append(PolicyCheck("BUD-01", "fail", "Бюджетный код", f"Код «{budget}» не соответствует формату."))
        else:
            checks.append(PolicyCheck("BUD-01", "fail", "Бюджетный код", "Бюджетный код не указан."))

        # 3. Обоснование
        justification = str(extracted.get("justification") or "")
        if len(justification) >= 30:
            checks.append(PolicyCheck("JUS-01", "pass", "Обоснование", "Обоснование содержательное."))
        else:
            checks.append(PolicyCheck(
                "JUS-01", "warn", "Обоснование",
                "Обоснование короче 30 символов или отсутствует.",
                "Уточнить цель и последствия отсутствия закупки",
            ))

        # 4. Порог суммы
        if amount is None:
            checks.append(PolicyCheck("AMT-01", "fail", "Сумма закупки", "Сумма не указана и не восстановлена из текста."))
        elif amount >= COMMITTEE_THRESHOLD:
            checks.append(PolicyCheck(
                "AMT-01", "warn", "Сумма закупки",
                f"{amount:,.0f} ₽ — выше порога 1 млн ₽.".replace(",", " "),
                "Тендер и согласование закупочного комитета",
            ))
        elif amount >= TENDER_THRESHOLD:
            checks.append(PolicyCheck(
                "AMT-01", "warn", "Сумма закупки",
                f"{amount:,.0f} ₽ — выше порога 500 тыс. ₽.".replace(",", " "),
                "Конкурентная процедура, не менее 3 предложений",
            ))
        elif amount >= QUOTE_THRESHOLD:
            checks.append(PolicyCheck(
                "AMT-01", "warn", "Сумма закупки",
                f"{amount:,.0f} ₽ — выше порога 100 тыс. ₽.".replace(",", " "),
                "Запросить 3 коммерческих предложения",
            ))
        else:
            checks.append(PolicyCheck("AMT-01", "pass", "Сумма закупки", "Порог конкурентной процедуры не превышен."))

        # 5. Поставщик
        supplier = str(extracted.get("supplier") or "")
        if supplier:
            checks.append(PolicyCheck("SUP-01", "pass", "Поставщик", f"Указан поставщик: {supplier}."))
        else:
            checks.append(PolicyCheck(
                "SUP-01", "warn", "Поставщик",
                "Поставщик не указан.",
                "Подобрать не менее 3 предложений из реестра",
            ))

        # 6. Срочность
        urgency = str(extracted.get("urgency") or "")
        if urgency == "высокая" and len(justification) < 30:
            checks.append(PolicyCheck(
                "URG-01", "fail", "Обоснование срочности",
                "Заявка срочная, но обоснование срочности отсутствует.",
                "Подтвердить причину срочности у руководителя",
            ))
        elif urgency == "высокая":
            checks.append(PolicyCheck("URG-01", "pass", "Срочность", "Срочность подтверждена обоснованием."))
        else:
            checks.append(PolicyCheck("URG-01", "pass", "Срочность", "Срочность не требует отдельного подтверждения."))

        # 7. Категорийные требования
        if category in CATEGORY_REQUIREMENTS:
            checks.append(PolicyCheck(
                "CAT-01", "warn", "Категорийное требование",
                CATEGORY_REQUIREMENTS[category],
                "Согласование профильного подразделения",
            ))
        else:
            checks.append(PolicyCheck("CAT-01", "pass", "Категорийное требование", "Дополнительных требований нет."))

        # 8. Дубликаты
        if duplicate.is_duplicate:
            checks.append(PolicyCheck(
                "DUP-01", "fail", "Дубликат",
                f"Похожая заявка {duplicate.request_id} (сходство {duplicate.similarity:.0%}).",
                "Объединить с существующей заявкой",
            ))
        elif duplicate.is_possible:
            checks.append(PolicyCheck(
                "DUP-01", "warn", "Возможный дубликат",
                f"Похожая заявка {duplicate.request_id} (сходство {duplicate.similarity:.0%}).",
                "Проверить вручную",
            ))
        else:
            checks.append(PolicyCheck("DUP-01", "pass", "Дубликаты", "Совпадений не найдено."))

        # 9. Цена относительно медианы категории
        unit_price = extracted.get("unit_price")
        median = self.price_medians.get(category)
        if unit_price and median and float(unit_price) > 0:
            ratio = float(unit_price) / float(median)
            if ratio > 3:
                checks.append(PolicyCheck(
                    "PRICE-01", "warn", "Аномалия цены",
                    f"Цена за единицу выше медианы категории в {ratio:.1f} раза.",
                    "Проверить спецификацию и рыночную цену",
                ))
            elif ratio < 0.3:
                checks.append(PolicyCheck(
                    "PRICE-01", "warn", "Аномалия цены",
                    f"Цена за единицу ниже медианы категории в {1/ratio:.1f} раза.",
                    "Проверить комплектацию и условия поставки",
                ))
            else:
                checks.append(PolicyCheck("PRICE-01", "pass", "Цена", "Цена в пределах медианного диапазона."))
        else:
            checks.append(PolicyCheck("PRICE-01", "pass", "Цена", "Недостаточно данных для сравнения цены."))

        # 10. Срок
        needed_by = str(extracted.get("needed_by") or "")
        if needed_by:
            try:
                target = datetime.fromisoformat(needed_by).date()
                if target < today:
                    checks.append(PolicyCheck("DATE-01", "fail", "Срок", f"Желаемый срок {needed_by} уже прошёл."))
                elif (target - today).days < 3 and urgency != "высокая":
                    checks.append(PolicyCheck(
                        "DATE-01", "warn", "Срок",
                        f"До желаемого срока {needed_by} менее 3 дней.",
                        "Подтвердить срочность",
                    ))
                else:
                    checks.append(PolicyCheck("DATE-01", "pass", "Срок", f"Желаемый срок {needed_by} реалистичен."))
            except ValueError:
                checks.append(PolicyCheck("DATE-01", "warn", "Срок", "Не удалось разобрать желаемый срок."))
        else:
            checks.append(PolicyCheck("DATE-01", "pass", "Срок", "Желаемый срок не указан."))

        # 11. Уверенность классификатора
        if confidence < 0.45:
            checks.append(PolicyCheck(
                "CLS-01", "warn", "Категория",
                f"Низкая уверенность классификатора ({confidence:.0%}).",
                "Подтвердить категорию вручную",
            ))
        else:
            checks.append(PolicyCheck("CLS-01", "pass", "Категория", "Категория определена уверенно."))

        return checks

    @staticmethod
    def risk(
        checks: list[PolicyCheck],
        extracted: dict[str, object],
        amount: float | None,
        duplicate: DuplicateMatch,
        confidence: float,
    ) -> tuple[int, list[str]]:
        score = 0
        factors: list[str] = []

        missing = extracted.get("_missing_fields", [])
        if missing:
            add = min(28, 7 * len(missing))
            score += add
            factors.append(f"Неполные данные: {len(missing)} поле(й), +{add}")

        if confidence < 0.45:
            score += 18
            factors.append("Низкая уверенность классификатора, +18")
        elif confidence < 0.60:
            score += 8
            factors.append("Средняя уверенность классификатора, +8")

        if duplicate.is_duplicate:
            score += 30
            factors.append("Дубликат заявки, +30")
        elif duplicate.is_possible:
            score += 12
            factors.append("Возможный дубликат, +12")

        if amount:
            if amount >= COMMITTEE_THRESHOLD:
                score += 18
                factors.append("Сумма выше 1 млн ₽, +18")
            elif amount >= TENDER_THRESHOLD:
                score += 12
                factors.append("Сумма выше 500 тыс. ₽, +12")
            elif amount >= QUOTE_THRESHOLD:
                score += 5
                factors.append("Сумма выше 100 тыс. ₽, +5")

        fails = [c for c in checks if c.status == "fail"]
        warns = [c for c in checks if c.status == "warn"]
        if fails:
            add = min(24, 8 * len(fails))
            score += add
            factors.append(f"Нарушения правил: {len(fails)}, +{add}")
        if warns:
            add = min(12, 3 * len(warns))
            score += add
            factors.append(f"Предупреждения: {len(warns)}, +{add}")

        if extracted.get("urgency") == "высокая" and len(str(extracted.get("justification") or "")) < 30:
            score += 10
            factors.append("Срочность без обоснования, +10")

        if not extracted.get("supplier"):
            score += 6
            factors.append("Поставщик не указан, +6")

        price_check = next((c for c in checks if c.code == "PRICE-01" and c.status == "warn"), None)
        if price_check:
            score += 8
            factors.append("Аномалия цены, +8")

        return min(100, score), factors

    @staticmethod
    def route(
        score: int,
        missing: list[str],
        duplicate: DuplicateMatch,
        fails: list[PolicyCheck],
        amount: float | None = None,
        category: str = "",
    ) -> tuple[str, str]:
        if duplicate.is_duplicate:
            return "manager_approval", "Согласование руководителем: дубликат"
        if missing:
            return "clarify", "Запрос уточнений у заявителя"
        hard_fail = [c for c in fails if c.code in {"BUD-01", "AMT-01", "URG-01", "DATE-01"}]
        if hard_fail:
            return "clarify", "Запрос уточнений: критичное нарушение"

        # Пороговые правила важнее суммы риск-баллов: нельзя автоматически
        # принимать заявку на 850 тыс. ₽ только потому, что она хорошо заполнена.
        if amount is not None:
            if amount >= COMMITTEE_THRESHOLD:
                return "manager_approval", "Согласование руководителем: сумма выше 1 млн ₽"
            if amount >= TENDER_THRESHOLD:
                return "procurement_review", "Проверка закупщиком: конкурентная процедура"
            if amount >= QUOTE_THRESHOLD:
                return "procurement_review", "Проверка закупщиком: нужны 3 предложения"
        if category in CATEGORY_REQUIREMENTS and (amount or 0) >= QUOTE_THRESHOLD:
            return "procurement_review", "Проверка закупщиком: категорийное требование"

        if score >= 80:
            return "manager_approval", "Согласование руководителем"
        if score >= 55:
            return "procurement_review", "Проверка закупщиком"
        if score >= 30:
            return "clarify", "Запрос уточнений у заявителя"
        return "auto_approve", "Автоматическое принятие карточки (без внешних действий)"
