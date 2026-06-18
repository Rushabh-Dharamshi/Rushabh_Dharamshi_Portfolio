from budget_tracker_api.services.agent_memory_service import AgentMemoryService
from budget_tracker_api.services.agentic_command_runtime import AgenticCommandRuntime
from budget_tracker_api.services.finance_mcp_server import FinanceMcpServer


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakePlanningLlm:
    def __init__(self, responses):
        self._responses = list(responses)
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        if not self._responses:
            raise AssertionError("No more fake LLM responses configured.")
        return FakeMessage(self._responses.pop(0))


def test_agentic_command_runtime_executes_plan_and_persists_memory():
    runtime = AgenticCommandRuntime(
        model_name="mistral:latest",
        base_url=None,
        mcp_server=FinanceMcpServer(
            {
                "set_monthly_budget": lambda arguments: {
                    "headline": "Monthly budget updated",
                    "summary": "Monthly budget is now GBP 1800.00.",
                    "action_result": {
                        "type": "monthly_budget_updated",
                        "message": "Monthly budget updated successfully.",
                        "payload": {"monthly_budget": 1800.0},
                    },
                }
            }
        ),
        memory_service=AgentMemoryService(None),
    )
    runtime._llm = FakePlanningLlm(
        [
            '{"intent":"update budget","steps":[{"tool":"set_monthly_budget","arguments":{"monthly_budget":1800},"reason":"Apply the requested budget."}],"success_criteria":["Budget updated"]}',
            '{"headline":"Monthly budget updated","summary":"Monthly budget is now GBP 1800.00.","risk_level":"low","recommended_actions":["Review the dashboard totals."],"email_subject":"Monthly budget updated","email_draft":"Monthly budget updated to GBP 1800.00."}',
        ]
    )

    result = runtime.run("Set my monthly budget to 1800 pounds.")

    assert result["headline"] == "Monthly budget updated"
    assert result["tools_used"] == ["set_monthly_budget"]
    assert result["action_result"]["type"] == "monthly_budget_updated"
    memories = runtime._memory_service.recall(1)
    assert memories[0]["summary"] == "Monthly budget is now GBP 1800.00."


def test_agentic_command_runtime_replans_once_after_tool_error():
    runtime = AgenticCommandRuntime(
        model_name="mistral:latest",
        base_url=None,
        mcp_server=FinanceMcpServer(
            {
                "set_monthly_income": lambda arguments: {
                    "headline": "Monthly income updated",
                    "summary": "Monthly income is now GBP 2400.00.",
                    "action_result": {
                        "type": "monthly_income_updated",
                        "message": "Monthly income updated successfully.",
                        "payload": {"monthly_income": 2400.0},
                    },
                }
            }
        ),
        memory_service=AgentMemoryService(None),
    )
    runtime._llm = FakePlanningLlm(
        [
            '{"intent":"update income","steps":[{"tool":"unknown_tool","arguments":{},"reason":"Bad first plan."}],"success_criteria":["Income updated"]}',
            '{"intent":"update income","steps":[{"tool":"set_monthly_income","arguments":{"monthly_income":2400},"reason":"Correct the income value."}],"success_criteria":["Income updated"]}',
            '{"headline":"Monthly income updated","summary":"Monthly income is now GBP 2400.00.","risk_level":"low","recommended_actions":["Review cash flow."],"email_subject":"Monthly income updated","email_draft":"Monthly income updated to GBP 2400.00."}',
        ]
    )

    result = runtime.run("Set my monthly income to 2400 pounds.")

    assert result["headline"] == "Monthly income updated"
    assert result["tools_used"] == ["set_monthly_income"]
    assert len(runtime._llm.prompts) == 3


def test_agentic_command_runtime_accepts_list_shaped_plan_steps():
    runtime = AgenticCommandRuntime(
        model_name="mistral:latest",
        base_url=None,
        mcp_server=FinanceMcpServer(
            {
                "set_monthly_budget": lambda arguments: {
                    "headline": "Monthly budget updated",
                    "summary": "Monthly budget is now GBP 1600.00.",
                    "action_result": {
                        "type": "monthly_budget_updated",
                        "message": "Monthly budget updated successfully.",
                        "payload": {"monthly_budget": 1600.0},
                    },
                }
            }
        ),
        memory_service=AgentMemoryService(None),
    )
    runtime._llm = FakePlanningLlm(
        [
            '{"intent":"update budget","steps":[["set_monthly_budget",{"monthly_budget":1600},"Apply the requested budget."]],"success_criteria":["Budget updated"]}',
            '{"headline":"Monthly budget updated","summary":"Monthly budget is now GBP 1600.00.","risk_level":"low","recommended_actions":["Review the dashboard totals."],"email_subject":"Monthly budget updated","email_draft":"Monthly budget updated to GBP 1600.00."}',
        ]
    )

    result = runtime.run("Set my monthly budget to 1600 pounds.")

    assert result["headline"] == "Monthly budget updated"
    assert result["tools_used"] == ["set_monthly_budget"]
