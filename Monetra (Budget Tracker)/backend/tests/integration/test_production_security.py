import base64

from budget_tracker_api import create_app
from werkzeug.security import generate_password_hash


def _basic_auth(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def test_demo_access_blocks_unauthenticated_api_requests(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "LOGIN_REQUIRED": False,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'security.db'}",
            "DEMO_ACCESS_ENABLED": True,
            "DEMO_ACCESS_USERNAME": "demo",
            "DEMO_ACCESS_PASSWORD": "safe-password",
        }
    )
    client = app.test_client()

    response = client.get("/api/dashboard")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required for this deployment."
    assert response.headers["WWW-Authenticate"] == 'Basic realm="Monetra Demo"'


def test_demo_access_allows_authenticated_api_requests(client, app):
    app.config.update(
        {
            "LOGIN_REQUIRED": False,
            "DEMO_ACCESS_ENABLED": True,
            "DEMO_ACCESS_USERNAME": "demo",
            "DEMO_ACCESS_PASSWORD": "safe-password",
        }
    )

    response = client.get("/api/dashboard", headers=_basic_auth("demo", "safe-password"))

    assert response.status_code == 200
    assert response.get_json()["data"]["monthly_budget"] == 1050.0


def test_public_healthcheck_can_remain_available_without_auth(client, app):
    app.config.update(
        {
            "LOGIN_REQUIRED": False,
            "DEMO_ACCESS_ENABLED": True,
            "DEMO_ACCESS_USERNAME": "demo",
            "DEMO_ACCESS_PASSWORD": "safe-password",
            "PUBLIC_HEALTHCHECK_ENABLED": True,
        }
    )

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_read_only_mode_blocks_mutations_even_with_valid_auth(client, app):
    app.config.update(
        {
            "LOGIN_REQUIRED": False,
            "DEMO_ACCESS_ENABLED": True,
            "DEMO_ACCESS_USERNAME": "demo",
            "DEMO_ACCESS_PASSWORD": "safe-password",
            "READ_ONLY_MODE": True,
        }
    )

    response = client.post(
        "/api/expenses",
        headers=_basic_auth("demo", "safe-password"),
        json={
            "date": "2026-03-15",
            "category": "Food",
            "description": "Lunch",
            "amount": "12.50",
        },
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "This deployment is running in read-only demo mode."


def test_login_required_blocks_unauthenticated_api_requests(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'auth.db'}",
            "AUTH_USERNAME": "Rushabh",
            "AUTH_PASSWORD_HASH": generate_password_hash("Dharamshi"),
        }
    )
    client = app.test_client()

    response = client.get("/api/dashboard")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Login required."


def test_login_flow_authenticates_and_allows_session_access(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'auth-session.db'}",
            "AUTH_USERNAME": "Rushabh",
            "AUTH_EMAIL": "rushabh.dharamshi@gmail.com",
            "AUTH_PASSWORD_HASH": generate_password_hash("Dharamshi"),
        }
    )
    client = app.test_client()

    bad_login = client.post("/api/auth/login", json={"username": "Rushabh", "password": "Wrong"})
    good_login = client.post("/api/auth/login", json={"username": "Rushabh", "password": "Dharamshi"})
    session_response = client.get("/api/auth/session")
    dashboard_response = client.get("/api/dashboard")
    logout_response = client.post("/api/auth/logout")
    session_after_logout = client.get("/api/auth/session")

    assert bad_login.status_code == 401
    assert bad_login.get_json()["error"] == "Invalid username or password."
    assert good_login.status_code == 200
    assert good_login.get_json()["data"] == {
        "authenticated": True,
        "user_id": 1,
        "username": "Rushabh",
        "email": "rushabh.dharamshi@gmail.com",
    }
    assert session_response.get_json()["data"] == {
        "authenticated": True,
        "user_id": 1,
        "username": "Rushabh",
        "email": "rushabh.dharamshi@gmail.com",
        "registered_user_count": 1,
    }
    assert dashboard_response.status_code == 200
    assert logout_response.get_json()["data"]["message"] == "Logged out successfully."
    assert session_after_logout.get_json()["data"] == {
        "authenticated": False,
        "user_id": None,
        "username": None,
        "email": None,
        "registered_user_count": 1,
    }


def test_manual_email_dispatch_uses_logged_in_users_registered_email(tmp_path):
    class FakeAutomationService:
        def __init__(self):
            self.month_end_recipient = None
            self.upcoming_bills_recipient = None

        def run_month_end_email_now(self, recipient=None):
            self.month_end_recipient = recipient
            return {
                "id": 1,
                "workflow_name": "month_end_email_manual_dispatch",
                "summary": f"Manual month-end PDF report emailed to {recipient}.",
            }

        def run_upcoming_bills_email_now(self, recipient=None):
            self.upcoming_bills_recipient = recipient
            return {
                "id": 2,
                "workflow_name": "upcoming_bills_email_manual_dispatch",
                "summary": f"Upcoming bills alert emailed to {recipient}.",
            }

    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'auth-email-dispatch.db'}",
            "AUTH_USERNAME": "Rushabh",
            "AUTH_EMAIL": "owner@example.com",
            "AUTH_PASSWORD_HASH": generate_password_hash("Dharamshi"),
        }
    )
    fake_automation_service = FakeAutomationService()
    app.extensions["services"]["automation_service"] = fake_automation_service
    client = app.test_client()

    login_response = client.post("/api/auth/login", json={"username": "Rushabh", "password": "Dharamshi"})
    month_end_response = client.post("/api/agents/automation/month-end-email")
    upcoming_response = client.post("/api/agents/automation/upcoming-bills-email")

    assert login_response.status_code == 200
    assert month_end_response.status_code == 200
    assert upcoming_response.status_code == 200
    assert fake_automation_service.month_end_recipient == "owner@example.com"
    assert fake_automation_service.upcoming_bills_recipient == "owner@example.com"


def test_agent_email_command_payload_uses_logged_in_users_registered_email(tmp_path):
    class FakeAgentService:
        def __init__(self):
            self.payload = None

        def start_finance_briefing(self, payload, app_obj):
            self.payload = payload
            return {"id": "agent-email-1", "status": "queued"}

    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'auth-agent-email.db'}",
            "AUTH_USERNAME": "Rushabh",
            "AUTH_EMAIL": "owner@example.com",
            "AUTH_PASSWORD_HASH": generate_password_hash("Dharamshi"),
        }
    )
    fake_agent_service = FakeAgentService()
    app.extensions["services"]["agent_service"] = fake_agent_service
    client = app.test_client()

    login_response = client.post("/api/auth/login", json={"username": "Rushabh", "password": "Dharamshi"})
    agent_response = client.post("/api/agents/finance-briefing", json={"task": "Send the month-end email now."})

    assert login_response.status_code == 200
    assert agent_response.status_code == 202
    assert fake_agent_service.payload["user_id"] == 1
    assert fake_agent_service.payload["recipient"] == "owner@example.com"


def test_demo_mock_inbox_exposes_only_simulated_mock_domain_email(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'mock-inbox.db'}",
            "AUTH_USERNAME": "Rushabh",
            "AUTH_EMAIL": "owner@example.com",
            "AUTH_PASSWORD_HASH": generate_password_hash("Dharamshi"),
            "EMAIL_DELIVERY_MODE": "hybrid",
            "EMAIL_MOCK_DOMAINS": "monetra.test",
            "MOCK_EMAIL_FROM": "demo@monetra.test",
            "EMAIL_ALLOWED_RECIPIENTS": "owner@example.com",
        }
    )
    client = app.test_client()

    register_response = client.post(
        "/api/auth/register",
        json={"username": "DemoUser", "email": "user001@monetra.test", "password": "DemoPass123"},
    )
    client.post("/api/auth/logout")
    forgot_response = client.post("/api/auth/forgot-password", json={"email": "user001@monetra.test"})
    inbox_response = client.get("/api/auth/mock-inbox?recipient=user001@monetra.test")
    blocked_response = client.get("/api/auth/mock-inbox?recipient=random.person@gmail.com")

    assert register_response.status_code == 201
    assert forgot_response.status_code == 200
    assert inbox_response.status_code == 200
    messages = inbox_response.get_json()["data"]["messages"]
    assert len(messages) == 1
    assert messages[0]["recipient"] == "user001@monetra.test"
    assert messages[0]["sender"] == "demo@monetra.test"
    assert messages[0]["subject"] == "Monetra password reset code"
    assert "Your Monetra password reset code is:" in messages[0]["body"]
    assert blocked_response.status_code == 503
    assert "mock email domains" in blocked_response.get_json()["error"]


def test_latency_report_records_api_calls_for_logged_in_user(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'latency.db'}",
            "AUTH_USERNAME": "Rushabh",
            "AUTH_EMAIL": "owner@example.com",
            "AUTH_PASSWORD_HASH": generate_password_hash("Dharamshi"),
        }
    )
    client = app.test_client()

    login_response = client.post("/api/auth/login", json={"username": "Rushabh", "password": "Dharamshi"})
    dashboard_response = client.get("/api/dashboard")
    latency_response = client.get("/api/observability/latency")

    assert login_response.status_code == 200
    assert dashboard_response.status_code == 200
    assert dashboard_response.headers["X-Request-ID"]
    assert float(dashboard_response.headers["X-Response-Time-ms"]) >= 0
    assert latency_response.status_code == 200
    report = latency_response.get_json()["data"]
    assert report["scope"] == "current_user"
    assert report["record_count"] >= 2
    assert report["summary"]["maximum_ms"] >= 0
    assert any(record["path"] == "/api/dashboard" for record in report["latest"])
    assert any(endpoint["path"] == "/api/dashboard" for endpoint in report["by_endpoint"])


def test_latency_report_records_client_visible_operation_failures(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'client-failure-latency.db'}",
            "AUTH_USERNAME": "Rushabh",
            "AUTH_EMAIL": "owner@example.com",
            "AUTH_PASSWORD_HASH": generate_password_hash("Dharamshi"),
        }
    )
    client = app.test_client()

    login_response = client.post("/api/auth/login", json={"username": "Rushabh", "password": "Dharamshi"})
    failure_response = client.post(
        "/api/observability/client-failure",
        json={
            "operation": "AI agent request",
            "error": "Request failed.",
            "duration_ms": 1234,
            "request_id": "client-test-failure",
        },
    )
    latency_response = client.get("/api/observability/latency")

    assert login_response.status_code == 200
    assert failure_response.status_code == 200
    report = latency_response.get_json()["data"]
    assert report["failed_count"] >= 1
    assert any(
        record["request_id"] == "client-test-failure"
        and record["method"] == "CLIENT"
        and record["path"] == "/api/client-operations/ai-agent-request"
        and record["status_code"] == 599
        and record["ok"] is False
        for record in report["latest"]
    )


def test_latency_records_persist_after_app_restart(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'persistent-latency.db'}"
    config = {
        "TESTING": True,
        "DATABASE_URL": database_url,
        "AUTH_USERNAME": "Rushabh",
        "AUTH_PASSWORD_HASH": generate_password_hash("Dharamshi"),
    }
    first_app = create_app(config)
    first_client = first_app.test_client()
    first_client.post("/api/auth/login", json={"username": "Rushabh", "password": "Dharamshi"})
    dashboard_response = first_client.get("/api/dashboard")
    first_app.extensions["db_engine"].dispose()

    second_app = create_app(config)
    second_client = second_app.test_client()
    second_client.post("/api/auth/login", json={"username": "Rushabh", "password": "Dharamshi"})
    latency_response = second_client.get("/api/observability/latency")

    assert dashboard_response.status_code == 200
    assert latency_response.status_code == 200
    report = latency_response.get_json()["data"]
    assert report["record_count"] >= 1
    assert any(record["path"] == "/api/dashboard" for record in report["latest"])


def test_registered_users_get_isolated_expense_records(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'multi-user.db'}",
            "AUTH_USERNAME": "Rushabh",
            "AUTH_PASSWORD_HASH": generate_password_hash("Dharamshi"),
        }
    )
    client = app.test_client()

    login_response = client.post("/api/auth/login", json={"username": "Rushabh", "password": "Dharamshi"})
    create_response = client.post(
        "/api/expenses",
        json={
            "date": "2026-03-15",
            "category": "Food",
            "description": "Owner lunch",
            "amount": "12.50",
        },
    )
    owner_records = client.get("/api/expenses")
    client.post("/api/auth/logout")

    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "SecondUser",
            "email": "second@example.com",
            "password": "password123",
        },
    )
    second_user_records = client.get("/api/expenses")

    assert login_response.status_code == 200
    assert create_response.status_code == 201
    assert len(owner_records.get_json()["data"]) == 1
    assert register_response.status_code == 201
    assert register_response.get_json()["data"]["username"] == "SecondUser"
    assert second_user_records.get_json()["data"] == []


def test_current_user_can_delete_account_and_is_logged_out(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'delete-user.db'}",
            "AUTH_USERNAME": "Rushabh",
            "AUTH_EMAIL": "owner@example.com",
            "AUTH_PASSWORD_HASH": generate_password_hash("Dharamshi"),
        }
    )
    client = app.test_client()

    client.post(
        "/api/auth/register",
        json={"username": "DeleteMe", "email": "delete@example.com", "password": "DeletePass123"},
    )
    delete_response = client.delete("/api/auth/me")
    session_response = client.get("/api/auth/session")

    assert delete_response.status_code == 200
    assert delete_response.get_json()["data"]["registered_user_count"] == 1
    assert session_response.get_json()["data"] == {
        "authenticated": False,
        "user_id": None,
        "username": None,
        "email": None,
        "registered_user_count": 1,
    }


def test_savings_goals_are_user_scoped_and_validated(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'savings-goals.db'}",
            "AUTH_USERNAME": "Rushabh",
            "AUTH_PASSWORD_HASH": generate_password_hash("Dharamshi"),
        }
    )
    client = app.test_client()

    client.post("/api/auth/login", json={"username": "Rushabh", "password": "Dharamshi"})
    invalid = client.post("/api/savings-goals", json={"name": "Holiday", "target_amount": "0"})
    created = client.post(
        "/api/savings-goals",
        json={
            "name": "Emergency fund",
            "target_amount": "3000",
            "current_amount": "750",
            "target_date": "2026-12-31",
        },
    )
    owner_goals = client.get("/api/savings-goals")
    client.post("/api/auth/logout")
    client.post(
        "/api/auth/register",
        json={"username": "GoalUser", "email": "goal@example.com", "password": "password123"},
    )
    second_user_goals = client.get("/api/savings-goals")

    assert invalid.status_code == 400
    assert created.status_code == 201
    assert created.get_json()["data"]["progress_percent"] == 25.0
    assert len(owner_goals.get_json()["data"]) == 1
    assert second_user_goals.get_json()["data"] == []


def test_expense_list_supports_category_text_and_date_filters(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'expense-filters.db'}",
            "AUTH_USERNAME": "Rushabh",
            "AUTH_PASSWORD_HASH": generate_password_hash("Dharamshi"),
        }
    )
    client = app.test_client()
    client.post("/api/auth/login", json={"username": "Rushabh", "password": "Dharamshi"})
    client.post("/api/expenses", json={"date": "2026-05-01", "category": "Travel", "description": "Tube fare", "amount": "6.40"})
    client.post("/api/expenses", json={"date": "2026-05-10", "category": "Food", "description": "Groceries", "amount": "42.10"})

    response = client.get("/api/expenses?category=Travel&q=tube&start_date=2026-05-01&end_date=2026-05-03")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert len(data) == 1
    assert data[0]["description"] == "Tube fare"
