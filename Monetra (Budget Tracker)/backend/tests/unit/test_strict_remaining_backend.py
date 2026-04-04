import importlib
import runpy
from datetime import datetime
from types import SimpleNamespace

import fastmcp
import pytest
from sqlalchemy import create_engine

import budget_tracker_api.config as config_module
from budget_tracker_api.errors import NotFoundError, ServiceUnavailableError, ValidationError
from budget_tracker_api.repositories.expense_repository import ExpenseRepository
from budget_tracker_api.repositories.recurring_repository import RecurringRepository
from budget_tracker_api.repositories.settings_repository import SettingsRepository
from budget_tracker_api.schemas import Expense
from budget_tracker_api.services.agent_service import AgentService
from budget_tracker_api.services.agentic_command_runtime import AgenticCommandRuntime
from budget_tracker_api.services.analytics_service import AnalyticsService
from budget_tracker_api.services.automation_scheduler import AutomationScheduler
from budget_tracker_api.services.automation_service import AutomationService
from budget_tracker_api.services.expense_service import ExpenseService
from tests.unit.test_agent_service_helpers import (
    StubAnalyticsService,
    StubExpenseService,
    StubPredictionService,
    StubRecurringService,
    StubReportService,
    StubRepository,
    StubSettingsService,
    StubOllamaClient,
)
from tests.unit.test_automation_service import (
    FakeAnalyticsService,
    FakeEmailService,
    FakeRecurringService,
    FakeReportService,
    FakeRunRepository,
)
from tests.unit.test_automation_service_extra import RecordingAgentService
from tests.unit.test_db import FakeConnection
from tests.unit.test_expense_service import StubExpenseRepository
from tests.unit.test_finance_server import (
    StubAnalyticsService as FinanceAnalyticsService,
    StubAutomationService,
    StubExpenseService as FinanceExpenseService,
    StubPredictionService as FinancePredictionService,
    StubRecurringService as FinanceRecurringService,
    StubReportService as FinanceReportService,
    StubSettingsService as FinanceSettingsService,
)


class EmailAutomationStub:
    def run_upcoming_bills_email_now(self):
        return {"summary": "Upcoming bills sent", "report_download_url": None}

    def run_month_end_email_now(self):
        return {"summary": "Month end sent", "report_download_url": "/api/reports/monthly"}


class FakeMcpServer:
    def __init__(self):
        self.calls = []

    def list_tools(self):
        return [{"name": "set_monthly_budget"}]

    def call_tool(self, tool_name, arguments):
        self.calls.append((tool_name, arguments))
        return {"action_result": {"type": "monthly_budget_updated"}, "report_download_url": "/api/reports/monthly"}


class FakeMemoryService:
    def recall(self, limit):
        return []

    def remember(self, **payload):
        self.payload = payload


class FakeLlm:
    def __init__(self, responses):
        self.responses = list(responses)

    def invoke(self, prompt):
        return SimpleNamespace(content=self.responses.pop(0))


class RuntimeWithStubLlm(AgenticCommandRuntime):
    def __init__(self, llm):
        super().__init__(model_name="qwen", base_url=None, mcp_server=FakeMcpServer(), memory_service=FakeMemoryService())
        self._llm = llm


class ExistingIncomeConnection(FakeConnection):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def execute(self, statement):
        self.calls += 1
        sql = str(statement)
        self.executed.append(sql)

        class Result:
            def __init__(self, row=None):
                self._row = row
                self.rowcount = 1

            def first(self):
                return self._row

        if self.calls == 1:
            return Result((5,))
        return Result()

    def commit(self):
        self.committed = True


class UpdateNoneRepository(StubExpenseRepository):
    def get_expense(self, expense_id):
        return Expense(expense_id, "2026-03-01", "Food", "Lunch", 12.0, "expense")

    def update_expense(self, expense_id, payload):
        return None


class DeleteFalseRepository(UpdateNoneRepository):
    def delete_expense(self, expense_id):
        return False


class NegativeCashFlowRepository:
    def monthly_total(self, month_key, entry_type="expense"):
        return 600.0 if entry_type == "expense" else 500.0

    def weekly_total(self, start_date, end_date, entry_type="expense"):
        return 120.0

    def category_totals(self, month_key, entry_type="expense"):
        return [("Food", 200.0), ("Travel", 150.0)]

    def description_totals_for_category(self, month_key, category, entry_type="expense"):
        return [("Groceries", 180.0)]

    def count_expenses_for_month(self, month_key, entry_type=None):
        return 5

    def recent_expenses(self, limit=5, entry_type=None):
        return []


class FailingBootstrapAgentService(RecordingAgentService):
    def run_workflow(self, workflow_name, payload):
        raise RuntimeError("workflow boom")


class FakeAppContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeApp:
    def __init__(self, service):
        self.extensions = {"services": {"automation_service": service}}

    def app_context(self):
        return FakeAppContext()


class FakeAutomationService:
    def run_upcoming_bills_email_if_due(self):
        return None

    def run_month_end_email_if_due(self):
        return None


class FinanceExpenseServiceExact(FinanceExpenseService):
    def list_expenses(self, sort_direction="desc"):
        return [
            {"id": 1, "date": "2026-04-01", "category": "Travel", "description": "Tube", "amount": 5.5, "entry_type": "expense"},
        ]


class FinanceRecurringServiceExact(FinanceRecurringService):
    def list_items(self):
        return [
            {"id": 3, "category": "Housing", "description": "Rent", "amount": 700.0, "entry_type": "expense", "frequency": "monthly", "start_date": "2026-04-01", "end_date": None, "active": True},
        ]


def build_agent_service(ollama=None, recurring=None):
    service = AgentService(
        ollama or StubOllamaClient(),
        StubAnalyticsService(),
        StubPredictionService(),
        recurring or StubRecurringService(),
        StubReportService(),
        StubExpenseService(),
        StubSettingsService(),
        StubRepository(),
    )
    service._automation_service = EmailAutomationStub()
    return service


def test_config_explicit_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://explicit")
    assert config_module._build_database_url() == "postgresql://explicit"


def test_finance_server_remaining_paths(monkeypatch):
    module = importlib.import_module("budget_tracker_api.mcp.finance_server")
    services = {
        "analytics_service": FinanceAnalyticsService(),
        "prediction_service": FinancePredictionService(),
        "settings_service": FinanceSettingsService(),
        "expense_service": FinanceExpenseServiceExact(),
        "recurring_service": FinanceRecurringServiceExact(),
        "report_service": FinanceReportService(),
        "automation_service": StubAutomationService(),
    }
    monkeypatch.setattr(module, "_app", SimpleNamespace(extensions={"services": services}, app_context=lambda: type("C", (), {"__enter__": lambda s: None, "__exit__": lambda s, *args: False})()))

    assert module._match_expenses(services, {"date": "2099-01-01"}) == []
    assert module._match_recurring(services, {"frequency": "weekly"}) == []
    assert module._match_recurring(services, {"start_date": "2099-01-01"}) == []
    assert module._match_recurring(services, {"amount": 999.0}) == []


def test_finance_server_main_guard_runs_with_patched_transport(monkeypatch):
    monkeypatch.setattr(fastmcp.FastMCP, "run", lambda self, transport="stdio": {"transport": transport})
    result = runpy.run_module("budget_tracker_api.mcp.finance_server", run_name="__main__")
    assert result["__name__"] == "__main__"


def test_remaining_repository_and_service_edges(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'strict.db'}", future=True)
    from budget_tracker_api.db import metadata

    metadata.create_all(engine)
    connection = engine.connect()
    try:
        expense_repository = ExpenseRepository(lambda: connection)
        expense_repository.create_expense({
            "date": "2026-03-01",
            "category": "Food",
            "description": "Groceries",
            "amount": 20.0,
            "entry_type": "expense",
        })
        expense_repository.create_expense({
            "date": "2026-03-02",
            "category": "Salary",
            "description": "Payroll",
            "amount": 100.0,
            "entry_type": "income",
        })
        assert expense_repository.cash_flow_totals("2026-03") == {"income": 100.0, "expense": 20.0, "net": 80.0}

        recurring_repository = RecurringRepository(lambda: connection)
        assert recurring_repository.update_item(999, {"category": "Bills", "description": "Water", "amount": 12, "entry_type": "expense", "frequency": "monthly", "start_date": "2026-04-01", "end_date": None, "active": True}) is None
    finally:
        connection.close()
        engine.dispose()

    settings_connection = ExistingIncomeConnection()
    settings_repository = SettingsRepository(lambda: settings_connection)
    settings_repository.get_monthly_income = lambda month_key=None: 2400.0
    result = settings_repository.update_monthly_income(2400.0, "2026-04")
    assert result["income_month"] == "2026-04"
    assert any("UPDATE monthly_income_records" in statement for statement in settings_connection.executed)

    with pytest.raises(NotFoundError):
        ExpenseService(UpdateNoneRepository()).update_expense(1, {"date": "2026-03-01", "category": "Food", "description": "Lunch", "amount": "12.00"})
    with pytest.raises(NotFoundError):
        ExpenseService(DeleteFalseRepository()).delete_expense(1)
    assert ExpenseService(StubExpenseRepository())._clean_csv_row({"date": None, "category": None, "description": None, "amount": None}) is None


def test_remaining_analytics_and_scheduler_edges():
    service = AnalyticsService(NegativeCashFlowRepository(), lambda: 1000.0, lambda _month=None: 500.0)
    assert service.financial_pulse()["narrative"] == "Cash outflow is currently ahead of income. Tighten discretionary spend."

    scheduler = AutomationScheduler(FakeApp(FakeAutomationService()), poll_seconds=900)
    now = datetime.now()
    scheduler._next_realtime_run_at = None
    assert scheduler._seconds_until_next_wake(now) >= 1.0


def test_remaining_automation_service_edges(caplog):
    repository = FakeRunRepository()
    service = AutomationService(
        FailingBootstrapAgentService(),
        FakeReportService(),
        FakeEmailService(),
        repository,
        FakeRecurringService([]),
        FakeAnalyticsService(),
        month_end_email_hour=22,
        month_end_email_minute=15,
    )

    service._run_bootstrap_background(type("A", (), {"app_context": lambda self: type("C", (), {"__enter__": lambda s: None, "__exit__": lambda s, *args: False})()})(), ["month_end_close"])
    assert "Automation bootstrap workflow failed" in caplog.text
    assert service._normalize_email_list(None) == []


def test_remaining_agent_service_edges(monkeypatch):
    service = build_agent_service()
    assert service._find_active_workflow_job("missing") is None

    assert service._infer_recurring_target_from_task("weekly gym membership", None)["frequency"] == "weekly"
    assert service._infer_recurring_target_from_task("gym membership", {"frequency": "monthly"})["frequency"] == "monthly"
    assert service._infer_recurring_target_from_task("delete rent copy", None)["description"] == "Rent Copy"

    parsed_service = build_agent_service(
        StubOllamaClient('{"operation":"create","category":"Bills","description":"Water","amount":12,"entry_type":"expense","frequency":"monthly","start_date":"2026-04-01","active":true}')
    )
    created = parsed_service._run_reminder_command("create a recurring water reminder")
    assert created["action_result"]["type"] in {"recurring_item_created", "recurring_item_updated"}

    updated = service._run_reminder_command(
        "update my recurring utility bill",
        {
            "operation": "update",
            "target": {"description": "Utility Bills", "category": "Utilities", "entry_type": "expense", "frequency": "weekly"},
            "reminder": {"category": "Utilities", "description": "Utility Bills", "amount": 21.0, "entry_type": "expense", "frequency": "weekly", "start_date": "2026-03-16", "end_date": None, "active": True},
        },
    )
    assert updated["action_result"]["type"] == "recurring_item_updated"
    assert service._recurring_service.deleted == [2]

    with pytest.raises(ValidationError, match="replace"):
        service._replace_matching_reminders({"description": "Missing"}, {"description": "New"})

    import budget_tracker_api.services.agent_service as agent_service_module
    from datetime import datetime as real_datetime

    class FrozenDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 4, 23, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(agent_service_module, "datetime", FrozenDateTime)
    assert service._resolve_start_date_from_task("pay on the 1st of every month", "2026-04-23") == "2026-05-01"


def test_remaining_agentic_runtime_edges(monkeypatch):
    runtime = RuntimeWithStubLlm(FakeLlm([]))
    assert runtime._parse_json_object('prefix {"ok": true}', "label") == {"ok": True}

    import budget_tracker_api.services.agentic_command_runtime as runtime_module

    class FakeCompiled:
        def invoke(self, state):
            return {}

    class FakeGraph:
        def add_node(self, *args, **kwargs):
            return None
        def add_edge(self, *args, **kwargs):
            return None
        def add_conditional_edges(self, *args, **kwargs):
            return None
        def compile(self):
            return FakeCompiled()

    original_state_graph = runtime_module.StateGraph
    monkeypatch.setattr(runtime_module, "StateGraph", lambda *_args, **_kwargs: FakeGraph())
    broken_runtime = RuntimeWithStubLlm(FakeLlm([]))
    with pytest.raises(ValidationError, match="final command result"):
        broken_runtime.run("set budget")
    monkeypatch.setattr(runtime_module, "StateGraph", original_state_graph)

    class MissingToolLlm(FakeLlm):
        pass

    planner = RuntimeWithStubLlm(
        FakeLlm([
            '{"intent":"update budget","steps":[{"tool":"","arguments":{},"reason":"bad"}],"success_criteria":["done"]}',
            '{"intent":"update budget","steps":[],"success_criteria":["done"]}',
            '{"headline":"ignored","summary":"ignored","risk_level":"low","recommended_actions":[],"email_subject":"ignored","email_draft":"ignored"}',
        ])
    )
    assert planner.run("set budget")["headline"] == "ignored"

    class FailCompiled:
        def __init__(self, nodes):
            self.nodes = nodes

        def invoke(self, state):
            return self.nodes["fail"]({"execution_error": "still broken"})

    class FailGraph:
        def __init__(self):
            self.nodes = {}

        def add_node(self, name, fn):
            self.nodes[name] = fn

        def add_edge(self, *args, **kwargs):
            return None

        def add_conditional_edges(self, *args, **kwargs):
            return None

        def compile(self):
            return FailCompiled(self.nodes)

    monkeypatch.setattr(runtime_module, "StateGraph", lambda *_args, **_kwargs: FailGraph())
    failing_runtime = RuntimeWithStubLlm(FakeLlm([]))
    with pytest.raises(ValidationError, match="still broken"):
        failing_runtime.run("set budget")







