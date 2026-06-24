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
        expense = Expense(3, payload["date"], payload["category"], payload["description"], payload["amount"], payload.get("entry_type", "expense"))
        self.rows.append(expense)
        return expense

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
            "user_expense_id": 1,
        }
    ]
    assert service.get_expense(1)["description"] == "Groceries"
    assert service.get_expense_by_user_expense_id(1)["id"] == 1

    with pytest.raises(NotFoundError):
        service.get_expense(2)
    with pytest.raises(NotFoundError):
        service.get_expense_by_user_expense_id("bad")
    with pytest.raises(NotFoundError):
        service.get_expense_by_user_expense_id(404)


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
    assert created["user_expense_id"] == 2
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


def test_expense_dates_cannot_be_in_the_future(monkeypatch):
    import budget_tracker_api.services.expense_service as expense_service_module
    from datetime import datetime as real_datetime

    class FrozenDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 5, 15, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(expense_service_module, "datetime", FrozenDateTime)
    service = ExpenseService(StubExpenseRepository())

    with pytest.raises(ValidationError, match="date cannot be in the future."):
        service.create_expense(
            {
                "date": "2026-05-16",
                "category": "Food",
                "description": "Tomorrow lunch",
                "amount": "12.00",
            }
        )


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


def test_import_csv_skips_future_dated_expenses(monkeypatch):
    import budget_tracker_api.services.expense_service as expense_service_module
    from datetime import datetime as real_datetime

    class FrozenDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 5, 15, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(expense_service_module, "datetime", FrozenDateTime)
    repository = StubExpenseRepository()
    service = ExpenseService(repository)

    file_storage = make_file_storage(
        b"date,category,description,amount\n"
        b"2026-05-15,Food,Today lunch,20.50\n"
        b"2026-05-16,Food,Future lunch,10.00\n"
    )

    result = service.import_csv(file_storage)

    assert result == {"imported_rows": 1, "skipped_rows": 1}
    assert repository.imported_rows[0]["description"] == "Today lunch"


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


def test_list_expenses_rejects_invalid_filter_dates():
    service = ExpenseService(StubExpenseRepository())

    with pytest.raises(ValidationError, match="start_date must use YYYY-MM-DD"):
        service.list_expenses(filters={"start_date": "06/01/2026"})
    with pytest.raises(ValidationError, match="end_date must use YYYY-MM-DD"):
        service.list_expenses(filters={"end_date": "06/30/2026"})


def test_export_csv_outputs_header_and_only_current_may_to_date_expense_rows(monkeypatch):
    import budget_tracker_api.services.expense_service as expense_service_module
    from datetime import datetime as real_datetime

    class FrozenDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 5, 15, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(expense_service_module, "datetime", FrozenDateTime)

    class MayExportRepository(StubExpenseRepository):
        def __init__(self):
            super().__init__()
            self.rows = [
                Expense(1, "2026-05-01", "Food", "Groceries", 20.0, "expense"),
                Expense(2, "2026-05-15", "Travel", "Train", 12.5, "expense"),
                Expense(3, "2026-05-16", "Food", "Future dinner", 30.0, "expense"),
                Expense(4, "2026-04-30", "Bills", "April energy", 80.0, "expense"),
                Expense(5, "2026-05-10", "Salary", "Payroll", 1500.0, "income"),
            ]

    service = ExpenseService(MayExportRepository())

    csv_output = service.export_csv()

    assert "ID,Date,Category,Description,Amount,Type" in csv_output
    assert "Groceries" in csv_output
    assert "Train" in csv_output
    assert "Future dinner" not in csv_output
    assert "April energy" not in csv_output
    assert "Payroll" not in csv_output
