from datetime import datetime

from budget_tracker_api.errors import NotFoundError, ValidationError
from budget_tracker_api.repositories.savings_goal_repository import SavingsGoalRepository


class SavingsGoalService:
    def __init__(self, repository: SavingsGoalRepository):
        self._repository = repository

    def list_goals(self) -> list[dict]:
        return self._repository.list_goals()

    def create_goal(self, payload: dict) -> dict:
        return self._repository.create_goal(self._validate_payload(payload))

    def update_goal(self, goal_id: int, payload: dict) -> dict:
        goal = self._repository.update_goal(goal_id, self._validate_payload(payload))
        if goal is None:
            raise NotFoundError(f"Savings goal with id {goal_id} was not found.")
        return goal

    def delete_goal(self, goal_id: int) -> None:
        if not self._repository.delete_goal(goal_id):
            raise NotFoundError(f"Savings goal with id {goal_id} was not found.")

    @staticmethod
    def _validate_payload(payload: dict) -> dict:
        name = str(payload.get("name") or "").strip()
        target_date = str(payload.get("target_date") or "").strip()
        if not name or payload.get("target_amount") in (None, ""):
            raise ValidationError("name and target_amount are required.")

        try:
            target_amount = round(float(payload.get("target_amount")), 2)
            current_amount = round(float(payload.get("current_amount") or 0), 2)
        except (TypeError, ValueError) as exc:
            raise ValidationError("target_amount and current_amount must be numeric.") from exc

        if target_amount <= 0:
            raise ValidationError("target_amount must be greater than zero.")
        if current_amount < 0:
            raise ValidationError("current_amount cannot be negative.")

        if target_date:
            try:
                datetime.strptime(target_date, "%Y-%m-%d")
            except ValueError as exc:
                raise ValidationError("target_date must use YYYY-MM-DD format.") from exc

        return {
            "name": name,
            "target_amount": target_amount,
            "current_amount": current_amount,
            "target_date": target_date or None,
        }
