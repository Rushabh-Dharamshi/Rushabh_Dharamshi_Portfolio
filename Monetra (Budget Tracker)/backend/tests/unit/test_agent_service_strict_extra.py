import pytest

from budget_tracker_api.errors import ValidationError
from budget_tracker_api.services.agent_service import AgentService
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


class EmailAutomationStub:
    def run_upcoming_bills_email_now(self):
        return {"summary": "Upcoming bills sent", "report_download_url": None}

    def run_month_end_email_now(self):
        return {"summary": "Month end sent", "report_download_url": "/api/reports/monthly"}


def build_service(ollama=None):
    service = AgentService(
        ollama or StubOllamaClient(),
        StubAnalyticsService(),
        StubPredictionService(),
        StubRecurringService(),
        StubReportService(),
        StubExpenseService(),
        StubSettingsService(),
        StubRepository(),
    )
    service._automation_service = EmailAutomationStub()
    return service


def test_agent_service_manual_legacy_and_mcp_wrappers(monkeypatch):
    service = build_service()

    monkeypatch.setattr(service, "_parse_manual_action_command", lambda task: {"domain": "unknown"})
    with pytest.raises(ValidationError, match="supported action"):
        service._run_manual_action_command_legacy("unknown")

    handlers = service._build_mcp_handlers()
    monkeypatch.setattr(service, "_run_settings_command", lambda task, parsed: {"task": task, **parsed})
    monkeypatch.setattr(service, "_run_expense_command", lambda task, parsed: {"task": task, **parsed})
    monkeypatch.setattr(service, "_run_reminder_command", lambda task, parsed: {"task": task, **parsed})
    monkeypatch.setattr(service, "_parse_reminder_payload", lambda payload, fallback_date: {"parsed": payload, "start_date": fallback_date})

    assert handlers["set_monthly_budget"]({"monthly_budget": 1200})["setting_key"] == "monthly_budget"
    assert handlers["set_monthly_income"]({"monthly_income": 1500, "month": "2026-04"})["setting_key"] == "monthly_income"
    assert handlers["create_transaction"]({"description": "Tube"})["operation"] == "create"
    assert handlers["update_transaction_by_match"]({"target": {"description": "Tube"}, "entity": {"amount": 7}})["operation"] == "update"
    assert handlers["delete_transaction_by_match"]({"target": {"description": "Tube"}})["operation"] == "delete"
    assert handlers["create_recurring_reminder"]({"description": "Rent"})["operation"] == "create"
    assert handlers["update_recurring_reminder_by_match"]({"target": {"description": "Rent"}, "reminder": {"description": "Rent"}})["operation"] == "update"
    assert handlers["delete_recurring_reminder_by_match"]({"target": {"description": "Rent"}})["operation"] == "delete"
    assert handlers["replace_recurring_reminder"]({"target": {"description": "Rent"}, "reminder": {"description": "Rent"}})["operation"] == "replace"


def test_agent_service_email_wrappers_and_parse_edges():
    service = build_service()

    assert service._mcp_list_recurring_reminders({})["items"]
    service._recurring_service = object()
    assert service._mcp_list_recurring_reminders({}) == {"items": []}

    service._automation_service = None
    with pytest.raises(ValidationError, match="Automation service"):
        service._mcp_send_upcoming_bills_email_now({})
    with pytest.raises(ValidationError, match="Automation service"):
        service._mcp_send_month_end_email_now({})

    service._automation_service = EmailAutomationStub()
    assert service._mcp_send_upcoming_bills_email_now({})["action_result"]["type"] == "upcoming_bills_email_sent"
    assert service._mcp_send_month_end_email_now({})["action_result"]["type"] == "month_end_email_sent"

    bad_json_service = build_service(StubOllamaClient("not-json"))
    with pytest.raises(ValidationError, match="could not understand the requested action"):
        bad_json_service._parse_manual_action_command("set something")

    expense_infer_service = build_service(StubOllamaClient('{"domain":"unknown","operation":"noop"}'))
    parsed = expense_infer_service._parse_manual_action_command("add an expense transaction")
    assert parsed["domain"] == "expense"

    unsupported_service = build_service(StubOllamaClient('{"domain":"unknown","operation":"noop"}'))
    with pytest.raises(ValidationError, match="settings, transactions, or recurring reminders"):
        unsupported_service._parse_manual_action_command("do something ambiguous")


def test_agent_service_recurring_parsing_and_matching_edges():
    service = build_service()

    with pytest.raises(ValidationError, match="recurring command"):
        service._parse_recurring_command_payload("not-json", "2026-04-01")

    parsed = service._parse_recurring_command_payload(
        '{"operation":"noop","category":"Bills","description":"Water","amount":12,"entry_type":"expense","frequency":"monthly","target":{"amount":12,"entry_type":"expense","frequency":"monthly","start_date":"2026-04-01","end_date":"2026-06-01"}}',
        "2026-04-01",
    )
    assert parsed["operation"] == "create"
    assert parsed["reminder"]["description"] == "Water"
    assert parsed["target"]["amount"] == 12.0

    assert service._infer_recurring_target_from_task("replace monthly rent with yearly mortgage", {"description": "Rent", "frequency": "monthly"})["frequency"] == "monthly"
    assert service._infer_recurring_target_from_task("replace annual rent with monthly mortgage", {"description": "Rent", "frequency": "monthly"})["frequency"] == "yearly"
    assert service._infer_recurring_target_from_task("delete daily utility bills", {"description": "Utility Bills"})["frequency"] == "daily"
    assert service._infer_recurring_target_from_task("delete rent", {"description": "Rent"})["category"] == "Housing"

    assert service._find_matching_reminders({"category": "missing"}) == []
    assert service._find_matching_reminders({"entry_type": "income"}) == []
    assert service._find_matching_reminders({"frequency": "monthly"}) == []
    assert service._find_matching_reminders({"start_date": "2099-01-01"}) == []
    assert service._find_matching_reminders({"amount": 999}) == []

    assert service._find_matching_expenses({"category": "missing"}) == []
    assert service._find_matching_expenses({"entry_type": "income"}) == []
    assert service._find_matching_expenses({"date": "2099-01-01"}) == []
    assert service._find_matching_expenses({"amount": 999}) == []


def test_agent_service_schedule_helper_edges(monkeypatch):
    service = build_service()

    import budget_tracker_api.services.agent_service as agent_service_module
    from datetime import datetime as real_datetime

    class FrozenDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 12, 15, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(agent_service_module, "datetime", FrozenDateTime)

    assert service._resolve_start_date_from_task("pay on the 1st of every month", "2026-12-15") == "2027-01-01"
    assert service._resolve_start_date_from_task("no date here", "2026-04-01") == "2026-04-01"
    assert service._normalize_recommended_actions({"bad": True}) == []
    assert service._extract_day_of_month("no day present") is None
    with pytest.raises(ValidationError, match="does not include any due dates"):
        service._resolve_task_schedule_bounds("from june 2026 to april 2026 exclusive", "monthly", "2026-04-23", None)
    with pytest.raises(ValidationError, match="day-of-month could not be resolved"):
        service._build_monthly_due_date(2026, 2, 0)
    assert service._previous_due_date(__import__("datetime").date(2026, 4, 23), "weekly").isoformat() == "2026-04-16"
    assert any(tool["function"]["name"] == "generate_monthly_report" for tool in service._tool_definitions())


