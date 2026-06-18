from flask import Flask
import pytest

from budget_tracker_api.errors import ValidationError
from budget_tracker_api.security import current_background_user_id
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
        return {"monthly_budget": self.budget, "budget_month": payload.get("month") or "2026-03"}

    def update_monthly_income(self, payload):
        self.income = float(payload["monthly_income"])
        return {"monthly_income": self.income, "income_month": payload.get("month") or "2026-03"}

    def get_monthly_budget(self, month_key=None):
        return self.budget

    def get_monthly_income(self, month_key=None):
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


def test_agent_service_deletes_expenses_by_inferred_month_and_date_range():
    class DateRangeExpenseService(StubExpenseService):
        def __init__(self):
            super().__init__()
            self.expenses = [
                {"id": 1, "date": "2026-05-18", "category": "Food", "description": "Lunch", "amount": 9.0, "entry_type": "expense"},
                {"id": 2, "date": "2026-05-19", "category": "Travel", "description": "Train", "amount": 12.0, "entry_type": "expense"},
                {"id": 3, "date": "2026-06-05", "category": "Food", "description": "Groceries", "amount": 30.0, "entry_type": "expense"},
                {"id": 4, "date": "2026-06-10", "category": "Salary", "description": "Part-time work", "amount": 200.0, "entry_type": "income"},
                {"id": 5, "date": "2026-04-10", "category": "Food", "description": "Coffee", "amount": 3.0, "entry_type": "expense"},
            ]

    expense_service = DateRangeExpenseService()
    service = build_service(expense=expense_service)

    result = service._run_expense_command(
        "remove all expenses for june and for expenses beyond 18th may",
        {"operation": "delete", "entity": {}, "target": {}},
    )

    assert result["action_result"]["type"] == "expense_deleted"
    assert sorted(expense_service.deleted) == [2, 3]
    assert "2026-06" in result["summary"]
    assert "2026-05-18" in result["summary"]


def test_agent_service_accepts_list_shaped_expense_delete_targets():
    expense_service = StubExpenseService()
    expense_service.expenses = [
        {"id": 1, "date": "2026-05-19", "category": "Travel", "description": "Train", "amount": 12.0, "entry_type": "expense"},
        {"id": 2, "date": "2026-06-05", "category": "Food", "description": "Groceries", "amount": 30.0, "entry_type": "expense"},
    ]
    service = build_service(expense=expense_service)

    result = service._run_expense_command(
        "remove all expenses for june and for expenses beyond 18th may",
        {
            "operation": "delete",
            "entity": {},
            "target": [{"month": "2026-06"}, {"date_after": "2026-05-18"}],
        },
    )

    assert result["headline"] == "Transaction deleted"
    assert sorted(expense_service.deleted) == [1, 2]


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
    current_month_days = service._execute_tool("get_upcoming_recurring_items", {"current_month_only": True})["days"]
    assert 1 <= current_month_days <= 31
    assert service._execute_tool("generate_monthly_report", {})["available"] is True
    assert service._execute_tool("unknown_tool", {})["error"].startswith("Unknown tool")
    assert service._should_use_context_prompt() is False
    assert service._looks_like_manual_action_command("Add a recurring bill") is True
    assert service._workflow_catalog()["month_end_close"]["label"] == "Month-end close"
    assert service._workflow_catalog()["upcoming_bills_check"]["steps"][1]["arguments"] == {"current_month_only": True}
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
    monkeypatch.setattr(service, "run_finance_briefing", lambda payload: {"headline": "done", "background_user_id": current_background_user_id()})
    monkeypatch.setattr(service, "run_workflow", lambda workflow_name, payload: {"workflow_name": workflow_name, "background_user_id": current_background_user_id()})
    service._run_finance_briefing_job("job-1", {"user_id": 2}, app)
    service._run_workflow_job("wf-1", "month_end_close", {"user_id": 3}, app)
    assert service._finance_briefing_jobs["job-1"]["status"] == "completed"
    assert service._workflow_jobs["wf-1"]["status"] == "completed"
    assert service._finance_briefing_jobs["job-1"]["result"]["background_user_id"] == 2
    assert service._workflow_jobs["wf-1"]["result"]["background_user_id"] == 3

    service._finance_briefing_jobs["job-2"] = {"id": "job-2", "status": "queued", "started_at": None, "completed_at": None, "error": None, "result": None}
    service._workflow_jobs["wf-2"] = {"id": "wf-2", "status": "queued", "workflow_name": "month_end_close", "started_at": None, "completed_at": None, "error": None, "result": None}
    monkeypatch.setattr(service, "run_finance_briefing", lambda payload: (_ for _ in ()).throw(ValidationError("brief fail")))
    monkeypatch.setattr(service, "run_workflow", lambda workflow_name, payload: (_ for _ in ()).throw(ValidationError("workflow fail")))
    service._run_finance_briefing_job("job-2", {}, app)
    service._run_workflow_job("wf-2", "month_end_close", {}, app)
    assert service._finance_briefing_jobs["job-2"]["status"] == "failed"
    assert service._workflow_jobs["wf-2"]["status"] == "failed"


def test_agent_service_remaining_parse_and_cfo_edges():
    service = build_service()

    class BadToolCallOllama(StubOllamaClient):
        def __init__(self, tool_calls):
            super().__init__()
            self._tool_calls = tool_calls

        def chat(self, messages, tools=None):
            return {"message": {"role": "assistant", "content": "", "tool_calls": self._tool_calls}}

    service = build_service(ollama=BadToolCallOllama(["bad"]))
    with pytest.raises(ValidationError, match="invalid tool call"):
        service.run_finance_briefing({"task": "general analysis"})

    service = build_service(ollama=BadToolCallOllama([{"function": "bad"}]))
    with pytest.raises(ValidationError, match="invalid tool function"):
        service.run_finance_briefing({"task": "general analysis"})

    service = build_service()
    assert service._parse_direct_prompt_command("") is None
    assert service._parse_direct_transaction_create("Add an expense for lunch today under Food.", "expense") is None
    assert service._parse_direct_recurring_command("hello world") is None
    assert service._parse_direct_recurring_command("Set a monthly reminder for university house rent.") is None
    assert service._parse_direct_recurring_command("Replace weekly utility bills with monthly utility bills.") is None
    assert service._parse_direct_recurring_command("Update the utility bills reminder.") is None
    assert service._extract_money_amount("costs 25 pounds") == 25.0
    assert service._extract_money_amount("no money here") is None

    assert service._run_direct_prompt_command_if_requested("not a direct finance action") is None
    settings_legacy = build_service(
        ollama=StubOllamaClient('{"domain":"settings","setting_key":"monthly_budget","value":1200}')
    )
    assert settings_legacy._run_manual_action_command_legacy("set budget")["headline"] == "Monthly budget updated"
    expense_legacy = build_service(
        ollama=StubOllamaClient('{"domain":"expense","operation":"create","entity":{"date":"2026-03-22","category":"Travel","description":"Tube","amount":6.4,"entry_type":"expense"}}')
    )
    assert expense_legacy._run_manual_action_command_legacy("add expense")["headline"] == "Transaction created"

    with pytest.raises(ValidationError, match="invalid command object"):
        build_service(ollama=StubOllamaClient('[{"bad":"object"},"invalid"]'))._parse_manual_action_command("set budget")
    with pytest.raises(ValidationError, match="invalid command object"):
        build_service(ollama=StubOllamaClient('"not an object"'))._parse_manual_action_command("set budget")
    assert build_service(
        ollama=StubOllamaClient('[{"domain":"settings","setting_key":"monthly_budget","value":1000}]')
    )._parse_manual_action_command("change settings")["value"] == 1000
    assert build_service(
        ollama=StubOllamaClient('[{"description":"Train"},{"category":"Food"}]')
    )._parse_manual_action_command("delete expense")["target"] == [{"description": "Train"}, {"category": "Food"}]
    with pytest.raises(ValidationError, match="could not map"):
        build_service(ollama=StubOllamaClient('{"domain":"unknown"}'))._parse_manual_action_command("do something vague")
    parsed_delete = build_service(ollama=StubOllamaClient('{"domain":"recurring","operation":"delete"}'))._parse_manual_action_command("delete the weekly rent bill")
    assert parsed_delete["domain"] == "recurring"
    assert parsed_delete["target"]["frequency"] == "weekly"

    parsed = build_service(ollama=StubOllamaClient('{"description":"Gym","amount":30}'))._parse_manual_action_command("add a gym subscription reminder")
    assert parsed["domain"] == "recurring"
    assert parsed["reminder"]["description"] == "Gym"
    inferred_recurring = build_service(
        ollama=StubOllamaClient('{"domain":"unknown","description":"Gym","amount":30}')
    )._parse_manual_action_command("gym subscription")
    assert inferred_recurring["domain"] == "recurring"

    target = service._infer_recurring_target_from_task(
        "update the rent reminder",
        {"description": "Rent", "category": "Housing"},
    )
    assert target["category"] == "Housing"

    with pytest.raises(ValidationError, match="list of objects"):
        service._normalize_expense_criteria_items([{"description": "Train"}, "bad"])
    assert service._normalize_expense_criteria_items(None) == [{}]
    with pytest.raises(ValidationError, match="must be an object"):
        service._normalize_expense_criteria_items("bad")

    expense = {"date": "2026-06-10", "category": "Food", "description": "Lunch", "amount": 10.0, "entry_type": "expense"}
    assert service._expense_matches_criteria(expense, {"date_from": "2026-06-11"}) is False
    assert service._expense_matches_criteria(expense, {"date_to": "2026-06-09"}) is False
    assert service._expense_matches_criteria(expense, {"date_after": "2026-06-10"}) is False
    assert service._expense_matches_criteria(expense, {"date_before": "2026-06-10"}) is False

    assert service._expense_criteria_label("bad") == "the requested criteria"
    assert service._expense_criteria_label({"date_before": "2026-06-10"}) == "dates before 2026-06-10"
    assert service._expense_criteria_label({"date_from": "2026-06-01", "date_to": "2026-06-10"}) == "date range 2026-06-01 to 2026-06-10"
    assert service._extract_relative_expense_date("before 28th february 2026") == ("date_before", "2026-02-28")
    assert service._extract_relative_expense_date("after 18th may 2026") == ("date_after", "2026-05-18")
    with pytest.raises(ValidationError, match="could not be resolved"):
        service._extract_relative_expense_date("before 31st february 2026")

    assert service._cash_flow_risk_line(None, None, None).startswith("Cash-flow risk")
    assert "high" in service._cash_flow_risk_line(-10, 100, 110)
    assert "moderate" in service._cash_flow_risk_line(10, 100, 90)
    assert service._budget_pressure_line(110, 100, -10, "over").startswith("Budget pressure")
    assert "late unpaid" in service._recurring_pressure_line({"late_occurrences": [{"description": "Rent", "amount": 700, "date": "2026-06-01"}]})
    assert "upcoming" in service._recurring_pressure_line({"occurrences": [{"description": "Rent", "amount": 700, "date": "2026-06-01"}]})
    assert "No category" in service._category_pressure_line({"top_categories": ["bad"]})
    assert "No next-month forecast" in service._forecast_line({}, 100)
    assert service._cfo_recommended_actions("high", {"late_occurrences": [{"description": "Rent"}]}, {"top_categories": [{"category": "Food"}]}, {"predicted_spending": 100})[:3] == [
        "Reduce or defer non-essential spending until cash flow returns positive.",
        "Verify or pay late reminders so recurring commitments do not stay overdue.",
        "Monitor Food because it is the largest current spending pressure.",
    ]
    assert service._cfo_recommended_actions("medium", {}, {}, {})[0].startswith("Review discretionary")
    assert AgentService._build_cfo_briefing_from_context(
        {
            "dashboard": {
                "month_label": "June 2026",
                "monthly_budget": 600,
                "monthly_income": 500,
                "monthly_expenses": 700,
                "net_cash_flow": -200,
                "remaining_budget": -100,
                "status": "over",
            },
            "financial_pulse": {},
            "category_insights": {},
            "prediction": {},
            "upcoming_recurring_items": {},
        }
    )["risk_level"] == "high"
    assert AgentService._build_cfo_briefing_from_context(
        {
            "dashboard": {
                "month_label": "June 2026",
                "monthly_budget": 600,
                "monthly_income": 1000,
                "monthly_expenses": 700,
                "net_cash_flow": 300,
                "remaining_budget": -100,
                "status": "over",
            },
            "financial_pulse": {},
            "category_insights": {},
            "prediction": {},
            "upcoming_recurring_items": {},
        }
    )["risk_level"] == "medium"
    assert service._as_float(object()) is None
    assert service._parse_python_style_payload("no object") is None
    assert service._parse_relaxed_json_payload('{"headline":"Hi","summary":"Done","recommended_actions":["A","B"]}')["headline"] == "Hi"
    assert service._parse_relaxed_json_value('["A", bad, "B"]') == ["A", "B"]
    assert service._parse_relaxed_json_value("plain text") == "plain text"
    assert service._with_standard_email_signoff("") == "Kind Regards,\nMonetra Organisation"


def test_agent_service_direct_prompt_unknown_domain_returns_none(monkeypatch):
    service = build_service()
    monkeypatch.setattr(service, "_parse_direct_prompt_command", lambda task: {"domain": "unknown"})
    assert service._run_direct_prompt_command_if_requested("unknown direct command") is None

