from flask import Blueprint, current_app, request, send_file

from budget_tracker_api.errors import ValidationError


reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


@reports_bp.get("/monthly")
def monthly_report():
    service = current_app.extensions["services"]["report_service"]
    month = request.args.get("month")
    try:
        pdf_path = service.generate_monthly_report(month)
    except ValueError as exc:
        raise ValidationError("month must be in YYYY-MM format.") from exc
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=pdf_path.name,
        mimetype="application/pdf",
    )
