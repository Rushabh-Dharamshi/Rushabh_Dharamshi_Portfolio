from datetime import date

from budget_tracker_api.services.recurring_service import RecurringService


class StubRecurringRepository:
    def __init__(self, items):
        self._items = items

    def list_items(self):
        return self._items

    def paid_occurrences_for_range(self, window_start, window_end):
        return set()

    def paid_occurrence_entries_for_range(self, window_start, window_end):
        return []


class StubExpenseService:
    def get_expense(self, expense_id):
        raise AssertionError("Expense lookup is not expected in this test")


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 3, 29)


def test_upcoming_calendar_respects_inclusive_end_date(monkeypatch):
    monkeypatch.setattr("budget_tracker_api.services.recurring_service.date", FixedDate)
    service = RecurringService(
        StubRecurringRepository(
            [
                {
                    "id": 1,
                    "category": "Rent",
                    "description": "University House Rent",
                    "amount": 452.74,
                    "entry_type": "expense",
                    "frequency": "monthly",
                    "start_date": "2026-04-23",
                    "end_date": "2026-06-23",
                    "active": True,
                }
            ]
        ),
        StubExpenseService(),
    )

    calendar = service.upcoming_calendar(90)

    assert [occurrence["date"] for occurrence in calendar["occurrences"]] == [
        "2026-04-23",
        "2026-05-23",
        "2026-06-23",
    ]
