from flask import Blueprint, current_app, jsonify, request
from werkzeug.security import check_password_hash

from budget_tracker_api.security import current_authenticated_user, log_in_user, log_out_user


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.get("/session")
def get_session():
    username = current_authenticated_user()
    return jsonify(
        {
            "data": {
                "authenticated": username is not None,
                "username": username,
            }
        }
    )


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))

    expected_username = current_app.config["AUTH_USERNAME"]
    password_hash = current_app.config["AUTH_PASSWORD_HASH"]
    if not password_hash:
        return jsonify({"error": "Application login is not configured."}), 500

    if username != expected_username or not check_password_hash(password_hash, password):
        return jsonify({"error": "Invalid username or password."}), 401

    log_in_user(expected_username)
    return jsonify(
        {
            "data": {
                "authenticated": True,
                "username": expected_username,
            }
        }
    )


@auth_bp.post("/logout")
def logout():
    log_out_user()
    return jsonify({"data": {"message": "Logged out successfully."}})
