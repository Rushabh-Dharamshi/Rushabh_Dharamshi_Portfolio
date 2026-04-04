from flask import Flask
import pytest

from budget_tracker_api.errors import ValidationError
from budget_tracker_api.services.agent_service import AgentService


class StubOllamaClient:
    def __init__(self, content='{"headline":"ok","summary":"done","risk_level":"low","recommended_actions":[],"email_subject":"ok","email_draft":"ok"}'):
        self.model = "qwen:latest"
        self.base_url = "http://ollama"
        self._content = content

    def chat(self, messages, tools=None):
        return {"message": {"role": "assistant", "content": self._content}}


class StubAnalyticsService:
    def dashboard(self):
        return {"month_label": "March 2026", "monthly_budget": 1000, "monthly_income": 1500, "monthly_expenses": 450, "net_cash_flow": 1050, "remaining_budget": 550, "status": "within"}

    def financial_pulse(self):
        return {"health_score": 82, "spend_velocity": 14, "runway_days": 18, "cash_in": 1500, "cash_out": 450, "income_coverage": 333, "narrative": "steady"}

    def category_insights(self):
        return {"top_categories": [{"category": "Food", "amount": 100}], "bottom_categories": [], "total_spending": 450}


class StubPredictionService:
    def __init__(self, fail=False):
        self.fail = fail

    def predict_next_month(self):
        if self.fail:
            raise ValidationError("No data")
        return {"predicted_spending": 900}


class StubRecurringService:
    def __init__(self):
        self.items = [
            {"id": 1, "category": "Utilities", "description": "Utility Bills", "amount": 20.0, "entry_type": "expense", "frequency": "weekly", "start_date": "2026-03-16", "end_date": None, "active": True},
            {"id": 2, "category": "Utilities", "description": "Utility Bills", "amount": 20.0, "entry_type": "expense", "frequency": "weekly", "start_date": "2026-03-16", "end_date": None, "active": True},
        ]
        self.deleted = []
        self.updated = []
        self.created = []

    def list_items(self):
        return list(self.items)

    def create_item(self, payload):
        self.created.append(payload)
        return {"id": 99, **payload}

    def update_item(self, item_id, payload):
        self.updated.append((item_id, payload))
        return {"id": item_id, **payload}

    def delete_item(self, item_id):
        self.deleted.append(item_id)

    def upcoming_calendar(self, days):
        return {"window_start": "2026-03-01", "window_end": "2026-03-21", "occurrences": [{"description": "Rent"}], "days": days}


class StubReportService:
    def __init__(self):
        self.called = 0

    def generate_monthly_report(self):
        self.called += 1
        return "report.pdf"


class StubExpenseService:
    def __init__(self):
        self.expenses = [
            {"id": 1, "date": "2026-03-20", "category": "Travel", "description": "Train pass", "amount": 80.0, "entry_type": "expense"},
            {"id": 2, "date": "2026-03-21", "category": "Travel", "description": "Train pass", "amount": 80.0, "entry_type": "expense"},
        ]
        self.created = []
        self.updated = []
        self.deleted = []

    def list_expenses(self, sort_direction="desc"):
        return list(self.expenses)

    def create_expense(self, payload):
        self.created.append(payload)
        return {"id": 10, **payload}

    def update_expense(self, expense_id, payload):
        self.updated.append((expense_id, payload))
        return {"id": expense_id, **payload}

    def delete_expense(self, expense_id):
        self.deleted.append(expense_id)


class StubSettingsService:
    def __init__(self):
        self.budget = 1000.0
        self.income = 1500.0

    def update_monthly_budget(self, payload):
        self.budget = float(payload["monthly_budget"])
        return {"monthly_budget": self.budget}

    def update_monthly_income(self, payload):
        self.income = float(payload["monthly_income"])
        return {"monthly_income": self.income, "income_month": payload.get("month") or "2026-03"}

    def get_monthly_budget(self):
        return self.budget

    def get_monthly_income(self):
        return self.income


class StubRepository:
    def __init__(self):
        self.runs = []

    def create_run(self, payload):
        run = {"id": len(self.runs) + 1, **payload}
        self.runs.append(run)
        return run

    def list_runs(self, limit):
        return self.runs[:limit]


class StubRuntime:
    def __init__(self, available=True, result=None, error=None):
        self._available = available
        self._result = result
        self._error = error

    def is_available(self):
        return self._available

    def run(self, task):
        if self._error:
            raise self._error
        return self._result


def build_service(ollama=None, prediction=None, recurring=None, report=None, expense=None, settings=None):
    return AgentService(
        ollama or StubOllamaClient(),
        StubAnalyticsService(),
        prediction or StubPredictionService(),
        recurring or StubRecurringService(),
        report or StubReportService(),
        expense or StubExpenseService(),
        settings or StubSettingsService(),
        StubRepository(),
    )


def test_agent_service_runtime_fallback_and_action_helpers(monkeypatch):
    service = build_service()
    service._agentic_command_runtime = StubRuntime(available=True, error=RuntimeError("primary"))
    service._fallback_agentic_command_runtime = StubRuntime(available=True, result={"headline": "fallback"})
    assert service._run_manual_action_command("set budget") == {"headline": "fallback"}

    service._agentic_command_runtime = StubRuntime(available=True, error=RuntimeError("primary"))
    service._fallback_agentic_command_runtime = StubRuntime(available=True, error=RuntimeError("fallback"))
    monkeypatch.setattr(service, "_run_manual_action_command_legacy", lambda task: {"headline": "legacy"})
    assert service._run_manual_action_command("set budget")["headline"] == "legacy"

    settings_result = service._run_settings_command("set budget", {"setting_key": "monthly_budget", "value": 1200})
    income_result = service._run_settings_command("set income", {"setting_key": "monthly_income", "value": 2400, "month": "2026-04"})
    assert settings_result["action_result"]["type"] == "monthly_budget_updated"
    assert income_result["action_result"]["payload"]["income_month"] == "2026-04"
    with pytest.raises(ValidationError):
        service._run_settings_command("bad", {"setting_key": "other", "value": 1})

    created = service._run_expense_command("create expense", {"operation": "create", "entity": {"date": "2026-03-22", "category": "Travel", "description": "Tube", "amount": 6.4, "entry_type": "expense"}, "target": {}})
    updated = service._run_expense_command("update expense", {"operation": "update", "entity": {"date": "2026-03-20", "category": "Travel", "description": "Train pass", "amount": 81.0, "entry_type": "expense"}, "target": {"description": "Train pass", "category": "Travel"}})
    deleted = service._run_expense_command("delete expense", {"operation": "delete", "entity": {}, "target": {"description": "Train pass", "category": "Travel"}})
    assert created["headline"] == "Transaction created"
    assert updated["headline"] == "Transaction updated"
    assert deleted["headline"] == "Transaction deleted"
    with pytest.raises(ValidationError):
        service._delete_matching_expenses({"description": "missing"})
    with pytest.raises(ValidationError):
        service._update_matching_expense({"description": "missing"}, {"amount": 10})


def test_agent_service_parsing_and_recurring_helpers(monkeypatch):
    service = build_service(ollama=StubOllamaClient('{"domain":"unknown","operation":"noop","setting_key":"monthly_budget","value":1500}'))
    parsed = service._parse_manual_action_command("set my monthly budget to 1500 pounds")
    assert parsed["domain"] == "settings"
    assert parsed["operation"] == "create"
    assert service._infer_recurring_target_from_task("replace weekly utility bills with monthly utility bills", {"description": "Utility Bills", "entry_type": "expense"})["frequency"] == "weekly"
    assert service._normalize_text_match("Utility Bills!!!") == "utility bills"

    assert service._parse_final_payload("plain text summary")["summary"] == "plain text summary"
    assert service._parse_final_payload('{"recommended_actions":["a","b"]}')["recommended_actions"] == ["ab"]
    assert service._normalize_recommended_actions(["Review", " plan "]) == ["Review", "plan"]
    assert service._normalize_recommended_actions("Call landlord") == ["Call landlord"]

    reminder = service._parse_reminder_payload({"category": "Bills", "description": "Water", "amount": 12, "entry_type": "expense", "frequency": "monthly"}, "2026-04-01")
    assert reminder["start_date"] == "2026-04-01"
    with pytest.raises(ValidationError):
        service._parse_reminder_payload("bad", "2026-04-01")
    with pytest.raises(ValidationError):
        service._parse_reminder_payload({}, "2026-04-01")

    recurring = service._run_reminder_command("replace weekly utility bills with monthly utility bills of 24.51 pounds on the 23rd of each month.", {
        "operation": "replace",
        "target": {"description": "Utility Bills", "category": "Utilities", "entry_type": "expense", "frequency": "weekly"},
        "reminder": {"category": "Utilities", "description": "Utility Bills", "amount": 24.51, "entry_type": "expense", "frequency": "monthly", "start_date": "2026-03-23", "end_date": None, "active": True},
    })
    assert recurring["action_result"]["type"] == "recurring_item_replaced"
    assert service._find_matching_reminders({"description": "Utility Bills", "category": "Utilities", "entry_type": "expense", "frequency": "weekly"})
    with pytest.raises(ValidationError):
        service._delete_matching_reminders({"description": "Missing"})
    with pytest.raises(ValidationError):
        service._update_matching_reminder({"description": "Missing"}, {"amount": 1})

    created, action_type, _ = service._upsert_matching_reminder({"category": "Subscriptions", "description": "Gym", "amount": 30.0, "entry_type": "expense", "frequency": "monthly", "start_date": "2026-04-01", "end_date": None, "active": True})
    assert action_type == "recurring_item_created"
    updated, action_type, _ = service._upsert_matching_reminder({"category": "Utilities", "description": "Utility Bills", "amount": 20.0, "entry_type": "expense", "frequency": "weekly", "start_date": "2026-03-16", "end_date": None, "active": True})
    assert action_type == "recurring_item_updated"

    monkeypatch.setattr("budget_tracker_api.services.agent_service.datetime", __import__("datetime").datetime)
    assert service._extract_month_range("from april 2026 to june 2026") == (2026, 4, 2026, 6)
    assert service._extract_day_of_month("on the 23rd of every month") == 23
    assert service._is_end_exclusive("through june 2026 exclusive") is True
    assert service._build_monthly_due_date(2026, 2, 31).isoformat() == "2026-02-28"
    assert service._previous_due_date(__import__("datetime").date(2026, 4, 23), "monthly").isoformat() == "2026-03-23"
    assert service._resolve_start_date_from_task("pay it on 2026-04-23", "2026-04-01") == "2026-04-23"
    assert service._apply_reminder_schedule_from_task("from april 2026 to june 2026 inclusive on the 23rd of every month", {"frequency": "monthly", "start_date": "2026-04-01", "end_date": None}, "2026-04-01")["end_date"] == "2026-06-23"


def test_agent_service_tool_context_and_background_jobs(monkeypatch):
    report = StubReportService()
    service = build_service(ollama=StubOllamaClient('{"headline":"Context","summary":"ok","risk_level":"low","recommended_actions":[],"email_subject":"Context","email_draft":"Context"}'), prediction=StubPredictionService(fail=True), report=report)

    assert service._execute_tool("get_dashboard_summary", {})["monthly_budget"] == 1000
    assert service._execute_tool("get_spending_prediction", {}) == {"error": "No data"}
    assert len(service._execute_tool("get_recent_transactions", {"limit": 99})["transactions"]) == 2
    assert service._execute_tool("get_upcoming_recurring_items", {"days": 99})["days"] == 60
    assert service._execute_tool("generate_monthly_report", {})["available"] is True
    assert service._execute_tool("unknown_tool", {})["error"].startswith("Unknown tool")
    assert service._should_use_context_prompt() is False
    assert service._looks_like_manual_action_command("Add a recurring bill") is True
    assert service._workflow_catalog()["month_end_close"]["label"] == "Month-end close"
    assert any(tool["function"]["name"] == "get_dashboard_summary" for tool in service._tool_definitions())
    workflow_context, automated_actions, tools_used, report_url = service._run_workflow_steps(service._workflow_catalog()["month_end_close"])
    assert "generate_monthly_report" in workflow_context
    assert report_url == "/api/reports/monthly"
    context_result = service._run_context_prompt("Create a report PDF")
    assert context_result["headline"] == "Context"
    assert report.called >= 1

    app = Flask(__name__)
    service._finance_briefing_jobs["job-1"] = {"id": "job-1", "status": "queued", "started_at": None, "completed_at": None, "error": None, "result": None}
    service._workflow_jobs["wf-1"] = {"id": "wf-1", "status": "queued", "workflow_name": "month_end_close", "started_at": None, "completed_at": None, "error": None, "result": None}
    monkeypatch.setattr(service, "run_finance_briefing", lambda payload: {"headline": "done"})
    monkeypatch.setattr(service, "run_workflow", lambda workflow_name, payload: {"workflow_name": workflow_name})
    service._run_finance_briefing_job("job-1", {}, app)
    service._run_workflow_job("wf-1", "month_end_close", {}, app)
    assert service._finance_briefing_jobs["job-1"]["status"] == "completed"
    assert service._workflow_jobs["wf-1"]["status"] == "completed"

    service._finance_briefing_jobs["job-2"] = {"id": "job-2", "status": "queued", "started_at": None, "completed_at": None, "error": None, "result": None}
    service._workflow_jobs["wf-2"] = {"id": "wf-2", "status": "queued", "workflow_name": "month_end_close", "started_at": None, "completed_at": None, "error": None, "result": None}
    monkeypatch.setattr(service, "run_finance_briefing", lambda payload: (_ for _ in ()).throw(ValidationError("brief fail")))
    monkeypatch.setattr(service, "run_workflow", lambda workflow_name, payload: (_ for _ in ()).throw(ValidationError("workflow fail")))
    service._run_finance_briefing_job("job-2", {}, app)
    service._run_workflow_job("wf-2", "month_end_close", {}, app)
    assert service._finance_briefing_jobs["job-2"]["status"] == "failed"
    assert service._workflow_jobs["wf-2"]["status"] == "failed"

