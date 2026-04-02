import json
import logging
from calendar import monthrange
from datetime import datetime
from pathlib import Path
from threading import Lock, Thread

from budget_tracker_api.repositories.agent_run_repository import AgentRunRepository
from budget_tracker_api.services.agent_service import AgentService
from budget_tracker_api.services.analytics_service import AnalyticsService
from budget_tracker_api.services.email_service import EmailService
from budget_tracker_api.services.recurring_service import RecurringService
from budget_tracker_api.services.report_service import ReportService

logger = logging.getLogger(__name__)


class AutomationService:
    def __init__(
        self,
        agent_service: AgentService,
        report_service: ReportService,
        email_service: EmailService,
        run_repository: AgentRunRepository,
        recurring_service: RecurringService,
        analytics_service: AnalyticsService,
        month_end_email_hour: int = 17,
        month_end_email_minute: int = 0,
    ):
        self._agent_service = agent_service
        self._report_service = report_service
        self._email_service = email_service
        self._run_repository = run_repository
        self._recurring_service = recurring_service
        self._analytics_service = analytics_service
        self._month_end_email_hour = max(0, min(23, int(month_end_email_hour)))
        self._month_end_email_minute = max(0, min(59, int(month_end_email_minute)))
        self._bootstrap_lock = Lock()
        self._bootstrap_running = False

    @staticmethod
    def _bootstrap_workflow_names() -> tuple[str, ...]:
        return (
            "month_end_close",
            "upcoming_bills_check",
            "cash_flow_recovery_plan",
        )

    def run_bootstrap_workflows(self) -> list[dict]:
        today_prefix = datetime.now().date().isoformat()
        runs: list[dict] = []
        for workflow_name in self._bootstrap_workflow_names():
            existing = self._run_repository.latest_run_for_day(workflow_name, today_prefix)
            if existing is not None:
                runs.append(existing)
                continue
            runs.append(self._agent_service.run_workflow(workflow_name, {}))
        return runs

    def run_bootstrap_workflows_async(self, flask_app) -> list[dict]:
        today_prefix = datetime.now().date().isoformat()
        runs: list[dict] = []
        missing: list[str] = []
        for workflow_name in self._bootstrap_workflow_names():
            existing = self._run_repository.latest_run_for_day(workflow_name, today_prefix)
            if existing is not None:
                runs.append(existing)
            else:
                missing.append(workflow_name)

        if missing:
            self._ensure_bootstrap_thread(flask_app, missing)

        return runs

    def queue_realtime_refresh(self, flask_app, event_type: str | None = None) -> list[dict]:
        normalized_event_type = str(event_type or "finance_state_changed").strip().lower() or "finance_state_changed"
        jobs: list[dict] = []
        for workflow_name in self._realtime_workflow_names(normalized_event_type):
            jobs.append(
                self._agent_service.start_workflow_run(
                    workflow_name,
                    {"task": self._workflow_refresh_task(workflow_name, normalized_event_type)},
                    flask_app,
                    reuse_active=True,
                )
            )
        return jobs

    @classmethod
    def _realtime_workflow_names(cls, event_type: str) -> tuple[str, ...]:
        if event_type in {
            "expense_created",
            "expense_updated",
            "expense_deleted",
            "expenses_imported",
            "monthly_income_updated",
            "monthly_budget_updated",
            "recurring_item_created",
            "recurring_item_updated",
            "recurring_item_deleted",
            "recurring_occurrence_paid",
            "recurring_occurrence_unpaid",
            "finance_state_changed",
            "ai_mutation",
        }:
            return cls._bootstrap_workflow_names()
        return cls._bootstrap_workflow_names()

    @staticmethod
    def _workflow_refresh_task(workflow_name: str, event_type: str) -> str:
        event_label = event_type.replace("_", " ")
        workflow_label = workflow_name.replace("_", " ")
        return (
            f"Refresh the {workflow_label} workflow because {event_label} changed. "
            "Use the latest live finance state so the automation summary reflects the current database."
        )

    def _ensure_bootstrap_thread(self, flask_app, workflow_names: list[str]) -> None:
        with self._bootstrap_lock:
            if self._bootstrap_running:
                logger.info(
                    "Automation bootstrap already running; skipping duplicate trigger."
                )
                return
            self._bootstrap_running = True

        thread = Thread(
            target=self._run_bootstrap_background,
            args=(flask_app, workflow_names),
            name="automation-bootstrap",
            daemon=True,
        )
        thread.start()

    def _run_bootstrap_background(self, flask_app, workflow_names: list[str]) -> None:
        logger.info(
            "Automation bootstrap background run started | workflows=%s",
            workflow_names,
        )
        try:
            with flask_app.app_context():
                today_prefix = datetime.now().date().isoformat()
                for workflow_name in workflow_names:
                    existing = self._run_repository.latest_run_for_day(
                        workflow_name, today_prefix
                    )
                    if existing is not None:
                        continue
                    try:
                        self._agent_service.run_workflow(workflow_name, {})
                        logger.info(
                            "Automation bootstrap workflow completed | workflow_name=%s",
                            workflow_name,
                        )
                    except Exception:
                        logger.exception(
                            "Automation bootstrap workflow failed | workflow_name=%s",
                            workflow_name,
                        )
        finally:
            with self._bootstrap_lock:
                self._bootstrap_running = False
            logger.info("Automation bootstrap background run finished.")

    def run_month_end_email_if_due(self) -> dict | None:
        now = datetime.now()
        if now.day != monthrange(now.year, now.month)[1]:
            return None
        if not self._is_month_end_send_time(now):
            return None

        today_prefix = now.date().isoformat()
        if self._run_repository.latest_run_for_day("month_end_email_dispatch", today_prefix):
            return None

        return self._dispatch_month_end_email(
            workflow_name="month_end_email_dispatch",
            workflow_label="Month-end email dispatch",
            task="Send the month-end report email automatically on the last day of the month at the configured dispatch time.",
            headline="Month-end report emailed",
            summary_template="Monthly PDF report emailed to {recipient}.",
            automated_actions_prefix=["Generated the month-end close workflow summary."],
        )

    def _is_month_end_send_time(self, now: datetime) -> bool:
        return (now.hour, now.minute) >= (
            self._month_end_email_hour,
            self._month_end_email_minute,
        )

    def run_month_end_email_now(self) -> dict:
        return self._dispatch_month_end_email(
            workflow_name="month_end_email_manual_dispatch",
            workflow_label="Month-end email manual dispatch",
            task="Manually send the current month's PDF report email now.",
            headline="Month-end report emailed manually",
            summary_template="Manual month-end PDF report emailed to {recipient}.",
            automated_actions_prefix=["Triggered the month-end close workflow manually."],
        )

    def run_upcoming_bills_email_if_due(self) -> dict | None:
        due_expenses = self._get_due_expenses_within_days(7)
        signature = self._upcoming_bills_signature(due_expenses)
        latest_run = self._run_repository.latest_run("upcoming_bills_email_dispatch")
        if latest_run and latest_run.get("task") == signature:
            return None

        return self._dispatch_upcoming_bills_email(
            due_expenses=due_expenses,
            signature=signature,
            workflow_name="upcoming_bills_email_dispatch",
            workflow_label="Upcoming bills email dispatch",
        )

    def run_upcoming_bills_email_now(self) -> dict:
        due_expenses = self._get_due_expenses_within_days(7)
        signature = self._upcoming_bills_signature(due_expenses)
        return self._dispatch_upcoming_bills_email(
            due_expenses=due_expenses,
            signature=signature,
            workflow_name="upcoming_bills_email_manual_dispatch",
            workflow_label="Upcoming bills email manual dispatch",
        )

    def _get_due_expenses_within_days(self, days: int) -> list[dict]:
        upcoming = self._recurring_service.upcoming_calendar(days)
        return [
            {
                "recurring_item_id": occurrence.get("recurring_item_id"),
                "date": occurrence.get("date"),
                "description": occurrence.get("description"),
                "amount": occurrence.get("amount"),
                "entry_type": occurrence.get("entry_type"),
                "frequency": occurrence.get("frequency"),
            }
            for occurrence in upcoming.get("occurrences", [])
            if occurrence.get("entry_type") == "expense"
        ]

    def _dispatch_month_end_email(
        self,
        *,
        workflow_name: str,
        workflow_label: str,
        task: str,
        headline: str,
        summary_template: str,
        automated_actions_prefix: list[str],
    ) -> dict:
        workflow_result = self._agent_service.run_workflow("month_end_close", {})
        report_path = self._report_service.generate_monthly_report()
        composed_email_body = self._compose_month_end_email_body(workflow_result, Path(report_path))
        email_result = self._email_service.send_report_email(
            subject=workflow_result["email_subject"],
            body=composed_email_body,
            attachment_path=Path(report_path),
        )
        return self._run_repository.create_run(
            {
                "workflow_name": workflow_name,
                "workflow_label": workflow_label,
                "status": "completed",
                "headline": headline,
                "summary": summary_template.format(recipient=email_result["recipient"]),
                "risk_level": workflow_result["risk_level"],
                "recommended_actions": workflow_result["recommended_actions"],
                "automated_actions": [
                    *automated_actions_prefix,
                    f"Emailed the monthly PDF report to {email_result['recipient']}.",
                ],
                "email_subject": email_result["subject"],
                "email_draft": composed_email_body,
                "task": task,
                "model": workflow_result["model"],
                "tools_used": workflow_result["tools_used"],
                "report_download_url": workflow_result["report_download_url"],
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            }
        )

    def _dispatch_upcoming_bills_email(
        self,
        *,
        due_expenses: list[dict],
        signature: str,
        workflow_name: str,
        workflow_label: str,
    ) -> dict:
        if due_expenses:
            workflow_result = self._agent_service.run_workflow("upcoming_bills_check", {})
            email_subject = workflow_result["email_subject"]
            email_body = workflow_result["email_draft"]
            headline = "Upcoming bills alert emailed"
            summary = "Upcoming bills alert emailed to {recipient} for items due within 7 days."
            risk_level = workflow_result["risk_level"]
            recommended_actions = workflow_result["recommended_actions"]
            automated_actions = [
                "Reviewed recurring bill pressure for the next 7 days.",
                "Prepared an updated upcoming-bills summary.",
            ]
            model = workflow_result["model"]
            tools_used = workflow_result["tools_used"]
            report_download_url = workflow_result["report_download_url"]
        else:
            email_subject = "Upcoming bills update: no bills due in the next 7 days"
            email_body = (
                "Your upcoming bills list has been refreshed. There are currently no expense reminders due within the next 7 days."
            )
            headline = "Upcoming bills cleared email sent"
            summary = "Upcoming bills update emailed to {recipient}; there are no expense reminders due within 7 days."
            risk_level = "low"
            recommended_actions = ["No immediate bill payments are due in the next 7 days."]
            automated_actions = [
                "Detected that the upcoming expense reminders list changed.",
                "Prepared the latest all-clear upcoming-bills update.",
            ]
            model = "system"
            tools_used = ["upcoming_bills_change_detection"]
            report_download_url = None

        email_result = self._email_service.send_email(
            subject=email_subject,
            body=email_body,
        )
        return self._run_repository.create_run(
            {
                "workflow_name": workflow_name,
                "workflow_label": workflow_label,
                "status": "completed",
                "headline": headline,
                "summary": summary.format(recipient=email_result["recipient"]),
                "risk_level": risk_level,
                "recommended_actions": recommended_actions,
                "automated_actions": [
                    *automated_actions,
                    f"Emailed the latest upcoming-bills update to {email_result['recipient']}.",
                ],
                "email_subject": email_result["subject"],
                "email_draft": email_body,
                "task": signature,
                "model": model,
                "tools_used": tools_used,
                "report_download_url": report_download_url,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            }
        )

    def _compose_month_end_email_body(self, workflow_result: dict, report_path: Path) -> str:
        dashboard = self._analytics_service.dashboard()
        month_label = str(dashboard.get("month_label") or datetime.now().strftime("%B %Y"))
        monthly_budget = float(dashboard.get("monthly_budget") or 0.0)
        monthly_expenses = float(
            dashboard.get("current_month_total")
            or dashboard.get("monthly_expenses")
            or 0.0
        )
        monthly_income = float(dashboard.get("monthly_income") or 0.0)
        net_cash_flow = float(dashboard.get("net_cash_flow") or 0.0)
        budget_delta = round(monthly_budget - monthly_expenses, 2)

        if budget_delta >= 0:
            budget_sentence = f"Spending stayed within the monthly budget by GBP {budget_delta:.2f}."
        else:
            budget_sentence = f"Spending exceeded the monthly budget by GBP {abs(budget_delta):.2f}."

        if net_cash_flow >= 0:
            cash_flow_sentence = f"Net cash flow for {month_label} was positive at GBP {net_cash_flow:.2f}."
        else:
            cash_flow_sentence = f"Net cash flow for {month_label} was negative at GBP {abs(net_cash_flow):.2f}."

        lines = [
            f"Month-end summary for {month_label}.",
            f"Total income for the month was GBP {monthly_income:.2f}.",
            f"Total spending for the month was GBP {monthly_expenses:.2f} against a monthly budget of GBP {monthly_budget:.2f}.",
            cash_flow_sentence,
            budget_sentence,
            f"The PDF report is attached as {report_path.name}.",
        ]

        workflow_summary = self._normalize_email_paragraph(workflow_result.get("summary"))
        if workflow_summary:
            lines.extend(["", workflow_summary])

        recommended_actions = self._normalize_email_list(workflow_result.get("recommended_actions"))
        if recommended_actions:
            lines.extend(["", "Recommended actions:"])
            lines.extend(f"- {action}" for action in recommended_actions[:3])

        lines.extend(["", "Best regards,", "Rushabh Dharamshi"])
        return "\n".join(lines)

    @staticmethod
    def _normalize_email_paragraph(text: object) -> str:
        if text is None:
            return ""
        if isinstance(text, (list, tuple)):
            text = " ".join(str(item) for item in text if str(item).strip())
        normalized = " ".join(str(text).replace("\r", " ").replace("\n", " ").split())
        return normalized.strip()

    @classmethod
    def _normalize_email_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            normalized = cls._normalize_email_paragraph(value)
            return [normalized] if normalized else []
        if isinstance(value, (list, tuple)):
            items: list[str] = []
            for item in value:
                normalized = cls._normalize_email_paragraph(item)
                if normalized:
                    items.append(normalized)
            return items
        normalized = cls._normalize_email_paragraph(value)
        return [normalized] if normalized else []

    @staticmethod
    def _upcoming_bills_signature(due_expenses: list[dict]) -> str:
        normalized = sorted(
            due_expenses,
            key=lambda item: (
                str(item.get("date") or ""),
                str(item.get("description") or ""),
                int(item.get("recurring_item_id") or 0),
            ),
        )
        return "UPCOMING_BILLS_SIGNATURE:" + json.dumps(normalized, sort_keys=True)


