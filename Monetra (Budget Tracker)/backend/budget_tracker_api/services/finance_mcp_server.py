from collections.abc import Callable

from budget_tracker_api.errors import ValidationError


class FinanceMcpServer:
    def __init__(self, handlers: dict[str, Callable[[dict], dict]]):
        self._handlers = handlers
        self._tools = [
            {
                "name": "get_dashboard_summary",
                "description": "Read the current monthly budget, income, expenses, and cash-flow summary.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_financial_pulse",
                "description": "Read finance health signals such as cash-in, cash-out, runway, and spend velocity.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_category_insights",
                "description": "Read top and bottom spending categories for the current month.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_spending_prediction",
                "description": "Read the next-month spending forecast.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_recent_transactions",
                "description": "Read the latest transactions for grounding and verification.",
                "input_schema": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}},
                },
            },
            {
                "name": "retrieve_finance_context",
                "description": "Retrieve semantically similar finance knowledge chunks for RAG-style question answering.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "top_k": {"type": "integer"},
                    },
                    "required": ["question"],
                },
            },
            {
                "name": "list_recurring_reminders",
                "description": "Read the current recurring reminders list.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_upcoming_recurring_items",
                "description": "Read recurring reminders due in the next N days.",
                "input_schema": {
                    "type": "object",
                    "properties": {"days": {"type": "integer"}},
                },
            },
            {
                "name": "set_monthly_budget",
                "description": "Update the monthly budget in pounds.",
                "input_schema": {
                    "type": "object",
                    "properties": {"monthly_budget": {"type": "number"}},
                    "required": ["monthly_budget"],
                },
            },
            {
                "name": "set_monthly_income",
                "description": "Update the monthly income in pounds sterling, optionally for a specific month in YYYY-MM.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "monthly_income": {"type": "number"},
                        "month": {"type": "string"},
                    },
                    "required": ["monthly_income"],
                },
            },
            {
                "name": "create_transaction",
                "description": "Create a new transaction with date, category, description, amount, and entry_type.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "category": {"type": "string"},
                        "description": {"type": "string"},
                        "amount": {"type": "number"},
                        "entry_type": {"type": "string"},
                    },
                    "required": ["date", "category", "description", "amount", "entry_type"],
                },
            },
            {
                "name": "update_transaction_by_match",
                "description": "Update an existing transaction by matching on description/category/date/amount and applying new values.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "object"},
                        "entity": {"type": "object"},
                    },
                    "required": ["target", "entity"],
                },
            },
            {
                "name": "delete_transaction_by_match",
                "description": "Delete an existing transaction by matching on description/category/date/amount.",
                "input_schema": {
                    "type": "object",
                    "properties": {"target": {"type": "object"}},
                    "required": ["target"],
                },
            },
            {
                "name": "create_recurring_reminder",
                "description": "Create a recurring reminder with category, description, amount, entry_type, frequency, start_date, optional end_date, and active.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "description": {"type": "string"},
                        "amount": {"type": "number"},
                        "entry_type": {"type": "string"},
                        "frequency": {"type": "string"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"},
                        "active": {"type": "boolean"},
                    },
                    "required": ["category", "description", "amount", "entry_type", "frequency", "start_date", "active"],
                },
            },
            {
                "name": "update_recurring_reminder_by_match",
                "description": "Update a recurring reminder by matching the target reminder and applying the new reminder payload.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "object"},
                        "reminder": {"type": "object"},
                    },
                    "required": ["target", "reminder"],
                },
            },
            {
                "name": "delete_recurring_reminder_by_match",
                "description": "Delete recurring reminders matching the supplied target criteria.",
                "input_schema": {
                    "type": "object",
                    "properties": {"target": {"type": "object"}},
                    "required": ["target"],
                },
            },
            {
                "name": "replace_recurring_reminder",
                "description": "Replace an existing recurring reminder pattern with a new recurring reminder payload.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "object"},
                        "reminder": {"type": "object"},
                    },
                    "required": ["target", "reminder"],
                },
            },
            {
                "name": "generate_monthly_report",
                "description": "Generate the current month's PDF report and return its download URL.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "send_upcoming_bills_email_now",
                "description": "Send the current 7-day upcoming bills email immediately.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "send_month_end_email_now",
                "description": "Send the current month-end report email immediately.",
                "input_schema": {"type": "object", "properties": {}},
            },
        ]

    def list_tools(self) -> list[dict]:
        return list(self._tools)

    def call_tool(self, tool_name: str, arguments: dict | None = None) -> dict:
        handler = self._handlers.get(tool_name)
        if handler is None:
            raise ValidationError(f"Unknown MCP tool '{tool_name}'.")
        return handler(arguments or {})
