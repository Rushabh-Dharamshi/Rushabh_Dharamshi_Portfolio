from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from werkzeug.security import generate_password_hash

from budget_tracker_api.db import (
    agent_runs_table,
    expenses_table,
    metadata,
    monthly_income_records_table,
    recurring_items_table,
    recurring_occurrence_status_table,
    savings_goals_table,
    settings_table,
)
from budget_tracker_api.errors import NotFoundError, ValidationError
from budget_tracker_api.repositories.latency_repository import LatencyRepository
from budget_tracker_api.repositories.savings_goal_repository import SavingsGoalRepository
from budget_tracker_api.repositories.settings_repository import SettingsRepository
from budget_tracker_api.repositories.user_repository import UserRepository
from budget_tracker_api.services.latency_service import LatencyService
from budget_tracker_api.services.savings_goal_service import SavingsGoalService
from budget_tracker_api.services.user_service import UserService


@pytest.fixture()
def sqlite_connection(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'last-mile.db'}", future=True)
    metadata.create_all(engine)
    connection = engine.connect()
    try:
        yield connection
    finally:
        connection.close()
        engine.dispose()


def test_savings_goal_service_validation_and_not_found_paths():
    class Repository:
        def __init__(self):
            self.deleted = False

        def list_goals(self):
            return [{"id": 1}]

        def create_goal(self, payload):
            return payload

        def update_goal(self, goal_id, payload):
            return None

        def delete_goal(self, goal_id):
            return self.deleted

    repository = Repository()
    service = SavingsGoalService(repository)

    assert service.list_goals() == [{"id": 1}]
    assert service.create_goal({"name": "  Buffer  ", "target_amount": "100", "current_amount": "", "target_date": ""}) == {
        "name": "Buffer",
        "target_amount": 100.0,
        "current_amount": 0.0,
        "target_date": None,
    }
    repository.update_goal = lambda goal_id, payload: {"id": goal_id, **payload}
    assert service.update_goal(1, {"name": "Buffer", "target_amount": "150", "current_amount": "25"}) == {
        "id": 1,
        "name": "Buffer",
        "target_amount": 150.0,
        "current_amount": 25.0,
        "target_date": None,
    }
    repository.update_goal = lambda goal_id, payload: None

    for payload, message in [
        ({}, "name and target_amount"),
        ({"name": "Goal", "target_amount": "bad"}, "must be numeric"),
        ({"name": "Goal", "target_amount": "0"}, "greater than zero"),
        ({"name": "Goal", "target_amount": "10", "current_amount": "-1"}, "cannot be negative"),
        ({"name": "Goal", "target_amount": "10", "target_date": "12/06/2026"}, "YYYY-MM-DD"),
    ]:
        with pytest.raises(ValidationError, match=message):
            service.create_goal(payload)

    with pytest.raises(NotFoundError):
        service.update_goal(99, {"name": "Goal", "target_amount": "10"})
    with pytest.raises(NotFoundError):
        service.delete_goal(99)


def test_savings_goal_repository_crud_and_payload_edges(sqlite_connection):
    repository = SavingsGoalRepository(lambda: sqlite_connection, user_id_provider=lambda: 7)

    created = repository.create_goal(
        {"name": "Holiday", "target_amount": "350.555", "current_amount": "400.12", "target_date": "2026-12-31"}
    )

    assert created["target_amount"] == 350.56
    assert created["current_amount"] == 400.12
    assert created["remaining_amount"] == 0.0
    assert created["progress_percent"] == 100.0
    assert created["target_date"] == "2026-12-31"
    assert repository.list_goals()[0]["name"] == "Holiday"

    updated = repository.update_goal(
        created["id"],
        {"name": "Holiday fund", "target_amount": "500", "current_amount": "125", "target_date": ""},
    )
    assert updated["target_date"] is None
    assert updated["progress_percent"] == 25.0
    assert repository.update_goal(999, {"name": "Missing", "target_amount": "100"}) is None
    assert repository.delete_goal(999) is False
    assert repository.delete_goal(created["id"]) is True


def test_user_repository_reset_token_and_delete_user_cascade(sqlite_connection):
    repository = UserRepository(lambda: sqlite_connection)
    user = repository.create_user("Owner", "owner@example.com", generate_password_hash("Password123"), "fingerprint")

    sqlite_connection.execute(
        expenses_table.insert().values(user_id=user["id"], date=date(2026, 6, 1), category="Food", description="Lunch", amount=10, entry_type="expense")
    )
    sqlite_connection.execute(settings_table.insert().values(user_id=user["id"], monthly_budget=600, monthly_income=1200))
    sqlite_connection.execute(monthly_income_records_table.insert().values(user_id=user["id"], month_key="2026-06", monthly_income=1200))
    recurring_result = sqlite_connection.execute(
        recurring_items_table.insert().values(
            user_id=user["id"],
            category="Bills",
            description="Internet",
            amount=30,
            entry_type="expense",
            frequency="monthly",
            start_date=date(2026, 6, 1),
            active=True,
        )
    )
    sqlite_connection.execute(
        recurring_occurrence_status_table.insert().values(
            user_id=user["id"],
            recurring_item_id=int(recurring_result.inserted_primary_key[0]),
            occurrence_date=date(2026, 6, 1),
            is_paid=True,
            transaction_id=None,
            updated_at="2026-06-01T00:00:00",
        )
    )
    sqlite_connection.execute(
        savings_goals_table.insert().values(
            user_id=user["id"],
            name="Buffer",
            target_amount=100,
            current_amount=20,
            target_date=None,
            created_at="2026-06-01T00:00:00",
        )
    )
    sqlite_connection.execute(
        agent_runs_table.insert().values(
            user_id=user["id"],
            workflow_name="month_end_close",
            workflow_label="Month-end close",
            task="Run",
            headline="Done",
            summary="Done",
            risk_level="low",
            recommended_actions="[]",
            automated_actions="[]",
            email_subject="Subject",
            email_draft="Draft",
            model="qwen",
            tools_used="[]",
            report_download_url=None,
            status="completed",
            generated_at="2026-06-01T00:00:00",
        )
    )
    sqlite_connection.commit()

    expires_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat(timespec="seconds").replace("+00:00", "Z")
    repository.create_reset_token(user["id"], "reset-code", expires_at)
    token_record = repository.get_reset_token("reset-code")
    assert token_record["used_at"] is None
    assert repository.get_reset_token("missing") is None
    repository.update_password_hash(user["id"], generate_password_hash("NewPassword123"), "new-fingerprint")
    updated_user = repository.get_user_by_id(user["id"])
    assert updated_user["password_fingerprint"] == "new-fingerprint"

    repository.mark_reset_token_used(token_record["id"])
    assert repository.get_reset_token("reset-code")["used_at"].endswith("Z")
    assert repository.delete_user(user["id"]) is True
    assert repository.delete_user(user["id"]) is False
    assert repository.count_users() == 0


def test_user_service_remaining_validation_and_reset_paths():
    class EmailService:
        def __init__(self, configured):
            self.configured = configured
            self.sent = []

        def is_configured(self):
            return self.configured

        def send_email(self, **payload):
            self.sent.append(payload)

    class Repository:
        def __init__(self):
            self.users = []
            self.tokens = {}

        def get_user_by_username(self, username):
            return next((user for user in self.users if user["username"] == username), None)

        def get_user_by_email(self, email):
            return next((user for user in self.users if user["email"] == email), None)

        def get_user_by_username_or_email(self, identifier):
            return self.get_user_by_email(identifier) if "@" in identifier else self.get_user_by_username(identifier)

        def get_user_by_id(self, user_id):
            return next((user for user in self.users if user["id"] == user_id), None)

        def list_users(self):
            return list(self.users)

        def count_users(self):
            return len(self.users)

        def create_user(self, username, email, password_hash, password_fingerprint=None):
            user = {"id": len(self.users) + 1, "username": username, "email": email, "password_hash": password_hash, "password_fingerprint": password_fingerprint}
            self.users.append(user)
            return user

        def delete_user(self, user_id):
            return False

        def create_reset_token(self, user_id, token, expires_at):
            self.tokens[token] = {"id": 1, "user_id": user_id, "expires_at": expires_at, "used_at": None}

        def get_reset_token(self, token):
            return self.tokens.get(token)

        def update_password_hash(self, user_id, password_hash, password_fingerprint=None):
            user = self.get_user_by_id(user_id)
            user["password_hash"] = password_hash
            user["password_fingerprint"] = password_fingerprint

        def mark_reset_token_used(self, token_id):
            for token in self.tokens.values():
                if token["id"] == token_id:
                    token["used_at"] = "used"

    repository = Repository()
    email_service = EmailService(configured=True)
    service = UserService(repository, email_service=email_service, expose_reset_tokens=True)

    for payload, message in [
        ({"username": "no", "email": "owner@example.com", "password": "Password123"}, "username must be"),
        ({"username": "Owner", "email": "bad", "password": "Password123"}, "email must be valid"),
        ({"username": "Owner", "email": "owner@example.com", "password": "short"}, "at least 8"),
    ]:
        with pytest.raises(ValidationError, match=message):
            service.register(payload)

    user = service.register({"username": "Owner", "email": "owner@example.com", "password": "Password123"})
    with pytest.raises(ValidationError, match="email is already registered"):
        service.register({"username": "Another", "email": "owner@example.com", "password": "Another123"})
    assert service.authenticate("Owner", "wrong") is None
    assert service.get_user(user["id"]) == user
    assert service.get_user(999) is None
    assert service.list_users() == [user]
    assert service.count_users() == 1

    with pytest.raises(ValidationError, match="username or email is required"):
        service.request_password_reset({})

    unknown_response = service.request_password_reset({"email": "missing@example.com"})
    assert unknown_response == {"message": "If that account exists, a password reset code has been sent."}

    reset_response = service.request_password_reset({"email": "owner@example.com"})
    assert "reset_token" not in reset_response
    assert email_service.sent[0]["recipient"] == "owner@example.com"

    token = next(iter(repository.tokens))
    assert service.reset_password({"token": token, "password": "Different123"}) == {
        "message": "Password updated successfully. You can now sign in."
    }
    with pytest.raises(ValidationError, match="already been used"):
        service.reset_password({"token": token, "password": "Another123"})
    with pytest.raises(ValidationError, match="reset code is required"):
        service.reset_password({"token": "", "password": "Another123"})
    with pytest.raises(ValidationError, match="invalid"):
        service.reset_password({"token": "missing", "password": "Another123"})

    repository.tokens["expired"] = {
        "id": 2,
        "user_id": user["id"],
        "expires_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "used_at": None,
    }
    with pytest.raises(ValidationError, match="expired"):
        service.reset_password({"token": "expired", "password": "Another123"})

    repository.tokens["orphan"] = {
        "id": 3,
        "user_id": 999,
        "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "used_at": None,
    }
    with pytest.raises(ValidationError, match="invalid"):
        service.reset_password({"token": "orphan", "password": "Another123"})

    with pytest.raises(ValidationError, match="user account was not found"):
        service.delete_user(999)
    with pytest.raises(ValidationError, match="user account was not found"):
        service.delete_user(user["id"])


def test_user_service_duplicate_password_without_fingerprint_branch():
    class Repository:
        def __init__(self):
            self.users = []

        def get_user_by_username(self, username):
            return next((user for user in self.users if user["username"] == username), None)

        def get_user_by_email(self, email):
            return next((user for user in self.users if user["email"] == email), None)

        def list_users(self):
            return list(self.users)

        def create_user(self, username, email, password_hash, password_fingerprint=None):
            user = {
                "id": len(self.users) + 1,
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "password_fingerprint": password_fingerprint,
            }
            self.users.append(user)
            return user

    repository = Repository()
    service = UserService(repository)
    service.register({"username": "Owner", "email": "owner@example.com", "password": "Password123"})
    repository.users[0]["password_fingerprint"] = None

    with pytest.raises(ValidationError, match="password is already used"):
        service.register({"username": "Second", "email": "second@example.com", "password": "Password123"})


def test_latency_repository_and_service_repository_mode(sqlite_connection):
    repository = LatencyRepository(lambda: sqlite_connection)
    service = LatencyService(repository=repository)

    service.record(
        request_id="anon-ok",
        method="GET",
        path="/api/health",
        status_code=200,
        duration_ms=10.126,
        user_id=None,
        username=None,
    )
    service.record(
        request_id="user-fail",
        method="POST",
        path="/api/expenses",
        status_code=500,
        duration_ms=25.0,
        user_id=7,
        username="Owner",
    )
    service.record(
        request_id="user-ok",
        method="GET",
        path="/api/dashboard",
        status_code=200,
        duration_ms=15.0,
        user_id=7,
        username="Owner",
    )

    anonymous_report = service.report_for_user(None, limit="bad")
    assert anonymous_report["scope"] == "anonymous"
    assert anonymous_report["record_count"] == 1
    assert anonymous_report["latest"][0]["request_id"] == "anon-ok"

    user_report = service.report_for_user(7, limit=5000)
    assert user_report["scope"] == "current_user"
    assert user_report["record_count"] == 2
    assert user_report["failed_count"] == 1
    assert user_report["latest_failures"][0]["request_id"] == "user-fail"
    assert user_report["by_endpoint"][0]["request_count"] == 1
    assert repository.list_records_for_user(7, limit=0)
    assert repository.list_failures_for_user(7, limit=None)
    assert repository.list_durations_for_user(None) == [10.13]
    assert LatencyService._percentile([], 95) == 0.0


def test_settings_repository_lists_and_updates_existing_month_records(sqlite_connection):
    repository = SettingsRepository(lambda: sqlite_connection, user_id_provider=lambda: 7)
    sqlite_connection.execute(settings_table.insert().values(user_id=1, monthly_budget=600, monthly_income=1000))
    sqlite_connection.commit()

    assert repository.get_settings("2026-06") == {
        "monthly_budget": 600.0,
        "budget_month": "2026-06",
        "monthly_income": 1000.0,
        "income_month": "2026-06",
    }

    assert repository.update_monthly_budget(700.555, "2026-06") == {
        "monthly_budget": 700.55,
        "budget_month": "2026-06",
    }
    assert repository.update_monthly_budget(800, "2026-06") == {
        "monthly_budget": 800.0,
        "budget_month": "2026-06",
    }
    assert repository.update_monthly_income(1200, "2026-05") == {
        "monthly_income": 1200.0,
        "income_month": "2026-05",
    }
    assert repository.update_monthly_income(1300, "2026-06") == {
        "monthly_income": 1300.0,
        "income_month": "2026-06",
    }
    assert repository.list_monthly_income_records("2026-06") == [
        {"month_key": "2026-05", "monthly_income": 1200.0}
    ]
