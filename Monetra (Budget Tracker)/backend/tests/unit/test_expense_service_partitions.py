from types import SimpleNamespace
import io

import pytest

from budget_tracker_api.errors import ValidationError
from budget_tracker_api.services.expense_service import ExpenseService


class PartitionRepository:
    def __init__(self):
        self.inserted_rows = []

    def bulk_insert(self, rows):
        self.inserted_rows.extend(rows)
        return len(rows)

    def list_expenses(self, _sort_direction="desc", entry_type=None):
        return []


def make_file_storage(content: bytes):
    return SimpleNamespace(stream=io.BytesIO(content))


@pytest.mark.parametrize(
    "payload",
    [
        {
            "date": "2026-03-08",
            "category": "Salary",
            "description": "Payroll",
            "amount": "2500.00",
            "entry_type": "income",
        },
        {
            "date": "2026-03-09",
            "category": "Travel",
            "description": "Train",
            "amount": "12.40",
            "type": "expense",
        },
    ],
)
def test_validate_payload_normalizes_supported_type_partitions_to_expense(payload):
    service = ExpenseService(PartitionRepository())

    validated = service._validate_payload(payload)

    assert validated["entry_type"] == "expense"


@pytest.mark.parametrize(
    "payload",
    [
        {
            "date": "2026-03-08",
            "category": "  ",
            "description": "Lunch",
            "amount": "12.50",
        },
        {
            "date": "2026-03-08",
            "category": "Food",
            "description": "",
            "amount": "12.50",
        },
        {
            "date": "2026-03-08",
            "category": "Food",
            "description": "Lunch",
            "amount": "",
        },
    ],
)
def test_validate_payload_rejects_required_field_partitions(payload):
    service = ExpenseService(PartitionRepository())

    with pytest.raises(ValidationError, match="date, category, description, and amount are required."):
        service._validate_payload(payload)


@pytest.mark.parametrize(
    "raw_amount,expected",
    [
        ("GBP 1,240.50", "1240.50"),
        ("gbp 82.00", "82.00"),
    ],
)
def test_clean_amount_normalizes_supported_amount_partitions(raw_amount, expected):
    service = ExpenseService(PartitionRepository())

    assert service._clean_amount(raw_amount) == expected


def test_import_csv_normalizes_all_rows_to_expense():
    repository = PartitionRepository()
    service = ExpenseService(repository)

    result = service.import_csv(
        make_file_storage(
            b"date,category,description,amount,entry_type\n"
            b"2026-03-01,Salary,Payroll,2500.00,income\n"
            b"2026-03-03,Food,Groceries,82.45,expense\n"
        )
    )

    assert result == {"imported_rows": 2, "skipped_rows": 0}
    assert repository.inserted_rows[0]["entry_type"] == "expense"
    assert repository.inserted_rows[1]["entry_type"] == "expense"


def test_import_csv_skips_partially_populated_rows():
    repository = PartitionRepository()
    service = ExpenseService(repository)

    result = service.import_csv(
        make_file_storage(
            b"date,category,description,amount\n"
            b"2026-03-01,Food,Groceries,25.00\n"
            b"2026-03-02,Travel,,12.00\n"
            b"2026-03-03,,Taxi,18.00\n"
            b",Bills,Rent,700.00\n"
        )
    )

    assert result == {"imported_rows": 1, "skipped_rows": 3}
    assert repository.inserted_rows == [
        {
            "date": "2026-03-01",
            "category": "Food",
            "description": "Groceries",
            "amount": 25.0,
            "entry_type": "expense",
        }
    ]