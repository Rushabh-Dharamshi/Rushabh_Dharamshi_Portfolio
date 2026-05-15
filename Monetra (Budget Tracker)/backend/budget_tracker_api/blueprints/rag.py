from flask import Blueprint, current_app, jsonify, request


rag_bp = Blueprint("rag", __name__, url_prefix="/api/rag")


def _service():
    return current_app.extensions["services"]["rag_service"]


@rag_bp.get("/status")
def rag_status():
    return jsonify({"data": _service().status()})


@rag_bp.post("/reindex")
def rag_reindex():
    payload = request.get_json(silent=True) or {}
    force = bool(payload.get("force", True))
    return jsonify({"data": _service().reindex(force=force)})


@rag_bp.post("/query")
def rag_query():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question") or "").strip()
    return jsonify({"data": _service().answer_question(question)})
