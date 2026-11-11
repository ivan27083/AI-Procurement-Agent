"""Тесты прототипа: извлечение, классификация, правила и маршрутизация."""

from __future__ import annotations

import unittest

from agent.agent import ProcurementAgent
from agent.extractor import extract_request
from agent.schema import PurchaseRequest


class ExtractorTests(unittest.TestCase):
    def test_extracts_quantity_amount_budget(self) -> None:
        request = PurchaseRequest(
            request_id="T-1",
            text=(
                "Прошу закупить 10 шт. ноутбуков Lenovo ThinkPad E16 для отдела продаж. "
                "Стоимость 850 000 руб. Бюджетный код IT-2025-04. "
                "Обоснование: замена устаревших ноутбуков у новых менеджеров."
            ),
        )
        data = extract_request(request)
        self.assertEqual(data["quantity"], 10)
        self.assertEqual(data["unit"], "шт.")
        self.assertEqual(data["amount"], 850_000)
        self.assertEqual(data["budget_code"], "IT-2025-04")
        self.assertEqual(data["urgency"], "")

    def test_extracts_urgency(self) -> None:
        request = PurchaseRequest(request_id="T-2", text="Нужен картридж, срочно, простой процесса.")
        data = extract_request(request)
        self.assertEqual(data["urgency"], "высокая")

    def test_missing_fields_are_detected(self) -> None:
        request = PurchaseRequest(request_id="T-3", text="Нужна закупка, детали позже.")
        data = extract_request(request)
        self.assertIsNone(data["quantity"])
        self.assertEqual(data["amount"], None)


class ClassifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.agent = ProcurementAgent()

    def test_office_supplies(self) -> None:
        category, _ = self.agent.classifier.predict("Заказать бумагу А4, 200 упаковок для офиса.")
        self.assertEqual(category, "Канцелярия и расходники")

    def test_it_equipment(self) -> None:
        category, _ = self.agent.classifier.predict("Нужен ноутбук Lenovo ThinkPad для менеджера.")
        self.assertEqual(category, "IT-оборудование")


class AgentScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.agent = ProcurementAgent()

    def test_high_value_goes_to_procurement_review(self) -> None:
        request = PurchaseRequest(
            request_id="T-10",
            text=(
                "Прошу закупить 10 шт. ноутбуков Lenovo ThinkPad E16 для отдела продаж. "
                "Стоимость 850 000 руб. Бюджетный код IT-2025-04. "
                "Обоснование: замена устаревших ноутбуков у новых менеджеров."
            ),
            department="Отдел продаж",
        )
        result = self.agent.process(request)
        self.assertEqual(result.route, "procurement_review")
        self.assertFalse(result.external_action_allowed)
        self.assertIn("конкурентная", result.route_label)

    def test_low_value_complete_is_auto(self) -> None:
        request = PurchaseRequest(
            request_id="T-11",
            text=(
                "Закупить 50 шт. ручек Pilot и 20 шт. папок-регистраторов для отдела кадров. "
                "Сумма 12 000 руб., бюджет HR-2025-03. "
                "Обоснование: плановая потребность на квартал, замена канцелярии."
            ),
            department="Отдел кадров",
        )
        result = self.agent.process(request)
        self.assertEqual(result.route, "auto_approve")
        self.assertFalse(result.external_action_allowed)

    def test_incomplete_request_goes_to_clarify(self) -> None:
        request = PurchaseRequest(
            request_id="T-12",
            text="Заказать бумагу А4, 200 упаковок. Нужно срочно.",
            department="Административный отдел",
            urgency="высокая",
        )
        result = self.agent.process(request)
        self.assertEqual(result.route, "clarify")
        self.assertIn("сумма или цена", result.missing_fields)

    def test_duplicate_is_detected(self) -> None:
        request = PurchaseRequest(
            request_id="T-13",
            text=(
                "Нужен ИБП APC Smart-UPS 3000VA (4 шт.) для обеспечения безопасности. "
                "Характеристики: 3000 ВА, rack 2U. Желаемый срок — в течение месяца."
            ),
            department="Служба безопасности",
            amount=383213.68,
        )
        result = self.agent.process(request)
        self.assertTrue(result.duplicate.is_duplicate)
        self.assertEqual(result.route, "manager_approval")


if __name__ == "__main__":
    unittest.main()
