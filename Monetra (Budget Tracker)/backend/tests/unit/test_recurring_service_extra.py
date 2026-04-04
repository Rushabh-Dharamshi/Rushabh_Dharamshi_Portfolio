from datetime import date

import pytest

from budget_tracker_api.errors import NotFoundError, ValidationError
from budget_tracker_api.services.recurring_service import RecurringService


class StubRecurringRepository:
    def __init__(self, items=None):
        self._items = items or []
        self.updated = None
        self.deleted = []
        self.created = None
        self.paid = set()
        self.paid_entries = []
        self.link_by_transaction = None

    def list_items(self):
        return self._items

    def get_item(self, item_id):
        return next((item for item in self._items if item["id"] == item_id), None)

    def create_item(self, payload):
        self.created = payload
        return {"id": 99, **payload}

    def update_item(self, item_id, payload):
        if not any(item["id"] == item_id for item in self._items):
            return None
        self.updated = (item_id, payload)
        return {"id": item_id, **payload}

    def delete_item(self, item_id):
        self.deleted.append(item_id)
        return any(item["id"] == item_id for item in self._items)

    def get_paid_occurrence_by_transaction_id(self, transaction_id):
        return self.link_by_transaction

    def mark_occurrence_paid(self, item_id, occurrence_date, transaction_id):
        self.paid.add((item_id, occurrence_date))
        return {"recurring_item_id": item_id, "occurrence_date": occurrence_date, "transaction_id": transaction_id}

    def mark_occurrence_unpaid(self, item_id, occurrence_date):
        self.paid.discard((item_id, occurrence_date))
        return {"recurring_item_id": item_id, "occurrence_date": occurrence_date, "is_paid": False}

    def paid_occurrences_for_range(self, window_start, window_end):
        return self.paid

    def paid_occurrence_entries_for_range(self, window_start, window_end):
        return self.paid_entries


class StubExpenseService:
    def __init__(self, expense=None):
        self.expense = expense or {
            "id": 5,
            "entry_type": "expense",
            "amount": 20.0,
            "category": "Travel",
        }

    def get_expense(self, expense_id):
        expense = dict(self.expense)
        expense["id"] = expense_id
        return expense


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 3, 29)


def build_item(**overrides):
    item = {
        "id": 1,
        "category": "Travel",
        "description": "Bus pass",
        "amount": 20.0,
        "entry_type": "expense",
        "frequency": "weekly",
        "start_date": "2026-03-20",
        "end_date": None,
        "active": True,
    }
    item.update(overrides)
    return item


def test_recurring_service_validation_and_crud_paths(monkeypatch):
    monkeypatch.setattr("budget_tracker_api.services.recurring_service.date", FixedDate)
    repository = StubRecurringRepository([build_item()])
    service = RecurringService(repository, StubExpenseService())

    assert service.list_items()[0]["description"] == "Bus pass"
    assert service.get_item(1)["category"] == "Travel"
    with pytest.raises(NotFoundError):
        service.get_item(404)

    created = service.create_item({
        "category": "Housing",
        "description": "Rent",
        "amount": "700",
        "entry_type": "expense",
        "frequency": "monthly",
        "start_date": "2026-04-01",
        "end_date": "2026-05-01",
        "active": True,
    })
    assert created["id"] == 99
    assert repository.created["amount"] == 700.0

    updated = service.update_item(1, {
        "category": "Travel",
        "description": "Bus pass",
        "amount": "25",
        "entry_type": "expense",
        "frequency": "weekly",
        "start_date": "2026-03-20",
        "end_date": "",
        "active": False,
    })
    assert updated["active"] is False
    with pytest.raises(NotFoundError):
        service.update_item(404, repository.created)

    service.delete_item(1)
    with pytest.raises(NotFoundError):
        service.delete_item(404)

    with pytest.raises(ValidationError):
        service.create_item({})
    with pytest.raises(ValidationError):
        service.create_item({"category": "x", "description": "y", "amount": "z", "start_date": "2026-04-01", "frequency": "monthly", "entry_type": "expense"})
    with pytest.raises(ValidationError):
        service.create_item({"category": "x", "description": "y", "amount": "1", "start_date": "bad", "frequency": "monthly", "entry_type": "expense"})
    with pytest.raises(ValidationError):
        service.create_item({"category": "x", "description": "y", "amount": "1", "start_date": "2026-04-01", "end_date": "bad", "frequency": "monthly", "entry_type": "expense"})
    with pytest.raises(ValidationError):
        service.create_item({"category": "x", "description": "y", "amount": "1", "start_date": "2026-04-01", "end_date": "2026-03-01", "frequency": "monthly", "entry_type": "expense"})
    with pytest.raises(ValidationError):
        service.create_item({"category": "x", "description": "y", "amount": "1", "start_date": "2026-04-01", "frequency": "yearly", "entry_type": "expense"})
    with pytest.raises(ValidationError):
        service.create_item({"category": "x", "description": "y", "amount": "1", "start_date": "2026-04-01", "frequency": "monthly", "entry_type": "other"})


def test_recurring_service_paid_and_calendar_branches(monkeypatch):
    monkeypatch.setattr("budget_tracker_api.services.recurring_service.date", FixedDate)
    paid_entry = {
        "recurring_item_id": 1,
        "occurrence_date": "2026-04-03",
        "updated_at": "2026-04-03T09:00:00Z",
        "transaction_id": 8,
    }
    repository = StubRecurringRepository(
        [
            build_item(),
            build_item(id=2, description="Salary", category="Salary", amount=1200.0, entry_type="income", frequency="monthly", start_date="2026-03-29"),
            build_item(id=3, description="Dormant", active=False),
            build_item(id=4, description="Expired", frequency="monthly", start_date="2026-01-15", end_date="2026-02-15"),
        ]
    )
    repository.paid = {(1, "2026-04-03")}
    repository.paid_entries = [paid_entry]
    service = RecurringService(repository, StubExpenseService({"id": 8, "entry_type": "expense", "amount": 20.0, "category": "Travel"}))

    marked = service.mark_occurrence_paid(1, {"occurrence_date": "2026-04-10", "transaction_id": 8})
    assert marked["message"].startswith("Reminder marked as paid")
    restored = service.mark_occurrence_unpaid(1, {"date": "2026-04-10"})
    assert restored["message"] == "Reminder restored for this date."

    calendar = service.upcoming_calendar(10)
    assert calendar["window_start"] == "2026-03-29"
    assert any(item["description"] == "Salary" for item in calendar["occurrences"])
    assert any(item["description"] == "Bus pass" and item["transaction_id"] == 8 for item in calendar["completed_occurrences"])
    assert all(item["description"] != "Dormant" for item in calendar["occurrences"])
    assert all(item["description"] != "Expired" for item in calendar["occurrences"])


def test_recurring_service_paid_validation_helpers():
    repository = StubRecurringRepository([build_item()])
    expense_service = StubExpenseService()
    service = RecurringService(repository, expense_service)

    with pytest.raises(ValidationError):
        service.mark_occurrence_paid(1, {"occurrence_date": "", "transaction_id": 5})
    with pytest.raises(ValidationError):
        service.mark_occurrence_paid(1, {"occurrence_date": "bad", "transaction_id": 5})
    with pytest.raises(ValidationError):
        service.mark_occurrence_paid(1, {"occurrence_date": "2026-04-01"})
    with pytest.raises(ValidationError):
        service.mark_occurrence_paid(1, {"occurrence_date": "2026-04-01", "transaction_id": "x"})

    repository.link_by_transaction = {"recurring_item_id": 99, "occurrence_date": "2026-04-01"}
    with pytest.raises(ValidationError):
        service.mark_occurrence_paid(1, {"occurrence_date": "2026-04-01", "transaction_id": 5})

    repository.link_by_transaction = None
    expense_service.expense = {"id": 5, "entry_type": "income", "amount": 20.0, "category": "Travel"}
    with pytest.raises(ValidationError):
        service.mark_occurrence_paid(1, {"occurrence_date": "2026-04-01", "transaction_id": 5})
    expense_service.expense = {"id": 5, "entry_type": "expense", "amount": 30.0, "category": "Travel"}
    with pytest.raises(ValidationError):
        service.mark_occurrence_paid(1, {"occurrence_date": "2026-04-01", "transaction_id": 5})
    expense_service.expense = {"id": 5, "entry_type": "expense", "amount": 20.0, "category": "Food"}
    with pytest.raises(ValidationError):
        service.mark_occurrence_paid(1, {"occurrence_date": "2026-04-01", "transaction_id": 5})

    assert service._first_due_on_or_after("2026-03-20", "weekly", date(2026, 3, 29)) == date(2026, 4, 3)
    assert service._next_due_date(date(2026, 1, 31), "monthly") == date(2026, 2, 28)
    assert service._parse_optional_date(None) is None
    assert service._parse_optional_date("2026-04-01") == date(2026, 4, 1)
