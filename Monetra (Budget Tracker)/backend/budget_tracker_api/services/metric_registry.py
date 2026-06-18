from __future__ import annotations

from enum import Enum
from typing import Callable


class FinanceIntent(Enum):
    CASH_FLOW = "METRIC_CASH_FLOW"
    MONTHLY_EXPENSES = "METRIC_MONTHLY_EXPENSES"
    MONTHLY_BUDGET = "METRIC_MONTHLY_BUDGET"
    WEEKLY_SPENDING = "METRIC_WEEKLY_SPENDING"
    BUDGET_STATUS = "METRIC_BUDGET_STATUS"
    AVERAGE_DAILY_BURN = "METRIC_AVERAGE_DAILY_BURN"
    MONTH_END_FORECAST = "METRIC_MONTH_END_FORECAST"
    LARGEST_CATEGORY_SHARE = "METRIC_LARGEST_CATEGORY_SHARE"
    CURRENT_MONTH_TRANSACTIONS = "METRIC_CURRENT_MONTH_TRANSACTIONS"
    REMAINING_BUDGET = "METRIC_REMAINING_BUDGET"
    BUDGET_USAGE = "METRIC_BUDGET_USAGE"
    MONTHLY_INCOME = "METRIC_MONTHLY_INCOME"
    FINANCIAL_STATUS = "METRIC_FINANCIAL_STATUS"
    AVERAGE_TRANSACTION = "METRIC_AVERAGE_TRANSACTION"
    SPEND_VELOCITY = "METRIC_SPEND_VELOCITY"
    INCOME_COVERAGE = "METRIC_INCOME_COVERAGE"
    TOP_CATEGORY_SHARE = "METRIC_TOP_CATEGORY_SHARE"
    BUDGET_RUNWAY = "METRIC_BUDGET_RUNWAY"
    HEALTH_SCORE = "METRIC_HEALTH_SCORE"
    CURRENT_PERIOD = "METRIC_CURRENT_PERIOD"
    AVERAGE_SPEND = "METRIC_AVERAGE_SPEND"
    STRONGEST_PERIOD = "METRIC_STRONGEST_PERIOD"
    CHANGE_VS_PREVIOUS = "METRIC_CHANGE_VS_PREVIOUS"
    PIGGY_BANK_BALANCE = "METRIC_PIGGY_BANK_BALANCE"
    PIGGY_BANK_CONTRIBUTION = "METRIC_PIGGY_BANK_CONTRIBUTION"
    PIGGY_BANK_CARRYOVER = "METRIC_PIGGY_BANK_CARRYOVER"
    MONTHLY_TOP_CATEGORIES = "METRIC_MONTHLY_TOP_CATEGORIES"
    MONTHLY_BOTTOM_CATEGORIES = "METRIC_MONTHLY_BOTTOM_CATEGORIES"
    MONTHLY_CATEGORY_INSIGHTS = "METRIC_MONTHLY_CATEGORY_INSIGHTS"
    MONTHLY_SPEND_EXTREMES = "METRIC_MONTHLY_SPEND_EXTREMES"
    CATEGORY_SPEND_EXTREMES = "METRIC_CATEGORY_SPEND_EXTREMES"
    OPEN_ENDED = "OPEN_ENDED"


class MetricRegistry:
    def __init__(self, handlers: dict[FinanceIntent, Callable[[str], dict | None]] | None = None):
        self._handlers = handlers or {}

    def execute(self, intent: FinanceIntent, normalized_question: str) -> dict | None:
        if intent == FinanceIntent.OPEN_ENDED:
            return None
        handler = self._handlers.get(intent)
        if handler is None:
            return None
        return handler(normalized_question)


class FinanceIntentRouter:
    def classify(self, question: str) -> FinanceIntent:
        normalized = f" {str(question or '').lower()} "

        if self._contains_any(
            normalized,
            "average daily burn",
            "daily burn",
            "daily spending rate",
            "spending rate per day",
            "spend per day",
            "spending each day",
            "spending per day",
            "burn per day",
            "burning cash",
            "burn through every 24 hours",
            "how fast am i spending",
        ):
            return FinanceIntent.AVERAGE_DAILY_BURN

        if self._contains_any(normalized, "month-end forecast", "month end forecast", "forecast"):
            return FinanceIntent.MONTH_END_FORECAST

        if self._contains_any(normalized, "largest category share", "biggest category share"):
            return FinanceIntent.LARGEST_CATEGORY_SHARE

        if self._contains_any(
            normalized,
            "current-month transactions",
            "current month transactions",
            "transactions this month",
            "monthly transaction count",
        ):
            return FinanceIntent.CURRENT_MONTH_TRANSACTIONS

        if self._contains_any(
            normalized,
            "remaining budget",
            "budget remaining",
            "left in my budget",
            "budget left",
            "money left to spend",
            "left to spend",
            "safe to spend",
            "how much can i still spend",
        ):
            return FinanceIntent.REMAINING_BUDGET

        if self._contains_any(
            normalized,
            "budget consumption",
            "budget utilisation",
            "budget utilization",
            "percent spent",
            "percentage spent",
            "budget usage",
            "budget used",
            "budget as a percentage",
            "budget consumption as a percentage",
        ) or (" budget " in normalized and " percentage " in normalized):
            return FinanceIntent.BUDGET_USAGE

        if self._contains_any(
            normalized,
            "cash flow",
            "cashflow",
            "net cash flow",
            "net position",
            "income vs expenses",
            "income versus expenses",
            "cash position",
        ) or (" cash " in normalized and " flow " in normalized):
            return FinanceIntent.CASH_FLOW

        if self._contains_any(normalized, "monthly expenses", "month expenses", "expenses this month", "current month total"):
            return FinanceIntent.MONTHLY_EXPENSES

        if self._contains_any(normalized, "monthly budget", "living-cost budget", "living cost budget"):
            return FinanceIntent.MONTHLY_BUDGET

        if self._contains_any(normalized, "weekly spending", "spending this week", "week spending"):
            return FinanceIntent.WEEKLY_SPENDING

        if self._contains_any(normalized, "budget status", "am i within budget", "over budget", "within budget"):
            return FinanceIntent.BUDGET_STATUS

        if self._contains_any(
            normalized,
            "financial status",
            "finance status",
            "financial health",
            "how am i doing financially",
            "how healthy are my finances",
        ) or (" how " in normalized and " financially " in normalized):
            return FinanceIntent.FINANCIAL_STATUS

        if self._contains_any(normalized, "income coverage"):
            return FinanceIntent.INCOME_COVERAGE
        if self._contains_any(normalized, "top category share", "category share"):
            return FinanceIntent.TOP_CATEGORY_SHARE
        if self._contains_any(normalized, "budget runway", "runway"):
            return FinanceIntent.BUDGET_RUNWAY
        if self._contains_any(normalized, "health score"):
            return FinanceIntent.HEALTH_SCORE
        if self._contains_any(normalized, "spend velocity", "spending velocity"):
            return FinanceIntent.SPEND_VELOCITY
        if self._contains_any(normalized, "average transaction", "avg transaction"):
            return FinanceIntent.AVERAGE_TRANSACTION

        if self._contains_any(normalized, "current period"):
            return FinanceIntent.CURRENT_PERIOD
        if self._contains_any(normalized, "average spend"):
            return FinanceIntent.AVERAGE_SPEND
        if self._contains_any(normalized, "strongest period"):
            return FinanceIntent.STRONGEST_PERIOD
        if self._contains_any(normalized, "change vs previous", "change versus previous"):
            return FinanceIntent.CHANGE_VS_PREVIOUS

        if self._contains_any(normalized, "piggy bank balance", "total piggy-bank balance", "total piggy bank balance"):
            return FinanceIntent.PIGGY_BANK_BALANCE
        if self._contains_any(normalized, "added this month", "piggy bank contribution", "piggy-bank contribution", "income flowing into piggy"):
            return FinanceIntent.PIGGY_BANK_CONTRIBUTION
        if self._contains_any(normalized, "previous carryover", "piggy bank carryover", "piggy-bank carryover"):
            return FinanceIntent.PIGGY_BANK_CARRYOVER
        if self._contains_any(normalized, "piggy bank", "piggy-bank"):
            return FinanceIntent.PIGGY_BANK_BALANCE

        if (
            self._contains_any(normalized, "category", "categories")
            and self._contains_any(normalized, "most", "highest", "biggest")
            and self._contains_any(normalized, "least", "lowest", "smallest")
        ):
            return FinanceIntent.CATEGORY_SPEND_EXTREMES
        if (
            self._contains_any(normalized, "month", "months")
            and self._contains_any(normalized, "spend", "spent", "expenses", "expense")
            and self._contains_any(normalized, "most", "highest", "biggest")
            and self._contains_any(normalized, "least", "lowest", "smallest")
        ):
            return FinanceIntent.MONTHLY_SPEND_EXTREMES
        if self._contains_any(normalized, "top categories", "highest categories", "biggest categories"):
            return FinanceIntent.MONTHLY_TOP_CATEGORIES
        if self._contains_any(normalized, "bottom categories", "lowest categories", "smallest categories"):
            return FinanceIntent.MONTHLY_BOTTOM_CATEGORIES
        if self._contains_any(normalized, "monthly insights", "category analysis", "where is money concentrating"):
            return FinanceIntent.MONTHLY_CATEGORY_INSIGHTS

        if "income" in normalized and not self._contains_any(
            normalized,
            " expense",
            " spend",
            " spent",
            " cost",
            " payment",
            " bill",
        ):
            return FinanceIntent.MONTHLY_INCOME

        return FinanceIntent.OPEN_ENDED

    @staticmethod
    def _contains_any(value: str, *needles: str) -> bool:
        return any(needle in value for needle in needles)
