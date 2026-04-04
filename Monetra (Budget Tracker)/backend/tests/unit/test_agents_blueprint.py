from types import SimpleNamespace


def test_agent_blueprint_endpoints(client, app):
    class FakeAgentService:
        def start_finance_briefing(self, payload, app_obj):
            assert payload == {"task": "brief"}
            return {"id": "brief-1", "status": "queued"}

        def get_finance_briefing_job(self, job_id):
            assert job_id == "brief-1"
            return {"id": job_id, "status": "completed"}

        def list_workflows(self):
            return [{"id": "month_end_close", "label": "Month-end close"}]

        def list_runs(self, limit):
            return [{"id": 1, "limit": limit}]

        def start_workflow_run(self, workflow_name, payload, app_obj):
            assert workflow_name == "month_end_close"
            assert payload == {"task": "run"}
            return {"id": "wf-1", "status": "queued", "workflow_name": workflow_name}

        def get_workflow_job(self, job_id):
            return {"id": job_id, "status": "running"}

    class FakeAutomationService:
        def run_upcoming_bills_email_now(self):
            return {"id": 2, "summary": "Upcoming bills sent"}

        def run_month_end_email_now(self):
            return {"id": 3, "summary": "Month-end sent"}

        def run_bootstrap_workflows_async(self, app_obj):
            return [{"id": 4}]

        def queue_realtime_refresh(self, app_obj, event_type):
            assert event_type == "expense_created"
            return [{"id": "job-1", "workflow_name": "month_end_close"}]

    app.extensions["services"]["agent_service"] = FakeAgentService()
    app.extensions["services"]["automation_service"] = FakeAutomationService()

    briefing = client.post("/api/agents/finance-briefing", json={"task": "brief"})
    briefing_status = client.get("/api/agents/finance-briefing/brief-1")
    workflows = client.get("/api/agents/workflows")
    runs = client.get("/api/agents/runs?limit=5")
    workflow_run = client.post("/api/agents/workflows/month_end_close/run", json={"task": "run"})
    workflow_status = client.get("/api/agents/workflow-jobs/wf-1")
    upcoming = client.post("/api/agents/automation/upcoming-bills-email")
    month_end = client.post("/api/agents/automation/month-end-email")
    bootstrap = client.post("/api/agents/bootstrap")
    refresh = client.post("/api/agents/automation/refresh", json={"event_type": "expense_created"})

    assert briefing.status_code == 202
    assert briefing.get_json()["data"]["id"] == "brief-1"
    assert briefing_status.get_json()["data"]["status"] == "completed"
    assert workflows.get_json()["data"][0]["id"] == "month_end_close"
    assert runs.get_json()["data"][0]["limit"] == 5
    assert workflow_run.status_code == 202
    assert workflow_status.get_json()["data"]["status"] == "running"
    assert upcoming.get_json()["data"]["summary"] == "Upcoming bills sent"
    assert month_end.get_json()["data"]["summary"] == "Month-end sent"
    assert bootstrap.get_json()["data"][0]["id"] == 4
    assert refresh.status_code == 202
    assert refresh.get_json()["data"][0]["workflow_name"] == "month_end_close"


def test_agent_refresh_defaults_event_type(client, app):
    class FakeAgentService:
        def start_finance_briefing(self, payload, app_obj):
            raise AssertionError("not used")

        def get_finance_briefing_job(self, job_id):
            raise AssertionError("not used")

        def list_workflows(self):
            return []

        def list_runs(self, limit):
            return []

        def start_workflow_run(self, workflow_name, payload, app_obj):
            raise AssertionError("not used")

        def get_workflow_job(self, job_id):
            raise AssertionError("not used")

    class FakeAutomationService:
        def queue_realtime_refresh(self, app_obj, event_type):
            return [{"event_type": event_type}]

        def run_upcoming_bills_email_now(self):
            raise AssertionError("not used")

        def run_month_end_email_now(self):
            raise AssertionError("not used")

        def run_bootstrap_workflows_async(self, app_obj):
            raise AssertionError("not used")

    app.extensions["services"]["agent_service"] = FakeAgentService()
    app.extensions["services"]["automation_service"] = FakeAutomationService()

    response = client.post("/api/agents/automation/refresh", json={})

    assert response.status_code == 202
    assert response.get_json()["data"][0]["event_type"] == "finance_state_changed"
