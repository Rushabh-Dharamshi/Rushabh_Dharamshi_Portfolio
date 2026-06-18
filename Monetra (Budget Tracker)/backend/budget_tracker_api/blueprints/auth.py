from flask import Blueprint, current_app, jsonify, request

from budget_tracker_api.security import current_authenticated_user, current_authenticated_user_id, log_in_user, log_out_user


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.get("/session")
def get_session():
    username = current_authenticated_user()
    user_id = current_authenticated_user_id()
    user = current_app.extensions["services"]["user_service"].get_user(user_id) if user_id is not None else None
    registered_user_count = current_app.extensions["services"]["user_service"].count_users()
    return jsonify(
        {
            "data": {
                "authenticated": username is not None,
                "user_id": user_id,
                "username": username,
                "email": user["email"] if user else None,
                "registered_user_count": registered_user_count,
            }
        }
    )


@auth_bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    user = current_app.extensions["services"]["user_service"].register(payload)
    log_in_user(user["username"], user["id"])
    return jsonify(
        {
            "data": {
                "authenticated": True,
                "user_id": user["id"],
                "username": user["username"],
                "email": user["email"],
            }
        }
    ), 201


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))

    user = current_app.extensions["services"]["user_service"].authenticate(username, password)
    if user is None:
        return jsonify({"error": "Invalid username or password."}), 401

    log_in_user(user["username"], user["id"])
    return jsonify(
        {
            "data": {
                "authenticated": True,
                "user_id": user["id"],
                "username": user["username"],
                "email": user["email"],
            }
        }
    )


@auth_bp.post("/forgot-password")
def forgot_password():
    payload = request.get_json(silent=True) or {}
    result = current_app.extensions["services"]["user_service"].request_password_reset(payload)
    return jsonify({"data": result})


@auth_bp.post("/reset-password")
def reset_password():
    payload = request.get_json(silent=True) or {}
    result = current_app.extensions["services"]["user_service"].reset_password(payload)
    return jsonify({"data": result})


@auth_bp.get("/mock-inbox")
def mock_inbox():
    recipient = str(request.args.get("recipient") or "").strip()
    limit = request.args.get("limit", 20)
    messages = current_app.extensions["services"]["email_service"].list_mock_messages(recipient, limit)
    return jsonify(
        {
            "data": {
                "recipient": recipient,
                "messages": messages,
            }
        }
    )


@auth_bp.post("/logout")
def logout():
    log_out_user()
    return jsonify({"data": {"message": "Logged out successfully."}})


@auth_bp.delete("/me")
def delete_current_user():
    user_id = current_authenticated_user_id()
    if user_id is None:
        return jsonify({"error": "Login required."}), 401
    result = current_app.extensions["services"]["user_service"].delete_user(user_id)
    log_out_user()
    return jsonify({"data": result})
