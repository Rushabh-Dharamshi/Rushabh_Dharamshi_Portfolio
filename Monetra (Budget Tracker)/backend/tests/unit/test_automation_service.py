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
    def __init__(self, occurrences, late_occurrences=None):
        self._occurrences = occurrences
        self._late_occurrences = late_occurrences or []

    def upcoming_calendar(self, days):
        return {"occurrences": self._occurrences, "late_occurrences": self._late_occurrences}


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


def test_month_end_email_uses_explicit_recipient_when_provided():
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

    result = service.run_month_end_email_now(recipient="registered-user@example.com")

    assert result["summary"] == "Manual month-end PDF report emailed to registered-user@example.com."
    assert email_service.sent_reports[-1]["recipient"] == "registered-user@example.com"


def test_upcoming_bills_email_uses_explicit_recipient_when_provided():
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

    result = service.run_upcoming_bills_email_now(recipient="registered-user@example.com")

    assert result["summary"] == "Upcoming bills alert emailed to registered-user@example.com for late unpaid reminders and bills due today plus the next 7 days (8 calendar dates total)."
    assert email_service.sent_messages[-1]["recipient"] == "registered-user@example.com"
    assert "8 calendar dates total" in email_service.sent_messages[-1]["body"]


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


def test_scheduled_month_end_email_uses_explicit_recipient(monkeypatch):
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

    result = service.run_month_end_email_if_due(recipient="scheduled-user@example.com")

    assert result is not None
    assert result["summary"] == "Monthly PDF report emailed to scheduled-user@example.com."
    assert email_service.sent_reports[-1]["recipient"] == "scheduled-user@example.com"


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


def test_scheduled_upcoming_bills_email_uses_explicit_recipient():
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

    result = service.run_upcoming_bills_email_if_due(recipient="scheduled-user@example.com")

    assert result is not None
    assert result["summary"] == "Upcoming bills alert emailed to scheduled-user@example.com for late unpaid reminders and bills due today plus the next 7 days (8 calendar dates total)."
    assert email_service.sent_messages[-1]["recipient"] == "scheduled-user@example.com"


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


def test_manual_upcoming_bills_email_sends_when_bills_exist_and_private_guard_rejects_empty_list():
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

    result = service.run_upcoming_bills_email_now()

    assert result["headline"] == "Upcoming bills alert emailed"
    assert email_service.sent_messages[-1]["subject"] == "Upcoming payment reminders"

    import pytest
    from budget_tracker_api.errors import ValidationError

    with pytest.raises(ValidationError, match="No expense reminders"):
        service._dispatch_upcoming_bills_email(
            due_expenses=[],
            signature="empty",
            workflow_name="upcoming_bills_email_manual_dispatch",
            workflow_label="Upcoming bills email manual dispatch",
        )


def test_upcoming_bills_email_includes_late_and_today_reminders():
    repository = FakeRunRepository()
    email_service = FakeEmailService()
    service = AutomationService(
        FakeAgentService(),
        FakeReportService(),
        email_service,
        repository,
        FakeRecurringService(
            [
                {
                    "recurring_item_id": 1,
                    "date": "2026-03-25",
                    "description": "Due today",
                    "amount": 12.0,
                    "entry_type": "expense",
                    "frequency": "monthly",
                    "days_until_due": 0,
                },
                {
                    "recurring_item_id": 2,
                    "date": "2026-04-10",
                    "description": "Outside window",
                    "amount": 20.0,
                    "entry_type": "expense",
                    "frequency": "monthly",
                    "days_until_due": 16,
                },
            ],
            late_occurrences=[
                {
                    "recurring_item_id": 3,
                    "date": "2026-03-20",
                    "description": "Late bill",
                    "amount": 30.0,
                    "entry_type": "expense",
                    "frequency": "monthly",
                    "days_until_due": -5,
                }
            ],
        ),
        FakeAnalyticsService(),
    )

    result = service.run_upcoming_bills_email_now()

    assert result["headline"] == "Upcoming bills alert emailed"
    body = email_service.sent_messages[-1]["body"]
    assert "Late bill: GBP 30.00, due 2026-03-20 (5 days late), monthly" in body
    assert "Due today: GBP 12.00, due 2026-03-25 (due today), monthly" in body
    assert "Outside window" not in body
    assert email_service.sent_messages[-1]["subject"] == "Overdue and due-today payment reminders"


def test_upcoming_bills_email_subject_does_not_say_due_today_for_late_only_reminder():
    class MisleadingSubjectAgentService(FakeAgentService):
        def run_workflow(self, workflow_name, payload):
            result = super().run_workflow(workflow_name, payload)
            result["email_subject"] = "[Urgent] Payment Reminder: Late Test Deposit - Due Today"
            return result

    email_service = FakeEmailService()
    service = AutomationService(
        MisleadingSubjectAgentService(),
        FakeReportService(),
        email_service,
        FakeRunRepository(),
        FakeRecurringService(
            [
                {
                    "recurring_item_id": 1,
                    "date": "2026-06-10",
                    "description": "Monthly Test Late Deposit Reminder",
                    "amount": 12.5,
                    "entry_type": "expense",
                    "frequency": "monthly",
                    "days_until_due": -9,
                }
            ]
        ),
        FakeAnalyticsService(),
    )

    service.run_upcoming_bills_email_now()

    assert email_service.sent_messages[-1]["subject"] == "Overdue payment reminder: Monthly Test Late Deposit Reminder"
    assert "Due Today" not in email_service.sent_messages[-1]["subject"]


def test_upcoming_bills_email_strips_duplicate_signoff_and_uses_clean_spacing():
    class SignoffAgentService(FakeAgentService):
        def run_workflow(self, workflow_name, payload):
            result = super().run_workflow(workflow_name, payload)
            result["email_draft"] = (
                "Dear Rushabh, Please pay the late bill. "
                "Kind Regards, Monetra Organisation"
            )
            result["recommended_actions"] = ["Pay the late bill."]
            return result

    repository = FakeRunRepository()
    email_service = FakeEmailService()
    service = AutomationService(
        SignoffAgentService(),
        FakeReportService(),
        email_service,
        repository,
        FakeRecurringService(
            [
                {
                    "recurring_item_id": 1,
                    "date": "2026-06-10",
                    "description": "Monthly Test Late Deposit Reminder",
                    "amount": 12.5,
                    "entry_type": "expense",
                    "frequency": "monthly",
                    "days_until_due": -7,
                }
            ]
        ),
        FakeAnalyticsService(),
    )

    service.run_upcoming_bills_email_now()

    body = email_service.sent_messages[-1]["body"]
    assert body.count("Kind Regards") == 1
    assert body.count("Monetra Organisation") == 1
    assert body.count("Dear") == 1
    assert "Dear User" not in body
    assert "Dear Rushabh Dharamshi, Please" not in body
    assert body.count("Included reminders:") == 1
    assert "This due-soon email includes today plus the next 7 days" not in body
    assert body.startswith("Dear [Recipient's Name],\n\n")
    assert "\n\nPlease pay the late bill.\n\n" in body
    assert "\n\nBills included:\n" in body
    assert "\n\nRecommended actions:\n" in body


def test_upcoming_bills_email_extracts_human_text_from_json_shaped_draft():
    class JsonDraftAgentService(FakeAgentService):
        def run_workflow(self, workflow_name, payload):
            result = super().run_workflow(workflow_name, payload)
            result["email_draft"] = (
                '{ "headline": "Upcoming Bills", "summary": "Raw summary", '
                '"email_draft": "Hello Team,\\n\\nPlease review the late bill.\\n\\nKind Regards,\\nMonetra Organisation" }'
            )
            return result

    email_service = FakeEmailService()
    service = AutomationService(
        JsonDraftAgentService(),
        FakeReportService(),
        email_service,
        FakeRunRepository(),
        FakeRecurringService(
            [
                {
                    "recurring_item_id": 1,
                    "date": "2026-06-10",
                    "description": "Monthly Test Late Deposit Reminder",
                    "amount": 12.5,
                    "entry_type": "expense",
                    "frequency": "monthly",
                    "days_until_due": -7,
                }
            ]
        ),
        FakeAnalyticsService(),
    )

    service.run_upcoming_bills_email_now()

    body = email_service.sent_messages[-1]["body"]
    assert "{ \"headline\"" not in body
    assert "Please review the late bill." in body
    assert body.count("Kind Regards") == 1


def test_all_upcoming_bills_email_includes_projected_schedule():
    repository = FakeRunRepository()
    email_service = FakeEmailService()
    service = AutomationService(
        FakeAgentService(),
        FakeReportService(),
        email_service,
        repository,
        FakeRecurringService(
            [
                {
                    "recurring_item_id": 1,
                    "date": "2026-03-25",
                    "description": "Due today",
                    "amount": 12.0,
                    "entry_type": "expense",
                    "frequency": "monthly",
                    "days_until_due": 0,
                },
                {
                    "recurring_item_id": 2,
                    "date": "2026-04-10",
                    "description": "Future bill",
                    "amount": 20.0,
                    "entry_type": "expense",
                    "frequency": "monthly",
                    "days_until_due": 16,
                },
            ],
            late_occurrences=[
                {
                    "recurring_item_id": 3,
                    "date": "2026-03-20",
                    "description": "Late bill",
                    "amount": 30.0,
                    "entry_type": "expense",
                    "frequency": "monthly",
                    "days_until_due": -5,
                }
            ],
        ),
        FakeAnalyticsService(),
    )

    result = service.run_all_upcoming_bills_email_now(recipient="registered-user@example.com")

    assert result["headline"] == "All upcoming bills emailed"
    assert result["summary"] == "All projected upcoming bills emailed to registered-user@example.com."
    body = email_service.sent_messages[-1]["body"]
    assert "Late bill" in body
    assert "Future bill" in body








