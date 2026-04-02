from flask import Blueprint, current_app, jsonify


analytics_bp = Blueprint("analytics", __name__, url_prefix="/api")


def _service():
    return current_app.extensions["services"]["analytics_service"]


@analytics_bp.get("/dashboard")
def dashboard():
    return jsonify({"data": _service().dashboard()})


@analytics_bp.get("/analytics/categories")
def category_insights():
    return jsonify({"data": _service().category_insights()})


@analytics_bp.get("/analytics/wordcloud")
def wordcloud_data():
    return jsonify({"data": _service().wordcloud_data()})


@analytics_bp.get("/analytics/financial-pulse")
def financial_pulse():
    return jsonify({"data": _service().financial_pulse()})
