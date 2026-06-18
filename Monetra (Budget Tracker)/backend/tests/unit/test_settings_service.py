import pytest

from budget_tracker_api.errors import ValidationError
from budget_tracker_api.services.settings_service import SettingsService


class StubSettingsRepository:
    def __init__(self):
        self.monthly_budget = 1050.0
        self.monthly_income = 1500.0
        self.last_get_month = None
        self.last_budget_month = None
        self.last_income_month = None

    def get_settings(self, month_key=None):
        self.last_get_month = month_key
        return {
            "monthly_budget": self.monthly_budget,
            "budget_month": month_key,
            "monthly_income": self.monthly_income,
            "income_month": month_key,
        }

    def get_monthly_budget(self, month_key=None):
        self.last_get_month = month_key
        return self.monthly_budget

    def get_monthly_income(self, month_key=None):
        self.last_get_month = month_key
        return self.monthly_income

    def list_monthly_income_records(self, before_month_key=None):
        return [{"month_key": "2026-05", "monthly_income": 900.0}]

    def update_monthly_budget(self, monthly_budget, month_key=None):
        self.monthly_budget = monthly_budget
        self.last_budget_month = month_key
        return {"monthly_budget": monthly_budget, "budget_month": month_key}

    def update_monthly_income(self, monthly_income, month_key=None):
        self.monthly_income = monthly_income
        self.last_income_month = month_key
        return {"monthly_income": monthly_income, "income_month": month_key}


def test_settings_service_covers_success_and_validation_paths():
    repository = StubSettingsRepository()
    service = SettingsService(repository)

    assert service.get_settings()["monthly_budget"] == 1050.0
    assert service.get_settings("2026-04")["income_month"] == "2026-04"
    assert service.get_monthly_budget("2026-04") == 1050.0
    assert service.get_monthly_income("2026-05") == 1500.0
    assert repository.last_get_month == "2026-05"
    assert service.list_monthly_income_records("2026-06") == [{"month_key": "2026-05", "monthly_income": 900.0}]

    assert service.update_monthly_budget({"monthly_budget": "1200.126", "month": "2026-06"}) == {
        "monthly_budget": 1200.13,
        "budget_month": "2026-06",
    }
    assert repository.last_budget_month == "2026-06"
    assert service.update_monthly_income({"monthly_income": "2400.499", "month": "2026-06"}) == {
        "monthly_income": 2400.5,
        "income_month": "2026-06",
    }
    assert repository.last_income_month == "2026-06"

    with pytest.raises(ValidationError, match="month must be in YYYY-MM format."):
        service.get_settings("2026/04")
    with pytest.raises(ValidationError, match="monthly_budget must be numeric."):
        service.update_monthly_budget({"monthly_budget": "abc"})
    with pytest.raises(ValidationError, match="monthly_budget must be greater than zero."):
        service.update_monthly_budget({"monthly_budget": 0})
    with pytest.raises(ValidationError, match="monthly_income must be numeric."):
        service.update_monthly_income({"monthly_income": "abc"})
    with pytest.raises(ValidationError, match="monthly_income must be greater than zero."):
        service.update_monthly_income({"monthly_income": -1})
