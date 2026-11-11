#!/usr/bin/env python3
"""Генерация синтетического набора заявок на закупку.

Набор имитирует выгрузку из условной системы электронных заявок
ООО «Северная Логистика» за 2025 год. Данные синтетические: они нужны
для воспроизводимой демонстрации методики, а не для выводов о реальном
рынке. Все закономерности и дефекты качества заложены генератором.
"""

from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

SEED = 42
N_UNIQUE = 2200
N_DUPLICATES = 200
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "procurement_requests_raw.csv"

random.seed(SEED)

DEPARTMENTS = [
    "Отдел продаж",
    "Отдел логистики",
    "Складской комплекс",
    "ИТ-отдел",
    "Финансовый отдел",
    "Отдел кадров",
    "Юридический отдел",
    "Отдел маркетинга",
    "Административный отдел",
    "Отдел закупок",
    "Служба безопасности",
    "Транспортный отдел",
    "Отдел обслуживания клиентов",
    "Руководство",
]

DEPT_VARIANTS = {
    "ИТ-отдел": ["IT-отдел", "ит отдел", "Отдел ИТ", "ИТ отдел "],
    "Отдел продаж": ["отдел продаж", "Отдел Продаж", "продажи"],
    "Отдел логистики": ["отдел логистики", "Логистика", "Отдел логистики "],
    "Складской комплекс": ["склад", "Складской комплекс", "Складской  комплекс"],
    "Финансовый отдел": ["финансовый отдел", "Фин. отдел", "Финансы"],
    "Отдел кадров": ["отдел кадров", "HR", "Кадры"],
    "Юридический отдел": ["юридический отдел", "Юр. отдел", "Юристы"],
    "Отдел маркетинга": ["маркетинг", "Отдел маркетинга", "Маркетинг "],
    "Административный отдел": ["АХО", "административный отдел", "Админ. отдел"],
    "Отдел закупок": ["закупки", "Отдел закупок", "Снабжение"],
    "Служба безопасности": ["СБ", "служба безопасности", "Служба  безопасности"],
    "Транспортный отдел": ["транспортный отдел", "Транспорт", "Автопарк"],
    "Отдел обслуживания клиентов": ["поддержка клиентов", "Отдел обслуживания", "Клиентский сервис"],
    "Руководство": ["руководство", "Дирекция", "Правление"],
}

CATALOG: dict[str, list[tuple[str, str, float, list[str], tuple[int, int]]]] = {
    "IT-оборудование": [
        ("Ноутбук Lenovo ThinkPad E16", "шт.", 95000, ["16 ГБ ОЗУ", "512 ГБ SSD", "Windows 11 Pro"], (1, 8)),
        ("Монитор Dell UltraSharp U2723QE", "шт.", 52000, ["27 дюймов", "4K", "USB-C"], (2, 12)),
        ("Сервер Dell PowerEdge R650", "шт.", 480000, ["2 процессора Xeon", "128 ГБ ОЗУ", "RAID-контроллер"], (1, 3)),
        ("МФУ Kyocera ECOSYS M4125idn", "шт.", 78000, ["А4", "ч/б", "дуплекс"], (1, 4)),
        ("Коммутатор Cisco Catalyst 1000-24T", "шт.", 65000, ["24 порта", "управляемый"], (1, 6)),
        ("ИБП APC Smart-UPS 3000VA", "шт.", 92000, ["3000 ВА", " rack 2U"], (1, 4)),
        ("Гарнитура Jabra Evolve2 65", "шт.", 21000, ["Bluetooth", "шумоподавление"], (3, 20)),
        ("Сканер Fujitsu fi-8170", "шт.", 85000, ["до 70 стр/мин", "А4"], (1, 3)),
    ],
    "ПО и лицензии": [
        ("Лицензия Microsoft 365 Business Standard", "лиц.", 14500, ["на 25 пользователей", "продление на 12 месяцев"], (5, 60)),
        ("Лицензия 1С:Бухгалтерия 8 ПРОФ", "лиц.", 22000, ["основная поставка", "12 месяцев"], (1, 10)),
        ("Антивирус Kaspersky Endpoint Security", "лиц.", 3200, ["на 100 устройств", "продление"], (20, 150)),
        ("Adobe Acrobat Pro", "лиц.", 18000, ["для дизайнеров", "годовая подписка"], (1, 8)),
        ("BI-платформа Visiology", "лиц.", 45000, ["10 аналитиков", "годовая поддержка"], (5, 20)),
    ],
    "Канцелярия и расходники": [
        ("Бумага А4 80 г/м²", "уп.", 420, ["белизна 146%", "500 листов"], (20, 300)),
        ("Картридж HP 26A CF226A", "шт.", 7800, ["оригинальный", "для LaserJet Pro"], (2, 20)),
        ("Тонер Kyocera TK-1170", "шт.", 5200, ["оригинальный", "ресурс 7200 страниц"], (2, 15)),
        ("Ручка шариковая Pilot BPS-GP", "шт.", 85, ["синяя", "0,7 мм"], (50, 500)),
        ("Папка-регистратор А4", "шт.", 320, ["70 мм", "синяя"], (20, 200)),
        ("Блокнот А5", "шт.", 240, ["96 листов", "клетка"], (20, 150)),
    ],
    "Услуги подрядчиков": [
        ("Услуги клининга офиса", "мес.", 180000, ["ежедневная уборка", "площадь 1 200 м²"], (1, 12)),
        ("Услуги охраны", "мес.", 240000, ["круглосуточный пост", "2 охранника"], (1, 12)),
        ("Услуги грузчиков", "смена", 45000, ["8 часов", "склад на Московском шоссе"], (1, 10)),
        ("Услуги переводчика", "час", 3500, ["английский", "синхронный перевод"], (2, 40)),
        ("Аутсорсинг бухгалтерии", "мес.", 150000, ["полное сопровождение", "НДС"], (1, 12)),
    ],
    "Транспорт и логистика": [
        ("Аренда грузового автомобиля с водителем", "смена", 38000, ["грузоподъёмность 10 т", "межгород"], (2, 30)),
        ("Дизельное топливо", "л", 68, ["ДТ ЕВРО-5", "для автопарка"], (2000, 15000)),
        ("Шины грузовые 315/80 R22.5", "шт.", 32000, ["ведущая ось", "зимние"], (4, 30)),
        ("Услуги экспедирования", "рейс", 55000, ["Москва — Санкт-Петербург", "сборный груз"], (2, 20)),
        ("Запчасти для погрузчика Toyota", "компл.", 78000, ["гидравлика", "для 8FBE20"], (1, 5)),
    ],
    "Мебель и обустройство": [
        ("Кресло офисное Ergo Line", "шт.", 24000, ["сетка", "регулировка высоты"], (2, 30)),
        ("Стол письменный 160x80", "шт.", 18000, ["ЛДСП", "дуб сонома"], (2, 20)),
        ("Шкаф архивный металлический", "шт.", 21000, ["4 полки", "замок"], (1, 10)),
        ("Стеллаж складской 2000x1000", "шт.", 15000, ["нагрузка 300 кг", "4 уровня"], (2, 25)),
        ("Перегородка офисная", "шт.", 32000, ["тканевая", "1600x1400"], (2, 15)),
    ],
    "Маркетинг и реклама": [
        ("Разработка сайта компании", "проект", 450000, ["корпоративный сайт", "интеграция с CRM"], (1, 2)),
        ("Печать буклетов А4", "тираж", 28000, ["полноцвет", "мелованная бумага"], (1, 5)),
        ("Реклама в Яндекс.Директ", "мес.", 120000, ["поиск и РСЯ", "ведение кампаний"], (1, 6)),
        ("Съёмка промо-ролика", "проект", 180000, ["2 минуты", "сценарий и монтаж"], (1, 2)),
        ("Сувенирная продукция с логотипом", "компл.", 65000, ["ежедневники", "ручки", "термокружки"], (1, 4)),
    ],
    "Обучение и развитие": [
        ("Курс повышения квалификации для логистов", "чел.", 32000, ["40 часов", "удостоверение"], (2, 20)),
        ("Тренинг по переговорам", "группа", 95000, ["2 дня", "до 12 человек"], (1, 3)),
        ("Онлайн-курс по Excel", "чел.", 12000, ["продвинутый уровень", "16 часов"], (3, 30)),
        ("Аттестация водителей", "чел.", 18000, ["категория C", "экзамен"], (2, 25)),
        ("Корпоративное обучение охране труда", "группа", 45000, ["ежегодное", "до 30 человек"], (1, 3)),
    ],
    "Ремонт и обслуживание": [
        ("Ремонт погрузчика Toyota 8FBE20", "услуга", 145000, ["замена гидронасоса", "выезд на склад"], (1, 3)),
        ("Обслуживание системы вентиляции", "услуга", 85000, ["ТО 2 раза в год", "офис и склад"], (1, 4)),
        ("Ремонт кровли склада", "проект", 620000, ["площадь 800 м²", "мягкая кровля"], (1, 2)),
        ("Замена ламп освещения", "услуга", 38000, ["120 светильников", "склад"], (1, 3)),
        ("ТО дизель-генератора", "услуга", 52000, ["150 кВт", "плановое ТО"], (1, 3)),
    ],
    "Хозтовары": [
        ("Средство для мытья полов", "канистра", 850, ["5 л", "концентрат"], (10, 100)),
        ("Мешки для мусора 120 л", "уп.", 320, ["30 шт.", "ПВД"], (20, 200)),
        ("Мыло жидкое", "канистра", 280, ["5 л", "антибактериальное"], (10, 80)),
        ("Перчатки хозяйственные", "пара", 65, ["латекс", "размер M"], (50, 500)),
        ("Тряпки микрофибра", "уп.", 450, ["10 шт.", "универсальные"], (10, 100)),
    ],
}

CATEGORY_VARIANTS = {
    "IT-оборудование": ["IT", "ит-оборудование", "IT оборудование", "Оборудование IT", "ИТ оборудование"],
    "ПО и лицензии": ["ПО", "Лицензии", "программное обеспечение", "ПО и лицензии "],
    "Канцелярия и расходники": ["Канцелярия", "канцелярские товары", "Расходники", "канцелярия и расходники"],
    "Услуги подрядчиков": ["Услуги", "подрядчики", "Услуги подрядчиков ", "аутсорсинг"],
    "Транспорт и логистика": ["Транспорт", "логистика", "Транспорт и логистика ", "перевозки"],
    "Мебель и обустройство": ["Мебель", "обустройство", "Мебель и обустройство ", "офисная мебель"],
    "Маркетинг и реклама": ["Маркетинг", "реклама", "Маркетинг и реклама ", "PR"],
    "Обучение и развитие": ["Обучение", "развитие", "Обучение и развитие ", "курсы"],
    "Ремонт и обслуживание": ["Ремонт", "обслуживание", "Ремонт и обслуживание ", "ТО"],
    "Хозтовары": ["Хозтовары", "хозяйственные товары", "Хозтовары ", "бытовая химия"],
}

URGENCY_VARIANTS = {
    "низкая": ["Низкая", "низкая ", "Не срочно", "плановая"],
    "средняя": ["Средняя", "обычная", "стандартная", "Средняя "],
    "высокая": ["Высокая", "Срочно", "СРОЧНО!", "ASAP", "критично"],
}

VAGUE_TEXTS = {
    "IT-оборудование": "Нужна техника для офиса, модель уточню у ИТ-отдела.",
    "ПО и лицензии": "Требуется продление лицензий на ПО, список пользователей позже.",
    "Канцелярия и расходники": "Закупить расходники для офиса, количество уточняется.",
    "Услуги подрядчиков": "Нужен подрядчик на услуги, детали обсудим.",
    "Транспорт и логистика": "Требуется транспорт для перевозки груза, маршрут уточняется.",
    "Мебель и обустройство": "Нужна мебель для нового офиса, планировка ещё согласуется.",
    "Маркетинг и реклама": "Требуются услуги по рекламе, бюджет уточняется.",
    "Обучение и развитие": "Нужно обучение сотрудников, программу выберем позже.",
    "Ремонт и обслуживание": "Требуется ремонт оборудования, неисправность описана в комментарии.",
    "Хозтовары": "Закупить хозяйственные товары, список позже.",
}

FIRST_NAMES = ["Алексей", "Мария", "Дмитрий", "Ольга", "Сергей", "Анна", "Иван", "Елена", "Павел", "Татьяна", "Михаил", "Ирина", "Андрей", "Наталья", "Роман", "Светлана"]
LAST_NAMES = ["Иванов", "Петрова", "Смирнов", "Кузнецова", "Попов", "Соколова", "Лебедев", "Новикова", "Морозов", "Волкова", "Козлов", "Зайцева", "Павлов", "Семёнова", "Голубев", "Виноградова"]

STATUSES = ["Одобрена", "В работе", "Возвращена на доработку", "Отклонена", "Отменена"]

PURPOSE = {
    "Отдел продаж": "для оснащения менеджеров",
    "Отдел логистики": "для диспетчерской службы",
    "Складской комплекс": "для складских операций",
    "ИТ-отдел": "для поддержки инфраструктуры",
    "Финансовый отдел": "для финансового планирования",
    "Отдел кадров": "для кадрового учёта",
    "Юридический отдел": "для юридического сопровождения",
    "Отдел маркетинга": "для маркетинговых кампаний",
    "Административный отдел": "для административных нужд",
    "Отдел закупок": "для закупочной деятельности",
    "Служба безопасности": "для обеспечения безопасности",
    "Транспортный отдел": "для автопарка",
    "Отдел обслуживания клиентов": "для клиентской поддержки",
    "Руководство": "для нужд дирекции",
}

BUDGET_CODES = {
    "Отдел продаж": "SL",
    "Отдел логистики": "LG",
    "Складской комплекс": "WH",
    "ИТ-отдел": "IT",
    "Финансовый отдел": "FI",
    "Отдел кадров": "HR",
    "Юридический отдел": "LE",
    "Отдел маркетинга": "MK",
    "Административный отдел": "AD",
    "Отдел закупок": "PR",
    "Служба безопасности": "SB",
    "Транспортный отдел": "TR",
    "Отдел обслуживания клиентов": "CS",
    "Руководство": "MG",
}


@dataclass
class Row:
    request_id: str
    created_at: str
    department: str
    requester: str
    request_text: str
    category: str
    quantity: str
    unit: str
    unit_price: str
    total_amount: str
    currency: str
    budget_code: str
    urgency: str
    supplier: str
    status: str
    lead_time_days: str
    attachment: str
    cost_center: str
    justification: str
    channel: str


def weighted_date() -> date:
    months = list(range(1, 13))
    weights = [8, 7, 10, 9, 8, 7, 7, 9, 11, 10, 9, 5]
    month = random.choices(months, weights=weights, k=1)[0]
    day = random.randint(1, 28)
    return date(2025, month, day)


def money_fmt(value: float) -> str:
    """Разные форматы суммы — как в реальной выгрузке."""
    style = random.random()
    if style < 0.55:
        return f"{value:.2f}"
    if style < 0.80:
        return f"{value:,.2f}".replace(",", " ").replace(".", ",")
    if style < 0.93:
        return f"{value:,.2f}".replace(",", " ").replace(".", ",") + " руб."
    return f"{value:.2f} RUB"


def to_float(value: str) -> float:
    s = str(value).replace(" руб.", "").replace(" RUB", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def date_fmt(d: date) -> str:
    style = random.random()
    if style < 0.68:
        return d.isoformat()
    if style < 0.90:
        return d.strftime("%d.%m.%Y")
    if style < 0.97:
        return d.strftime("%d/%m/%Y")
    return str((d - date(1899, 12, 30)).days)


def make_base_rows(n: int) -> list[Row]:
    categories = list(CATALOG.keys())
    cat_weights = [18, 12, 18, 12, 8, 7, 6, 6, 7, 6]
    rows: list[Row] = []
    for i in range(n):
        cat = random.choices(categories, weights=cat_weights, k=1)[0]
        item, unit, base_price, specs, qty_range = random.choice(CATALOG[cat])
        dept = random.choice(DEPARTMENTS)
        first, last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
        requester = f"{last} {first}"
        qty = random.randint(*qty_range)
        price = max(1.0, base_price * math.exp(random.gauss(0, 0.16)))
        total = qty * price
        urgency = random.choices(["низкая", "средняя", "высокая"], weights=[25, 58, 17], k=1)[0]
        d = weighted_date()
        budget_prefix = BUDGET_CODES[dept]
        budget_code = f"{budget_prefix}-2025-{random.randint(1, 12):02d}"
        cost_center = f"CC-{random.randint(100, 999)}"
        supplier = random.choice([
            "ООО Комус", "ООО Ситилинк", "АО Софтлайн", "ООО Техноком",
            "ИП Смирнов А.А.", "ООО Офис-Снаб", "ООО Логистик-Сервис",
            "ООО Проф-Клининг", "АО Деловые Линии", "Не указан",
        ])
        if random.random() < 0.55:
            supplier = "Не указан"
        purpose = PURPOSE[dept]
        spec_text = ", ".join(specs)
        templates = [
            f"Прошу закупить {item} — {qty} {unit}. {spec_text}. Назначение: {purpose}.",
            f"Требуется {item}, количество: {qty} {unit}. {spec_text}. {purpose.capitalize()}.",
            f"Коллеги, согласуйте закупку: {item}, {qty} {unit}, ориентировочно {total:,.0f} руб. {spec_text}.".replace(",", " "),
            f"Нужен {item} ({qty} {unit}) {purpose}. Характеристики: {spec_text}. Желаемый срок — в течение месяца.",
            f"Заявка на {item}: {qty} {unit}. {spec_text}. Поставщик: {supplier}.",
        ]
        text = random.choice(templates)
        if random.random() < 0.08:
            text = random.choice([
                VAGUE_TEXTS[cat],
                "Прошу согласовать закупку, подробности уточню в комментарии.",
                "Нужна закупка для отдела, позиции и количество уточняются.",
            ])
        if urgency == "высокая":
            text += " Срочно, простой процесса."
        justification = random.choice([
            f"Замена выбывшего оборудования, {purpose}.",
            f"Плановая потребность на 2025 год, {purpose}.",
            f"Истечение срока текущего договора, {purpose}.",
            f"Расширение штата и новых рабочих мест, {purpose}.",
            f"Обеспечение непрерывности процессов, {purpose}.",
        ])
        rows.append(Row(
            request_id=f"REQ-2025-{i + 1:05d}",
            created_at=date_fmt(d),
            department=dept,
            requester=requester,
            request_text=text,
            category=cat,
            quantity=str(qty),
            unit=unit,
            unit_price=money_fmt(price),
            total_amount=money_fmt(total),
            currency="RUB",
            budget_code=budget_code,
            urgency=urgency,
            supplier=supplier,
            status="В работе",
            lead_time_days="",
            attachment=random.choice(["да", "нет", "нет", "да"]),
            cost_center=cost_center,
            justification=justification,
            channel=random.choice(["1С:Заявки", "E-mail", "Excel", "1С:Заявки", "E-mail"]),
        ))
    return rows


def apply_quality_issues(rows: list[Row]) -> None:
    for row in rows:
        # Вариативность справочников
        if random.random() < 0.16:
            row.category = random.choice(CATEGORY_VARIANTS[row.category])
        if random.random() < 0.12:
            row.department = random.choice(DEPT_VARIANTS.get(row.department, [row.department]))
        if random.random() < 0.14:
            row.urgency = random.choice(URGENCY_VARIANTS[row.urgency])

        # Пропуски и некорректные значения
        if random.random() < 0.05:
            row.quantity = ""
        if random.random() < 0.07:
            row.unit_price = ""
        if random.random() < 0.04:
            row.urgency = ""
        if random.random() < 0.18:
            row.budget_code = ""
        if random.random() < 0.03:
            row.budget_code = random.choice(["б/н", "нет", "TBD", "БЮДЖЕТ-1"])
        if random.random() < 0.03:
            row.attachment = random.choice(["", "Да", "Нет", "есть"])
        if random.random() < 0.03:
            row.lead_time_days = ""

        # Отрицательные и экстремальные значения
        if random.random() < 0.004:
            row.quantity = str(-random.randint(1, 20))
        if random.random() < 0.004:
            row.unit_price = money_fmt(-random.uniform(1000, 50000))
        if random.random() < 0.006:
            # Экстремальное количество зависит от категории: 20 000 мониторов
            # так же нереалистичны, как 3 пачки бумаги. Для расходников
            # допускаем крупный объём, для дорогой техники — только 2–4x.
            if row.category in {"Канцелярия и расходники", "Хозтовары"}:
                row.quantity = str(random.randint(1000, 5000))
            elif row.category == "Транспорт и логистика" and row.unit == "л":
                row.quantity = str(random.randint(20000, 50000))
            else:
                try:
                    base_qty = max(1, int(float(row.quantity or 1)))
                except ValueError:
                    base_qty = 1
                row.quantity = str(random.randint(base_qty * 2, max(base_qty * 2, base_qty * 4)))

        # Валюта: 3% заявок в валюте
        if random.random() < 0.03:
            row.currency = random.choice(["USD", "EUR"])
            rate = 92.5 if row.currency == "USD" else 100.5
            try:
                price = float(row.unit_price.replace(" руб.", "").replace(" RUB", "").replace(" ", "").replace(",", "."))
                total = price * float(row.quantity or 1)
                row.unit_price = money_fmt(price / rate)
                row.total_amount = money_fmt(total / rate)
            except ValueError:
                pass

        # Рассогласование количества, цены и суммы
        if row.quantity and row.unit_price and row.total_amount and random.random() < 0.06:
            try:
                qty = float(row.quantity)
                price = float(row.unit_price.replace(" руб.", "").replace(" RUB", "").replace(" ", "").replace(",", "."))
                current = float(row.total_amount.replace(" руб.", "").replace(" RUB", "").replace(" ", "").replace(",", "."))
                row.total_amount = money_fmt(current * random.choice([0.72, 0.81, 1.18, 1.27]))
            except ValueError:
                pass

        # Короткое или отсутствующее обоснование
        if random.random() < 0.27:
            row.justification = random.choice(["", "нужно", "по плану", "срочно", "для работы"])

        # Статус зависит от полноты заявки на входе: пять ключевых полей.
        budget_valid = row.budget_code not in {"", "б/н", "нет", "TBD", "БЮДЖЕТ-1"}
        completeness = sum([
            bool(row.quantity) and to_float(row.quantity) > 0,
            bool(row.unit_price) and to_float(row.unit_price) > 0,
            budget_valid,
            len(row.justification.strip()) >= 30,
            bool(row.urgency),
        ]) / 5
        if completeness >= 0.8:
            row.status = random.choices(STATUSES, weights=[58, 20, 12, 6, 4], k=1)[0]
        elif completeness >= 0.5:
            row.status = random.choices(STATUSES, weights=[35, 20, 30, 10, 5], k=1)[0]
        else:
            row.status = random.choices(STATUSES, weights=[15, 15, 50, 15, 5], k=1)[0]

        # Срок обработки: срочные — быстрее, дорогие и возвращённые — дольше.
        amount = to_float(row.total_amount)
        urgency_norm = next(
            (k for k, variants in URGENCY_VARIANTS.items() if row.urgency == k or row.urgency in variants),
            "",
        )
        urgency_adj = {"высокая": -1.3, "средняя": 0.0, "низкая": 0.8}.get(urgency_norm, 0.0)
        amount_adj = min(2.0, max(0.0, (math.log10(max(amount, 1)) - 5) * 0.7))
        base_days = 2.0 + abs(random.gauss(1.8, 1.0)) + urgency_adj + amount_adj
        if row.status == "Возвращена на доработку":
            base_days += random.uniform(1.5, 4.0)
        if random.random() < 0.08:
            base_days += random.uniform(3, 8)
        row.lead_time_days = f"{max(0.5, base_days):.1f}"

        # Грязные строковые значения
        if random.random() < 0.05:
            row.requester = row.requester.upper()
        if random.random() < 0.04:
            row.request_text = "  " + row.request_text + "  "
        if random.random() < 0.03:
            row.unit = random.choice(["шт", "ШТ.", "шт ", "ед."])


def add_duplicates(rows: list[Row], n: int) -> list[Row]:
    duplicates: list[Row] = []
    for j in range(n):
        src = random.choice(rows)
        d = Row(**src.__dict__)
        d.request_id = f"REQ-2025-{N_UNIQUE + j + 1:05d}"
        if random.random() < 0.30:
            # Точный дубликат
            duplicates.append(d)
        else:
            # Почти дубликат: другой заявитель, дата и незначительная правка
            d.requester = random.choice(FIRST_NAMES) + " " + random.choice(LAST_NAMES)
            try:
                base = date.fromisoformat(src.created_at) if "-" in src.created_at and len(src.created_at) == 10 else None
            except ValueError:
                base = None
            if base:
                d.created_at = date_fmt(base + timedelta(days=random.randint(1, 5)))
            else:
                d.created_at = date_fmt(weighted_date())
            if random.random() < 0.5:
                d.request_text = d.request_text.replace("Прошу", "Просьба").replace("Требуется", "Нужно")
            duplicates.append(d)
    return duplicates


def main() -> None:
    rows = make_base_rows(N_UNIQUE)
    apply_quality_issues(rows)
    rows.extend(add_duplicates(rows, N_DUPLICATES))
    random.shuffle(rows)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(Row.__dataclass_fields__.keys())
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)
    print(f"Сохранено {len(rows)} строк: {OUT}")
    print(f"Уникальных заявок до дублирования: {N_UNIQUE}, дубликатов: {N_DUPLICATES}")


if __name__ == "__main__":
    main()
