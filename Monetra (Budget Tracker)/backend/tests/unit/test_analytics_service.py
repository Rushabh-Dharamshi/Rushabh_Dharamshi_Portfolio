from budget_tracker_api.services.analytics_service import AnalyticsService


class StubAnalyticsRepository:
    def monthly_total(self, month_key, entry_type="expense"):
        assert month_key.startswith("20")
        return 420.0 if entry_type == "expense" else 420.0

    def weekly_total(self, start_date, end_date, entry_type="expense"):
        assert start_date <= end_date
        return 84.5

    def category_totals(self, month_key, entry_type="expense"):
        assert month_key.startswith("20")
        return [("Food", 220.0), ("Travel", 120.0), ("Bills", 80.0)]

    def description_totals_for_category(self, month_key, category, entry_type="expense"):
        assert category == "Food"
        return [("Groceries", 180.0), ("Cafe", 40.0)]

    def count_expenses_for_month(self, month_key, entry_type=None):
        return 7

    def recent_expenses(self, limit=5, entry_type=None):
        return []


class ConcentratedAnalyticsRepository(StubAnalyticsRepository):
    def monthly_total(self, month_key, entry_type="expense"):
        return 1100.0 if entry_type == "expense" else 500.0

    def category_totals(self, month_key, entry_type="expense"):
        return [("Bills", 700.0), ("Food", 200.0), ("Travel", 200.0)]

    def count_expenses_for_month(self, month_key, entry_type=None):
        return 3


def test_dashboard_and_category_views():
    service = AnalyticsService(StubAnalyticsRepository(), lambda: 1050.0, lambda _month=None: 1500.0)

    dashboard = service.dashboard()
    categories = service.category_insights()
    wordcloud = service.wordcloud_data()

    assert dashboard["status"] == "within"
    assert dashboard["current_month_total"] == 420.0
    assert dashboard["monthly_income"] == 1500.0
    assert categories["top_categories"][0]["category"] == "Food"
    assert categories["bottom_categories"][-1]["category"] == "Bills"
    assert wordcloud["top_category"] == "Food"
    assert wordcloud["frequencies"][0]["label"] == "Groceries"


def test_wordcloud_data_without_categories():
    class EmptyRepository(StubAnalyticsRepository):
        def category_totals(self, month_key, entry_type="expense"):
            return []

    service = AnalyticsService(EmptyRepository(), lambda: 1050.0, lambda _month=None: 1500.0)

    assert service.wordcloud_data() == {
        "top_category": None,
        "top_category_total": 0.0,
        "dominant_label": None,
        "dominant_value": 0.0,
        "frequencies": [],
    }


def test_financial_pulse_balanced_month():
    service = AnalyticsService(StubAnalyticsRepository(), lambda: 1050.0, lambda _month=None: 1500.0)

    pulse = service.financial_pulse()

    assert pulse["health_score"] >= 0
    assert pulse["average_transaction"] == 120.0
    assert pulse["transaction_count"] == 7
    assert pulse["top_category_share"] == 52.38
    assert pulse["cash_in"] == 1500.0
    assert "recent_expenses" in pulse


def test_financial_pulse_detects_pressure():
    service = AnalyticsService(ConcentratedAnalyticsRepository(), lambda: 1050.0, lambda _month=None: 1500.0)

    pulse = service.financial_pulse()

    assert pulse["health_score"] <= 100
    assert pulse["narrative"] in {
        "Budget threshold exceeded. Review the largest categories immediately.",
        "Spending is concentrated in one category this month.",
        "Budget runway is getting tight for the rest of the month.",
    }


def test_dashboard_warning_status():
    class WarningRepository(StubAnalyticsRepository):
        def monthly_total(self, month_key, entry_type="expense"):
            return 900.0 if entry_type == "expense" else 1100.0

    service = AnalyticsService(WarningRepository(), lambda: 1050.0, lambda _month=None: 1500.0)

    assert service.dashboard()["status"] == "warning"


def test_dashboard_over_status():
    class OverBudgetRepository(StubAnalyticsRepository):
        def monthly_total(self, month_key, entry_type="expense"):
            return 1200.0 if entry_type == "expense" else 900.0

    service = AnalyticsService(OverBudgetRepository(), lambda: 1050.0, lambda _month=None: 1500.0)

    assert service.dashboard()["status"] == "over"


def test_financial_pulse_detects_tight_runway():
    class TightRunwayRepository(StubAnalyticsRepository):
        def monthly_total(self, month_key, entry_type="expense"):
            return 800.0 if entry_type == "expense" else 1200.0

        def category_totals(self, month_key, entry_type="expense"):
            return [("Food", 200.0), ("Travel", 150.0), ("Bills", 100.0)]

        def count_expenses_for_month(self, month_key, entry_type=None):
            return 40

    service = AnalyticsService(TightRunwayRepository(), lambda: 900.0, lambda _month=None: 1500.0)

    assert service.financial_pulse()["narrative"] == "Budget runway is getting tight for the rest of the month."


def test_dashboard_uses_configured_income_when_no_income_transactions_exist():
    class NoIncomeRepository(StubAnalyticsRepository):
        def monthly_total(self, month_key, entry_type="expense"):
            return 420.0 if entry_type == "expense" else 0.0

    service = AnalyticsService(NoIncomeRepository(), lambda: 1050.0, lambda _month=None: 1800.0)

    dashboard = service.dashboard()

    assert dashboard["monthly_income"] == 1800.0

