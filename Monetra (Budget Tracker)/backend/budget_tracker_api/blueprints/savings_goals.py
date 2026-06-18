from flask import Blueprint, current_app, jsonify, request


savings_goals_bp = Blueprint("savings_goals", __name__, url_prefix="/api/savings-goals")


def _service():
    return current_app.extensions["services"]["savings_goal_service"]


@savings_goals_bp.get("")
def list_goals():
    return jsonify({"data": _service().list_goals()})


@savings_goals_bp.post("")
def create_goal():
    payload = request.get_json(silent=True) or {}
    return jsonify({"data": _service().create_goal(payload)}), 201


@savings_goals_bp.put("/<int:goal_id>")
def update_goal(goal_id: int):
    payload = request.get_json(silent=True) or {}
    return jsonify({"data": _service().update_goal(goal_id, payload)})


@savings_goals_bp.delete("/<int:goal_id>")
def delete_goal(goal_id: int):
    _service().delete_goal(goal_id)
    return jsonify({"data": {"message": "Savings goal deleted successfully."}})
