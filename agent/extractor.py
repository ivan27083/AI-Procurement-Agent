"""Извлечение структурированных полей из свободного текста заявки.

Детерминированный offline-экстрактор: регулярные выражения и справочники.
Он не заменяет LLM, но делает прототип воспроизводимым без API-ключа и
показывает, какие поля вообще можно восстановить из текста.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from .schema import PurchaseRequest

UNITS = [
    "шт", "штук", "штуки", "единиц", "ед", "уп", "упаков", "упаковок",
    "лиц", "лицензи", "пользовател", "мес", "месяц", "чел", "компл",
    "проект", "рейс", "смен", "час", "л", "литр", "канистр", "пар",
    "тираж", "группа", "услуга", "комплект",
]

UNIT_CANON = {
    "шт": "шт.", "штук": "шт.", "штуки": "шт.", "единиц": "шт.", "ед": "шт.",
    "уп": "уп.", "упаков": "уп.", "упаковок": "уп.",
    "лиц": "лиц.", "лицензи": "лиц.", "пользовател": "лиц.",
    "мес": "мес.", "месяц": "мес.",
    "чел": "чел.", "компл": "компл.", "комплект": "компл.",
    "проект": "проект", "рейс": "рейс", "смен": "смена", "час": "час",
    "л": "л", "литр": "л", "канистр": "канистра", "пар": "пара",
    "тираж": "тираж", "группа": "группа", "услуга": "услуга",
}

DEPARTMENTS = {
    "отдел продаж": "Отдел продаж",
    "продажи": "Отдел продаж",
    "отдел логистики": "Отдел логистики",
    "логистика": "Отдел логистики",
    "складской комплекс": "Складской комплекс",
    "склад": "Складской комплекс",
    "ит-отдел": "ИТ-отдел",
    "ит отдел": "ИТ-отдел",
    "отдел ит": "ИТ-отдел",
    "финансовый отдел": "Финансовый отдел",
    "фин. отдел": "Финансовый отдел",
    "финансы": "Финансовый отдел",
    "отдел кадров": "Отдел кадров",
    "кадры": "Отдел кадров",
    "hr": "Отдел кадров",
    "юридический отдел": "Юридический отдел",
    "юр. отдел": "Юридический отдел",
    "отдел маркетинга": "Отдел маркетинга",
    "маркетинг": "Отдел маркетинга",
    "административный отдел": "Административный отдел",
    "ахо": "Административный отдел",
    "отдел закупок": "Отдел закупок",
    "закупки": "Отдел закупок",
    "служба безопасности": "Служба безопасности",
    "сб": "Служба безопасности",
    "транспортный отдел": "Транспортный отдел",
    "транспорт": "Транспортный отдел",
    "автопарк": "Транспортный отдел",
    "отдел обслуживания клиентов": "Отдел обслуживания клиентов",
    "поддержка клиентов": "Отдел обслуживания клиентов",
    "руководство": "Руководство",
    "дирекция": "Руководство",
}


def _to_float(value: str) -> float | None:
    s = value.replace("\xa0", " ").replace("\u202f", " ").replace(" ", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def extract_quantity(text: str) -> tuple[float | None, str]:
    unit_alt = "|".join(sorted(UNITS, key=len, reverse=True))
    pattern = re.compile(
        r"(\d+(?:[.,]\d+)?)\s*(" + unit_alt + r")\b",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None, ""
    qty = _to_float(match.group(1))
    unit_raw = match.group(2).lower()
    unit = UNIT_CANON.get(unit_raw, unit_raw)
    # «10 месяцев» — это количество месяцев, а не 10 единиц товара.
    return qty, unit


def extract_amount(text: str) -> float | None:
    patterns = [
        r"(?:бюджет|стоимость|сумма|ориентировочно|на\s+сумму|цена)[^\d]{0,25}"
        r"(\d[\d\s]*(?:[.,]\d+)?)\s*(тыс\.?|млн\.?)?\s*(?:руб|₽|rub)",
        r"(\d[\d\s]*(?:[.,]\d+)?)\s*(тыс\.?|млн\.?)?\s*(?:руб|₽|rub)",
    ]
    best: float | None = None
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw = match.group(1)
            mult = (match.group(2) or "").lower()
            value = _to_float(raw)
            if value is None:
                continue
            if mult.startswith("тыс"):
                value *= 1_000
            elif mult.startswith("млн"):
                value *= 1_000_000
            if value > 0 and (best is None or value > best):
                best = value
    return best


def extract_budget_code(text: str) -> str:
    match = re.search(r"\b([A-ZА-Я]{2,4})\s*-\s*(\d{4})\s*-\s*(\d{2})\b", text.upper())
    if not match:
        return ""
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"


def extract_urgency(text: str) -> str:
    low = text.lower()
    if any(w in low for w in ["не срочно", "плановая", "планово", "без срочности"]):
        return "низкая"
    if any(w in low for w in ["срочно", "asap", "критично", "простой", "аварий"]):
        return "высокая"
    if any(w in low for w in ["средняя срочность", "обычная"]):
        return "средняя"
    return ""


def extract_department(text: str) -> str:
    low = text.lower()
    for key in sorted(DEPARTMENTS, key=len, reverse=True):
        if key in low:
            return DEPARTMENTS[key]
    return ""


def extract_supplier(text: str) -> str:
    match = re.search(
        r"(?:поставщик[:\s]+)?((?:ООО|АО|ПАО|ИП)\s+[«\"]?[^,.;\n]{2,45})",
        text,
        re.IGNORECASE,
    )
    if not match:
        return ""
    value = match.group(1).strip().strip("«»\"")
    return re.sub(r"\s+", " ", value)


def extract_justification(text: str) -> str:
    match = re.search(r"обоснован\w*[:\s]+(.{10,220}?)(?:\.|$)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    return ""


def extract_needed_by(text: str) -> str:
    match = re.search(r"(?:до|к|срок[:\s]+)\s*(\d{2}[./]\d{2}[./]\d{4}|\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    if not match:
        return ""
    raw = match.group(1)
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def extract_item_hint(text: str) -> str:
    match = re.search(
        r"(?:закупить|требуется|нужен|нужна|нужно|заявка на|прошу)\s+(.{3,90}?)(?:[.,;]|$)",
        text,
        re.IGNORECASE,
    )
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    return text[:90].strip()


def extract_request(request: PurchaseRequest) -> dict[str, object]:
    """Объединяет явно переданные поля с результатами извлечения из текста."""
    text = request.text or ""
    qty, unit = extract_quantity(text)
    amount = request.amount if request.amount is not None else extract_amount(text)
    quantity = request.quantity if request.quantity is not None else qty
    unit_value = request.unit or unit
    unit_price = request.unit_price
    if unit_price is None and amount and quantity and quantity > 0:
        unit_price = round(amount / quantity, 2)

    urgency = (request.urgency or extract_urgency(text)).lower()
    urgency = {"срочно": "высокая", "asap": "высокая", "критично": "высокая"}.get(urgency, urgency)
    if urgency not in {"низкая", "средняя", "высокая"}:
        urgency = ""

    budget_code = request.budget_code or extract_budget_code(text)
    budget_code = re.sub(r"\s+", "", budget_code.upper())

    justification = request.justification or extract_justification(text)
    supplier = request.supplier or extract_supplier(text)
    department = request.department or extract_department(text)
    needed_by = request.needed_by or extract_needed_by(text)

    return {
        "request_id": request.request_id,
        "text": text,
        "item_hint": extract_item_hint(text),
        "department": department,
        "requester": request.requester,
        "quantity": quantity,
        "unit": unit_value,
        "unit_price": unit_price,
        "amount": amount,
        "budget_code": budget_code,
        "urgency": urgency,
        "supplier": supplier,
        "justification": justification,
        "needed_by": needed_by,
        "attachments": request.attachments,
        "source": request.source,
    }


def completeness(extracted: dict[str, object]) -> tuple[float, list[str]]:
    """Полнота заявки для маршрутизации. Поставщик проверяется отдельно."""
    checks = [
        ("подразделение", bool(extracted.get("department"))),
        ("количество", bool(extracted.get("quantity"))),
        ("единица измерения", bool(extracted.get("unit"))),
        ("сумма или цена", bool(extracted.get("amount") or extracted.get("unit_price"))),
        ("бюджетный код", bool(re.fullmatch(r"[A-ZА-Я]{2,4}-\d{4}-\d{2}", str(extracted.get("budget_code") or "")))),
        ("обоснование (не короче 30 символов)", len(str(extracted.get("justification") or "")) >= 30),
    ]
    passed = sum(1 for _, ok in checks if ok)
    missing = [name for name, ok in checks if not ok]
    return passed / len(checks), missing


def is_valid_date(value: str) -> bool:
    if not value:
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False
