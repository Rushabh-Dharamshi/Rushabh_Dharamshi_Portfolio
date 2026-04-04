from datetime import datetime

import budget_tracker_api.services.automation_service as automation_module
from budget_tracker_api.services.automation_service import AutomationService

from tests.unit.test_automation_service import (
    FakeAnalyticsService,
    FakeEmailService,
    FakeRecurringService,
    FakeReportService,
    FakeRunRepository,
)


class RecordingAgentService:
    def __init__(self):
        self.workflow_runs = []
        self.jobs = []

    def run_workflow(self, workflow_name, payload):
        self.workflow_runs.append((workflow_name, payload))
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

    def start_workflow_run(self, workflow_name, payload, flask_app, reuse_active=False):
        job = {"id": f"{workflow_name}-job", "workflow_name": workflow_name, "payload": payload, "reuse_active": reuse_active}
        self.jobs.append(job)
        return job


class AppContextStub:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False


class FlaskAppStub:
    def app_context(self):
        return AppContextStub()


def make_service(agent_service=None, recurring_occurrences=None, repository=None):
    repository = repository or FakeRunRepository()
    email_service = FakeEmailService()
    service = AutomationService(
        agent_service or RecordingAgentService(),
        FakeReportService(),
        email_service,
        repository,
        FakeRecurringService(recurring_occurrences or []),
        FakeAnalyticsService(),
        month_end_email_hour=22,
        month_end_email_minute=15,
    )
    return service, repository, email_service


def test_automation_service_bootstrap_refresh_and_helpers(monkeypatch):
    agent_service = RecordingAgentService()
    service, repository, _ = make_service(agent_service=agent_service)

    bootstrap_runs = service.run_bootstrap_workflows()
    assert [run["risk_level"] for run in bootstrap_runs] == ["low", "medium", "low"]
    assert [name for name, _ in agent_service.workflow_runs] == list(service._bootstrap_workflow_names())

    repeated = service.run_bootstrap_workflows()
    assert repeated == bootstrap_runs

    fake_app = FlaskAppStub()
    today_prefix = datetime.now().date().isoformat()
    repository.runs = [
        {"workflow_name": "month_end_close", "generated_at": f"{today_prefix}T09:00:00", "risk_level": "low"},
        {"workflow_name": "upcoming_bills_check", "generated_at": f"{today_prefix}T09:00:01", "risk_level": "medium"},
        {"workflow_name": "cash_flow_recovery_plan", "generated_at": f"{today_prefix}T09:00:02", "risk_level": "low"},
    ]
    queued_existing = service.run_bootstrap_workflows_async(fake_app)
    assert [run["workflow_name"] for run in queued_existing] == ["month_end_close", "upcoming_bills_check", "cash_flow_recovery_plan"]

    repository.runs = []
    ensured = []
    monkeypatch.setattr(service, "_ensure_bootstrap_thread", lambda flask_app, workflow_names: ensured.append((flask_app, workflow_names)))
    async_result = service.run_bootstrap_workflows_async(fake_app)
    assert async_result == []
    assert ensured == [(fake_app, list(service._bootstrap_workflow_names()))]

    refresh_jobs = service.queue_realtime_refresh(fake_app, "expense_created")
    assert len(refresh_jobs) == 3
    assert all(job["reuse_active"] is True for job in refresh_jobs)
    assert "expense created changed" in agent_service.jobs[0]["payload"]["task"]
    assert service._workflow_refresh_task("month_end_close", "finance_state_changed").startswith("Refresh the month end close workflow")
    assert service._realtime_workflow_names("unknown_event") == service._bootstrap_workflow_names()


def test_automation_service_bootstrap_thread_and_dispatch_variants(monkeypatch):
    agent_service = RecordingAgentService()
    service, _, email_service = make_service(
        agent_service=agent_service,
        recurring_occurrences=[
            {
                "recurring_item_id": 3,
                "date": "2026-03-25",
                "description": "Salary",
                "amount": 1200.0,
                "entry_type": "income",
                "frequency": "monthly",
            }
        ],
    )

    started_threads = []

    class FakeThread:
        def __init__(self, target, args, name, daemon):
            self.target = target
            self.args = args
            started_threads.append((name, daemon))

        def start(self):
            self.target(*self.args)

    monkeypatch.setattr(automation_module, "Thread", FakeThread)
    service._ensure_bootstrap_thread(FlaskAppStub(), ["month_end_close"])
    assert started_threads == [("automation-bootstrap", True)]

    service._bootstrap_running = True
    service._ensure_bootstrap_thread(None, ["month_end_close"])
    assert len(started_threads) == 1

    class FakeDateTime:
        @classmethod
        def now(cls):
            return datetime(2026, 3, 30, 22, 15, 0)

    monkeypatch.setattr(automation_module, "datetime", FakeDateTime)
    assert service.run_month_end_email_if_due() is None

    due_expenses = service._get_due_expenses_within_days(7)
    assert due_expenses == []
    upcoming = service.run_upcoming_bills_email_now()
    assert upcoming["headline"] == "Upcoming bills cleared email sent"
    assert email_service.sent_messages[-1]["subject"] == "Upcoming bills update: no bills due in the next 7 days"
    assert service._upcoming_bills_signature(
        [{"recurring_item_id": 2, "date": "2026-04-02", "description": "B"}, {"recurring_item_id": 1, "date": "2026-04-01", "description": "A"}]
    ).startswith("UPCOMING_BILLS_SIGNATURE:")
    assert service._normalize_email_paragraph(["hello", "world"]) == "hello world"
    assert service._normalize_email_list("single") == ["single"]
    assert service._normalize_email_list([" one ", None, "two"]) == ["one", "two"]
