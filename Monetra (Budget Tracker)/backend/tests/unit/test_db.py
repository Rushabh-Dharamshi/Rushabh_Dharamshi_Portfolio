from contextlib import contextmanager
from types import SimpleNamespace

from flask import Flask, g

from budget_tracker_api import db


class FakeConnection:
    def __init__(self):
        self.closed = False
        self.executed = []
        self.scalar = 0
        self.first_row = None

    def close(self):
        self.closed = True

    def execute(self, statement):
        self.executed.append(str(statement))
        return SimpleNamespace(scalar_one=lambda: self.scalar, first=lambda: self.first_row)


class FakeEngine:
    def __init__(self, dialect_name="sqlite"):
        self.dialect = SimpleNamespace(name=dialect_name)
        self.connection = FakeConnection()
        self.created = False

    def connect(self):
        return self.connection

    def begin(self):
        engine = self

        @contextmanager
        def ctx():
            yield engine.connection

        return ctx()


class FakeCursor:
    def __init__(self, row=None):
        self.row = row
        self.executed = []

    def execute(self, statement, params=None):
        self.executed.append((statement, params))

    def fetchone(self):
        return self.row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakePsycopgConnection:
    def __init__(self, row=None):
        self.cursor_obj = FakeCursor(row=row)

    def cursor(self):
        return self.cursor_obj

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeInspector:
    def __init__(self, columns):
        self.columns = columns

    def get_columns(self, table_name):
        return [{"name": name} for name in self.columns.get(table_name, [])]


def test_db_engine_connection_and_close(monkeypatch):
    app = Flask(__name__)
    app.config.update(DATABASE_URL="sqlite:///test.db", MONTHLY_BUDGET=1000, MONTHLY_INCOME=1500)
    engine = FakeEngine()
    created = []
    monkeypatch.setattr(db, "create_engine", lambda *args, **kwargs: created.append(True) or engine)

    with app.app_context():
        first = db.get_engine()
        second = db.get_engine()
        assert first is second
        conn = db.get_db()
        assert conn is engine.connection
        db.close_db()
        assert engine.connection.closed is True
        db.close_db()
    assert created == [True]


def test_db_migration_seed_and_database_creation(monkeypatch):
    app = Flask(__name__)
    app.config.update(
        DATABASE_URL="postgresql://user:pass@localhost:5432/monetra",
        POSTGRES_MAINTENANCE_DB="postgres",
        MONTHLY_BUDGET=1000,
        MONTHLY_INCOME=1500,
        AUTH_USERNAME="Rushabh",
        AUTH_EMAIL="rushabh@example.com",
        AUTH_PASSWORD_HASH="hashed-password",
    )
    engine = FakeEngine(dialect_name="postgresql")
    engine.connection.scalar = 0
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    monkeypatch.setattr(db.metadata, "create_all", lambda incoming: setattr(incoming, "created", True))
    monkeypatch.setattr(db, "inspect", lambda incoming: FakeInspector({
        "expenses": ["id"],
        "settings": ["id"],
        "recurring_occurrence_status": ["id"],
        "recurring_items": ["id"],
        "monthly_budget_records": ["id", "month_key", "monthly_budget"],
    }))
    psycopg_conn = FakePsycopgConnection(row=None)
    monkeypatch.setattr(db, "connect", lambda **kwargs: psycopg_conn)

    with app.app_context():
        db.init_db()
        db._ensure_database_exists()

    sql_calls = "\n".join(engine.connection.executed)
    assert "ALTER TABLE expenses ADD COLUMN entry_type" in sql_calls
    assert "ALTER TABLE settings ADD COLUMN monthly_income" in sql_calls
    assert "ALTER TABLE recurring_occurrence_status ADD COLUMN transaction_id" in sql_calls
    assert "ALTER TABLE recurring_items ADD COLUMN end_date" in sql_calls
    assert "ALTER TABLE monthly_budget_records ADD COLUMN user_id" in sql_calls
    assert "pg_get_serial_sequence('users', 'id')" in sql_calls
    assert any("CREATE DATABASE" in str(call[0]) for call in psycopg_conn.cursor_obj.executed)


def test_db_ensure_database_exists_short_circuits(monkeypatch):
    app = Flask(__name__)
    app.config.update(DATABASE_URL="sqlite:///test.db", MONTHLY_BUDGET=1000, MONTHLY_INCOME=1500)

    with app.app_context():
        db._ensure_database_exists()

    app2 = Flask(__name__)
    app2.config.update(DATABASE_URL="postgresql://user:pass@localhost:5432", MONTHLY_BUDGET=1000, MONTHLY_INCOME=1500)
    with app2.app_context():
        db._ensure_database_exists()
