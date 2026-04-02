from datetime import datetime

from budget_tracker_api.errors import ValidationError
from budget_tracker_api.repositories.settings_repository import SettingsRepository


class SettingsService:
    def __init__(self, repository: SettingsRepository):
        self._repository = repository

    @staticmethod
    def _parse_month_key(month_key: str | None) -> str | None:
        if month_key in (None, ""):
            return None
        try:
            return datetime.strptime(str(month_key), "%Y-%m").strftime("%Y-%m")
        except ValueError as exc:
            raise ValidationError("month must be in YYYY-MM format.") from exc

    def get_settings(self, month_key: str | None = None) -> dict:
        return self._repository.get_settings(self._parse_month_key(month_key))

    def get_monthly_budget(self) -> float:
        return self._repository.get_monthly_budget()

    def get_monthly_income(self, month_key: str | None = None) -> float:
        return self._repository.get_monthly_income(self._parse_month_key(month_key))

    def update_monthly_budget(self, payload: dict) -> dict:
        value = payload.get("monthly_budget")
        try:
            monthly_budget = round(float(value), 2)
        except (TypeError, ValueError) as exc:
            raise ValidationError("monthly_budget must be numeric.") from exc

        if monthly_budget <= 0:
            raise ValidationError("monthly_budget must be greater than zero.")

        return {
            "monthly_budget": self._repository.update_monthly_budget(monthly_budget)
        }

    def update_monthly_income(self, payload: dict) -> dict:
        value = payload.get("monthly_income")
        try:
            monthly_income = round(float(value), 2)
        except (TypeError, ValueError) as exc:
            raise ValidationError("monthly_income must be numeric.") from exc

        if monthly_income <= 0:
            raise ValidationError("monthly_income must be greater than zero.")

        month_key = self._parse_month_key(payload.get("month"))
        return self._repository.update_monthly_income(monthly_income, month_key)
