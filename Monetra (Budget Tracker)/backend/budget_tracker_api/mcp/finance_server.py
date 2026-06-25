from __future__ import annotations

from fastmcp import FastMCP
import re

from budget_tracker_api import create_app
from budget_tracker_api.errors import ValidationError


_app = None
mcp = FastMCP(
    "Monetra Finance MCP Server",
    instructions=(
        "Provides finance tools for the Monetra budgeting system, including dashboard analytics, "
        "transaction CRUD, recurring reminder CRUD, report generation, and manual email dispatch."
    ),
)


def _get_app():
    global _app
    if _app is None:
        _app = create_app({"AUTOMATION_SCHEDULER_ENABLED": False})
    return _app


def _services() -> dict:
    return _get_app().extensions["services"]


def _with_app_context(handler):
    with _get_app().app_context():
        return handler(_services())


@mcp.tool
def get_dashboard_summary() -> dict:
    return _with_app_context(lambda services: services["analytics_service"].dashboard())


@mcp.tool
def get_financial_pulse() -> dict:
    return _with_app_context(lambda services: services["analytics_service"].financial_pulse())


@mcp.tool
def get_category_insights() -> dict:
    return _with_app_context(lambda services: services["analytics_service"].category_insights())


@mcp.tool
def get_spending_prediction() -> dict:
    def _handler(services):
        try:
            return services["prediction_service"].predict_next_month()
        except ValidationError as exc:
            return {"error": exc.message}

    return _with_app_context(_handler)


@mcp.tool
def get_recent_transactions(limit: int = 8) -> dict:
    return _with_app_context(
        lambda services: {"transactions": services["expense_service"].list_expenses()[: max(1, min(limit, 15))]}
    )


@mcp.tool
def retrieve_finance_context(question: str, top_k: int = 6) -> dict:
    return _with_app_context(lambda services: services["rag_service"].retrieve_context(question, top_k=top_k))


@mcp.tool
def list_recurring_reminders() -> dict:
    return _with_app_context(lambda services: {"items": services["recurring_service"].list_items()})


@mcp.tool
def get_upcoming_recurring_items(days: int = 21) -> dict:
    bounded_days = max(1, min(days, 60))
    return _with_app_context(lambda services: services["recurring_service"].upcoming_calendar(bounded_days))


@mcp.tool
def set_monthly_budget(monthly_budget: float, month: str | None = None) -> dict:
    def _handler(services):
        result = services["settings_service"].update_monthly_budget({"monthly_budget": monthly_budget, "month": month})
        budget_month = result.get("budget_month")
        return {
            "headline": "Monthly budget updated",
            "summary": f"Monthly budget for {budget_month} is now GBP {float(result['monthly_budget']):.2f}.",
            "action_result": {
                "type": "monthly_budget_updated",
                "message": "Monthly budget updated successfully.",
                "payload": {
                    "monthly_budget": float(result["monthly_budget"]),
                    "budget_month": budget_month,
                    "monthly_income": services["settings_service"].get_monthly_income(budget_month),
                },
            },
        }

    return _with_app_context(_handler)


@mcp.tool
def set_monthly_income(monthly_income: float, month: str | None = None) -> dict:
    def _handler(services):
        result = services["settings_service"].update_monthly_income({"monthly_income": monthly_income, "month": month})
        return {
            "headline": "Monthly income updated",
            "summary": f"Monthly income for {result.get('income_month')} is now GBP {float(result['monthly_income']):.2f}.",
            "action_result": {
                "type": "monthly_income_updated",
                "message": "Monthly income updated successfully.",
                "payload": {
                    "monthly_income": float(result["monthly_income"]),
                    "income_month": result.get("income_month"),
                    "monthly_budget": services["settings_service"].get_monthly_budget(result.get("income_month")),
                },
            },
        }

    return _with_app_context(_handler)


@mcp.tool
def create_transaction(date: str, category: str, description: str, amount: float, entry_type: str = "expense") -> dict:
    def _handler(services):
        created = services["expense_service"].create_expense(
            {
                "date": date,
                "category": category,
                "description": description,
                "amount": amount,
                "entry_type": "expense",
            }
        )
        return {
            "headline": "Expense created",
            "summary": f"Created expense '{created['description']}' for GBP {float(created['amount']):.2f} on {created['date']}.",
            "action_result": {
                "type": "expense_created",
                "message": "Expense created successfully.",
                "payload": created,
            },
        }

    return _with_app_context(_handler)


def _match_expenses(services, criteria: dict) -> list[dict]:
    expenses = services["expense_service"].list_expenses("desc")
    normalized_description = str(criteria.get("description") or "").strip().lower()
    normalized_category = str(criteria.get("category") or "").strip().lower()
    normalized_entry_type = str(criteria.get("entry_type") or "").strip().lower()
    normalized_date = str(criteria.get("date") or "").strip()
    normalized_amount = criteria.get("amount")

    matches = []
    for expense in expenses:
        if normalized_description and normalized_description not in expense["description"].strip().lower():
            continue
        if normalized_category and normalized_category not in expense["category"].strip().lower():
            continue
        if normalized_entry_type and normalized_entry_type != expense["entry_type"]:
            continue
        if normalized_date and normalized_date != expense["date"]:
            continue
        if normalized_amount not in (None, "") and abs(float(expense["amount"]) - float(normalized_amount)) >= 0.01:
            continue
        matches.append(expense)
    return matches


def _normalize_text_match(value: object) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _text_matches(needle: object, haystack: object) -> bool:
    normalized_needle = _normalize_text_match(needle)
    if not normalized_needle:
        return True
    normalized_haystack = _normalize_text_match(haystack)
    needle_tokens = set(normalized_needle.split())
    haystack_tokens = set(normalized_haystack.split())
    plan_tokens = {"plus", "pro", "free"}
    required_plan_tokens = needle_tokens & plan_tokens
    if required_plan_tokens and not required_plan_tokens.issubset(haystack_tokens):
        return False
    compact_needle = normalized_needle.replace(" ", "")
    compact_haystack = normalized_haystack.replace(" ", "")
    return (
        needle_tokens.issubset(haystack_tokens)
        or haystack_tokens.issubset(needle_tokens)
        or
        normalized_needle in normalized_haystack
        or normalized_haystack in normalized_needle
        or compact_needle in compact_haystack
        or compact_haystack in compact_needle
    )


@mcp.tool
def update_transaction_by_match(target: dict, entity: dict) -> dict:
    def _handler(services):
        matches = _match_expenses(services, target)
        if not matches:
            raise ValidationError("No matching transaction was found to update.")
        primary = sorted(matches, key=lambda item: item["id"])[0]
        updated = services["expense_service"].update_expense(int(primary["id"]), entity)
        for duplicate in matches[1:]:
            services["expense_service"].delete_expense(int(duplicate["id"]))
        return {
            "headline": "Transaction updated",
            "summary": f"Updated transaction '{updated['description']}' to GBP {float(updated['amount']):.2f} on {updated['date']}.",
            "action_result": {
                "type": "expense_updated",
                "message": "Transaction updated successfully.",
                "payload": updated,
            },
        }

    return _with_app_context(_handler)


@mcp.tool
def delete_transaction_by_match(target: dict) -> dict:
    def _handler(services):
        matches = _match_expenses(services, target)
        if not matches:
            raise ValidationError("No matching transaction was found to delete.")
        for expense in matches:
            services["expense_service"].delete_expense(int(expense["id"]))
        return {
            "headline": "Transaction deleted",
            "summary": f"Deleted {len(matches)} transaction(s) matching {matches[0]['description']}.",
            "action_result": {
                "type": "expense_deleted",
                "message": f"Deleted {len(matches)} matching transaction(s).",
                "payload": matches[0],
            },
        }

    return _with_app_context(_handler)


def _match_recurring(services, criteria: dict) -> list[dict]:
    items = services["recurring_service"].list_items()
    description = criteria.get("description")
    category = criteria.get("category")
    identity_text = " ".join(
        part for part in (str(description or "").strip(), str(category or "").strip()) if part
    )
    normalized_entry_type = str(criteria.get("entry_type") or "").strip().lower()
    normalized_frequency = str(criteria.get("frequency") or "").strip().lower()
    normalized_start_date = str(criteria.get("start_date") or "").strip()
    normalized_end_date = str(criteria.get("end_date") or "").strip()
    normalized_amount = criteria.get("amount")
    has_text_identity = bool(_normalize_text_match(description) or _normalize_text_match(category))

    matches = []
    for item in items:
        item_identity_text = f"{item['description']} {item['category']}"
        if identity_text and not _text_matches(identity_text, item_identity_text):
            continue
        if normalized_entry_type and normalized_entry_type != item["entry_type"]:
            continue
        if normalized_frequency and normalized_frequency != item["frequency"]:
            continue
        if normalized_start_date and normalized_start_date != item["start_date"]:
            continue
        if normalized_end_date and normalized_end_date != str(item.get("end_date") or ""):
            continue
        if (
            not has_text_identity
            and normalized_amount not in (None, "")
            and abs(float(item["amount"]) - float(normalized_amount)) >= 0.01
        ):
            continue
        matches.append(item)
    return matches


@mcp.tool
def create_recurring_reminder(
    category: str,
    description: str,
    amount: float,
    entry_type: str,
    frequency: str,
    start_date: str,
    end_date: str | None = None,
    active: bool = True,
) -> dict:
    def _handler(services):
        payload = {
            "category": category,
            "description": description,
            "amount": amount,
            "entry_type": entry_type,
            "frequency": frequency,
            "start_date": start_date,
            "end_date": end_date,
            "active": active,
        }
        matches = _match_recurring(
            services,
            {
                "category": category,
                "description": description,
                "entry_type": entry_type,
                "frequency": frequency,
            },
        )
        if matches:
            primary = sorted(matches, key=lambda item: item["id"])[0]
            updated = services["recurring_service"].update_item(primary["id"], payload)
            for duplicate in matches[1:]:
                services["recurring_service"].delete_item(duplicate["id"])
            return {
                "headline": "Recurring reminder updated",
                "summary": f"{updated['description']} is now scheduled as a {updated['frequency']} {updated['entry_type']} reminder starting {updated['start_date']}.",
                "action_result": {
                    "type": "recurring_item_updated",
                    "message": "An existing similar reminder was updated instead of creating a duplicate.",
                    "recurring_item": updated,
                },
            }

        created = services["recurring_service"].create_item(payload)
        return {
            "headline": "Recurring reminder created",
            "summary": f"{created['description']} is now scheduled as a {created['frequency']} {created['entry_type']} reminder starting {created['start_date']}.",
            "action_result": {
                "type": "recurring_item_created",
                "message": "The reminder was created automatically from your prompt.",
                "recurring_item": created,
            },
        }

    return _with_app_context(_handler)


@mcp.tool
def update_recurring_reminder_by_match(target: dict, reminder: dict) -> dict:
    def _handler(services):
        matches = _match_recurring(services, target)
        if not matches:
            raise ValidationError("No matching recurring reminder was found to update.")
        primary = sorted(matches, key=lambda item: item["id"])[0]
        updated = services["recurring_service"].update_item(primary["id"], reminder)
        for duplicate in matches[1:]:
            services["recurring_service"].delete_item(duplicate["id"])
        return {
            "headline": "Recurring reminder updated",
            "summary": f"{updated['description']} is now scheduled as a {updated['frequency']} {updated['entry_type']} reminder starting {updated['start_date']}.",
            "action_result": {
                "type": "recurring_item_updated",
                "message": "The existing recurring reminder was updated automatically.",
                "recurring_item": updated,
            },
        }

    return _with_app_context(_handler)


@mcp.tool
def delete_recurring_reminder_by_match(target: dict) -> dict:
    def _handler(services):
        matches = _match_recurring(services, target)
        if not matches:
            raise ValidationError("No matching recurring reminder was found to delete.")
        for item in matches:
            services["recurring_service"].delete_item(item["id"])
        return {
            "headline": "Recurring reminder deleted",
            "summary": f"Removed {len(matches)} recurring reminder(s) matching {matches[0]['description']}.",
            "action_result": {
                "type": "recurring_item_deleted",
                "message": f"Deleted {len(matches)} matching recurring reminder(s).",
                "recurring_item": matches[0],
            },
        }

    return _with_app_context(_handler)


@mcp.tool
def replace_recurring_reminder(target: dict, reminder: dict) -> dict:
    def _handler(services):
        matches = _match_recurring(services, target)
        if not matches:
            raise ValidationError("No matching recurring reminder was found to replace.")
        for item in matches:
            services["recurring_service"].delete_item(item["id"])
        created = services["recurring_service"].create_item(reminder)
        return {
            "headline": "Recurring reminder replaced",
            "summary": f"Replaced {len(matches)} recurring reminder(s) with {created['description']} starting {created['start_date']}.",
            "action_result": {
                "type": "recurring_item_replaced",
                "message": f"Replaced {len(matches)} matching recurring reminder(s).",
                "recurring_item": created,
            },
        }

    return _with_app_context(_handler)


@mcp.tool
def generate_monthly_report() -> dict:
    def _handler(services):
        services["report_service"].generate_monthly_report()
        return {"available": True, "download_url": "/api/reports/monthly"}

    return _with_app_context(_handler)


@mcp.tool
def send_upcoming_bills_email_now() -> dict:
    return _with_app_context(lambda services: services["automation_service"].run_upcoming_bills_email_now())


@mcp.tool
def send_all_upcoming_bills_email_now() -> dict:
    return _with_app_context(lambda services: services["automation_service"].run_all_upcoming_bills_email_now())


@mcp.tool
def send_month_end_email_now() -> dict:
    return _with_app_context(lambda services: services["automation_service"].run_month_end_email_now())


if __name__ == "__main__":
    mcp.run(transport="stdio")



