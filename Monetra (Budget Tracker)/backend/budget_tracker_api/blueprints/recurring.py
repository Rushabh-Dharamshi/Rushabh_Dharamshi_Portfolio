from flask import Blueprint, current_app, jsonify, request


recurring_bp = Blueprint("recurring", __name__, url_prefix="/api/recurring-items")


def _service():
    return current_app.extensions["services"]["recurring_service"]


@recurring_bp.get("")
def list_items():
    return jsonify({"data": _service().list_items()})


@recurring_bp.get("/calendar")
def recurring_calendar():
    days_ahead = request.args.get("days", default=35, type=int)
    return jsonify({"data": _service().upcoming_calendar(days_ahead)})


@recurring_bp.post("")
def create_item():
    payload = request.get_json(silent=True) or {}
    return jsonify({"data": _service().create_item(payload)}), 201


@recurring_bp.put("/<int:item_id>")
def update_item(item_id: int):
    payload = request.get_json(silent=True) or {}
    return jsonify({"data": _service().update_item(item_id, payload)})


@recurring_bp.delete("/<int:item_id>")
def delete_item(item_id: int):
    _service().delete_item(item_id)
    return jsonify({"data": {"message": "Recurring item deleted successfully."}})


@recurring_bp.post("/<int:item_id>/occurrences/pay")
def mark_occurrence_paid(item_id: int):
    payload = request.get_json(silent=True) or {}
    return jsonify({"data": _service().mark_occurrence_paid(item_id, payload)})


@recurring_bp.post("/<int:item_id>/occurrences/unpay")
def mark_occurrence_unpaid(item_id: int):
    payload = request.get_json(silent=True) or {}
    return jsonify({"data": _service().mark_occurrence_unpaid(item_id, payload)})
