from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from hmac import compare_digest

from flask import Flask, Response, jsonify, request, session


AUTH_SESSION_KEY = "authenticated_username"
AUTH_USER_ID_SESSION_KEY = "authenticated_user_id"
_BACKGROUND_USER_ID: ContextVar[int | None] = ContextVar("background_user_id", default=None)
PUBLIC_AUTH_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/session",
    "/api/auth/forgot-password",
    "/api/auth/mock-inbox",
    "/api/auth/reset-password",
    "/api/auth/logout",
}


def register_request_guards(app: Flask) -> None:
    @app.before_request
    def enforce_demo_guards():
        if not request.path.startswith("/api/"):
            return None

        if request.method == "OPTIONS":
            return None

        if _is_public_healthcheck(app, request.path) or request.path in PUBLIC_AUTH_PATHS:
            return None

        if app.config["DEMO_ACCESS_ENABLED"] and not _is_basic_authorized(app):
            return _basic_unauthorized()

        if app.config["LOGIN_REQUIRED"] and not is_logged_in():
            return jsonify({"error": "Login required."}), 401

        if app.config["READ_ONLY_MODE"] and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            return jsonify({"error": "This deployment is running in read-only demo mode."}), 403

        return None


def should_expose_error_details(app: Flask) -> bool:
    return app.testing or app.debug or app.config["EXPOSE_ERROR_DETAILS"]


def current_authenticated_user() -> str | None:
    username = session.get(AUTH_SESSION_KEY)
    return username if isinstance(username, str) and username else None


def current_authenticated_user_id() -> int | None:
    user_id = session.get(AUTH_USER_ID_SESSION_KEY)
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return None


def current_background_user_id() -> int | None:
    return _BACKGROUND_USER_ID.get()


@contextmanager
def background_user_context(user_id: int):
    token = _BACKGROUND_USER_ID.set(int(user_id))
    try:
        yield
    finally:
        _BACKGROUND_USER_ID.reset(token)


def is_logged_in() -> bool:
    return current_authenticated_user() is not None and current_authenticated_user_id() is not None


def log_in_user(username: str, user_id: int) -> None:
    session.clear()
    session.permanent = True
    session[AUTH_SESSION_KEY] = username
    session[AUTH_USER_ID_SESSION_KEY] = int(user_id)


def log_out_user() -> None:
    session.clear()


def _is_public_healthcheck(app: Flask, path: str) -> bool:
    return app.config["PUBLIC_HEALTHCHECK_ENABLED"] and path == "/api/health"


def _is_basic_authorized(app: Flask) -> bool:
    auth = request.authorization
    if auth is None:
        return False

    expected_username = app.config["DEMO_ACCESS_USERNAME"]
    expected_password = app.config["DEMO_ACCESS_PASSWORD"]
    if not expected_username or not expected_password:
        return False

    return compare_digest(auth.username or "", expected_username) and compare_digest(
        auth.password or "",
        expected_password,
    )


def _basic_unauthorized() -> Response:
    response = jsonify({"error": "Authentication required for this deployment."})
    response.status_code = 401
    response.headers["WWW-Authenticate"] = 'Basic realm="Monetra Demo"'
    return response
