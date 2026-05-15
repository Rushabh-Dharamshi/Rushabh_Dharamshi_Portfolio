import importlib
from datetime import datetime
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from budget_tracker_api import create_app
from budget_tracker_api.security import register_request_guards
from budget_tracker_api.services.automation_service import AutomationService
from tests.unit.test_automation_service import (
    FakeAnalyticsService,
    FakeEmailService,
    FakeRecurringService,
    FakeReportService,
    FakeRunRepository,
)
from tests.unit.test_automation_service_extra import RecordingAgentService


class FakeScheduler:
    def __init__(self, app, poll_seconds):
        self.app = app
        self.poll_seconds = poll_seconds
        self.started = False

    def start(self):
        self.started = True


def test_create_app_starts_scheduler_when_enabled(monkeypatch, tmp_path):
    module = importlib.import_module("budget_tracker_api")
    created = []

    def factory(app, poll_seconds):
        scheduler = FakeScheduler(app, poll_seconds)
        created.append(scheduler)
        return scheduler

    monkeypatch.setattr(module, "AutomationScheduler", factory)
    app = create_app(
        {
            "TESTING": False,
            "LOGIN_REQUIRED": False,
            "AUTOMATION_SCHEDULER_ENABLED": True,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'app.db'}",
            "GENERATED_REPORTS_DIR": tmp_path / "reports",
        }
    )

    assert len(created) == 1
    assert created[0].started is True
    assert app.extensions["automation_scheduler"] is created[0]


def test_create_app_uses_configured_fastmcp_python_executable(monkeypatch, tmp_path):
    module = importlib.import_module("budget_tracker_api")
    created = {}

    class FakeFastMcpClientService:
        def __init__(self, **kwargs):
            created.update(kwargs)

    monkeypatch.setattr(module, "FastMcpClientService", FakeFastMcpClientService)

    create_app(
        {
            "TESTING": True,
            "LOGIN_REQUIRED": False,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'mcp.db'}",
            "GENERATED_REPORTS_DIR": tmp_path / "reports",
            "FASTMCP_PYTHON_EXECUTABLE": "python",
        }
    )

    assert created["python_executable"] == "python"


def test_auth_login_returns_500_when_password_hash_missing(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "LOGIN_REQUIRED": False,
            "AUTH_PASSWORD_HASH": "",
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'auth.db'}",
            "GENERATED_REPORTS_DIR": tmp_path / "reports",
        }
    )
    client = app.test_client()

    response = client.post("/api/auth/login", json={"username": "Rushabh", "password": "secret"})

    assert response.status_code == 500
    assert response.get_json()["error"] == "Application login is not configured."


def test_security_non_api_path_is_not_intercepted():
    from flask import Flask

    app = Flask(__name__)
    app.secret_key = "test"
    app.config.update(
        DEMO_ACCESS_ENABLED=True,
        LOGIN_REQUIRED=True,
        READ_ONLY_MODE=False,
        PUBLIC_HEALTHCHECK_ENABLED=False,
        DEMO_ACCESS_USERNAME="demo",
        DEMO_ACCESS_PASSWORD="secret",
        EXPOSE_ERROR_DETAILS=False,
    )
    register_request_guards(app)
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 404


def test_finance_server_additional_match_paths(monkeypatch):
    module = importlib.import_module("budget_tracker_api.mcp.finance_server")

    class ExpenseService:
        def list_expenses(self, sort_direction="desc"):
            return [
                {"id": 1, "date": "2026-04-01", "category": "Travel", "description": "Tube", "amount": 5.5, "entry_type": "expense"},
                {"id": 2, "date": "2026-04-01", "category": "Salary", "description": "Payroll", "amount": 1000.0, "entry_type": "income"},
            ]

    class RecurringService:
        def list_items(self):
            return [
                {"id": 3, "category": "Housing", "description": "Rent", "amount": 700.0, "entry_type": "expense", "frequency": "monthly", "start_date": "2026-04-01", "end_date": None},
                {"id": 4, "category": "Salary", "description": "Payroll", "amount": 1000.0, "entry_type": "income", "frequency": "monthly", "start_date": "2026-04-01", "end_date": "2026-12-01"},
            ]

    services = {"expense_service": ExpenseService(), "recurring_service": RecurringService()}
    monkeypatch.setattr(module, "_with_app_context", lambda handler: handler(services))
    monkeypatch.setattr(module.mcp, "run", lambda transport="stdio": {"transport": transport})

    assert module._match_expenses(services, {"category": "salary"})[0]["id"] == 2
    assert module._match_expenses(services, {"entry_type": "income"})[0]["id"] == 2
    assert module._match_expenses(services, {"date": "2026-04-01", "amount": 5.5})[0]["id"] == 1
    assert module._match_recurring(services, {"category": "salary"})[0]["id"] == 4
    assert module._match_recurring(services, {"entry_type": "income"})[0]["id"] == 4
    assert module._match_recurring(services, {"frequency": "monthly", "start_date": "2026-04-01", "end_date": "2026-12-01", "amount": 1000.0})[0]["id"] == 4

def test_automation_service_additional_email_branches(monkeypatch):
    repository = FakeRunRepository()
    service = AutomationService(
        RecordingAgentService(),
        FakeReportService(),
        FakeEmailService(),
        repository,
        FakeRecurringService([]),
        FakeAnalyticsService(),
        month_end_email_hour=22,
        month_end_email_minute=15,
    )

    today_prefix = datetime.now().date().isoformat()
    repository.runs = [{"workflow_name": "month_end_close", "generated_at": f"{today_prefix}T09:00:00", "summary": "cached"}]
    runs = service.run_bootstrap_workflows()
    assert runs[0]["workflow_name"] == "month_end_close"

    service._run_bootstrap_background(type("A", (), {"app_context": lambda self: type("C", (), {"__enter__": lambda s: None, "__exit__": lambda s, *args: False})()})(), ["month_end_close"])

    class FakeDateTime:
        @classmethod
        def now(cls):
            from datetime import datetime
            return datetime(2026, 4, 30, 22, 15, 0)

    monkeypatch.setattr(importlib.import_module("budget_tracker_api.services.automation_service"), "datetime", FakeDateTime)
    repository.runs = [{"workflow_name": "month_end_email_dispatch", "generated_at": "2026-04-30T18:00:00"}]
    assert service.run_month_end_email_if_due() is None

    dashboard_negative = {
        "month_label": "April 2026",
        "monthly_budget": 1000.0,
        "current_month_total": 1200.0,
        "monthly_income": 900.0,
        "net_cash_flow": -300.0,
    }
    monkeypatch.setattr(service._analytics_service, "dashboard", lambda: dashboard_negative)
    body = service._compose_month_end_email_body(
        {"summary": "AI summary", "recommended_actions": {"next": "review"}},
        Path("Monthly_Budget_Report_April_2026.pdf"),
    )
    assert "Spending exceeded the monthly budget by GBP 200.00." in body
    assert "Net cash flow for April 2026 was negative at GBP 300.00." in body
    assert "AI summary" in body
    assert "review" in body


def test_upcoming_bills_email_uses_seven_day_window():
    class RecordingRecurringService(FakeRecurringService):
        def __init__(self):
            super().__init__([])
            self.requested_days = None

        def upcoming_calendar(self, days_ahead):
            self.requested_days = days_ahead
            return {
                "occurrences": [
                    {
                        "recurring_item_id": 7,
                        "date": "2026-05-12",
                        "description": "Internet",
                        "amount": 35.0,
                        "entry_type": "expense",
                        "frequency": "monthly",
                        "days_until_due": 7,
                    },
                    {
                        "recurring_item_id": 9,
                        "date": "2026-05-13",
                        "description": "Insurance",
                        "amount": 85.0,
                        "entry_type": "expense",
                        "frequency": "monthly",
                        "days_until_due": 8,
                    },
                    {
                        "recurring_item_id": 8,
                        "date": "2026-05-20",
                        "description": "Salary",
                        "amount": 1500.0,
                        "entry_type": "income",
                        "frequency": "monthly",
                        "days_until_due": 7,
                    },
                ]
            }

    recurring_service = RecordingRecurringService()
    service = AutomationService(
        RecordingAgentService(),
        FakeReportService(),
        FakeEmailService(),
        FakeRunRepository(),
        recurring_service,
        FakeAnalyticsService(),
        month_end_email_hour=22,
        month_end_email_minute=15,
    )

    due_expenses = service._get_due_expenses_within_days(7)

    assert recurring_service.requested_days == 8
    assert [item["description"] for item in due_expenses] == ["Internet"]



