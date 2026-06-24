import csv
import io
from datetime import datetime
from typing import Any

from budget_tracker_api.errors import NotFoundError, ValidationError
from budget_tracker_api.repositories.expense_repository import ExpenseRepository


class ExpenseService:
    def __init__(self, repository: ExpenseRepository):
        self._repository = repository

    def list_expenses(
        self,
        sort_direction: str = "desc",
        filters: dict | None = None,
    ) -> list[dict]:
        expenses = self._with_user_expense_ids([
            expense.to_dict()
            for expense in self._repository.list_expenses(sort_direction, entry_type="expense")
        ])
        return self._apply_filters(expenses, filters or {})

    def get_expense(self, expense_id: int) -> dict:
        expense = self._repository.get_expense(expense_id)
        if expense is None or getattr(expense, "entry_type", "expense") != "expense":
            raise NotFoundError(f"Expense with id {expense_id} was not found.")
        return self._decorate_expense(expense.to_dict())

    def get_expense_by_user_expense_id(self, user_expense_id: int) -> dict:
        try:
            normalized_id = int(user_expense_id)
        except (TypeError, ValueError) as exc:
            raise NotFoundError(f"Expense with id {user_expense_id} was not found.") from exc
        for expense in self._expense_dicts_with_user_expense_ids():
            if expense["user_expense_id"] == normalized_id:
                return expense
        raise NotFoundError(f"Expense with id {user_expense_id} was not found.")

    def create_expense(self, payload: dict) -> dict:
        data = self._validate_payload(payload)
        return self._decorate_expense(self._repository.create_expense(data).to_dict())

    def update_expense(self, expense_id: int, payload: dict) -> dict:
        existing = self._repository.get_expense(expense_id)
        if existing is None or getattr(existing, "entry_type", "expense") != "expense":
            raise NotFoundError(f"Expense with id {expense_id} was not found.")
        data = self._validate_payload(payload)
        expense = self._repository.update_expense(expense_id, data)
        if expense is None:
            raise NotFoundError(f"Expense with id {expense_id} was not found.")
        return self._decorate_expense(expense.to_dict())

    def delete_expense(self, expense_id: int) -> None:
        existing = self._repository.get_expense(expense_id)
        if existing is None or getattr(existing, "entry_type", "expense") != "expense":
            raise NotFoundError(f"Expense with id {expense_id} was not found.")
        deleted = self._repository.delete_expense(expense_id)
        if not deleted:
            raise NotFoundError(f"Expense with id {expense_id} was not found.")

    def import_csv(self, file_storage) -> dict:
        if file_storage is None:
            raise ValidationError("CSV file is required.")

        try:
            raw = file_storage.stream.read()
            text = raw.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
        except UnicodeDecodeError as exc:
            raise ValidationError("CSV file must use UTF-8 encoding.") from exc

        if not reader.fieldnames:
            raise ValidationError("CSV file format is invalid.")

        reader.fieldnames = [self._normalize_header(field) for field in reader.fieldnames]
        valid_rows: list[dict] = []
        skipped_rows = 0
        try:
            for row in reader:
                cleaned_row = self._clean_csv_row(row)
                if cleaned_row is None:
                    skipped_rows += 1
                    continue
                try:
                    valid_rows.append(self._validate_payload(cleaned_row))
                except ValidationError:
                    skipped_rows += 1
        except csv.Error as exc:
            raise ValidationError("CSV file format is invalid.") from exc

        imported_rows = self._repository.bulk_insert(valid_rows)
        return {
            "imported_rows": imported_rows,
            "skipped_rows": skipped_rows,
        }

    def export_csv(self) -> str:
        today = datetime.now().date()
        month_key = today.strftime("%Y-%m")
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Date", "Category", "Description", "Amount", "Type"])
        for expense in self._with_user_expense_ids(
            [expense.to_dict() for expense in self._repository.list_expenses("desc", entry_type="expense")]
        ):
            if not str(expense["date"]).startswith(month_key) or str(expense["date"]) > today.isoformat():
                continue
            writer.writerow(
                [
                    expense["user_expense_id"],
                    expense["date"],
                    expense["category"],
                    expense["description"],
                    f"{expense['amount']:.2f}",
                    "expense",
                ]
            )
        return output.getvalue()

    def _expense_dicts_with_user_expense_ids(self) -> list[dict]:
        return self._with_user_expense_ids([
            expense.to_dict()
            for expense in self._repository.list_expenses("asc", entry_type="expense")
        ])

    def _decorate_expense(self, expense: dict) -> dict:
        account_ids = {
            item["id"]: item["user_expense_id"]
            for item in self._expense_dicts_with_user_expense_ids()
        }
        return {
            **expense,
            "user_expense_id": account_ids.get(expense["id"], expense["id"]),
        }

    @staticmethod
    def _with_user_expense_ids(expenses: list[dict]) -> list[dict]:
        account_ids = {
            expense["id"]: index + 1
            for index, expense in enumerate(sorted(expenses, key=lambda item: int(item["id"])))
        }
        return [
            {
                **expense,
                "user_expense_id": account_ids.get(expense["id"], expense["id"]),
            }
            for expense in expenses
        ]

    def _validate_payload(self, payload: dict) -> dict:
        date = (payload.get("date") or "").strip()
        category = (payload.get("category") or "").strip()
        description = (payload.get("description") or "").strip()
        amount_value = payload.get("amount")

        if not date or not category or not description or amount_value in (None, ""):
            raise ValidationError("date, category, description, and amount are required.")

        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError("date must use YYYY-MM-DD format.") from exc
        if parsed_date > datetime.now().date():
            raise ValidationError("date cannot be in the future.")

        try:
            amount = round(float(amount_value), 2)
        except (TypeError, ValueError) as exc:
            raise ValidationError("amount must be numeric.") from exc

        return {
            "date": date,
            "category": category,
            "description": description,
            "amount": amount,
            "entry_type": "expense",
        }

    def _apply_filters(self, expenses: list[dict], filters: dict) -> list[dict]:
        category = str(filters.get("category") or "").strip().lower()
        query = str(filters.get("q") or "").strip().lower()
        start_date = str(filters.get("start_date") or "").strip()
        end_date = str(filters.get("end_date") or "").strip()

        for label, raw_date in (("start_date", start_date), ("end_date", end_date)):
            if raw_date:
                try:
                    datetime.strptime(raw_date, "%Y-%m-%d")
                except ValueError as exc:
                    raise ValidationError(f"{label} must use YYYY-MM-DD format.") from exc

        filtered = expenses
        if category:
            filtered = [expense for expense in filtered if expense["category"].strip().lower() == category]
        if start_date:
            filtered = [expense for expense in filtered if expense["date"] >= start_date]
        if end_date:
            filtered = [expense for expense in filtered if expense["date"] <= end_date]
        if query:
            filtered = [
                expense
                for expense in filtered
                if query in expense["description"].lower() or query in expense["category"].lower()
            ]
        return filtered

    @staticmethod
    def _normalize_header(header: str | None) -> str:
        return (header or "").strip().lower()

    def _clean_csv_row(self, row: dict[str, Any]) -> dict[str, str] | None:
        cleaned = {
            "date": self._clean_cell(row.get("date")),
            "category": self._clean_cell(row.get("category")),
            "description": self._clean_cell(row.get("description")),
            "amount": self._clean_amount(row.get("amount")),
            "entry_type": "expense",
        }

        if not any(cleaned[field] for field in ("date", "category", "description", "amount")):
            return None
        if any(value == "" for value in cleaned.values()):
            return None
        return cleaned

    @staticmethod
    def _clean_cell(value: Any) -> str:
        return str(value or "").strip()

    def _clean_amount(self, value: Any) -> str:
        normalized = self._clean_cell(value)
        return (
            normalized.replace(",", "")
            .replace("GBP", "")
            .replace("gbp", "")
            .replace("Â£", "")
            .replace("£", "")
            .strip()
        )
