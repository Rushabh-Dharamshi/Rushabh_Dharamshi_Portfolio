import re
import uuid

from flask import Blueprint, current_app, jsonify, request

from budget_tracker_api.security import current_authenticated_user, current_authenticated_user_id


observability_bp = Blueprint("observability", __name__, url_prefix="/api/observability")


@observability_bp.get("/latency")
def latency_report():
    user_id = current_authenticated_user_id()
    limit = request.args.get("limit", 50)
    report = current_app.extensions["services"]["latency_service"].report_for_user(user_id, limit)
    return jsonify({"data": report})


@observability_bp.post("/client-failure")
def record_client_failure():
    payload = request.get_json(silent=True) or {}
    operation = re.sub(r"[^a-z0-9-]+", "-", str(payload.get("operation") or "client-operation").lower()).strip("-")
    operation = operation[:80] or "client-operation"
    try:
        duration_ms = max(0.0, float(payload.get("duration_ms") or 0.0))
    except (TypeError, ValueError):
        duration_ms = 0.0

    current_app.extensions["services"]["latency_service"].record(
        request_id=str(payload.get("request_id") or f"client-{uuid.uuid4()}"),
        method="CLIENT",
        path=f"/api/client-operations/{operation}",
        status_code=599,
        duration_ms=duration_ms,
        user_id=current_authenticated_user_id(),
        username=current_authenticated_user(),
    )
    return jsonify({"data": {"recorded": True}})
