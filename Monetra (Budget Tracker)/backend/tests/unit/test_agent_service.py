from budget_tracker_api.errors import ValidationError
from budget_tracker_api.services.agent_service import AgentService
from datetime import datetime, timedelta


class FakeOllamaClient:
    model = "qwen3:4b"

    def __init__(self):
        self.calls = 0

    def chat(self, messages, tools=None):
        self.calls += 1
        if self.calls == 1:
            return {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"function": {"name": "get_dashboard_summary", "arguments": {}}},
                        {"function": {"name": "generate_monthly_report", "arguments": {}}},
                    ],
                }
            }
        return {
            "message": {
                "role": "assistant",
                "content": (
                    '{"headline":"March finance briefing","summary":"Cash flow remains positive.",'
                    '"risk_level":"low","recommended_actions":["Maintain current travel spend controls"],'
                    '"email_subject":"March finance briefing","email_draft":"Monthly briefing attached."}'
                ),
            }
        }


class FakeAnalyticsService:
    def dashboard(self):
        return {"monthly_budget": 1200.0, "net_cash_flow": 400.0}

    def financial_pulse(self):
        return {"health_score": 82}

    def category_insights(self):
        return {"top_categories": [{"category": "Travel", "amount": 80.0}]}


class FakePredictionService:
    def predict_next_month(self):
        return {"predicted_spending": 910.0}


class FailingPredictionService(FakePredictionService):
    def predict_next_month(self):
        raise ValidationError("No expense data available for prediction.")


class FakeSettingsService:
    def __init__(self):
        self.monthly_budget = 1200.0
        self.monthly_income = 1500.0

    def get_monthly_budget(self, month_key=None):
        return self.monthly_budget

    def get_monthly_income(self, month_key=None):
        return self.monthly_income

    def update_monthly_budget(self, payload):
        self.monthly_budget = round(float(payload["monthly_budget"]), 2)
        return {"monthly_budget": self.monthly_budget, "budget_month": payload.get("month") or "2026-06"}

    def update_monthly_income(self, payload):
        self.monthly_income = round(float(payload["monthly_income"]), 2)
        return {"monthly_income": self.monthly_income}


class FakeRecurringService:
    def upcoming_calendar(self, days):
        return {"window_end": "2026-04-10", "occurrences": [{"description": "Rent"}], "days": days}


class FakeReportService:
    def generate_monthly_report(self):
        return "report.pdf"


class FakeExpenseService:
    def list_expenses(self, sort_direction="desc"):
        return [{"id": 1, "date": "2026-03-20", "category": "Travel", "description": "Train pass", "amount": 80.0, "entry_type": "expense"}, {"id": 2, "date": "2026-03-01", "category": "Housing", "description": "Rent", "amount": 700.0, "entry_type": "expense"}]


class FakeAgentRunRepository:
    def __init__(self):
        self.runs = []

    def create_run(self, payload):
        run = {"id": len(self.runs) + 1, **payload}
        self.runs.append(run)
        return run

    def list_runs(self, limit=8):
        return self.runs[:limit]


def test_agent_service_runs_tool_loop_and_returns_structured_briefing():
    service = AgentService(
        FakeOllamaClient(),
        FakeAnalyticsService(),
        FakePredictionService(),
        FakeRecurringService(),
        FakeReportService(),
        FakeExpenseService(),
        FakeSettingsService(),
        FakeAgentRunRepository(),
    )

    result = service.run_finance_briefing({"task": "Create a concise finance briefing."})

    assert result["headline"] == "March finance briefing"
    assert result["model"] == "qwen3:4b"
    assert "get_dashboard_summary" in result["tools_used"]
    assert result["report_download_url"] == "/api/reports/monthly"


def test_agent_service_generates_report_from_prompt_chip_without_model_round_trip():
    ollama_client = FakeOllamaClient()

    class RecordingReportService(FakeReportService):
        def __init__(self):
            self.calls = 0

        def generate_monthly_report(self):
            self.calls += 1
            return "report.pdf"

    report_service = RecordingReportService()
    service = AgentService(
        ollama_client,
        FakeAnalyticsService(),
        FakePredictionService(),
        FakeRecurringService(),
        report_service,
        FakeExpenseService(),
        FakeSettingsService(),
        FakeAgentRunRepository(),
    )

    result = service.run_finance_briefing(
        {"task": "Generate the current monthly report and summarise the main budget pressure points."}
    )

    assert result["headline"] == "Monthly report generated"
    assert result["action_result"]["type"] == "monthly_report_generated"
    assert result["report_download_url"] == "/api/reports/monthly"
    assert report_service.calls == 1
    assert ollama_client.calls == 0


def test_agent_service_formats_python_style_briefing_payload():
    result = AgentService._parse_final_payload(
        "{'cash_flow': 'Cash flow is currently strong with a net cash flow of £2388.35.', "
        "'recurring_bills': 'Test Late Deposit is due on July 10th for £12.50.', "
        "'recommended_actions': ['Monitor Food and Travel.', 'Review the July forecast.']}"
    )

    assert result["headline"] == "Finance briefing generated"
    assert "Cash flow: Cash flow is currently strong" in result["summary"]
    assert "Recurring bill pressure: Test Late Deposit" in result["summary"]
    assert result["recommended_actions"] == ["Monitor Food and Travel.", "Review the July forecast."]
    assert "Monthly finance briefing" in result["email_draft"]
    assert "Kind Regards,\nMonetra Organisation" in result["email_draft"]
    assert "{'cash_flow'" not in result["summary"]


def test_agent_service_formats_relaxed_json_payload_without_raw_braces():
    result = AgentService._parse_final_payload(
        '{ "headline": "Upcoming Bills and Late Payments for June 2026", '
        '"summary": "This month cash flow remains within budget.", '
        '"risk_level": "Low", '
        '"recommended_actions": "Please settle late payments and review due dates.", '
        '"email_subject": "Reminder: Upcoming Bills", '
        '"email_draft": "Hello Team,\n\nIncluded reminders:\n- late unpaid reminders\n\nBills included:\n- Monthly Test Late Deposit Reminder\n\nKind Regards,\nMonetra Organisation" }'
    )

    assert result["headline"] == "Upcoming Bills and Late Payments for June 2026"
    assert result["summary"] == "This month cash flow remains within budget."
    assert result["recommended_actions"] == ["Please settle late payments and review due dates."]
    assert "Hello Team" in result["email_draft"]
    assert "{ \"headline\"" not in result["summary"]
    assert "{ \"headline\"" not in result["email_draft"]
    assert result["email_draft"].count("Kind Regards") == 1


def test_agent_service_enriches_sparse_cfo_briefing_from_tool_context():
    sparse_payload = AgentService._parse_final_payload(
        "{'cash_flow': 2388.35, 'recommended_actions': ['Review and categorize recent expenses.']}"
    )
    context = {
        "dashboard": {
            "month_label": "June 2026",
            "monthly_budget": 600.0,
            "monthly_income": 2400.0,
            "monthly_expenses": 11.65,
            "net_cash_flow": 2388.35,
            "remaining_budget": 588.35,
            "status": "within",
        },
        "category_insights": {
            "top_categories": [
                {"category": "Food", "amount": 13.0},
                {"category": "Travel", "amount": 6.4},
            ]
        },
        "prediction": {"predicted_spending": 207.62},
        "upcoming_recurring_items": {
            "next_occurrences": [
                {"description": "Test Late Deposit", "amount": 12.5, "due_date": "2026-07-10"}
            ]
        },
    }

    result = AgentService._enrich_sparse_cfo_briefing(
        sparse_payload,
        context,
        "Prepare a CFO-style monthly finance briefing with cash-flow risk and an email-ready summary.",
    )

    assert result["headline"] == "June 2026 CFO-style finance briefing"
    assert "Cash-flow risk:" in result["summary"]
    assert "Budget pressure:" in result["summary"]
    assert "Recurring bill pressure:" in result["summary"]
    assert "Spending pressure:" in result["summary"]
    assert "Forecast:" in result["summary"]
    assert "Subject: [Monetra] June 2026 Monthly Finance Briefing" in result["email_draft"]
    assert "Cash-flow and budget position:" in result["email_draft"]
    assert "Spending and forecast:" in result["email_draft"]
    assert "Test Late Deposit" in result["email_draft"]
    assert "Recommended actions:" in result["email_draft"]
    assert "Review and categorize recent expenses." in result["recommended_actions"]
    assert "Kind Regards,\nMonetra Organisation" in result["email_draft"]


def test_agent_service_completes_exact_cfo_prompt_when_model_response_is_incomplete():
    incomplete_payload = AgentService._parse_final_payload(
        '{"headline":"Finance briefing","summary":"Cash flow remains positive.",'
        '"risk_level":"low","recommended_actions":["Monitor spend."],'
        '"email_subject":"Briefing","email_draft":"Monthly briefing attached."}'
    )
    context = {
        "dashboard": {
            "month_label": "June 2026",
            "monthly_budget": 600.0,
            "monthly_income": 2400.0,
            "monthly_expenses": 11.65,
            "net_cash_flow": 2388.35,
            "remaining_budget": 588.35,
            "status": "within",
        },
        "category_insights": {"top_categories": [{"category": "Travel", "amount": 6.4}]},
        "prediction": {"predicted_spending": 207.62},
        "upcoming_recurring_items": {
            "next_occurrences": [
                {"description": "Test Late Deposit", "amount": 12.5, "due_date": "2026-07-10"}
            ]
        },
    }

    result = AgentService._enrich_sparse_cfo_briefing(
        incomplete_payload,
        context,
        "Prepare a CFO-style monthly finance briefing with cash-flow risk, recurring bill pressure, recommended actions, and an email-ready summary.",
    )

    assert "Cash-flow risk:" in result["summary"]
    assert "Recurring bill pressure:" in result["summary"]
    assert result["recommended_actions"]
    assert "Subject: [Monetra] June 2026 Monthly Finance Briefing" in result["email_draft"]
    assert "Recommended actions:" in result["email_draft"]


def test_agent_service_handles_prediction_validation_gracefully():
    class PredictionFirstOllamaClient(FakeOllamaClient):
        def chat(self, messages, tools=None):
            self.calls += 1
            if self.calls == 1:
                return {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {"function": {"name": "get_spending_prediction", "arguments": {}}}
                        ],
                    }
                }
            return {
                "message": {
                    "role": "assistant",
                    "content": "Fallback narrative",
                }
            }

    service = AgentService(
        PredictionFirstOllamaClient(),
        FakeAnalyticsService(),
        FailingPredictionService(),
        FakeRecurringService(),
        FakeReportService(),
        FakeExpenseService(),
        FakeSettingsService(),
        FakeAgentRunRepository(),
    )

    result = service.run_finance_briefing({})

    assert result["headline"] == "Current Month CFO-style finance briefing"
    assert "Cash-flow risk:" in result["summary"]
    assert "Forecast: Prediction was unavailable" in result["summary"]


def test_agent_service_email_ready_briefing_is_not_direct_email_dispatch():
    service = AgentService(
        FakeOllamaClient(),
        FakeAnalyticsService(),
        FakePredictionService(),
        FakeRecurringService(),
        FakeReportService(),
        FakeExpenseService(),
        FakeSettingsService(),
        FakeAgentRunRepository(),
    )

    assert service._run_direct_email_dispatch_if_requested("Prepare an email-ready summary") is None
    assert service._run_direct_email_dispatch_if_requested("send me a summary") is None
    assert service._normalized_text_matches("chat gpt pro", "chat gpt plus") is False


def test_agent_service_runs_workflow_and_logs_the_result():
    repository = FakeAgentRunRepository()

    class WorkflowOllamaClient:
        model = "mistral:latest"

        def chat(self, messages, tools=None):
            return {
                "message": {
                    "role": "assistant",
                    "content": (
                        '{"headline":"Month-end pack ready","summary":"The KPI pack has been refreshed.",'
                        '"risk_level":"low","recommended_actions":["Share the pack with stakeholders"],'
                        '"email_subject":"Month-end pack ready","email_draft":"The report and summary are ready."}'
                    ),
                }
            }

    service = AgentService(
        WorkflowOllamaClient(),
        FakeAnalyticsService(),
        FakePredictionService(),
        FakeRecurringService(),
        FakeReportService(),
        FakeExpenseService(),
        FakeSettingsService(),
        repository,
    )

    result = service.run_workflow("month_end_close", {})

    assert result["workflow_name"] == "month_end_close"
    assert result["workflow_label"] == "Month-end close"
    assert result["automated_actions"]
    assert result["tools_used"]
    assert repository.list_runs(1)[0]["workflow_name"] == "month_end_close"


def test_agent_service_can_create_a_recurring_reminder_from_prompt():
    repository = FakeAgentRunRepository()

    class ReminderOllamaClient:
        model = "mistral:latest"

        def chat(self, messages, tools=None):
            return {
                "message": {
                    "role": "assistant",
                    "content": (
                        '{"category":"Housing","description":"Rent","amount":850,'
                        '"entry_type":"expense","frequency":"weekly","start_date":"2026-03-27","active":true}'
                    ),
                }
            }

    class RecordingRecurringService(FakeRecurringService):
        def __init__(self):
            self.created_payload = None

        def create_item(self, payload):
            self.created_payload = payload
            return {"id": 9, **payload}

    recurring_service = RecordingRecurringService()
    service = AgentService(
        ReminderOllamaClient(),
        FakeAnalyticsService(),
        FakePredictionService(),
        recurring_service,
        FakeReportService(),
        FakeExpenseService(),
        FakeSettingsService(),
        repository,
    )

    result = service.run_finance_briefing(
        {"task": "Add a weekly reminder for rent of 850 starting 2026-03-27"}
    )

    assert result["headline"] == "Recurring reminder created"
    assert result["action_result"]["type"] == "recurring_item_created"
    assert recurring_service.created_payload["description"] == "Rent"


def test_agent_service_updates_existing_weekly_reminder_and_normalizes_next_monday():
    repository = FakeAgentRunRepository()

    class ReminderOllamaClient:
        model = "mistral:latest"

        def chat(self, messages, tools=None):
            return {
                "message": {
                    "role": "assistant",
                    "content": (
                        '{"category":"Transportation","description":"Train Cost","amount":15.30,'
                        '"entry_type":"expense","frequency":"weekly","start_date":"2026-03-29","active":true}'
                    ),
                }
            }

    class UpdatingRecurringService(FakeRecurringService):
        def __init__(self):
            self.items = [
                {
                    "id": 2,
                    "category": "Transportation",
                    "description": "Train Cost",
                    "amount": 15.30,
                    "entry_type": "expense",
                    "frequency": "weekly",
                    "start_date": "2026-03-29",
                    "active": True,
                },
                {
                    "id": 4,
                    "category": "Transportation",
                    "description": "Train Cost",
                    "amount": 15.30,
                    "entry_type": "expense",
                    "frequency": "weekly",
                    "start_date": "2026-03-29",
                    "active": True,
                },
            ]
            self.updated_payload = None
            self.deleted_ids = []

        def list_items(self):
            return self.items

        def update_item(self, item_id, payload):
            self.updated_payload = (item_id, payload)
            return {"id": item_id, **payload}

        def delete_item(self, item_id):
            self.deleted_ids.append(item_id)

    recurring_service = UpdatingRecurringService()
    service = AgentService(
        ReminderOllamaClient(),
        FakeAnalyticsService(),
        FakePredictionService(),
        recurring_service,
        FakeReportService(),
        FakeExpenseService(),
        FakeSettingsService(),
        repository,
    )

    result = service.run_finance_briefing(
        {"task": "Add a weekly reminder of train cost of 15.30 pounds starting next Monday not Sunday."}
    )

    today = datetime.now().date()
    days_ahead = (0 - today.weekday()) % 7
    expected_monday = today + timedelta(days=7 if days_ahead == 0 else days_ahead)
    assert result["headline"] == "Recurring reminder updated"
    assert result["action_result"]["type"] == "recurring_item_updated"
    assert recurring_service.updated_payload[1]["start_date"] == expected_monday.isoformat()
    assert recurring_service.deleted_ids == [4]


def test_agent_service_can_delete_a_recurring_reminder_from_prompt():
    repository = FakeAgentRunRepository()

    class ReminderOllamaClient:
        model = "mistral:latest"

        def chat(self, messages, tools=None):
            return {
                "message": {
                    "role": "assistant",
                    "content": (
                        '{"operation":"delete","target":{"description":"Utility Bills","frequency":"weekly","entry_type":"expense"}}'
                    ),
                }
            }

    class DeletingRecurringService(FakeRecurringService):
        def __init__(self):
            self.items = [
                {
                    "id": 3,
                    "category": "Utilities",
                    "description": "Utility Bills",
                    "amount": 12.75,
                    "entry_type": "expense",
                    "frequency": "weekly",
                    "start_date": "2026-03-22",
                    "active": True,
                }
            ]
            self.deleted_ids = []

        def list_items(self):
            return self.items

        def delete_item(self, item_id):
            self.deleted_ids.append(item_id)

    recurring_service = DeletingRecurringService()
    service = AgentService(
        ReminderOllamaClient(),
        FakeAnalyticsService(),
        FakePredictionService(),
        recurring_service,
        FakeReportService(),
        FakeExpenseService(),
        FakeSettingsService(),
        repository,
    )

    result = service.run_finance_briefing(
        {"task": "Remove the weekly utility bills reminder."}
    )

    assert result["headline"] == "Recurring reminder deleted"
    assert result["action_result"]["type"] == "recurring_item_deleted"
    assert recurring_service.deleted_ids == [3]



def test_agent_service_can_update_monthly_budget_from_prompt():
    repository = FakeAgentRunRepository()

    class CommandOllamaClient:
        model = "mistral:latest"

        def chat(self, messages, tools=None):
            return {
                "message": {
                    "role": "assistant",
                    "content": '{"domain":"settings","operation":"update","setting_key":"monthly_budget","value":1650}',
                }
            }

    settings_service = FakeSettingsService()
    service = AgentService(
        CommandOllamaClient(),
        FakeAnalyticsService(),
        FakePredictionService(),
        FakeRecurringService(),
        FakeReportService(),
        FakeExpenseService(),
        settings_service,
        repository,
    )

    result = service.run_finance_briefing({"task": "Set my monthly budget to 1650 pounds."})

    assert result["headline"] == "Monthly budget updated"
    assert result["action_result"]["type"] == "monthly_budget_updated"
    assert settings_service.monthly_budget == 1650.0


def test_agent_service_can_create_transaction_from_prompt():
    repository = FakeAgentRunRepository()

    class CommandOllamaClient:
        model = "mistral:latest"

        def chat(self, messages, tools=None):
            return {
                "message": {
                    "role": "assistant",
                    "content": (
                        '{"domain":"expense","operation":"create","entity":{"date":"2026-03-22","category":"Travel","description":"Tube fare","amount":6.40,"entry_type":"expense"}}'
                    ),
                }
            }

    class RecordingExpenseService(FakeExpenseService):
        def __init__(self):
            self.created_payload = None

        def create_expense(self, payload):
            self.created_payload = payload
            return {"id": 11, **payload}

        def list_expenses(self, sort_direction="desc"):
            return []

    expense_service = RecordingExpenseService()
    service = AgentService(
        CommandOllamaClient(),
        FakeAnalyticsService(),
        FakePredictionService(),
        FakeRecurringService(),
        FakeReportService(),
        expense_service,
        FakeSettingsService(),
        repository,
    )

    result = service.run_finance_briefing({"task": "Add an expense for Tube fare of 6.40 pounds today under travel."})

    assert result["headline"] == "Expense created"
    assert result["action_result"]["type"] == "expense_created"
    assert expense_service.created_payload["entry_type"] == "expense"
    assert expense_service.created_payload["description"] == "Tube fare"




def test_agent_service_can_replace_weekly_utility_bills_without_start_date_in_payload():
    repository = FakeAgentRunRepository()

    class ReminderOllamaClient:
        model = "mistral:latest"

        def chat(self, messages, tools=None):
            return {
                "message": {
                    "role": "assistant",
                    "content": (
                        '{"operation":"replace","category":"Utilities","description":"Utility Bills","amount":24.51,"entry_type":"expense","frequency":"monthly","active":true}'
                    ),
                }
            }

    class ReplacingRecurringService(FakeRecurringService):
        def __init__(self):
            self.items = [
                {
                    "id": 8,
                    "category": "Utilities",
                    "description": "Utility Bills",
                    "amount": 11.00,
                    "entry_type": "expense",
                    "frequency": "weekly",
                    "start_date": "2026-03-16",
                    "active": True,
                }
            ]
            self.deleted_ids = []
            self.created_payload = None

        def list_items(self):
            return self.items

        def delete_item(self, item_id):
            self.deleted_ids.append(item_id)

        def create_item(self, payload):
            self.created_payload = payload
            return {"id": 9, **payload}

    recurring_service = ReplacingRecurringService()
    service = AgentService(
        ReminderOllamaClient(),
        FakeAnalyticsService(),
        FakePredictionService(),
        recurring_service,
        FakeReportService(),
        FakeExpenseService(),
        FakeSettingsService(),
        repository,
    )

    result = service.run_finance_briefing(
        {"task": "Replace weekly utility bills with monthly utility bills of 24.51 pounds on the 23rd of each month."}
    )

    assert result["headline"] == "Recurring reminder replaced"
    assert result["action_result"]["type"] == "recurring_item_replaced"
    assert recurring_service.deleted_ids == [8]
    assert recurring_service.created_payload["start_date"].endswith("-23")
def test_agent_service_can_replace_weekly_utility_bills_with_monthly_prompt():
    repository = FakeAgentRunRepository()

    class ReminderOllamaClient:
        model = "mistral:latest"

        def chat(self, messages, tools=None):
            return {
                "message": {
                    "role": "assistant",
                    "content": (
                        '{"operation":"replace","category":"Utilities","description":"Utility Bills","amount":24.51,"entry_type":"expense","frequency":"monthly","start_date":"2026-03-23","active":true}'
                    ),
                }
            }

    class ReplacingRecurringService(FakeRecurringService):
        def __init__(self):
            self.items = [
                {
                    "id": 6,
                    "category": "Utilities",
                    "description": "Utility Bills",
                    "amount": 11.00,
                    "entry_type": "expense",
                    "frequency": "weekly",
                    "start_date": "2026-03-16",
                    "active": True,
                }
            ]
            self.deleted_ids = []
            self.created_payload = None

        def list_items(self):
            return self.items

        def delete_item(self, item_id):
            self.deleted_ids.append(item_id)

        def create_item(self, payload):
            self.created_payload = payload
            return {"id": 7, **payload}

    recurring_service = ReplacingRecurringService()
    service = AgentService(
        ReminderOllamaClient(),
        FakeAnalyticsService(),
        FakePredictionService(),
        recurring_service,
        FakeReportService(),
        FakeExpenseService(),
        FakeSettingsService(),
        repository,
    )

    result = service.run_finance_briefing(
        {"task": "Replace weekly utility bills with monthly utility bills of 24.51 pounds on the 23rd of each month."}
    )

    assert result["headline"] == "Recurring reminder replaced"
    assert result["action_result"]["type"] == "recurring_item_replaced"
    assert recurring_service.deleted_ids == [6]
    assert recurring_service.created_payload["frequency"] == "monthly"
    assert recurring_service.created_payload["amount"] == 24.51



def test_agent_service_can_create_bounded_monthly_reminder_from_inclusive_month_range():
    repository = FakeAgentRunRepository()

    class ReminderOllamaClient:
        model = "mistral:latest"

        def chat(self, messages, tools=None):
            return {
                "message": {
                    "role": "assistant",
                    "content": (
                        '{"category":"Rent","description":"University House Rent","amount":452.74,'
                        '"entry_type":"expense","frequency":"monthly","active":true}'
                    ),
                }
            }

    class RecordingRecurringService(FakeRecurringService):
        def __init__(self):
            self.created_payload = None

        def list_items(self):
            return []

        def create_item(self, payload):
            self.created_payload = payload
            return {"id": 12, **payload}

    recurring_service = RecordingRecurringService()
    service = AgentService(
        ReminderOllamaClient(),
        FakeAnalyticsService(),
        FakePredictionService(),
        recurring_service,
        FakeReportService(),
        FakeExpenseService(),
        FakeSettingsService(),
        repository,
    )

    result = service.run_finance_briefing(
        {
            "task": "Set a monthly reminder for university house rent on the 23rd of every month from April 2026 to June 2026 inclusive at 452.74 pounds."
        }
    )

    assert result["headline"] == "Recurring reminder created"
    assert recurring_service.created_payload["start_date"] == "2026-04-23"
    assert recurring_service.created_payload["end_date"] == "2026-06-23"


def test_agent_service_can_create_bounded_monthly_reminder_from_exclusive_month_range():
    repository = FakeAgentRunRepository()

    class ReminderOllamaClient:
        model = "mistral:latest"

        def chat(self, messages, tools=None):
            return {
                "message": {
                    "role": "assistant",
                    "content": (
                        '{"category":"Rent","description":"University House Rent","amount":452.74,'
                        '"entry_type":"expense","frequency":"monthly","active":true}'
                    ),
                }
            }

    class RecordingRecurringService(FakeRecurringService):
        def __init__(self):
            self.created_payload = None

        def list_items(self):
            return []

        def create_item(self, payload):
            self.created_payload = payload
            return {"id": 13, **payload}

    recurring_service = RecordingRecurringService()
    service = AgentService(
        ReminderOllamaClient(),
        FakeAnalyticsService(),
        FakePredictionService(),
        recurring_service,
        FakeReportService(),
        FakeExpenseService(),
        FakeSettingsService(),
        repository,
    )

    service.run_finance_briefing(
        {
            "task": "Set a monthly reminder for university house rent due on the 23rd of every month from April 2026 to June 2026 exclusive at 452.74 pounds."
        }
    )

    assert recurring_service.created_payload["start_date"] == "2026-04-23"
    assert recurring_service.created_payload["end_date"] == "2026-05-23"
