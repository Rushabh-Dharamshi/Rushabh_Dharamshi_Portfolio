from flask import Blueprint, current_app, jsonify


predictions_bp = Blueprint("predictions", __name__, url_prefix="/api/predictions")


@predictions_bp.get("/next-month")
def predict_next_month():
    service = current_app.extensions["services"]["prediction_service"]
    return jsonify({"data": service.predict_next_month()})

