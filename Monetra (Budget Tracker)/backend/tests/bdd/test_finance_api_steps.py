import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from datetime import date

from budget_tracker_api import create_app


scenarios("features/finance_api.feature")


@pytest.fixture()
def bdd_context(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'bdd.db'}",
            "GENERATED_REPORTS_DIR": tmp_path / "reports",
            "EMAIL_DELIVERY_MODE": "hybrid",
            "EMAIL_MOCK_DOMAINS": "monetra.test",
            "MOCK_EMAIL_FROM": "demo@monetra.test",
            "LOGIN_REQUIRED": True,
        }
    )
    return {"app": app, "client": app.test_client(), "responses": {}}


@given("a fresh Monetra API")
def fresh_api(bdd_context):
    assert bdd_context["client"].get("/api/auth/session").status_code == 200


@when(parsers.parse('I register a user named "{username}" with email "{email}"'))
def register_user(bdd_context, username, email):
    response = bdd_context["client"].post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": f"{username}Pass123"},
    )
    bdd_context["responses"]["register"] = response
    assert response.status_code == 201


@when(parsers.parse('I add an expense of {amount:g} for "{description}" in category "{category}"'))
def add_expense(bdd_context, amount, description, category):
    response = bdd_context["client"].post(
        "/api/expenses",
        json={
            "date": date.today().isoformat(),
            "category": category,
            "description": description,
            "amount": amount,
            "entry_type": "expense",
        },
    )
    bdd_context["responses"]["expense"] = response
    assert response.status_code == 201


@when(parsers.parse('I request a password reset for "{email}"'))
def request_reset(bdd_context, email):
    bdd_context["client"].post("/api/auth/logout")
    response = bdd_context["client"].post("/api/auth/forgot-password", json={"email": email})
    bdd_context["responses"]["forgot"] = response
    assert response.status_code == 200


@when("I request the dashboard")
def request_dashboard(bdd_context):
    response = bdd_context["client"].get("/api/dashboard")
    bdd_context["responses"]["dashboard"] = response
    assert response.status_code == 200


@then(parsers.parse('the expense list should include "{description}"'))
def expense_list_contains(bdd_context, description):
    response = bdd_context["client"].get("/api/expenses")
    assert response.status_code == 200
    descriptions = {item["description"] for item in response.get_json()["data"]}
    assert description in descriptions


@then(parsers.parse("the dashboard monthly expenses should be at least {amount:g}"))
def dashboard_monthly_expenses_at_least(bdd_context, amount):
    response = bdd_context["client"].get("/api/dashboard")
    assert response.status_code == 200
    assert float(response.get_json()["data"]["monthly_expenses"]) >= amount


@then(parsers.parse('the mock inbox for "{email}" should contain "{subject}"'))
def mock_inbox_contains(bdd_context, email, subject):
    response = bdd_context["client"].get(f"/api/auth/mock-inbox?recipient={email}")
    assert response.status_code == 200
    subjects = {item["subject"] for item in response.get_json()["data"]["messages"]}
    assert subject in subjects


@then(parsers.parse('the latency report should include a "{method}" call to "{path}"'))
def latency_report_contains(bdd_context, method, path):
    response = bdd_context["client"].get("/api/observability/latency")
    assert response.status_code == 200
    records = response.get_json()["data"]["latest"]
    assert any(record["method"] == method and record["path"] == path for record in records)
