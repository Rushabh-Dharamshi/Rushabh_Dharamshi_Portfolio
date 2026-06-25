import json

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


class RagServiceStub:
    def retrieve_context(self, question, top_k=None):
        return {"question": question, "retrieved_count": int(top_k or 6), "sources": [{"source_label": "Dashboard"}]}


class EmailAutomationStub:
    def __init__(self):
        self.upcoming_recipient = None
        self.month_end_recipient = None

    def run_upcoming_bills_email_now(self, recipient=None):
        self.upcoming_recipient = recipient
        return {"headline": "Upcoming bills email sent", "summary": "Upcoming bills sent", "report_download_url": None}

    def run_all_upcoming_bills_email_now(self, recipient=None):
        self.upcoming_recipient = recipient
        return {"headline": "All upcoming bills emailed", "summary": "All upcoming bills sent", "report_download_url": None}

    def run_month_end_email_now(self, recipient=None):
        self.month_end_recipient = recipient
        return {"headline": "Month-end report sent", "summary": "Month end sent", "report_download_url": "/api/reports/monthly"}


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
        rag_service=RagServiceStub(),
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
    assert handlers["retrieve_finance_context"]({"question": "What changed?", "top_k": 3})["retrieved_count"] == 3
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
        service._mcp_send_all_upcoming_bills_email_now({})
    with pytest.raises(ValidationError, match="Automation service"):
        service._mcp_send_month_end_email_now({})

    service._automation_service = EmailAutomationStub()
    upcoming_result = service._mcp_send_upcoming_bills_email_now({})
    all_upcoming_result = service._mcp_send_all_upcoming_bills_email_now({})
    month_end_result = service._mcp_send_month_end_email_now({})
    assert upcoming_result["action_result"]["type"] == "upcoming_bills_email_sent"
    assert all_upcoming_result["action_result"]["type"] == "upcoming_bills_email_sent"
    assert month_end_result["action_result"]["type"] == "month_end_email_sent"
    json.dumps(upcoming_result)
    json.dumps(all_upcoming_result)
    json.dumps(month_end_result)
    assert service._looks_like_manual_action_command("send me the month-end report email")
    assert service._looks_like_manual_action_command("email me if bills are due")

    report_email = service.run_finance_briefing({"task": "send an email of my current financial report"})
    assert report_email["action_result"]["type"] == "month_end_email_sent"
    assert report_email["report_download_url"] == "/api/reports/monthly"

    current_report_email = service.run_finance_briefing({"task": "send the current financial report to the user's email address"})
    assert current_report_email["action_result"]["type"] == "month_end_email_sent"
    assert current_report_email["report_download_url"] == "/api/reports/monthly"

    bills_email = service.run_finance_briefing({"task": "email me if bills are due"})
    assert bills_email["action_result"]["type"] == "upcoming_bills_email_sent"

    all_bills_email = service.run_finance_briefing({"task": "Send all upcoming bills."})
    assert all_bills_email["action_result"]["type"] == "upcoming_bills_email_sent"

    per_user_email = service.run_finance_briefing(
        {"task": "Send the month-end email now.", "recipient": "registered-user@example.com"}
    )
    assert per_user_email["action_result"]["type"] == "month_end_email_sent"
    assert service._automation_service.month_end_recipient == "registered-user@example.com"

    per_user_bills = service.run_finance_briefing(
        {"task": "Send the upcoming bills email now.", "recipient_email": "registered-user@example.com"}
    )
    assert per_user_bills["action_result"]["type"] == "upcoming_bills_email_sent"
    assert service._automation_service.upcoming_recipient == "registered-user@example.com"

    bad_json_service = build_service(StubOllamaClient("not-json"))
    with pytest.raises(ValidationError, match="could not understand the requested action"):
        bad_json_service._parse_manual_action_command("set something")

    expense_infer_service = build_service(StubOllamaClient('{"domain":"unknown","operation":"noop"}'))
    parsed = expense_infer_service._parse_manual_action_command("add an expense transaction")
    assert parsed["domain"] == "expense"

    unsupported_service = build_service(StubOllamaClient('{"domain":"unknown","operation":"noop"}'))
    with pytest.raises(ValidationError, match="settings, transactions, or recurring reminders"):
        unsupported_service._parse_manual_action_command("do something ambiguous")


def test_agent_service_builtin_prompt_library_commands_are_direct_and_versatile():
    prompt_expectations = [
        ("Generate the current monthly report and summarise the main budget pressure points.", "monthly_report_generated"),
        ("Send due-soon bills for today plus the next 7 days. This covers 8 calendar dates total and includes late unpaid reminders.", "upcoming_bills_email_sent"),
        ("Send all upcoming bills.", "upcoming_bills_email_sent"),
        ("Send the month-end email now.", "month_end_email_sent"),
        ("Set my monthly budget to 1600 pounds.", "monthly_budget_updated"),
        ("Set my monthly income to 2400 pounds.", "monthly_income_updated"),
        ("Set my monthly income for 2026-04 to 2400 pounds.", "monthly_income_updated"),
        ("Add an expense for Tube fare of 6.40 pounds today under Travel.", "expense_created"),
        ("Update the Travel expense called Train pass to 81 pounds on 2026-03-20.", "expense_updated"),
        ("Delete the expense matching Train pass under Travel.", "expense_deleted"),
        ("Remove all expenses for June 2026.", "expense_deleted"),
        ("Remove all expenses for June 2026 and expenses beyond 18th May 2026.", "expense_deleted"),
        (
            "Set a monthly reminder for university house rent on the 23rd of every month from April 2026 to June 2026 inclusive at 452.74 pounds.",
            "recurring_item_created",
        ),
        ("Add a weekly reminder for rent of 850 pounds starting 2026-03-27.", "recurring_item_created"),
        ("Replace weekly utility bills with monthly utility bills of 24.51 pounds on the 23rd of each month.", "recurring_item_replaced"),
        ("Remove the weekly utility bills reminder.", "recurring_item_deleted"),
        ("Update the utility bills reminder to 24.51 pounds monthly from 2026-04-23.", "recurring_item_updated"),
    ]

    class DateRangeExpenseService(StubExpenseService):
        def __init__(self):
            super().__init__()
            self.expenses = [
                {"id": 1, "date": "2026-03-20", "category": "Travel", "description": "Train pass", "amount": 80.0, "entry_type": "expense"},
                {"id": 2, "date": "2026-05-19", "category": "Food", "description": "Lunch", "amount": 9.0, "entry_type": "expense"},
                {"id": 3, "date": "2026-06-05", "category": "Food", "description": "Groceries", "amount": 30.0, "entry_type": "expense"},
                {"id": 4, "date": "2026-06-10", "category": "Work", "description": "Notebook", "amount": 20.0, "entry_type": "expense"},
            ]

    def build_prompt_service():
        service = AgentService(
            StubOllamaClient(),
            StubAnalyticsService(),
            StubPredictionService(),
            StubRecurringService(),
            StubReportService(),
            DateRangeExpenseService(),
            StubSettingsService(),
            StubRepository(),
            rag_service=RagServiceStub(),
        )
        service._automation_service = EmailAutomationStub()
        return service

    for prompt, expected_action_type in prompt_expectations:
        service = build_prompt_service()
        result = service.run_finance_briefing({"task": prompt})
        assert result["action_result"]["type"] == expected_action_type, prompt

    income_transaction_service = build_prompt_service()
    with pytest.raises(ValidationError, match="monthly income settings"):
        income_transaction_service.run_finance_briefing(
            {"task": "Add an income transaction for part-time work of 250 pounds on 2026-05-18 under Income."}
        )

    custom_rent_service = build_prompt_service()
    custom_rent_service.run_finance_briefing(
        {
            "task": (
                "Set a monthly reminder for university house rent on the 23rd of every month "
                "from April 2026 to June 2026 inclusive at 500 pounds."
            )
        }
    )
    assert custom_rent_service._recurring_service.created[-1]["amount"] == 500.0

    briefing_service = build_service()
    briefing = briefing_service.run_finance_briefing(
        {
            "task": (
                "Prepare a CFO-style monthly finance briefing with cash pressure, recurring bill pressure, "
                "recommended actions, and an email-ready summary."
            )
        }
    )
    assert briefing["headline"]


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
    assert any(tool["function"]["name"] == "retrieve_finance_context" for tool in service._tool_definitions())


def test_agent_service_rag_handlers_fail_cleanly_when_rag_is_missing():
    service = build_service()
    service._rag_service = None

    with pytest.raises(ValidationError, match="RAG service"):
        service._mcp_retrieve_finance_context({"question": "What changed?"})

    assert service._execute_tool("retrieve_finance_context", {"question": "What changed?"}) == {
        "error": "RAG service is not available.",
    }


def test_agent_service_execute_tool_returns_rag_context_when_available():
    service = build_service()

    assert service._execute_tool("retrieve_finance_context", {"question": "What changed?", "top_k": 2}) == {
        "question": "What changed?",
        "retrieved_count": 2,
        "sources": [{"source_label": "Dashboard"}],
    }

