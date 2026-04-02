import csv
import io
from types import SimpleNamespace

import pytest

from budget_tracker_api.errors import NotFoundError, ValidationError
from budget_tracker_api.schemas import Expense
from budget_tracker_api.services.expense_service import ExpenseService


class StubExpenseRepository:
    def __init__(self):
        self.created_payload = None
        self.updated_payload = None
        self.deleted_ids = []
        self.imported_rows = []
        self.rows = [
            Expense(1, "2026-03-01", "Food", "Groceries", 20.0, "expense"),
            Expense(2, "2026-03-02", "Salary", "Payroll", 1500.0, "income"),
        ]

    def list_expenses(self, sort_direction="desc", entry_type=None):
        if entry_type is None:
            return self.rows
        return [row for row in self.rows if row.entry_type == entry_type]

    def get_expense(self, expense_id):
        return next((row for row in self.rows if row.id == expense_id), None)

    def create_expense(self, payload):
        self.created_payload = payload
        return Expense(3, payload["date"], payload["category"], payload["description"], payload["amount"], payload.get("entry_type", "expense"))

    def update_expense(self, expense_id, payload):
        self.updated_payload = (expense_id, payload)
        if expense_id == 99:
            return None
        return Expense(expense_id, payload["date"], payload["category"], payload["description"], payload["amount"], payload.get("entry_type", "expense"))

    def delete_expense(self, expense_id):
        self.deleted_ids.append(expense_id)
        return expense_id != 99

    def bulk_insert(self, rows):
        self.imported_rows = rows
        return len(rows)


def make_file_storage(content: bytes):
    return SimpleNamespace(stream=io.BytesIO(content))


def test_list_and_get_expense_only_surface_expense_records():
    service = ExpenseService(StubExpenseRepository())

    assert service.list_expenses() == [
        {
            "id": 1,
            "date": "2026-03-01",
            "category": "Food",
            "description": "Groceries",
            "amount": 20.0,
            "entry_type": "expense",
        }
    ]
    assert service.get_expense(1)["description"] == "Groceries"

    with pytest.raises(NotFoundError):
        service.get_expense(2)


def test_get_update_and_delete_raise_not_found():
    service = ExpenseService(StubExpenseRepository())

    with pytest.raises(NotFoundError):
        service.get_expense(99)

    with pytest.raises(NotFoundError):
        service.update_expense(
            99,
            {
                "date": "2026-03-01",
                "category": "Food",
                "description": "Lunch",
                "amount": "12.50",
            },
        )

    with pytest.raises(NotFoundError):
        service.delete_expense(99)


def test_create_and_update_normalize_entry_type_to_expense():
    repository = StubExpenseRepository()
    service = ExpenseService(repository)

    created = service.create_expense(
        {
            "date": "2026-03-08",
            "category": "Travel",
            "description": "Bus ticket",
            "amount": "4.55",
            "entry_type": "income",
        }
    )
    updated = service.update_expense(
        1,
        {
            "date": "2026-03-09",
            "category": "Bills",
            "description": "Internet",
            "amount": "34.00",
            "entry_type": "income",
        },
    )

    assert repository.created_payload["amount"] == 4.55
    assert repository.created_payload["entry_type"] == "expense"
    assert repository.updated_payload[1]["entry_type"] == "expense"
    assert created["entry_type"] == "expense"
    assert updated["description"] == "Internet"


@pytest.mark.parametrize(
    "payload,error_message",
    [
        ({}, "date, category, description, and amount are required."),
        (
            {"date": "2026/03/08", "category": "Travel", "description": "Bus", "amount": "3"},
            "date must use YYYY-MM-DD format.",
        ),
        (
            {"date": "2026-03-08", "category": "Travel", "description": "Bus", "amount": "abc"},
            "amount must be numeric.",
        ),
    ],
)
def test_validate_payload_errors(payload, error_message):
    service = ExpenseService(StubExpenseRepository())

    with pytest.raises(ValidationError, match=error_message):
        service.create_expense(payload)


def test_import_csv_counts_imported_and_skipped_rows_and_forces_expense_type():
    repository = StubExpenseRepository()
    service = ExpenseService(repository)

    file_storage = make_file_storage(
        b"date,category,description,amount,entry_type\n"
        b"2026-03-01,Food,Groceries,20.50,expense\n"
        b"2026-03-02,Salary,Payroll,2500.00,income\n"
        b"invalid-date,Food,Bad Row,10.00,expense\n"
    )

    result = service.import_csv(file_storage)

    assert result == {"imported_rows": 2, "skipped_rows": 1}
    assert repository.imported_rows[0]["description"] == "Groceries"
    assert repository.imported_rows[0]["entry_type"] == "expense"
    assert repository.imported_rows[1]["entry_type"] == "expense"


def test_import_csv_cleans_headers_whitespace_and_missing_values():
    repository = StubExpenseRepository()
    service = ExpenseService(repository)

    file_storage = make_file_storage(
        b" date , category , description , amount \n"
        b"2026-03-02, Food , Market , 19.50 \n"
        b"2026-03-03,Travel,,14.00\n"
        b",Bills,Energy,65.00\n"
    )

    result = service.import_csv(file_storage)

    assert result == {"imported_rows": 1, "skipped_rows": 2}
    assert repository.imported_rows == [
        {
            "date": "2026-03-02",
            "category": "Food",
            "description": "Market",
            "amount": 19.5,
            "entry_type": "expense",
        }
    ]


def test_import_csv_handles_missing_file_encoding_and_format_errors():
    service = ExpenseService(StubExpenseRepository())

    with pytest.raises(ValidationError, match="CSV file is required."):
        service.import_csv(None)

    with pytest.raises(ValidationError, match="UTF-8 encoding"):
        service.import_csv(make_file_storage(b"\xff\xfe\x00\x00"))


def test_import_csv_rejects_missing_headers():
    service = ExpenseService(StubExpenseRepository())

    with pytest.raises(ValidationError, match="CSV file format is invalid."):
        service.import_csv(make_file_storage(b""))


def test_import_csv_rejects_csv_reader_errors(monkeypatch):
    service = ExpenseService(StubExpenseRepository())

    class BrokenReader:
        fieldnames = ["date", "category", "description", "amount"]

        def __iter__(self):
            raise csv.Error("bad csv")

    monkeypatch.setattr(csv, "DictReader", lambda *_args, **_kwargs: BrokenReader())

    with pytest.raises(ValidationError, match="CSV file format is invalid."):
        service.import_csv(make_file_storage(b"date,category,description,amount\n"))


def test_clean_csv_row_returns_none_for_blank_rows():
    service = ExpenseService(StubExpenseRepository())

    assert service._clean_csv_row({"date": " ", "category": "", "description": None, "amount": ""}) is None


def test_export_csv_outputs_header_and_only_expense_rows():
    service = ExpenseService(StubExpenseRepository())

    csv_output = service.export_csv()

    assert "ID,Date,Category,Description,Amount,Type" in csv_output
    assert "Groceries" in csv_output
    assert "Payroll" not in csv_output