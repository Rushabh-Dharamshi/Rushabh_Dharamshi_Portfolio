from datetime import date

from sqlalchemy import create_engine

from budget_tracker_api.db import metadata
from budget_tracker_api.repositories.expense_repository import ExpenseRepository


def build_repository(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'repository.db'}", future=True)
    metadata.create_all(engine)
    connection = engine.connect()
    repository = ExpenseRepository(lambda: connection)
    return repository, connection, engine


def test_repository_crud_and_aggregates(tmp_path):
    repository, connection, engine = build_repository(tmp_path)
    try:
        assert repository.bulk_insert([]) == 0

        created = repository.create_expense(
            {
                "date": "2026-03-04",
                "category": "Food",
                "description": "Groceries",
                "amount": 24.5,
                "entry_type": "expense",
            }
        )
        repository.bulk_insert(
            [
                {
                    "date": "2026-03-10",
                    "category": "Travel",
                    "description": "Train",
                    "amount": 60.0,
                    "entry_type": "expense",
                },
                {
                    "date": "2026-02-15",
                    "category": "Bills",
                    "description": "Energy",
                    "amount": 120.0,
                    "entry_type": "expense",
                },
                {
                    "date": "2026-03-12",
                    "category": "Salary",
                    "description": "Payroll",
                    "amount": 900.0,
                    "entry_type": "income",
                },
            ]
        )

        listed = repository.list_expenses("asc")
        assert listed[0].date == "2026-02-15"
        assert repository.get_expense(created.id).description == "Groceries"
        assert repository.update_expense(999, {"date": "2026-03-01", "category": "Food", "description": "Missing", "amount": 10, "entry_type": "expense"}) is None
        assert repository.monthly_spending() == [("2026-02", 120.0), ("2026-03", 84.5)]
        assert repository.monthly_spending("income") == [("2026-03", 900.0)]
        assert repository.monthly_cash_flow()[-1]["net"] == 815.5
        assert repository.monthly_total("2026-03") == 84.5
        assert repository.monthly_total("2026-03", "income") == 900.0
        assert repository.weekly_total("2026-03-01", "2026-03-31") == 84.5
        assert repository.category_totals("2026-03") == [("Travel", 60.0), ("Food", 24.5)]
        assert repository.count_expenses_for_month("2026-03") == 3
        assert repository.description_totals_for_category("2026-03", "Food") == [("Groceries", 24.5)]
        assert repository.daily_totals("2026-03") == [("2026-03-04", 24.5), ("2026-03-10", 60.0)]
        assert repository.largest_expenses("2026-03", limit=1)[0].description == "Train"
        assert repository.delete_expense(created.id) is True
        assert repository.delete_expense(999) is False
    finally:
        connection.close()
        engine.dispose()


def test_repository_date_helpers_cover_edge_cases():
    december_start, december_end = ExpenseRepository._month_bounds("2026-12")

    assert december_start == date(2026, 12, 1)
    assert december_end == date(2027, 1, 1)
    assert ExpenseRepository._month_key("2026-03-01") == "2026-03"
