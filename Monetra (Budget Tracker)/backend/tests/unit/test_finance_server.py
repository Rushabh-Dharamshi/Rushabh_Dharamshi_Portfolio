import importlib
from types import SimpleNamespace

import pytest

from budget_tracker_api.errors import ValidationError


class StubAnalyticsService:
    def dashboard(self):
        return {"monthly_budget": 1050.0}

    def financial_pulse(self):
        return {"health_score": 80}

    def category_insights(self):
        return {"top_categories": []}


class StubPredictionService:
    def __init__(self, error=False):
        self.error = error

    def predict_next_month(self):
        if self.error:
            raise ValidationError("No expense data available.")
        return {"predicted_spending": 900.0}


class StubSettingsService:
    def update_monthly_budget(self, payload):
        return {"monthly_budget": float(payload["monthly_budget"])}

    def update_monthly_income(self, payload):
        return {"monthly_income": float(payload["monthly_income"]), "income_month": payload.get("month")}

    def get_monthly_income(self):
        return 1500.0

    def get_monthly_budget(self):
        return 1050.0


class StubExpenseService:
    def __init__(self):
        self.updated = None
        self.deleted = []

    def list_expenses(self, sort_direction="desc"):
        return [
            {"id": 3, "date": "2026-04-01", "category": "Travel", "description": "Tube fare", "amount": 6.4, "entry_type": "expense"},
            {"id": 4, "date": "2026-04-01", "category": "Travel", "description": "Tube fare duplicate", "amount": 6.4, "entry_type": "expense"},
        ]

    def create_expense(self, payload):
        return {"id": 5, **payload}

    def update_expense(self, expense_id, payload):
        self.updated = (expense_id, payload)
        return {"id": expense_id, "date": "2026-04-01", **payload}

    def delete_expense(self, expense_id):
        self.deleted.append(expense_id)


class StubRecurringService:
    def __init__(self):
        self.updated = None
        self.deleted = []

    def list_items(self):
        return [
            {"id": 10, "category": "Housing", "description": "Rent", "amount": 700.0, "entry_type": "expense", "frequency": "monthly", "start_date": "2026-04-01", "end_date": "2026-06-01", "active": True},
            {"id": 11, "category": "Housing", "description": "Rent copy", "amount": 700.0, "entry_type": "expense", "frequency": "monthly", "start_date": "2026-04-01", "end_date": "2026-06-01", "active": True},
        ]

    def upcoming_calendar(self, days):
        return {"days": days, "occurrences": [{"description": "Rent"}]}

    def create_item(self, payload):
        return {"id": 12, **payload}

    def update_item(self, item_id, payload):
        merged = {**self.list_items()[0], **payload}
        self.updated = (item_id, merged)
        return {"id": item_id, **merged}
    def delete_item(self, item_id):
        self.deleted.append(item_id)


class StubReportService:
    def generate_monthly_report(self):
        return "report.pdf"


class StubAutomationService:
    def run_upcoming_bills_email_now(self):
        return {"headline": "Upcoming"}

    def run_month_end_email_now(self):
        return {"headline": "Month end"}


def test_finance_server_get_app_initializes_lazily(monkeypatch):
    module = importlib.import_module("budget_tracker_api.mcp.finance_server")
    created = []

    class StubContext:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    stub_app = SimpleNamespace(
        extensions={"services": {}},
        app_context=lambda: StubContext(),
    )

    monkeypatch.setattr(module, "_app", None)
    monkeypatch.setattr(module, "create_app", lambda config: created.append(config) or stub_app)

    assert module._get_app() is stub_app
    assert created == [{"AUTOMATION_SCHEDULER_ENABLED": False}]


@pytest.fixture()
def finance_server(monkeypatch):
    module = importlib.import_module("budget_tracker_api.mcp.finance_server")
    services = {
        "analytics_service": StubAnalyticsService(),
        "prediction_service": StubPredictionService(),
        "settings_service": StubSettingsService(),
        "expense_service": StubExpenseService(),
        "recurring_service": StubRecurringService(),
        "report_service": StubReportService(),
        "automation_service": StubAutomationService(),
    }
    monkeypatch.setattr(module, "_app", SimpleNamespace(extensions={"services": services}, app_context=lambda: type("C", (), {"__enter__": lambda s: None, "__exit__": lambda s, *args: False})()))
    return module, services


def test_finance_server_tools_cover_success_paths(finance_server, monkeypatch):
    module, services = finance_server

    assert module.get_dashboard_summary() == {"monthly_budget": 1050.0}
    assert module.get_financial_pulse() == {"health_score": 80}
    assert module.get_category_insights() == {"top_categories": []}
    assert module.get_spending_prediction() == {"predicted_spending": 900.0}
    assert module.get_recent_transactions(99)["transactions"] == services["expense_service"].list_expenses()[:15]
    assert module.list_recurring_reminders()["items"][0]["description"] == "Rent"
    assert module.get_upcoming_recurring_items(90)["days"] == 60
    assert module.set_monthly_budget(1200.25)["action_result"]["payload"]["monthly_income"] == 1500.0
    assert module.set_monthly_income(2400.5, "2026-04")["action_result"]["payload"]["monthly_budget"] == 1050.0
    assert module.create_transaction("2026-04-01", "Travel", "Tube fare", 6.4)["action_result"]["payload"]["description"] == "Tube fare"
    assert module.generate_monthly_report() == {"available": True, "download_url": "/api/reports/monthly"}
    assert module.send_upcoming_bills_email_now()["headline"] == "Upcoming"
    assert module.send_month_end_email_now()["headline"] == "Month end"

    updated = module.update_transaction_by_match(
        {"description": "Tube fare", "category": "Travel", "amount": 6.4, "date": "2026-04-01", "entry_type": "expense"},
        {"description": "Tube fare adjusted", "amount": 7.4},
    )
    assert updated["action_result"]["payload"]["description"] == "Tube fare adjusted"
    assert services["expense_service"].updated[0] == 3
    assert services["expense_service"].deleted == [4]

    deleted = module.delete_transaction_by_match({"description": "Tube fare", "entry_type": "expense"})
    assert deleted["action_result"]["message"] == "Deleted 2 matching transaction(s)."

    created_reminder = module.create_recurring_reminder(
        "Housing", "Rent", 700.0, "expense", "monthly", "2026-04-01", "2026-06-01", True
    )
    assert created_reminder["action_result"]["recurring_item"]["description"] == "Rent"

    updated_reminder = module.update_recurring_reminder_by_match(
        {"description": "Rent", "category": "Housing", "amount": 700.0, "entry_type": "expense", "frequency": "monthly", "start_date": "2026-04-01", "end_date": "2026-06-01"},
        {"description": "Updated rent", "amount": 710.0},
    )
    assert updated_reminder["action_result"]["recurring_item"]["description"] == "Updated rent"
    assert services["recurring_service"].updated[0] == 10
    assert services["recurring_service"].deleted == [11]

    deleted_reminder = module.delete_recurring_reminder_by_match({"description": "Rent", "entry_type": "expense"})
    assert deleted_reminder["action_result"]["message"] == "Deleted 2 matching recurring reminder(s)."

    services["recurring_service"].deleted.clear()
    replaced = module.replace_recurring_reminder(
        {"description": "Rent", "entry_type": "expense"},
        {"category": "Housing", "description": "New rent", "amount": 715.0, "entry_type": "expense", "frequency": "monthly", "start_date": "2026-05-01", "active": True},
    )
    assert replaced["action_result"]["recurring_item"]["description"] == "New rent"
    assert services["recurring_service"].deleted == [10, 11]

    monkeypatch.setattr(module, "_with_app_context", lambda handler: handler({"prediction_service": StubPredictionService(error=True)}))
    assert module.get_spending_prediction() == {"error": "No expense data available."}


def test_finance_server_match_failures_raise_validation(finance_server):
    module, _ = finance_server

    with pytest.raises(ValidationError, match="No matching transaction was found to update."):
        module.update_transaction_by_match({"description": "missing"}, {"amount": 1})
    with pytest.raises(ValidationError, match="No matching transaction was found to delete."):
        module.delete_transaction_by_match({"description": "missing"})
    with pytest.raises(ValidationError, match="No matching recurring reminder was found to update."):
        module.update_recurring_reminder_by_match({"description": "missing"}, {"amount": 1})
    with pytest.raises(ValidationError, match="No matching recurring reminder was found to delete."):
        module.delete_recurring_reminder_by_match({"description": "missing"})
    with pytest.raises(ValidationError, match="No matching recurring reminder was found to replace."):
        module.replace_recurring_reminder({"description": "missing"}, {"description": "new"})



