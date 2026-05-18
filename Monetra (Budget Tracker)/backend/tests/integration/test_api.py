from datetime import date, timedelta
from io import BytesIO


def test_health_and_not_found(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}
    assert client.get("/api/missing").status_code == 404


def test_expense_crud_and_dashboard(client):
    response = client.get("/api/expenses")
    payload = response.get_json()["data"]

    assert response.status_code == 200
    assert len(payload) == 4

    created = client.post(
        "/api/expenses",
        json={
            "date": "2026-03-09",
            "category": "Health",
            "description": "Pharmacy",
            "amount": "12.30",
        },
    )
    created_payload = created.get_json()["data"]
    expense_id = created_payload["id"]

    assert created.status_code == 201
    assert created_payload["category"] == "Health"

    fetched = client.get(f"/api/expenses/{expense_id}")
    assert fetched.get_json()["data"]["description"] == "Pharmacy"

    updated = client.put(
        f"/api/expenses/{expense_id}",
        json={
            "date": "2026-03-10",
            "category": "Health",
            "description": "Prescription",
            "amount": "20.00",
        },
    )
    assert updated.get_json()["data"]["description"] == "Prescription"

    deleted = client.delete(f"/api/expenses/{expense_id}")
    assert deleted.get_json()["data"]["message"] == "Expense deleted successfully."

    dashboard = client.get("/api/dashboard")
    assert dashboard.get_json()["data"]["monthly_budget"] == 1050.0
    assert dashboard.get_json()["data"]["monthly_income"] == 1500.0


def test_import_export_and_analytics_endpoints(client):
    import_response = client.post(
        "/api/expenses/import",
        data={
            "file": (
                BytesIO(
                    b"date,category,description,amount\n"
                    b"2026-03-11,Food,Market,24.50\n"
                    b"bad-date,Food,Invalid,10.00\n"
                ),
                "expenses.csv",
            )
        },
        content_type="multipart/form-data",
    )
    assert import_response.get_json()["data"] == {"imported_rows": 1, "skipped_rows": 1}

    export_response = client.get("/api/expenses/export")
    assert export_response.status_code == 200
    assert "text/csv" in export_response.content_type

    categories = client.get("/api/analytics/categories")
    wordcloud = client.get("/api/analytics/wordcloud")
    pulse = client.get("/api/analytics/financial-pulse")

    assert categories.status_code == 200
    assert wordcloud.status_code == 200
    assert pulse.get_json()["data"]["health_score"] >= 0


def test_prediction_report_and_error_handler(client, app, tmp_path):
    class FakePredictionService:
        def predict_next_month(self):
            return {
                "next_month": "April 2026",
                "predicted_spending": 880.0,
                "is_budget_exceeded": False,
                "monthly_budget": 1050.0,
            }

    class FakeReportService:
        def generate_monthly_report(self):
            report_path = tmp_path / "report.pdf"
            report_path.write_bytes(b"%PDF-1.4 fake")
            return report_path

    class FailingAnalyticsService:
        def dashboard(self):
            raise RuntimeError("boom")

    app.extensions["services"]["prediction_service"] = FakePredictionService()
    app.extensions["services"]["report_service"] = FakeReportService()

    prediction = client.get("/api/predictions/next-month")
    report = client.get("/api/reports/monthly")

    assert prediction.get_json()["data"]["predicted_spending"] == 880.0
    assert report.status_code == 200
    assert "application/pdf" in report.content_type

    app.extensions["services"]["analytics_service"] = FailingAnalyticsService()
    error_response = client.get("/api/dashboard")

    assert error_response.status_code == 500
    assert error_response.get_json()["error"] == "Internal server error."


def test_agent_finance_briefing_endpoint(client, app):
    class FakeAgentService:
        def start_finance_briefing(self, payload, app):
            assert payload["task"] == "Prepare a finance briefing"
            return {
                "id": "job-1",
                "status": "queued",
                "task": payload["task"],
                "created_at": "2026-03-21T10:00:00Z",
                "started_at": None,
                "completed_at": None,
                "error": None,
                "result": None,
            }

        def get_finance_briefing_job(self, job_id):
            assert job_id == "job-1"
            return {
                "id": "job-1",
                "status": "completed",
                "task": "Prepare a finance briefing",
                "created_at": "2026-03-21T10:00:00Z",
                "started_at": "2026-03-21T10:00:01Z",
                "completed_at": "2026-03-21T10:00:05Z",
                "error": None,
                "result": {
                    "headline": "Finance briefing",
                    "summary": "Stable cash flow.",
                    "risk_level": "low",
                    "recommended_actions": ["Keep monitoring recurring bills."],
                    "email_subject": "Finance briefing",
                    "email_draft": "Stable month overall.",
                    "model": "qwen3:4b",
                    "tools_used": ["get_dashboard_summary"],
                    "report_download_url": "/api/reports/monthly",
                    "generated_at": "2026-03-21T10:00:05Z",
                },
            }

        def list_workflows(self):
            return [{"id": "month_end_close", "label": "Month-end close"}]

        def list_runs(self, limit):
            assert limit == 8
            return [{"id": 1, "workflow_name": "month_end_close"}]

        def start_workflow_run(self, workflow_name, payload, app):
            assert workflow_name == "month_end_close"
            assert payload == {}
            assert app is not None
            return {
                "id": "workflow-job-1",
                "status": "queued",
                "workflow_name": workflow_name,
                "task": "Run the workflow",
                "created_at": "2026-03-21T10:00:00Z",
                "started_at": None,
                "completed_at": None,
                "error": None,
                "result": None,
            }

        def get_workflow_job(self, job_id):
            assert job_id == "workflow-job-1"
            return {
                "id": "workflow-job-1",
                "status": "completed",
                "workflow_name": "month_end_close",
                "task": "Run the workflow",
                "created_at": "2026-03-21T10:00:00Z",
                "started_at": "2026-03-21T10:00:01Z",
                "completed_at": "2026-03-21T10:00:05Z",
                "error": None,
                "result": {
                    "id": 1,
                    "workflow_name": "month_end_close",
                    "workflow_label": "Month-end close",
                    "status": "completed",
                    "headline": "Month-end pack ready",
                    "summary": "Report and KPI pack completed.",
                    "risk_level": "low",
                    "recommended_actions": ["Review the executive summary."],
                    "automated_actions": ["Generated a fresh monthly PDF report for distribution."],
                    "email_subject": "Month-end pack ready",
                    "email_draft": "The close pack is attached.",
                    "task": "Run the workflow",
                    "model": "qwen3:4b",
                    "tools_used": ["generate_monthly_report"],
                    "report_download_url": "/api/reports/monthly",
                    "generated_at": "2026-03-21T10:00:00Z",
                },
            }

    app.extensions["services"]["agent_service"] = FakeAgentService()

    response = client.post(
        "/api/agents/finance-briefing",
        json={"task": "Prepare a finance briefing"},
    )

    assert response.status_code == 202
    assert response.get_json()["data"]["id"] == "job-1"

    briefing_status = client.get("/api/agents/finance-briefing/job-1")
    assert briefing_status.status_code == 200
    assert briefing_status.get_json()["data"]["result"]["headline"] == "Finance briefing"

    workflows = client.get("/api/agents/workflows")
    runs = client.get("/api/agents/runs")
    workflow_run = client.post("/api/agents/workflows/month_end_close/run", json={})
    workflow_status = client.get("/api/agents/workflow-jobs/workflow-job-1")

    assert workflows.get_json()["data"][0]["id"] == "month_end_close"
    assert runs.get_json()["data"][0]["workflow_name"] == "month_end_close"
    assert workflow_run.status_code == 202
    assert workflow_run.get_json()["data"]["id"] == "workflow-job-1"
    assert workflow_status.get_json()["data"]["result"]["workflow_label"] == "Month-end close"


def test_agent_bootstrap_endpoint(client, app):
    class FakeAutomationService:
        def run_bootstrap_workflows_async(self, flask_app):
            assert flask_app is app
            return [
                {"id": 1, "workflow_name": "month_end_close"},
                {"id": 2, "workflow_name": "upcoming_bills_check"},
            ]

    app.extensions["services"]["automation_service"] = FakeAutomationService()

    response = client.post("/api/agents/bootstrap")

    assert response.status_code == 200
    assert len(response.get_json()["data"]) == 2


def test_recurring_occurrence_paid_and_restored(client):
    today = date.today()
    occurrence_date = (today.replace(day=28) + timedelta(days=4)).replace(day=1).isoformat()

    matching_transaction = client.post(
        "/api/expenses",
        json={
            "date": today.isoformat(),
            "category": "Housing",
            "description": "Rent payment",
            "amount": "700.00",
        },
    )
    transaction_id = matching_transaction.get_json()["data"]["id"]

    paid = client.post(
        "/api/recurring-items/1/occurrences/pay",
        json={"occurrence_date": occurrence_date, "transaction_id": transaction_id},
    )
    calendar_after_paid = client.get("/api/recurring-items/calendar?days=45")
    restored = client.post(
        "/api/recurring-items/1/occurrences/unpay",
        json={"occurrence_date": occurrence_date},
    )
    calendar_after_restore = client.get("/api/recurring-items/calendar?days=45")

    assert matching_transaction.status_code == 201
    assert paid.status_code == 200
    assert paid.get_json()["data"]["message"] == f"Reminder marked as paid for this date using transaction #{transaction_id}."
    assert all(
        not (
            item["recurring_item_id"] == 1
            and item["date"] == occurrence_date
        )
        for item in calendar_after_paid.get_json()["data"]["occurrences"]
    )
    assert restored.status_code == 200
    assert restored.get_json()["data"]["message"] == "Reminder restored for this date."
    assert any(
        item["recurring_item_id"] == 1 and item["date"] == occurrence_date
        for item in calendar_after_restore.get_json()["data"]["occurrences"]
    )


def test_create_expense_validation_error(client):
    response = client.post(
        "/api/expenses",
        json={
            "date": "2026/03/09",
            "category": "Health",
            "description": "Pharmacy",
            "amount": "12.30",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "date must use YYYY-MM-DD format."


def test_get_expense_not_found(client):
    response = client.get("/api/expenses/999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Expense with id 999 was not found."


def test_delete_expense_not_found(client):
    response = client.delete("/api/expenses/999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Expense with id 999 was not found."


def test_import_csv_requires_file(client):
    response = client.post("/api/expenses/import", data={}, content_type="multipart/form-data")

    assert response.status_code == 400
    assert response.get_json()["error"] == "CSV file is required."


def test_import_csv_skips_rows_with_missing_values(client):
    response = client.post(
        "/api/expenses/import",
        data={
            "file": (
                BytesIO(
                    b"date,category,description,amount\n"
                    b"2026-03-11,Food,Market,24.50\n"
                    b"2026-03-12,Food,,10.00\n"
                    b",Travel,Taxi,18.00\n"
                ),
                "expenses.csv",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["data"] == {"imported_rows": 1, "skipped_rows": 2}


def test_import_csv_rejects_bad_encoding(client):
    response = client.post(
        "/api/expenses/import",
        data={"file": (BytesIO(b"\xff\xfe\x00\x00"), "expenses.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "CSV file must use UTF-8 encoding."


def test_expenses_can_be_sorted_ascending(client):
    response = client.get("/api/expenses?sort=asc")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data[0]["date"] <= data[-1]["date"]






