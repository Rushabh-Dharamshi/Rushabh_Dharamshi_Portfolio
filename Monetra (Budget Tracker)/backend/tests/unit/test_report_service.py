from datetime import datetime, timedelta
from pathlib import Path

from budget_tracker_api.schemas import Expense
from budget_tracker_api.services.report_service import ReportService


class StubReportRepository:
    def __init__(self):
        self.current_key = datetime.now().strftime("%Y-%m")
        self.previous_key = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    def expenses_for_month(self, month_key, entry_type="expense"):
        if entry_type == "income":
            if month_key == self.current_key:
                return [Expense(20, f"{month_key}-01", "Salary", "Payroll", 1200.0, "income")]
            return [Expense(21, f"{month_key}-01", "Salary", "Payroll", 1000.0, "income")]
        if month_key == self.current_key:
            return [
                Expense(1, f"{month_key}-01", "Food", "Groceries", 180.0),
                Expense(2, f"{month_key}-04", "Travel", "Train pass", 120.0),
                Expense(3, f"{month_key}-08", "Bills", "Energy bill", 90.0),
                Expense(4, f"{month_key}-11", "Food", "Cafe", 42.0),
            ]
        return [
            Expense(10, f"{month_key}-03", "Food", "Groceries", 150.0),
            Expense(11, f"{month_key}-06", "Travel", "Train pass", 95.0),
        ]

    def category_totals(self, month_key, entry_type="expense"):
        expenses = self.expenses_for_month(month_key, entry_type)
        totals = {}
        for expense in expenses:
            totals[expense.category] = totals.get(expense.category, 0.0) + expense.amount
        return sorted(totals.items(), key=lambda item: (-item[1], item[0]))

    def monthly_total(self, month_key, entry_type="expense"):
        return round(sum(item.amount for item in self.expenses_for_month(month_key, entry_type)), 2)

    def largest_expenses(self, month_key, limit=10):
        return sorted(
            self.expenses_for_month(month_key),
            key=lambda expense: (-expense.amount, expense.date),
        )[:limit]

    def daily_totals(self, month_key, entry_type="expense"):
        return [(expense.date, expense.amount) for expense in self.expenses_for_month(month_key, entry_type)]

    def monthly_spending(self, entry_type="expense"):
        return [
            ("2025-10", 310.0),
            ("2025-11", 355.0),
            ("2025-12", 402.0),
            ("2026-01", 390.0),
            (self.previous_key, 245.0),
            (self.current_key, 432.0),
        ]

    def monthly_cash_flow(self):
        return [
            {"month": "2025-12", "income": 1000.0, "expense": 402.0, "net": 598.0},
            {"month": "2026-01", "income": 1000.0, "expense": 390.0, "net": 610.0},
            {"month": self.previous_key, "income": 1000.0, "expense": 245.0, "net": 755.0},
            {"month": self.current_key, "income": 1200.0, "expense": 432.0, "net": 768.0},
        ]


def test_build_context_returns_rich_metrics(tmp_path: Path):
    service = ReportService(StubReportRepository(), lambda: 1050.0, lambda _month=None: 1500.0, tmp_path)

    context = service._build_context(datetime.now())

    assert context.current_total == 432.0
    assert context.previous_total == 245.0
    assert context.current_income_total == 1200.0
    assert context.current_net_cash_flow == 768.0
    assert context.transaction_count == 4
    assert context.category_rows[0]["category"] == "Food"
    assert context.insights
    assert context.recommendations


def test_generate_monthly_report_creates_detailed_pdf(tmp_path: Path):
    service = ReportService(StubReportRepository(), lambda: 1050.0, lambda _month=None: 1500.0, tmp_path)

    pdf_path = service.generate_monthly_report()

    assert pdf_path.exists()
    assert pdf_path.suffix == ".pdf"
    assert pdf_path.stat().st_size > 5000


def test_report_helpers_cover_empty_and_over_budget_paths(tmp_path: Path):
    class EmptyRepository(StubReportRepository):
        def expenses_for_month(self, month_key, entry_type="expense"):
            return []

        def category_totals(self, month_key, entry_type="expense"):
            return []

        def monthly_total(self, month_key, entry_type="expense"):
            return 0.0

        def largest_expenses(self, month_key, limit=10):
            return []

        def daily_totals(self, month_key, entry_type="expense"):
            return []

        def monthly_spending(self, entry_type="expense"):
            return []

        def monthly_cash_flow(self):
            return []

    service = ReportService(EmptyRepository(), lambda: 200.0, lambda _month=None: 500.0, tmp_path)
    context = service._build_context(datetime.now())

    assert service._create_category_comparison_chart(context) is None
    assert service._create_daily_spending_chart(context) is None
    assert service._create_monthly_trend_chart(context) is None
    assert service._create_cash_flow_chart(context) is None
    assert service._build_recommendations(remaining_budget=-20.0, projected_month_end_spend=250.0, net_cash_flow=-15.0, largest_transaction=None, top_category=None, top_category_share=0.0)[0].startswith("Introduce a short-term spending hold")

