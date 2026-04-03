def test_smoke_core_finance_endpoints_return_seeded_data(client):
    responses = {
        "health": client.get("/api/health"),
        "dashboard": client.get("/api/dashboard"),
        "settings": client.get("/api/settings"),
        "categories": client.get("/api/analytics/categories"),
        "pulse": client.get("/api/analytics/financial-pulse"),
        "recurring": client.get("/api/recurring-items"),
        "calendar": client.get("/api/recurring-items/calendar?days=45"),
    }

    assert responses["health"].status_code == 200
    assert responses["dashboard"].status_code == 200
    assert responses["settings"].status_code == 200
    assert responses["categories"].status_code == 200
    assert responses["pulse"].status_code == 200
    assert responses["recurring"].status_code == 200
    assert responses["calendar"].status_code == 200

    dashboard = responses["dashboard"].get_json()["data"]
    settings = responses["settings"].get_json()["data"]
    recurring_items = responses["recurring"].get_json()["data"]
    calendar = responses["calendar"].get_json()["data"]

    assert dashboard["monthly_budget"] == 1050.0
    assert dashboard["monthly_income"] == 1500.0
    assert settings["monthly_budget"] == 1050.0
    assert settings["monthly_income"] == 1500.0
    assert settings["income_month"]
    assert len(recurring_items) == 2
    assert {item["description"] for item in recurring_items} == {"Rent", "Payroll"}
    assert any(item["description"] == "Rent" for item in calendar["occurrences"])


def test_sanity_budget_update_and_recurring_crud_flow(client):
    update_budget = client.put("/api/settings/budget", json={"monthly_budget": 1325.75})
    update_income = client.put("/api/settings/income", json={"monthly_income": 2400.50, "month": "2026-04"})
    create_recurring = client.post(
        "/api/recurring-items",
        json={
            "category": "Travel",
            "description": "Weekly commute",
            "amount": "45.00",
            "entry_type": "expense",
            "frequency": "weekly",
            "start_date": "2026-03-24",
            "active": True,
        },
    )

    assert update_budget.status_code == 200
    assert update_budget.get_json()["data"]["monthly_budget"] == 1325.75
    assert update_income.status_code == 200
    assert update_income.get_json()["data"]["monthly_income"] == 2400.50
    assert update_income.get_json()["data"]["income_month"] == "2026-04"
    april_settings = client.get("/api/settings?month=2026-04")
    march_settings = client.get("/api/settings?month=2026-03")
    assert april_settings.get_json()["data"]["monthly_income"] == 2400.50
    assert march_settings.get_json()["data"]["monthly_income"] == 1500.0
    assert create_recurring.status_code == 201

    item_id = create_recurring.get_json()["data"]["id"]
    update_recurring = client.put(
        f"/api/recurring-items/{item_id}",
        json={
            "category": "Travel",
            "description": "Updated commute",
            "amount": "49.50",
            "entry_type": "expense",
            "frequency": "weekly",
            "start_date": "2026-03-24",
            "active": True,
        },
    )
    delete_recurring = client.delete(f"/api/recurring-items/{item_id}")

    assert update_recurring.status_code == 200
    assert update_recurring.get_json()["data"]["description"] == "Updated commute"
    assert delete_recurring.status_code == 200
    assert delete_recurring.get_json()["data"]["message"] == "Recurring item deleted successfully."


def test_partition_invalid_budget_and_recurring_payloads_return_validation_errors(client):
    invalid_budget = client.put("/api/settings/budget", json={"monthly_budget": 0})
    invalid_income = client.put("/api/settings/income", json={"monthly_income": 0})
    invalid_recurring = client.post(
        "/api/recurring-items",
        json={
            "category": "Housing",
            "description": "Rent",
            "amount": "700.00",
            "entry_type": "expense",
            "frequency": "daily",
            "start_date": "2026-03-01",
            "active": True,
        },
    )

    assert invalid_budget.status_code == 400
    assert invalid_budget.get_json()["error"] == "monthly_budget must be greater than zero."
    assert invalid_income.status_code == 400
    assert invalid_income.get_json()["error"] == "monthly_income must be greater than zero."
    assert invalid_recurring.status_code == 400
    assert invalid_recurring.get_json()["error"] == "frequency must be weekly or monthly."


def test_smoke_agent_workflows_and_run_history(client, app):
    class FakeAgentService:
        def list_workflows(self):
            return [{"id": "month_end_close", "label": "Month-end close"}]

        def list_runs(self, limit):
            assert limit == 8
            return [{"id": 1, "workflow_name": "month_end_close"}]

        def start_workflow_run(self, workflow_name, payload, flask_app):
            assert workflow_name == "month_end_close"
            assert payload == {}
            assert flask_app is not None
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
                    "recommended_actions": ["Review the summary."],
                    "automated_actions": ["Generated a fresh monthly PDF report for distribution."],
                    "email_subject": "Month-end pack ready",
                    "email_draft": "The close pack is ready.",
                    "task": "Run the workflow",
                    "model": "mistral:latest",
                    "tools_used": ["generate_monthly_report"],
                    "report_download_url": "/api/reports/monthly",
                    "generated_at": "2026-03-21T10:00:00Z",
                },
            }

    app.extensions["services"]["agent_service"] = FakeAgentService()

    workflows = client.get("/api/agents/workflows")
    run = client.post("/api/agents/workflows/month_end_close/run", json={})
    workflow_status = client.get("/api/agents/workflow-jobs/workflow-job-1")
    runs = client.get("/api/agents/runs")

    assert workflows.status_code == 200
    assert run.status_code == 202
    assert workflow_status.status_code == 200
    assert runs.status_code == 200
    assert any(item["id"] == "month_end_close" for item in workflows.get_json()["data"])
    assert run.get_json()["data"]["workflow_name"] == "month_end_close"
    assert workflow_status.get_json()["data"]["result"]["automated_actions"]
    assert runs.get_json()["data"][0]["workflow_name"] == "month_end_close"

