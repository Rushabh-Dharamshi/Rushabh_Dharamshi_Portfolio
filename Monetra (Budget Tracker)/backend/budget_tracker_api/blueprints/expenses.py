from io import BytesIO

from flask import Blueprint, current_app, jsonify, request, send_file


expenses_bp = Blueprint("expenses", __name__, url_prefix="/api/expenses")


def _service():
    return current_app.extensions["services"]["expense_service"]


@expenses_bp.get("")
def list_expenses():
    sort_direction = request.args.get("sort", "desc")
    return jsonify({"data": _service().list_expenses(sort_direction)})


@expenses_bp.get("/<int:expense_id>")
def get_expense(expense_id: int):
    return jsonify({"data": _service().get_expense(expense_id)})


@expenses_bp.post("")
def create_expense():
    payload = request.get_json(silent=True) or {}
    expense = _service().create_expense(payload)
    return jsonify({"data": expense}), 201


@expenses_bp.put("/<int:expense_id>")
def update_expense(expense_id: int):
    payload = request.get_json(silent=True) or {}
    expense = _service().update_expense(expense_id, payload)
    return jsonify({"data": expense})


@expenses_bp.delete("/<int:expense_id>")
def delete_expense(expense_id: int):
    _service().delete_expense(expense_id)
    return jsonify({"data": {"message": "Expense deleted successfully."}})


@expenses_bp.post("/import")
def import_expenses():
    file_storage = request.files.get("file")
    result = _service().import_csv(file_storage)
    return jsonify({"data": result})


@expenses_bp.get("/export")
def export_expenses():
    csv_text = _service().export_csv()
    csv_bytes = BytesIO(csv_text.encode("utf-8"))
    csv_bytes.seek(0)
    return send_file(
        csv_bytes,
        as_attachment=True,
        download_name="budget-expenses.csv",
        mimetype="text/csv",
    )
