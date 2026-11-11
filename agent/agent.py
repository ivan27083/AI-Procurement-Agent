"""Оркестрация агента первичной обработки заявок на закупку."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .classifier import CategoryClassifier
from .duplicates import DuplicateIndex
from .extractor import completeness, extract_request
from .policy import PolicyEngine
from .schema import AgentResult, DuplicateMatch, PolicyCheck, PurchaseRequest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_LOG = ROOT / "demo_output" / "audit_log.jsonl"


def money(value: float | None) -> str:
    if value is None:
        return "не указана"
    return f"{value:,.0f} ₽".replace(",", " ")


class ProcurementAgent:
    def __init__(self, history_path: Path | str | None = None, audit_log: Path | str = AUDIT_LOG) -> None:
        history_path = Path(history_path) if history_path else ROOT / "data" / "processed" / "procurement_requests_clean.csv"
        self.classifier = CategoryClassifier()
        self.duplicates = DuplicateIndex(history_path)
        self.policy = PolicyEngine(history_path)
        self.audit_log = Path(audit_log)

    def process(self, request: PurchaseRequest) -> AgentResult:
        extracted = extract_request(request)
        completeness_score, missing = completeness(extracted)
        extracted["_missing_fields"] = missing

        category, confidence = self.classifier.predict(str(extracted.get("text") or ""))

        amount = extracted.get("amount")
        if not amount:
            qty = extracted.get("quantity")
            price = extracted.get("unit_price")
            if qty and price:
                amount = float(qty) * float(price)
                extracted["amount"] = amount

        duplicate = self.duplicates.find(
            str(extracted.get("text") or ""),
            amount=float(amount) if amount else None,
            request_id=request.request_id,
        )

        checks = self.policy.evaluate(
            extracted=extracted,
            category=category,
            confidence=confidence,
            amount=float(amount) if amount else None,
            duplicate=duplicate,
        )
        risk_score, risk_factors = self.policy.risk(
            checks=checks,
            extracted=extracted,
            amount=float(amount) if amount else None,
            duplicate=duplicate,
            confidence=confidence,
        )
        fails = [c for c in checks if c.status == "fail"]
        route, route_label = self.policy.route(
            risk_score,
            missing,
            duplicate,
            fails,
            amount=float(amount) if amount else None,
            category=category,
        )

        audit_id = hashlib.sha256(
            f"{request.request_id}|{extracted.get('text')}".encode("utf-8")
        ).hexdigest()[:12]

        draft = build_draft(
            request=request,
            extracted=extracted,
            category=category,
            confidence=confidence,
            amount=float(amount) if amount else None,
            checks=checks,
            duplicate=duplicate,
            risk_score=risk_score,
            risk_factors=risk_factors,
            route=route,
            route_label=route_label,
            completeness_score=completeness_score,
            missing=missing,
            audit_id=audit_id,
        )

        result = AgentResult(
            request_id=request.request_id,
            extracted={k: v for k, v in extracted.items() if not k.startswith("_")},
            category=category,
            category_confidence=confidence,
            completeness=completeness_score,
            missing_fields=missing,
            duplicate=duplicate,
            policy_checks=checks,
            risk_score=risk_score,
            risk_factors=risk_factors,
            route=route,
            route_label=route_label,
            draft_message=draft,
            next_steps=next_steps(route),
            human_review_required=route != "auto_approve",
            external_action_allowed=False,
            audit_id=audit_id,
        )
        self._write_audit(result)
        return result

    def process_batch(self, requests: list[PurchaseRequest]) -> list[AgentResult]:
        return [self.process(r) for r in requests]

    def _write_audit(self, result: AgentResult) -> None:
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result.as_dict(), ensure_ascii=False) + "\n")


def next_steps(route: str) -> list[str]:
    return {
        "auto_approve": [
            "Создать карточку заявки в ERP (черновик)",
            "Проверить остаток бюджета по коду",
            "Передать карточку закупщику для оформления заказа",
        ],
        "clarify": [
            "Отправить запрос заявителю только после подтверждения человеком",
            "Зафиксировать ответ в карточке заявки",
            "Перезапустить проверку после дополнения данных",
        ],
        "procurement_review": [
            "Проверить спецификацию и рыночную цену",
            "Запросить коммерческие предложения у поставщиков",
            "Подготовить проект договора и согласовать категорию",
        ],
        "manager_approval": [
            "Проверить обоснование и риск-факторы",
            "Согласовать способ закупки или отклонить заявку",
            "Зафиксировать решение и ответственного в аудите",
        ],
    }[route]


def build_draft(
    request: PurchaseRequest,
    extracted: dict[str, object],
    category: str,
    confidence: float,
    amount: float | None,
    checks: list[PolicyCheck],
    duplicate: DuplicateMatch,
    risk_score: int,
    risk_factors: list[str],
    route: str,
    route_label: str,
    completeness_score: float,
    missing: list[str],
    audit_id: str,
) -> str:
    header = (
        f"ЧЕРНОВИК. Не отправлено. Требуется подтверждение человека.\n"
        f"Заявка: {request.request_id} | Аудит: {audit_id}\n"
    )
    problems = [c for c in checks if c.status in {"fail", "warn"}]
    problem_text = "\n".join(f"- [{c.status.upper()}] {c.title}: {c.detail}" for c in problems) or "- критичных замечаний нет"
    summary = (
        f"Категория: {category} (уверенность {confidence:.0%})\n"
        f"Сумма: {money(amount)}\n"
        f"Полнота: {completeness_score:.0%}\n"
        f"Риск: {risk_score}/100\n"
        f"Маршрут: {route_label}\n"
    )

    if route == "clarify":
        missing_text = "\n".join(f"- {m}" for m in missing) or "- уточнить цель закупки"
        return (
            header
            + "Кому: " + (request.requester or "заявителю") + "\n"
            + f"Тема: Уточнение заявки {request.request_id}\n\n"
            + "Здравствуйте!\n\n"
            + f"Для запуска закупки по заявке {request.request_id} не хватает данных:\n"
            + missing_text
            + "\n\n"
            + "Пожалуйста, дополните заявку и приложите подтверждение бюджета. "
            + "После этого проверка будет выполнена повторно.\n\n"
            + summary
            + "\nЗамечания:\n" + problem_text + "\n"
        )

    if route == "procurement_review":
        return (
            header
            + "Кому: закупщику категории\n"
            + f"Тема: Заявка {request.request_id} — проверка перед закупкой\n\n"
            + "Коллеги, заявка прошла первичную проверку и направлена на профессиональную проверку.\n\n"
            + summary
            + "\nЧто проверить:\n" + problem_text + "\n\n"
            + "Рекомендуемые действия:\n"
            + "\n".join(f"- {s}" for s in next_steps(route)) + "\n"
        )

    if route == "manager_approval":
        dup = ""
        if duplicate.is_duplicate or duplicate.is_possible:
            dup = (
                f"\nПохожая заявка: {duplicate.request_id}, сходство {duplicate.similarity:.0%}, "
                f"сумма {money(duplicate.amount)}.\n"
            )
        return (
            header
            + "Кому: руководителю закупочного комитета\n"
            + f"Тема: Согласование заявки {request.request_id}\n\n"
            + "Заявка требует управленческого решения.\n\n"
            + summary
            + dup
            + "\nРиск-факторы:\n" + "\n".join(f"- {f}" for f in risk_factors) + "\n"
            + "\nЗамечания:\n" + problem_text + "\n\n"
            + "Запрашиваемое решение: согласовать способ закупки, запросить обоснование или отклонить заявку.\n"
        )

    return (
        header
        + "Кому: заявителю и закупщику\n"
        + f"Тема: Заявка {request.request_id} принята в обработку\n\n"
        + "Заявка заполнена достаточно для создания карточки. "
        + "Закупка не запускается автоматически: карточку проверяет человек.\n\n"
        + summary
        + "\nПроверки:\n" + problem_text + "\n"
    )
