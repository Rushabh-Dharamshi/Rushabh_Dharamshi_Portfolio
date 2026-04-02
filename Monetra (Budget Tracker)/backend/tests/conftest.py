import shutil
import uuid
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import insert

from budget_tracker_api import create_app
from budget_tracker_api.db import expenses_table, get_db, recurring_items_table, settings_table


@pytest.fixture()
def tmp_path():
    path = Path(__file__).resolve().parents[1] / ".tmp" / str(uuid.uuid4())
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture()
def app(tmp_path: Path):
    database_path = tmp_path / "test-budget.db"
    reports_path = tmp_path / "reports"

    app = create_app(
        {
            "TESTING": True,
            "PROPAGATE_EXCEPTIONS": False,
            "LOGIN_REQUIRED": False,
            "DATABASE_URL": f"sqlite+pysqlite:///{database_path}",
            "GENERATED_REPORTS_DIR": reports_path,
            "MONTHLY_BUDGET": 1050.0,
        }
    )

    with app.app_context():
        db = get_db()
        db.execute(expenses_table.delete())
        db.execute(recurring_items_table.delete())
        db.execute(settings_table.delete())
        db.execute(
            insert(expenses_table),
            [
                {
                    "date": date(2026, 3, 1),
                    "category": "Food",
                    "description": "Groceries",
                    "amount": 65.25,
                    "entry_type": "expense",
                },
                {
                    "date": date(2026, 3, 3),
                    "category": "Travel",
                    "description": "Train pass",
                    "amount": 80.00,
                    "entry_type": "expense",
                },
                {
                    "date": date(2026, 3, 5),
                    "category": "Food",
                    "description": "Cafe",
                    "amount": 18.40,
                    "entry_type": "expense",
                },
                {
                    "date": date(2026, 2, 10),
                    "category": "Bills",
                    "description": "Energy bill",
                    "amount": 120.00,
                    "entry_type": "expense",
                },
                {
                    "date": date(2026, 3, 2),
                    "category": "Salary",
                    "description": "Payroll",
                    "amount": 1200.00,
                    "entry_type": "income",
                },
            ],
        )
        db.execute(
            insert(settings_table),
            [{"id": 1, "monthly_budget": 1050.0, "monthly_income": 1500.0}],
        )
        db.execute(
            insert(recurring_items_table),
            [
                {
                    "category": "Housing",
                    "description": "Rent",
                    "amount": 700.00,
                    "entry_type": "expense",
                    "frequency": "monthly",
                    "start_date": date(2026, 3, 1),
                    "active": True,
                },
                {
                    "category": "Salary",
                    "description": "Payroll",
                    "amount": 1200.00,
                    "entry_type": "income",
                    "frequency": "monthly",
                    "start_date": date(2026, 3, 2),
                    "active": True,
                },
            ],
        )
        db.commit()

    return app


@pytest.fixture()
def client(app):
    return app.test_client()
