"""Схемы данных агента первичной обработки заявок на закупку."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PurchaseRequest:
    """Входящая заявка: структурированные поля + свободный текст."""

    request_id: str
    text: str
    department: str = ""
    requester: str = ""
    quantity: float | None = None
    unit: str = ""
    unit_price: float | None = None
    amount: float | None = None
    budget_code: str = ""
    urgency: str = ""
    supplier: str = ""
    justification: str = ""
    needed_by: str = ""
    attachments: list[str] = field(default_factory=list)
    source: str = "manual"

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "text": self.text,
            "department": self.department,
            "requester": self.requester,
            "quantity": self.quantity,
            "unit": self.unit,
            "unit_price": self.unit_price,
            "amount": self.amount,
            "budget_code": self.budget_code,
            "urgency": self.urgency,
            "supplier": self.supplier,
            "justification": self.justification,
            "needed_by": self.needed_by,
            "attachments": list(self.attachments),
            "source": self.source,
        }


@dataclass
class PolicyCheck:
    code: str
    status: str  # pass | warn | fail
    title: str
    detail: str
    requires: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "status": self.status,
            "title": self.title,
            "detail": self.detail,
            "requires": self.requires,
        }


@dataclass
class DuplicateMatch:
    is_duplicate: bool
    is_possible: bool
    request_id: str = ""
    similarity: float = 0.0
    amount: float | None = None
    created_at: str = ""
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "is_duplicate": self.is_duplicate,
            "is_possible": self.is_possible,
            "request_id": self.request_id,
            "similarity": round(self.similarity, 3),
            "amount": self.amount,
            "created_at": self.created_at,
            "reason": self.reason,
        }


@dataclass
class AgentResult:
    request_id: str
    extracted: dict[str, Any]
    category: str
    category_confidence: float
    completeness: float
    missing_fields: list[str]
    duplicate: DuplicateMatch
    policy_checks: list[PolicyCheck]
    risk_score: int
    risk_factors: list[str]
    route: str
    route_label: str
    draft_message: str
    next_steps: list[str]
    human_review_required: bool
    external_action_allowed: bool
    audit_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    model_mode: str = "offline-hybrid"

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "model_mode": self.model_mode,
            "audit_id": self.audit_id,
            "extracted": self.extracted,
            "category": self.category,
            "category_confidence": round(self.category_confidence, 4),
            "completeness": round(self.completeness, 3),
            "missing_fields": self.missing_fields,
            "duplicate": self.duplicate.as_dict(),
            "policy_checks": [c.as_dict() for c in self.policy_checks],
            "risk_score": self.risk_score,
            "risk_factors": self.risk_factors,
            "route": self.route,
            "route_label": self.route_label,
            "draft_message": self.draft_message,
            "next_steps": self.next_steps,
            "human_review_required": self.human_review_required,
            "external_action_allowed": self.external_action_allowed,
        }
