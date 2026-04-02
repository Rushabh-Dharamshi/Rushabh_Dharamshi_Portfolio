from flask import Blueprint, current_app, send_file


reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


@reports_bp.get("/monthly")
def monthly_report():
    service = current_app.extensions["services"]["report_service"]
    pdf_path = service.generate_monthly_report()
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=pdf_path.name,
        mimetype="application/pdf",
    )

