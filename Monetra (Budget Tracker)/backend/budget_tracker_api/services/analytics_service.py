from collections.abc import Callable
from datetime import datetime, timedelta

from budget_tracker_api.repositories.expense_repository import ExpenseRepository


class AnalyticsService:
    def __init__(
        self,
        repository: ExpenseRepository,
        budget_provider: Callable[[], float],
        income_provider: Callable[[str | None], float],
    ):
        self._repository = repository
        self._budget_provider = budget_provider
        self._income_provider = income_provider

    def dashboard(self) -> dict:
        now = datetime.now()
        month_key = now.strftime("%Y-%m")
        monthly_budget = self._budget_provider()
        monthly_income = self._income_provider(month_key)
        expense_total = self._repository.monthly_total(month_key, "expense")
        remaining_budget = monthly_budget - expense_total
        percent_spent = (expense_total / monthly_budget * 100) if monthly_budget else 0

        start_week = now - timedelta(days=now.weekday())
        weekly_spent = self._repository.weekly_total(
            start_week.strftime("%Y-%m-%d"),
            now.strftime("%Y-%m-%d"),
            "expense",
        )

        status = "within"
        if expense_total > monthly_budget:
            status = "over"
        elif percent_spent >= 75:
            status = "warning"

        return {
            "monthly_budget": round(monthly_budget, 2),
            "current_month_total": round(expense_total, 2),
            "monthly_expenses": round(expense_total, 2),
            "monthly_income": round(monthly_income, 2),
            "income_month": month_key,
            "month_key": month_key,
            "net_cash_flow": round(monthly_income - expense_total, 2),
            "remaining_budget": round(remaining_budget, 2),
            "weekly_spending": round(weekly_spent, 2),
            "percent_spent": round(percent_spent, 2),
            "status": status,
            "month_label": now.strftime("%B %Y"),
        }

    def category_insights(self) -> dict:
        month_key = datetime.now().strftime("%Y-%m")
        categories = self._repository.category_totals(month_key, "expense")
        top_categories = categories[:3]
        bottom_categories = categories[-3:] if len(categories) >= 3 else categories

        return {
            "top_categories": [
                {"category": category, "amount": round(amount, 2)}
                for category, amount in top_categories
            ],
            "bottom_categories": [
                {"category": category, "amount": round(amount, 2)}
                for category, amount in bottom_categories
            ],
            "total_spending": round(sum(amount for _, amount in categories), 2),
        }

    def wordcloud_data(self) -> dict:
        month_key = datetime.now().strftime("%Y-%m")
        categories = self._repository.category_totals(month_key, "expense")
        if not categories:
            return {
                "top_category": None,
                "top_category_total": 0.0,
                "dominant_label": None,
                "dominant_value": 0.0,
                "frequencies": [],
            }

        top_category, top_category_total = categories[0]
        frequencies = self._repository.description_totals_for_category(
            month_key,
            top_category,
            "expense",
        )
        weighted_total = round(sum(amount for _, amount in frequencies), 2) or round(top_category_total, 2)
        dominant_label = frequencies[0][0] if frequencies else None
        dominant_value = round(frequencies[0][1], 2) if frequencies else 0.0
        return {
            "top_category": top_category,
            "top_category_total": round(weighted_total, 2),
            "dominant_label": dominant_label,
            "dominant_value": dominant_value,
            "frequencies": [
                {
                    "label": description,
                    "value": round(amount, 2),
                    "share": round((amount / weighted_total * 100), 2) if weighted_total else 0.0,
                }
                for description, amount in frequencies
            ],
        }

    def financial_pulse(self) -> dict:
        now = datetime.now()
        month_key = now.strftime("%Y-%m")
        monthly_budget = self._budget_provider()
        income_total = self._income_provider(month_key)
        recorded_income = self._repository.monthly_total(month_key, "income")
        expense_total = self._repository.monthly_total(month_key, "expense")
        transaction_count = self._repository.count_expenses_for_month(month_key, None)
        categories = self._repository.category_totals(month_key, "expense")
        recent_transactions = self._repository.recent_expenses(entry_type=None)

        day_of_month = max(now.day, 1)
        average_transaction = (
            (expense_total + recorded_income) / transaction_count if transaction_count else 0.0
        )
        spend_velocity = expense_total / day_of_month if expense_total else 0.0
        remaining_budget = monthly_budget - expense_total
        net_cash_flow = income_total - expense_total

        top_category_amount = categories[0][1] if categories else 0.0
        top_category_share = (top_category_amount / expense_total * 100) if expense_total else 0.0
        income_coverage = (income_total / expense_total * 100) if expense_total else 0.0

        budget_utilization_score = max(
            0.0,
            100 - ((expense_total / monthly_budget) * 100) if monthly_budget else 100.0,
        )
        category_diversity_score = max(0.0, 100 - top_category_share)
        cash_flow_score = min(100.0, max(0.0, 50 + (net_cash_flow / max(monthly_budget, 1)) * 50))
        activity_score = min(100.0, transaction_count * 6)
        health_score = round(
            (budget_utilization_score * 0.35)
            + (category_diversity_score * 0.2)
            + (cash_flow_score * 0.3)
            + (activity_score * 0.15)
        )
        health_score = max(0, min(100, health_score))

        runway_days = None
        if spend_velocity > 0 and remaining_budget > 0:
            runway_days = round(remaining_budget / spend_velocity, 1)

        narrative = "Cash flow is balanced and spending remains controllable."
        if expense_total > monthly_budget:
            narrative = "Budget threshold exceeded. Review the largest categories immediately."
        elif net_cash_flow < 0:
            narrative = "Cash outflow is currently ahead of income. Tighten discretionary spend."
        elif top_category_share >= 45:
            narrative = "Spending is concentrated in one category this month."
        elif runway_days is not None and runway_days < 10:
            narrative = "Budget runway is getting tight for the rest of the month."

        transactions_payload = [expense.to_dict() for expense in recent_transactions]
        return {
            "health_score": health_score,
            "average_transaction": round(average_transaction, 2),
            "transaction_count": transaction_count,
            "spend_velocity": round(spend_velocity, 2),
            "top_category_share": round(top_category_share, 2),
            "runway_days": runway_days,
            "narrative": narrative,
            "cash_in": round(income_total, 2),
            "cash_out": round(expense_total, 2),
            "net_cash_flow": round(net_cash_flow, 2),
            "income_coverage": round(income_coverage, 2),
            "recent_transactions": transactions_payload,
            "recent_expenses": transactions_payload,
        }
