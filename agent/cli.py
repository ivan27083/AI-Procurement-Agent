"""CLI прототипа агента первичной обработки заявок на закупку."""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

from .agent import ProcurementAgent
from .schema import AgentResult, PurchaseRequest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "requests.json"
OUT_DIR = ROOT / "demo_output"

STATUS_MARK = {"pass": "[OK]", "warn": "[!]", "fail": "[X]"}
ROUTE_COLOR = {
    "auto_approve": "AUTO",
    "clarify": "CLARIFY",
    "procurement_review": "REVIEW",
    "manager_approval": "MANAGER",
}


def wrap(text: str, width: int = 76, prefix: str = "") -> list[str]:
    lines = []
    for chunk in str(text).splitlines() or [""]:
        wrapped = textwrap.wrap(chunk, width=width) or [""]
        lines.extend(prefix + line for line in wrapped)
    return lines


def format_result(result: AgentResult, show_draft: bool = True) -> str:
    width = 82
    out: list[str] = []
    out.append("╭" + "─" * (width - 2) + "╮")
    title = f" {result.request_id}  |  {ROUTE_COLOR.get(result.route, result.route)} "
    out.append("│" + title.ljust(width - 2) + "│")
    out.append("├" + "─" * (width - 2) + "┤")

    def row(text: str = "") -> None:
        for line in wrap(text, width - 4):
            out.append("│ " + line.ljust(width - 4) + " │")

    row(f"Категория: {result.category}  (уверенность {result.category_confidence:.0%})")
    amount = result.extracted.get("amount")
    amount_text = f"{float(amount):,.0f} ₽".replace(",", " ") if amount else "не указана"
    row(f"Сумма: {amount_text}   |   Полнота: {result.completeness:.0%}   |   Риск: {result.risk_score}/100")
    row(f"Маршрут: {result.route_label}")
    if result.missing_fields:
        row("Не хватает: " + ", ".join(result.missing_fields))
    if result.duplicate.is_duplicate or result.duplicate.is_possible:
        row(
            f"Дубликат: {result.duplicate.request_id} "
            f"(сходство {result.duplicate.similarity:.0%}, {result.duplicate.reason})"
        )

    row("")
    row("Проверки:")
    for check in result.policy_checks:
        if check.status == "pass":
            continue
        row(f"  {STATUS_MARK[check.status]} {check.title}: {check.detail}")
    if all(c.status == "pass" for c in result.policy_checks):
        row("  [OK] Критичных замечаний нет")

    row("")
    row("Риск-факторы:")
    if result.risk_factors:
        for factor in result.risk_factors:
            row(f"  - {factor}")
    else:
        row("  - существенных факторов нет")

    row("")
    row("Следующие шаги:")
    for step in result.next_steps:
        row(f"  - {step}")

    if show_draft:
        row("")
        row("Черновик сообщения (первые строки):")
        draft_lines = result.draft_message.splitlines()
        for line in draft_lines[:12]:
            row("  " + line)
        if len(draft_lines) > 12:
            row("  ...")

    row("")
    row(f"Аудит: {result.audit_id}   |   Внешние действия: запрещены без подтверждения")
    out.append("╰" + "─" * (width - 2) + "╯")
    return "\n".join(out)


def load_requests(path: Path) -> list[PurchaseRequest]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [PurchaseRequest(**item) for item in data]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="AI-агент первичной обработки заявок на закупку")
    parser.add_argument("--demo", action="store_true", help="Запустить демонстрационный набор")
    parser.add_argument("--file", help="JSON-файл со списком заявок")
    parser.add_argument("--text", help="Текст одной заявки")
    parser.add_argument("--id", default="REQ-CLI-001", help="Идентификатор заявки для --text")
    parser.add_argument("--json", action="store_true", help="Вывести результат в JSON")
    parser.add_argument("--confirm-send", action="store_true", help="Подтвердить внешнее действие (в прототипе только логируется)")
    args = parser.parse_args()

    if not (args.demo or args.file or args.text):
        parser.print_help()
        return

    agent = ProcurementAgent()

    if args.text:
        requests = [PurchaseRequest(request_id=args.id, text=args.text)]
    else:
        path = EXAMPLES if args.demo else Path(args.file)
        requests = load_requests(path)

    results = agent.process_batch(requests)

    if args.json:
        print(json.dumps([r.as_dict() for r in results], ensure_ascii=False, indent=2))
        return

    blocks = []
    for result in results:
        block = format_result(result)
        print(block)
        print()
        blocks.append(block)

    if args.confirm_send:
        print("ВНЕШНЕЕ ДЕЙСТВИЕ ПОДТВЕРЖДЕНО ПОЛЬЗОВАТЕЛЕМ.")
        print("Прототип не отправляет письма: подтверждение записано в аудит-лог.")
    else:
        print("Внешние действия не выполнялись. Все сообщения — черновики.")

    if args.demo:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "demo_console.txt").write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
        (OUT_DIR / "demo_results.json").write_text(
            json.dumps([r.as_dict() for r in results], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nСохранено: {OUT_DIR / 'demo_console.txt'}")
        print(f"Сохранено: {OUT_DIR / 'demo_results.json'}")


if __name__ == "__main__":
    main()
