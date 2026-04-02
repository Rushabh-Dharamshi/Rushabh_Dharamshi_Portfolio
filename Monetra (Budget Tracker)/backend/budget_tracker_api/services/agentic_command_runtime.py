import json
import logging
import re
from typing import TypedDict

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from budget_tracker_api.errors import ServiceUnavailableError, ValidationError
from budget_tracker_api.services.agent_memory_service import AgentMemoryService
from budget_tracker_api.services.finance_mcp_server import FinanceMcpServer


logger = logging.getLogger(__name__)


class AgenticCommandRuntime:
    def __init__(
        self,
        *,
        model_name: str,
        base_url: str | None,
        mcp_server: FinanceMcpServer,
        memory_service: AgentMemoryService,
    ):
        self._model_name = model_name
        self._mcp_server = mcp_server
        self._memory_service = memory_service
        self._llm = (
            ChatOllama(model=model_name, base_url=base_url, temperature=0)
            if base_url
            else None
        )

    def is_available(self) -> bool:
        return self._llm is not None

    def run(self, task: str) -> dict:
        if self._llm is None:
            raise ServiceUnavailableError("Local LangChain agent runtime is unavailable because Ollama is not configured.")

        class ManualAgentState(TypedDict, total=False):
            task: str
            memories: list[dict]
            tool_catalog: list[dict]
            plan: dict
            execution_results: list[dict]
            execution_error: str | None
            latest_action_result: dict | None
            tools_used: list[str]
            repair_attempts: int
            final_result: dict | None

        graph = StateGraph(ManualAgentState)

        def planner_node(state: ManualAgentState):
            planning_prompt = self._build_planner_prompt(
                task=state["task"],
                memories=state.get("memories", []),
                tool_catalog=state.get("tool_catalog", []),
                previous_error=state.get("execution_error"),
                prior_plan=state.get("plan"),
            )
            plan = self._parse_json_object(self._invoke(planning_prompt), "manual action plan")
            return {
                "plan": plan,
                "execution_error": None,
            }

        def executor_node(state: ManualAgentState):
            plan = state.get("plan") or {}
            steps = plan.get("steps") or []
            execution_results: list[dict] = []
            latest_action_result = None
            tools_used: list[str] = []

            try:
                for step in steps:
                    tool_name = str(step.get("tool") or "").strip()
                    arguments = step.get("arguments") or {}
                    if not tool_name:
                        raise ValidationError("The agent planner returned a step without a tool name.")
                    result = self._mcp_server.call_tool(tool_name, arguments)
                    execution_results.append(
                        {
                            "tool": tool_name,
                            "reason": str(step.get("reason") or ""),
                            "arguments": arguments,
                            "result": result,
                        }
                    )
                    tools_used.append(tool_name)
                    if isinstance(result, dict) and result.get("action_result"):
                        latest_action_result = result.get("action_result")
                return {
                    "execution_results": execution_results,
                    "execution_error": None,
                    "latest_action_result": latest_action_result,
                    "tools_used": tools_used,
                }
            except Exception as exc:
                logger.warning("Agentic executor failed | task=%s error=%s", state.get("task"), exc)
                return {
                    "execution_results": execution_results,
                    "execution_error": str(exc),
                    "latest_action_result": latest_action_result,
                    "tools_used": tools_used,
                }

        def repair_node(state: ManualAgentState):
            return {"repair_attempts": state.get("repair_attempts", 0) + 1}

        def verifier_node(state: ManualAgentState):
            verification_prompt = self._build_verifier_prompt(
                task=state["task"],
                plan=state.get("plan") or {},
                execution_results=state.get("execution_results", []),
                latest_action_result=state.get("latest_action_result"),
            )
            verification = self._parse_json_object(self._invoke(verification_prompt), "manual action verification")
            execution_results = state.get("execution_results", [])
            final_result = {
                "headline": str(verification.get("headline") or "Agent action completed"),
                "summary": str(verification.get("summary") or "The requested change was applied."),
                "risk_level": str(verification.get("risk_level") or "low").lower(),
                "recommended_actions": [
                    str(item)
                    for item in verification.get("recommended_actions", [])
                    if str(item).strip()
                ]
                or [
                    "Review the refreshed dashboard values.",
                    "Confirm the change in the relevant table or planner view.",
                ],
                "email_subject": str(verification.get("email_subject") or "Finance command completed"),
                "email_draft": str(verification.get("email_draft") or "Your finance command has been completed."),
                "task": state["task"],
                "model": self._model_name,
                "tools_used": state.get("tools_used", []),
                "report_download_url": self._extract_report_url(execution_results),
                "generated_at": self._utc_now(),
                "action_result": state.get("latest_action_result"),
                "trace": {
                    "memory": state.get("memories", []),
                    "plan": state.get("plan") or {},
                    "execution_results": execution_results,
                    "verification": verification,
                    "repair_attempts": state.get("repair_attempts", 0),
                },
            }
            self._memory_service.remember(
                kind="manual_action",
                task=state["task"],
                summary=final_result["summary"],
                tools_used=final_result["tools_used"],
                metadata={
                    "headline": final_result["headline"],
                    "action_type": (final_result.get("action_result") or {}).get("type"),
                },
            )
            return {"final_result": final_result}

        def fail_node(state: ManualAgentState):
            raise ValidationError(state.get("execution_error") or "The agent could not complete the command.")

        graph.add_node("plan", planner_node)
        graph.add_node("execute", executor_node)
        graph.add_node("repair", repair_node)
        graph.add_node("verify", verifier_node)
        graph.add_node("fail", fail_node)

        graph.add_edge(START, "plan")
        graph.add_edge("plan", "execute")
        graph.add_conditional_edges(
            "execute",
            self._route_after_execute,
            {
                "verify": "verify",
                "repair": "repair",
                "fail": "fail",
            },
        )
        graph.add_edge("repair", "plan")
        graph.add_edge("verify", END)
        graph.add_edge("fail", END)

        compiled = graph.compile()
        result_state = compiled.invoke(
            {
                "task": task,
                "memories": self._memory_service.recall(6),
                "tool_catalog": self._mcp_server.list_tools(),
                "repair_attempts": 0,
            }
        )
        final_result = result_state.get("final_result")
        if not final_result:
            raise ValidationError("The agent could not produce a final command result.")
        return final_result

    @staticmethod
    def _route_after_execute(state: dict) -> str:
        if state.get("execution_error"):
            return "repair" if state.get("repair_attempts", 0) < 1 else "fail"
        return "verify"

    def _build_planner_prompt(
        self,
        *,
        task: str,
        memories: list[dict],
        tool_catalog: list[dict],
        previous_error: str | None,
        prior_plan: dict | None,
    ) -> str:
        return (
            "You are a local finance operations planner running inside a budgeting app. "
            "You must create a short multi-step tool plan using the available MCP tools. "
            "Return JSON only with keys: intent, steps, success_criteria. "
            "Each step must contain tool, arguments, reason. "
            "Prefer the minimum number of tools needed, but use read tools first if verification context is needed. "
            "If the user asks to modify data, include the exact write tool.\n\n"
            f"Recent memory:\n{json.dumps(memories)}\n\n"
            f"Available MCP tools:\n{json.dumps(tool_catalog)}\n\n"
            f"Previous plan: {json.dumps(prior_plan or {})}\n"
            f"Previous execution error: {previous_error or 'none'}\n\n"
            f"User task: {task}"
        )

    def _build_verifier_prompt(
        self,
        *,
        task: str,
        plan: dict,
        execution_results: list[dict],
        latest_action_result: dict | None,
    ) -> str:
        return (
            "You are a finance operations verifier. The tool steps have already been executed. "
            "Return JSON only with keys: headline, summary, risk_level, recommended_actions, email_subject, email_draft. "
            "Summarise the completed action clearly for the end user in pounds. Keep risk_level low unless the tool output explicitly shows a problem.\n\n"
            f"User task: {task}\n"
            f"Plan executed: {json.dumps(plan)}\n"
            f"Tool results: {json.dumps(execution_results)}\n"
            f"Latest action result: {json.dumps(latest_action_result or {})}"
        )

    def _invoke(self, prompt: str) -> str:
        if self._llm is None:
            raise ServiceUnavailableError("Local LangChain agent runtime is unavailable because Ollama is not configured.")
        response = self._llm.invoke(prompt)
        content = response.content
        if isinstance(content, list):
            return "\n".join(str(item) for item in content)
        return str(content)

    @staticmethod
    def _parse_json_object(raw_content: str, label: str) -> dict:
        content = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL | re.IGNORECASE).strip()
        fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", content, flags=re.DOTALL)
        if fenced_match:
            content = fenced_match.group(1)
        elif not content.startswith("{"):
            object_match = re.search(r"(\{.*\})", content, flags=re.DOTALL)
            if object_match:
                content = object_match.group(1)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"The agent returned invalid JSON for {label}.") from exc
        if not isinstance(parsed, dict):
            raise ValidationError(f"The agent returned a non-object payload for {label}.")
        return parsed

    @staticmethod
    def _extract_report_url(execution_results: list[dict]) -> str | None:
        for item in reversed(execution_results):
            result = item.get("result") if isinstance(item, dict) else None
            if isinstance(result, dict) and result.get("report_download_url"):
                return result.get("report_download_url")
            if isinstance(result, dict) and result.get("download_url"):
                return result.get("download_url")
        return None

    @staticmethod
    def _utc_now() -> str:
        from datetime import UTC, datetime

        return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
