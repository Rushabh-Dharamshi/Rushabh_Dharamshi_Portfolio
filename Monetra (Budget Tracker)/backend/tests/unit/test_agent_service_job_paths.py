import pytest

from budget_tracker_api.errors import ServiceUnavailableError, ValidationError
from budget_tracker_api.services.agent_service import AgentService
from tests.unit.test_agent_service_helpers import (
    StubAnalyticsService,
    StubExpenseService,
    StubPredictionService,
    StubRecurringService,
    StubReportService,
    StubRepository,
    StubSettingsService,
    StubOllamaClient,
)


class InlineExecutor:
    def submit(self, fn, *args):
        return fn(*args)


class ToolLoopOllama:
    model = "qwen:latest"
    base_url = "http://ollama"

    def __init__(self):
        self.calls = 0

    def chat(self, messages, tools=None):
        self.calls += 1
        if self.calls == 1:
            return {"message": {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "get_dashboard_summary", "arguments": {}}}]}}
        return {"message": {"role": "assistant", "content": '{"headline":"Loop","summary":"done","risk_level":"low","recommended_actions":[],"email_subject":"Loop","email_draft":"Loop"}'}}


def build_service(ollama):
    service = AgentService(
        ollama,
        StubAnalyticsService(),
        StubPredictionService(),
        StubRecurringService(),
        StubReportService(),
        StubExpenseService(),
        StubSettingsService(),
        StubRepository(),
    )
    service._job_executor = InlineExecutor()
    return service


def test_agent_service_job_entrypoints_and_reuse(app, monkeypatch):
    service = build_service(StubOllamaClient())
    monkeypatch.setattr(service, "_run_finance_briefing_job", lambda job_id, payload, flask_app: None)
    monkeypatch.setattr(service, "_run_workflow_job", lambda job_id, workflow_name, payload, flask_app: None)

    finance_job = service.start_finance_briefing({}, app)
    assert finance_job["status"] == "queued"
    assert finance_job["task"].startswith("Prepare a CFO-style monthly briefing")
    assert service.get_finance_briefing_job(finance_job["id"])["id"] == finance_job["id"]
    with pytest.raises(ValidationError):
        service.get_finance_briefing_job("missing")

    queued = {"id": "existing", "workflow_name": "month_end_close", "status": "running", "created_at": "2026-04-03T10:00:00Z", "started_at": "2026-04-03T10:01:00Z"}
    service._workflow_jobs[queued["id"]] = queued
    reused = service.start_workflow_run("month_end_close", {}, app, reuse_active=True)
    assert reused["id"] == "existing"
    new_job = service.start_workflow_run("upcoming_bills_check", {"task": "custom"}, app)
    assert new_job["task"] == "custom"
    assert service.get_workflow_job(new_job["id"])["id"] == new_job["id"]
    with pytest.raises(ValidationError):
        service.get_workflow_job("missing")
    with pytest.raises(ValidationError):
        service.start_workflow_run("missing", {}, app)
    assert service.list_workflows()
    assert service.list_runs(99) == []


def test_agent_service_run_finance_briefing_branches(monkeypatch):
    manual_service = build_service(StubOllamaClient())
    monkeypatch.setattr(manual_service, "_looks_like_manual_action_command", lambda task: True)
    monkeypatch.setattr(manual_service, "_run_manual_action_command", lambda task, recipient=None: {"headline": "manual"})
    assert manual_service.run_finance_briefing({"task": "set my budget"})["headline"] == "manual"

    context_service = build_service(StubOllamaClient())
    context_service._ollama_client.model = "mistral:latest"
    monkeypatch.setattr(context_service, "_run_context_prompt", lambda task: {"headline": "context", "summary": "ok", "risk_level": "low", "recommended_actions": [], "email_subject": "context", "email_draft": "context", "tools_used": ["dashboard"], "report_download_url": None})
    context_result = context_service.run_finance_briefing({"task": "brief me"})
    assert context_result["headline"] == "context"
    assert context_result["model"] == "mistral:latest"

    fallback_service = build_service(StubOllamaClient('{"headline":"ignored","summary":"ignored","risk_level":"low","recommended_actions":[],"email_subject":"ignored","email_draft":"ignored"}'))
    monkeypatch.setattr(fallback_service, "_run_context_prompt", lambda task: {"headline": "fallback", "summary": "ok", "risk_level": "low", "recommended_actions": [], "email_subject": "fallback", "email_draft": "fallback", "tools_used": ["dashboard"], "report_download_url": None})
    assert fallback_service.run_finance_briefing({"task": "brief me"})["headline"] == "fallback"

    tool_service = build_service(ToolLoopOllama())
    tool_result = tool_service.run_finance_briefing({"task": "brief me"})
    assert tool_result["headline"] == "Loop"
    assert tool_result["tools_used"] == ["get_dashboard_summary"]

    timeout_service = build_service(ToolLoopOllama())
    monkeypatch.setattr(timeout_service._ollama_client, "chat", lambda messages, tools=None: {"message": {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "get_dashboard_summary", "arguments": {}}}]}})
    with pytest.raises(ServiceUnavailableError):
        timeout_service.run_finance_briefing({"task": "brief me"})


def test_agent_service_run_workflow_paths(monkeypatch):
    service = build_service(StubOllamaClient())
    monkeypatch.setattr(service, "_run_workflow_with_langgraph", lambda workflow_name, workflow, task: {"workflow_name": workflow_name, "headline": workflow["label"]})
    result = service.run_workflow("month_end_close", {})
    assert result["workflow_name"] == "month_end_close"
    with pytest.raises(ValidationError):
        service.run_workflow("missing", {})
