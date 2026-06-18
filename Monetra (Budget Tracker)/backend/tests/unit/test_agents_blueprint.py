from types import SimpleNamespace

from budget_tracker_api.security import AUTH_SESSION_KEY, AUTH_USER_ID_SESSION_KEY


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
        def run_upcoming_bills_email_now(self, recipient=None):
            assert recipient is None
            return {"id": 2, "summary": "Upcoming bills sent"}

        def run_all_upcoming_bills_email_now(self, recipient=None):
            assert recipient is None
            return {"id": 5, "summary": "All upcoming bills sent"}

        def run_month_end_email_now(self, recipient=None):
            assert recipient is None
            return {"id": 3, "summary": "Month-end sent"}

        def run_bootstrap_workflows_async(self, app_obj):
            return [{"id": 4}]

        def queue_realtime_refresh(self, app_obj, event_type, user_id=None):
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
    all_upcoming = client.post("/api/agents/automation/all-upcoming-bills-email")
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
    assert all_upcoming.get_json()["data"]["summary"] == "All upcoming bills sent"
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
        def queue_realtime_refresh(self, app_obj, event_type, user_id=None):
            return [{"event_type": event_type}]

        def run_upcoming_bills_email_now(self, recipient=None):
            raise AssertionError("not used")

        def run_all_upcoming_bills_email_now(self, recipient=None):
            raise AssertionError("not used")

        def run_month_end_email_now(self, recipient=None):
            raise AssertionError("not used")

        def run_bootstrap_workflows_async(self, app_obj):
            raise AssertionError("not used")

    app.extensions["services"]["agent_service"] = FakeAgentService()
    app.extensions["services"]["automation_service"] = FakeAutomationService()

    response = client.post("/api/agents/automation/refresh", json={})

    assert response.status_code == 202
    assert response.get_json()["data"][0]["event_type"] == "finance_state_changed"


def test_agent_routes_attach_signed_in_user_context(client, app):
    calls = []

    class FakeAgentService:
        def start_finance_briefing(self, payload, app_obj):
            calls.append(("briefing", payload))
            return {"id": "brief-user", "status": "queued"}

        def start_workflow_run(self, workflow_name, payload, app_obj):
            calls.append(("workflow", workflow_name, payload))
            return {"id": "workflow-user", "status": "queued"}

    class FakeAutomationService:
        def queue_realtime_refresh(self, app_obj, event_type, user_id=None):
            calls.append(("refresh", event_type, user_id))
            return [{"id": "refresh-user"}]

        def run_upcoming_bills_email_now(self, recipient=None):
            calls.append(("upcoming", recipient))
            return {"summary": "sent"}

    class FakeUserService:
        def get_user(self, user_id):
            if user_id == 7:
                return None
            return {"id": user_id, "email": "owner@example.com"}

    app.extensions["services"]["agent_service"] = FakeAgentService()
    app.extensions["services"]["automation_service"] = FakeAutomationService()
    app.extensions["services"]["user_service"] = FakeUserService()

    with client.session_transaction() as session:
        session[AUTH_SESSION_KEY] = "Owner"
        session[AUTH_USER_ID_SESSION_KEY] = 5

    assert client.post("/api/agents/finance-briefing", json={"task": "brief"}).status_code == 202
    assert client.post("/api/agents/workflows/month_end_close/run", json={"task": "run"}).status_code == 202
    assert client.post("/api/agents/automation/refresh", json={"event_type": "expense_created"}).status_code == 202
    assert client.post("/api/agents/automation/upcoming-bills-email").status_code == 200

    assert calls[0] == ("briefing", {"task": "brief", "user_id": 5, "recipient": "owner@example.com"})
    assert calls[1] == ("workflow", "month_end_close", {"task": "run", "user_id": 5})
    assert calls[2] == ("refresh", "expense_created", 5)
    assert calls[3] == ("upcoming", "owner@example.com")

    with client.session_transaction() as session:
        session[AUTH_USER_ID_SESSION_KEY] = 7

    assert client.post("/api/agents/finance-briefing", json={"task": "brief"}).status_code == 202
    assert calls[-1] == ("briefing", {"task": "brief", "user_id": 7})
