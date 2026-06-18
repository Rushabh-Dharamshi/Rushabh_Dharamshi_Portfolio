from flask import Flask

from budget_tracker_api import security


def make_app(**overrides):
    app = Flask(__name__)
    app.secret_key = "test"
    app.config.update(
        DEMO_ACCESS_ENABLED=False,
        LOGIN_REQUIRED=False,
        READ_ONLY_MODE=False,
        PUBLIC_HEALTHCHECK_ENABLED=False,
        DEMO_ACCESS_USERNAME="demo",
        DEMO_ACCESS_PASSWORD="secret",
        EXPOSE_ERROR_DETAILS=False,
    )
    app.config.update(overrides)
    security.register_request_guards(app)
    return app


def test_security_helpers_and_guards():
    app = make_app(DEMO_ACCESS_ENABLED=True, READ_ONLY_MODE=True, PUBLIC_HEALTHCHECK_ENABLED=True)
    client = app.test_client()

    health = client.get("/api/health")
    options = client.open("/api/expenses", method="OPTIONS")
    readonly = client.post("/api/expenses")

    assert health.status_code != 401
    assert options.status_code != 401
    assert readonly.status_code == 401
    assert readonly.get_json()["error"] == "Authentication required for this deployment."

    with app.test_request_context("/"):
        assert security.should_expose_error_details(app) is False
        assert security.current_authenticated_user() is None
        security.log_in_user("Rushabh", 1)
        assert security.is_logged_in() is True
        assert security.current_authenticated_user() == "Rushabh"
        assert security.current_authenticated_user_id() == 1
        security.log_out_user()
        assert security.is_logged_in() is False

    with app.test_request_context("/api/expenses"):
        assert security._is_basic_authorized(app) is False

    app.config["DEMO_ACCESS_PASSWORD"] = ""
    with app.test_request_context("/api/expenses", headers={"Authorization": "Basic ZGVtbzpzZWNyZXQ="}):
        assert security._is_basic_authorized(app) is False

    with app.app_context():
        unauthorized = security._basic_unauthorized()
        assert unauthorized.status_code == 401
        assert unauthorized.headers["WWW-Authenticate"] == 'Basic realm="Monetra Demo"'
