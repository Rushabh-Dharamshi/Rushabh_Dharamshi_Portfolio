from types import SimpleNamespace

import pytest

from budget_tracker_api.errors import ServiceUnavailableError, ValidationError
from budget_tracker_api.services.agentic_command_runtime import AgenticCommandRuntime


class FakeMcpServer:
    def __init__(self, raise_without_tool=False):
        self.raise_without_tool = raise_without_tool
        self.calls = []

    def list_tools(self):
        return [{"name": "set_monthly_budget"}]

    def call_tool(self, tool_name, arguments):
        if self.raise_without_tool and not tool_name:
            raise ValidationError("missing tool")
        self.calls.append((tool_name, arguments))
        return {"action_result": {"type": "monthly_budget_updated"}, "report_download_url": "/api/reports/monthly"}


class FakeMemoryService:
    def __init__(self):
        self.entries = []

    def recall(self, limit):
        return [{"summary": "prior action"}]

    def remember(self, **payload):
        self.entries.append(payload)


class FakeLlm:
    def __init__(self, responses):
        self.responses = list(responses)

    def invoke(self, prompt):
        return SimpleNamespace(content=self.responses.pop(0))


class RuntimeWithStubLlm(AgenticCommandRuntime):
    def __init__(self, llm, mcp_server=None, memory_service=None):
        super().__init__(model_name="qwen", base_url=None, mcp_server=mcp_server or FakeMcpServer(), memory_service=memory_service or FakeMemoryService())
        self._llm = llm


def test_agentic_runtime_service_unavailable_and_helpers():
    runtime = AgenticCommandRuntime(model_name="qwen", base_url=None, mcp_server=FakeMcpServer(), memory_service=FakeMemoryService())
    assert runtime.is_available() is False
    with pytest.raises(ServiceUnavailableError):
        runtime.run("set budget")
    with pytest.raises(ServiceUnavailableError):
        runtime._invoke("prompt")
    assert runtime._route_after_execute({"execution_error": None}) == "verify"
    assert runtime._route_after_execute({"execution_error": "bad", "repair_attempts": 0}) == "repair"
    assert runtime._route_after_execute({"execution_error": "bad", "repair_attempts": 1}) == "fail"
    assert runtime._extract_report_url([{"result": {"report_download_url": "/a"}}]) == "/a"
    assert runtime._extract_report_url([{"result": {"download_url": "/b"}}]) == "/b"
    assert runtime._extract_report_url([]) is None


def test_agentic_runtime_parsing_and_prompt_helpers():
    runtime = RuntimeWithStubLlm(FakeLlm([]))
    assert "User task: task" in runtime._build_planner_prompt(task="task", memories=[], tool_catalog=[], previous_error=None, prior_plan=None)
    assert "Tool results" in runtime._build_verifier_prompt(task="task", plan={}, execution_results=[], latest_action_result=None)
    assert runtime._parse_json_object('{"ok": true}', "label") == {"ok": True}
    assert runtime._parse_json_object('```json\n{"ok": true}\n```', "label") == {"ok": True}
    assert runtime._parse_json_object('<think>ignored</think>{"ok": true}', "label") == {"ok": True}
    with pytest.raises(ValidationError):
        runtime._parse_json_object('[]', "label")
    with pytest.raises(ValidationError):
        runtime._parse_json_object('not json', "label")
    assert runtime._utc_now().endswith("Z")


def test_agentic_runtime_runs_full_graph_and_handles_list_content():
    llm = FakeLlm([
        '{"intent":"update budget","steps":[{"tool":"set_monthly_budget","arguments":{"monthly_budget":1200},"reason":"apply budget"}],"success_criteria":["budget saved"]}',
        ['{"headline":"Budget updated","summary":"Budget saved.","risk_level":"low","recommended_actions":[],"email_subject":"Budget updated","email_draft":"Budget updated."}'],
    ])
    memory = FakeMemoryService()
    runtime = RuntimeWithStubLlm(llm, mcp_server=FakeMcpServer(), memory_service=memory)

    result = runtime.run("set my budget")

    assert result["headline"] == "Budget updated"
    assert result["action_result"]["type"] == "monthly_budget_updated"
    assert result["report_download_url"] == "/api/reports/monthly"
    assert memory.entries[0]["kind"] == "manual_action"
