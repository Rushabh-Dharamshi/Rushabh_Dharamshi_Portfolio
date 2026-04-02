import csv
import io
from datetime import datetime
from typing import Any

from budget_tracker_api.errors import NotFoundError, ValidationError
from budget_tracker_api.repositories.expense_repository import ExpenseRepository


class ExpenseService:
    def __init__(self, repository: ExpenseRepository):
        self._repository = repository

    def list_expenses(self, sort_direction: str = "desc") -> list[dict]:
        return [
            expense.to_dict()
            for expense in self._repository.list_expenses(sort_direction, entry_type="expense")
        ]

    def get_expense(self, expense_id: int) -> dict:
        expense = self._repository.get_expense(expense_id)
        if expense is None or getattr(expense, "entry_type", "expense") != "expense":
            raise NotFoundError(f"Expense with id {expense_id} was not found.")
        return expense.to_dict()

    def create_expense(self, payload: dict) -> dict:
        data = self._validate_payload(payload)
        return self._repository.create_expense(data).to_dict()

    def update_expense(self, expense_id: int, payload: dict) -> dict:
        existing = self._repository.get_expense(expense_id)
        if existing is None or getattr(existing, "entry_type", "expense") != "expense":
            raise NotFoundError(f"Expense with id {expense_id} was not found.")
        data = self._validate_payload(payload)
        expense = self._repository.update_expense(expense_id, data)
        if expense is None:
            raise NotFoundError(f"Expense with id {expense_id} was not found.")
        return expense.to_dict()

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
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Date", "Category", "Description", "Amount", "Type"])
        for expense in self._repository.list_expenses("desc", entry_type="expense"):
            writer.writerow(
                [
                    expense.id,
                    expense.date,
                    expense.category,
                    expense.description,
                    f"{expense.amount:.2f}",
                    "expense",
                ]
            )
        return output.getvalue()

    def _validate_payload(self, payload: dict) -> dict:
        date = (payload.get("date") or "").strip()
        category = (payload.get("category") or "").strip()
        description = (payload.get("description") or "").strip()
        amount_value = payload.get("amount")

        if not date or not category or not description or amount_value in (None, ""):
            raise ValidationError("date, category, description, and amount are required.")

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValidationError("date must use YYYY-MM-DD format.") from exc

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

        if not any(cleaned.values()):
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