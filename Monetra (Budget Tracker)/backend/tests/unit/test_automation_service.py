from datetime import datetime
from pathlib import Path

import budget_tracker_api.services.automation_service as automation_module
from budget_tracker_api.services.automation_service import AutomationService


class FakeAgentService:
    def run_workflow(self, workflow_name, payload):
        if workflow_name == "upcoming_bills_check":
            return {
                "risk_level": "medium",
                "recommended_actions": ["Pay rent before Friday."],
                "email_subject": "Upcoming bills summary",
                "email_draft": "Rent and utilities are due soon.",
                "model": "mistral:latest",
                "tools_used": ["get_upcoming_recurring_items"],
                "report_download_url": None,
            }
        return {
            "risk_level": "low",
            "recommended_actions": ["Review the attached report."],
            "email_subject": "Month-end report",
            "email_draft": "Cash flow remained stable and the attached report captures the monthly close.",
            "model": "mistral:latest",
            "tools_used": ["generate_monthly_report"],
            "report_download_url": "/api/reports/monthly",
        }


class FakeReportService:
    def generate_monthly_report(self):
        return Path("report.pdf")


class FakeAnalyticsService:
    def dashboard(self):
        return {
            "month_label": "March 2026",
            "monthly_budget": 1200.0,
            "current_month_total": 950.0,
            "monthly_expenses": 950.0,
            "monthly_income": 1400.0,
            "net_cash_flow": 450.0,
        }


class FakeEmailService:
    def __init__(self):
        self.sent_messages = []
        self.sent_reports = []

    def send_email(self, subject, body, recipient=None):
        record = {"recipient": recipient or "rushabh.dharamshi@gmail.com", "subject": subject, "body": body}
        self.sent_messages.append(record)
        return {"recipient": record["recipient"], "subject": subject}

    def send_report_email(self, subject, body, attachment_path, recipient=None):
        record = {
            "recipient": recipient or "rushabh.dharamshi@gmail.com",
            "subject": subject,
            "body": body,
            "attachment_path": str(attachment_path),
        }
        self.sent_reports.append(record)
        return {"recipient": record["recipient"], "subject": subject}


class FakeRunRepository:
    def __init__(self):
        self.runs = []

    def create_run(self, payload):
        record = {"id": len(self.runs) + 1, **payload}
        self.runs.append(record)
        return record

    def latest_run_for_day(self, workflow_name, date_prefix):
        for run in reversed(self.runs):
            if run["workflow_name"] == workflow_name and str(run["generated_at"]).startswith(date_prefix):
                return run
        return None

    def latest_run(self, workflow_name):
        for run in reversed(self.runs):
            if run["workflow_name"] == workflow_name:
                return run
        return None


class FakeRecurringService:
    def __init__(self, occurrences):
        self._occurrences = occurrences

    def upcoming_calendar(self, days):
        return {"occurrences": self._occurrences}


def test_month_end_email_includes_cash_flow_budget_status_and_attachment():
    repository = FakeRunRepository()
    email_service = FakeEmailService()
    service = AutomationService(
        FakeAgentService(),
        FakeReportService(),
        email_service,
        repository,
        FakeRecurringService([]),
        FakeAnalyticsService(),
    )

    result = service.run_month_end_email_now()

    assert result["headline"] == "Month-end report emailed manually"
    assert email_service.sent_reports
    body = email_service.sent_reports[-1]["body"]
    assert "Net cash flow for March 2026 was positive at GBP 450.00." in body
    assert "Spending stayed within the monthly budget by GBP 250.00." in body
    assert "The PDF report is attached as report.pdf." in body
    assert email_service.sent_reports[-1]["attachment_path"].endswith("report.pdf")


def test_month_end_email_waits_until_configured_send_time(monkeypatch):
    class FakeDateTime:
        @classmethod
        def now(cls):
            return datetime(2026, 3, 31, 22, 14, 0)

    monkeypatch.setattr(automation_module, "datetime", FakeDateTime)
    repository = FakeRunRepository()
    email_service = FakeEmailService()
    service = AutomationService(
        FakeAgentService(),
        FakeReportService(),
        email_service,
        repository,
        FakeRecurringService([]),
        FakeAnalyticsService(),
        month_end_email_hour=22,
        month_end_email_minute=15,
    )

    result = service.run_month_end_email_if_due()

    assert result is None
    assert not email_service.sent_reports


def test_month_end_email_sends_on_exact_configured_minute(monkeypatch):
    class FakeDateTime:
        @classmethod
        def now(cls):
            return datetime(2026, 3, 31, 22, 15, 0)

    monkeypatch.setattr(automation_module, "datetime", FakeDateTime)
    repository = FakeRunRepository()
    email_service = FakeEmailService()
    service = AutomationService(
        FakeAgentService(),
        FakeReportService(),
        email_service,
        repository,
        FakeRecurringService([]),
        FakeAnalyticsService(),
        month_end_email_hour=22,
        month_end_email_minute=15,
    )

    result = service.run_month_end_email_if_due()

    assert result is not None
    assert result["headline"] == "Month-end report emailed"
    assert email_service.sent_reports


def test_upcoming_bills_email_runs_when_signature_changes():
    repository = FakeRunRepository()
    service = AutomationService(
        FakeAgentService(),
        FakeReportService(),
        FakeEmailService(),
        repository,
        FakeRecurringService([
            {
                "recurring_item_id": 1,
                "date": "2026-03-25",
                "description": "Rent",
                "amount": 700.0,
                "entry_type": "expense",
                "frequency": "monthly",
            }
        ]),
        FakeAnalyticsService(),
    )

    first = service.run_upcoming_bills_email_if_due()
    second = service.run_upcoming_bills_email_if_due()

    assert first is not None
    assert second is None
    assert repository.runs[0]["headline"] == "Upcoming bills alert emailed"


def test_upcoming_bills_email_does_not_send_all_clear_after_bills_disappear():
    repository = FakeRunRepository()
    email_service = FakeEmailService()
    service = AutomationService(
        FakeAgentService(),
        FakeReportService(),
        email_service,
        repository,
        FakeRecurringService([
            {
                "recurring_item_id": 1,
                "date": "2026-03-25",
                "description": "Rent",
                "amount": 700.0,
                "entry_type": "expense",
                "frequency": "monthly",
            }
        ]),
        FakeAnalyticsService(),
    )

    service.run_upcoming_bills_email_if_due()
    service._recurring_service = FakeRecurringService([])
    cleared = service.run_upcoming_bills_email_if_due()

    assert cleared is None
    assert len(email_service.sent_messages) == 1








