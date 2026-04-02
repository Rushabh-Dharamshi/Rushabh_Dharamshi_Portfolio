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
    assert good_login.get_json()["data"] == {"authenticated": True, "username": "Rushabh"}
    assert session_response.get_json()["data"] == {"authenticated": True, "username": "Rushabh"}
    assert dashboard_response.status_code == 200
    assert logout_response.get_json()["data"]["message"] == "Logged out successfully."
    assert session_after_logout.get_json()["data"] == {"authenticated": False, "username": None}
