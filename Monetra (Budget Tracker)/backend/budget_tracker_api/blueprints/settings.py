from flask import Blueprint, current_app, jsonify, request


settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")


def _service():
    return current_app.extensions["services"]["settings_service"]


@settings_bp.get("")
def get_settings():
    month = request.args.get("month")
    return jsonify({"data": _service().get_settings(month)})


@settings_bp.put("/budget")
def update_budget():
    payload = request.get_json(silent=True) or {}
    return jsonify({"data": _service().update_monthly_budget(payload)})


@settings_bp.put("/income")
def update_income():
    payload = request.get_json(silent=True) or {}
    return jsonify({"data": _service().update_monthly_income(payload)})


@settings_bp.get("/income-records")
def list_income_records():
    before_month = request.args.get("before")
    return jsonify({"data": _service().list_monthly_income_records(before_month)})
