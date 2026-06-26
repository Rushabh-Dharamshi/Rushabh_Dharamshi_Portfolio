from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from budget_tracker_api.errors import NotFoundError, ValidationError
from budget_tracker_api.repositories.recurring_repository import RecurringRepository
from budget_tracker_api.services.expense_service import ExpenseService


class RecurringService:
    def __init__(self, repository: RecurringRepository, expense_service: ExpenseService, timezone_name: str | None = None):
        self._repository = repository
        self._expense_service = expense_service
        self._timezone_name = str(timezone_name or "").strip()

    def list_items(self) -> list[dict]:
        return self._repository.list_items()

    def get_item(self, item_id: int) -> dict:
        item = self._repository.get_item(item_id)
        if item is None:
            raise NotFoundError(f"Recurring item with id {item_id} was not found.")
        return item

    def create_item(self, payload: dict) -> dict:
        return self._repository.create_item(self._validate_payload(payload))

    def update_item(self, item_id: int, payload: dict) -> dict:
        item = self._repository.update_item(item_id, self._validate_payload(payload))
        if item is None:
            raise NotFoundError(f"Recurring item with id {item_id} was not found.")
        return item

    def delete_item(self, item_id: int) -> None:
        if not self._repository.delete_item(item_id):
            raise NotFoundError(f"Recurring item with id {item_id} was not found.")

    def mark_occurrence_paid(self, item_id: int, payload: dict) -> dict:
        item = self.get_item(item_id)
        occurrence_date = self._validate_occurrence_date(payload)
        transaction = self._validate_paid_transaction(item, payload)
        existing_link = self._repository.get_paid_occurrence_by_transaction_id(int(transaction["id"]))
        if existing_link and not (
            existing_link["recurring_item_id"] == item_id
            and existing_link["occurrence_date"] == occurrence_date
        ):
            raise ValidationError(
                f"Transaction #{transaction['id']} is already linked to another paid reminder occurrence."
            )
        return {
            "item": item,
            "occurrence": self._repository.mark_occurrence_paid(item_id, occurrence_date, int(transaction["id"])),
            "transaction": transaction,
            "message": f"Reminder marked as paid for this date using expense #{transaction.get('user_expense_id', transaction['id'])}."
        }

    def mark_occurrence_unpaid(self, item_id: int, payload: dict) -> dict:
        item = self.get_item(item_id)
        occurrence_date = self._validate_occurrence_date(payload)
        return {
            "item": item,
            "occurrence": self._repository.mark_occurrence_unpaid(item_id, occurrence_date),
            "message": "Reminder restored for this date.",
        }

    def upcoming_calendar(self, days_ahead: int = 35) -> dict:
        horizon = max(1, min(int(days_ahead), 90))
        today = self._today()
        current_month_start = today.replace(day=1)
        window_end_date = today + timedelta(days=horizon - 1)
        items = self._repository.list_items()
        paid_occurrences = self._repository.paid_occurrences_for_range(
            current_month_start.isoformat(),
            window_end_date.isoformat(),
        )
        paid_entries = {
            (entry["recurring_item_id"], entry["occurrence_date"]): entry
            for entry in self._repository.paid_occurrence_entries_for_range(
                current_month_start.isoformat(),
                window_end_date.isoformat(),
            )
        }

        occurrences: list[dict] = []
        late_occurrences: list[dict] = []
        completed_occurrences: list[dict] = []
        for item in items:
            if not item["active"]:
                continue
            item_end_date = self._parse_optional_date(item.get("end_date"))
            overdue_date = self._first_due_on_or_after(item["start_date"], item["frequency"], current_month_start)
            while overdue_date < today and (item_end_date is None or overdue_date <= item_end_date):
                occurrence_key = (item["id"], overdue_date.isoformat())
                if occurrence_key not in paid_occurrences:
                    late_occurrences.append(
                        {
                            "recurring_item_id": item["id"],
                            "date": overdue_date.isoformat(),
                            "category": item["category"],
                            "description": item["description"],
                            "amount": item["amount"],
                            "entry_type": item["entry_type"],
                            "frequency": item["frequency"],
                            "days_until_due": (overdue_date - today).days,
                        }
                    )
                if item["frequency"] == "once":
                    break
                overdue_date = self._next_due_date(overdue_date, item["frequency"])

            due_date = self._first_due_on_or_after(item["start_date"], item["frequency"], today)
            if item["frequency"] == "once" and due_date < today:
                continue
            if item_end_date and due_date > item_end_date:
                continue
            while due_date <= window_end_date and (item_end_date is None or due_date <= item_end_date):
                occurrence_key = (item["id"], due_date.isoformat())
                occurrence_payload = {
                    "recurring_item_id": item["id"],
                    "date": due_date.isoformat(),
                    "category": item["category"],
                    "description": item["description"],
                    "amount": item["amount"],
                    "entry_type": item["entry_type"],
                    "frequency": item["frequency"],
                    "days_until_due": (due_date - today).days,
                }
                if occurrence_key in paid_occurrences:
                    linked_entry = paid_entries[occurrence_key]
                    completed_occurrences.append(
                        {
                            **occurrence_payload,
                            "updated_at": linked_entry["updated_at"],
                            "is_paid": True,
                            "transaction_id": linked_entry.get("transaction_id"),
                            "user_transaction_id": self._user_expense_id_for_transaction(linked_entry.get("transaction_id")),
                        }
                    )
                    if item["frequency"] == "once":
                        break
                    due_date = self._next_due_date(due_date, item["frequency"])
                    continue
                occurrences.append(occurrence_payload)
                if item["frequency"] == "once":
                    break
                due_date = self._next_due_date(due_date, item["frequency"])

        occurrences.sort(key=lambda item: (item["date"], item["description"], item["recurring_item_id"]))
        late_occurrences.sort(key=lambda item: (item["date"], item["description"], item["recurring_item_id"]))
        completed_occurrences.sort(
            key=lambda item: (item["date"], item["description"], item["recurring_item_id"])
        )
        return {
            "window_start": today.isoformat(),
            "window_end": window_end_date.isoformat(),
            "occurrences": occurrences,
            "late_occurrences": late_occurrences,
            "completed_occurrences": completed_occurrences,
        }

    def _validate_payload(self, payload: dict) -> dict:
        category = (payload.get("category") or "").strip()
        description = (payload.get("description") or "").strip()
        start_date = (payload.get("start_date") or "").strip()
        end_date = (payload.get("end_date") or "").strip()
        frequency = (payload.get("frequency") or "").strip().lower()
        entry_type = (payload.get("entry_type") or "expense").strip().lower()
        active = payload.get("active", True)

        if not category or not description or not start_date or payload.get("amount") in (None, ""):
            raise ValidationError("category, description, amount, and start_date are required.")

        try:
            parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValidationError("start_date must use YYYY-MM-DD format.") from exc

        parsed_end_date = None
        if end_date:
            try:
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError as exc:
                raise ValidationError("end_date must use YYYY-MM-DD format.") from exc
            if parsed_end_date.date() < parsed_start_date.date():
                raise ValidationError("end_date must be on or after start_date.")

        try:
            amount = round(float(payload.get("amount")), 2)
        except (TypeError, ValueError) as exc:
            raise ValidationError("amount must be numeric.") from exc

        if frequency not in {"once", "weekly", "monthly"}:
            raise ValidationError("frequency must be once, weekly, or monthly.")
        if entry_type != "expense":
            raise ValidationError("recurring reminders only support expense type.")
        if frequency == "once":
            end_date = start_date

        return {
            "category": category,
            "description": description,
            "amount": amount,
            "entry_type": entry_type,
            "frequency": frequency,
            "start_date": start_date,
            "end_date": end_date or None,
            "active": bool(active),
        }

    @staticmethod
    def _validate_occurrence_date(payload: dict) -> str:
        raw_date = (payload.get("occurrence_date") or payload.get("date") or "").strip()
        if not raw_date:
            raise ValidationError("occurrence_date is required.")
        try:
            datetime.strptime(raw_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValidationError("occurrence_date must use YYYY-MM-DD format.") from exc
        return raw_date

    def _validate_paid_transaction(self, item: dict, payload: dict) -> dict:
        transaction_id = payload.get("transaction_id")
        if transaction_id in (None, ""):
            raise ValidationError("transaction_id is required to verify this paid reminder.")
        try:
            normalized_transaction_id = int(transaction_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError("transaction_id must be a valid integer.") from exc

        transaction = self._expense_service.get_expense_by_user_expense_id(normalized_transaction_id)
        if transaction["entry_type"] != item["entry_type"]:
            raise ValidationError("The selected transaction type does not match this reminder.")
        if abs(float(transaction["amount"]) - float(item["amount"])) >= 0.01:
            raise ValidationError("The selected transaction amount does not match this reminder.")
        if transaction["category"].strip().lower() != item["category"].strip().lower():
            raise ValidationError("The selected transaction category does not match this reminder.")
        return transaction

    def _user_expense_id_for_transaction(self, transaction_id) -> int | None:
        if transaction_id in (None, ""):
            return None
        try:
            transaction = self._expense_service.get_expense(int(transaction_id))
        except (NotFoundError, TypeError, ValueError):
            return None
        return transaction.get("user_expense_id", transaction.get("id"))

    @staticmethod
    def _first_due_on_or_after(raw_start_date: str, frequency: str, target_date: date) -> date:
        due_date = datetime.strptime(raw_start_date, "%Y-%m-%d").date()
        if frequency == "once":
            return due_date
        while due_date < target_date:
            due_date = RecurringService._next_due_date(due_date, frequency)
        return due_date

    @staticmethod
    def _next_due_date(current_due_date: date, frequency: str) -> date:
        if frequency == "weekly":
            return current_due_date + timedelta(days=7)

        next_month = current_due_date.replace(day=28) + timedelta(days=4)
        month_start = next_month.replace(day=1)
        month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        next_day = min(current_due_date.day, month_end.day)
        return month_start.replace(day=next_day)

    @staticmethod
    def _parse_optional_date(raw_date: str | None) -> date | None:
        if not raw_date:
            return None
        return datetime.strptime(raw_date, "%Y-%m-%d").date()

    def _today(self) -> date:
        if not self._timezone_name:
            return date.today()
        try:
            return datetime.now(ZoneInfo(self._timezone_name)).date()
        except ZoneInfoNotFoundError:
            return date.today()
