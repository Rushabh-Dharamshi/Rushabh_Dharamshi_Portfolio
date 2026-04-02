import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from budget_tracker_api.errors import ServiceUnavailableError, ValidationError
from budget_tracker_api.repositories.agent_run_repository import AgentRunRepository
from budget_tracker_api.services.analytics_service import AnalyticsService
from budget_tracker_api.services.agent_memory_service import AgentMemoryService
from budget_tracker_api.services.agentic_command_runtime import AgenticCommandRuntime
from budget_tracker_api.services.expense_service import ExpenseService
from budget_tracker_api.services.fastmcp_client_service import FastMcpClientService
from budget_tracker_api.services.finance_mcp_server import FinanceMcpServer
from budget_tracker_api.services.ollama_client import OllamaClient
from budget_tracker_api.services.prediction_service import PredictionService
from budget_tracker_api.services.recurring_service import RecurringService
from budget_tracker_api.services.report_service import ReportService
from budget_tracker_api.services.settings_service import SettingsService


logger = logging.getLogger(__name__)


class AgentService:
    def __init__(
        self,
        ollama_client: OllamaClient,
        analytics_service: AnalyticsService,
        prediction_service: PredictionService,
        recurring_service: RecurringService,
        report_service: ReportService,
        expense_service: ExpenseService,
        settings_service: SettingsService,
        agent_run_repository: AgentRunRepository,
        agent_memory_service: AgentMemoryService | None = None,
        mcp_tool_adapter: object | None = None,
    ):
        self._ollama_client = ollama_client
        self._analytics_service = analytics_service
        self._prediction_service = prediction_service
        self._recurring_service = recurring_service
        self._report_service = report_service
        self._expense_service = expense_service
        self._settings_service = settings_service
        self._agent_run_repository = agent_run_repository
        self._agent_memory_service = agent_memory_service or AgentMemoryService(None)
        self._automation_service = None
        self._mcp_server = FinanceMcpServer(self._build_mcp_handlers())
        self._mcp_tool_adapter = mcp_tool_adapter or self._mcp_server
        self._agentic_command_runtime = AgenticCommandRuntime(
            model_name=self._ollama_client.model,
            base_url=getattr(self._ollama_client, "base_url", None),
            mcp_server=self._mcp_tool_adapter,
            memory_service=self._agent_memory_service,
        )
        self._fallback_agentic_command_runtime = AgenticCommandRuntime(
            model_name=self._ollama_client.model,
            base_url=getattr(self._ollama_client, "base_url", None),
            mcp_server=self._mcp_server,
            memory_service=self._agent_memory_service,
        )
        self._job_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agent-work")
        self._job_lock = Lock()
        self._finance_briefing_jobs: dict[str, dict] = {}
        self._workflow_jobs: dict[str, dict] = {}

    def attach_automation_service(self, automation_service) -> None:
        self._automation_service = automation_service

    def start_finance_briefing(self, payload: dict | None, app) -> dict:
        request_payload = payload or {}
        task = (request_payload.get("task") or "").strip() or (
            "Prepare a CFO-style monthly briefing, include cash-flow risk, upcoming recurring costs, "
            "and draft an email summary for the user."
        )
        job_id = uuid4().hex
        created_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        job = {
            "id": job_id,
            "status": "queued",
            "task": task,
            "created_at": created_at,
            "started_at": None,
            "completed_at": None,
            "error": None,
            "result": None,
        }
        with self._job_lock:
            self._finance_briefing_jobs[job_id] = job

        self._job_executor.submit(self._run_finance_briefing_job, job_id, request_payload, app)
        return dict(job)

    def get_finance_briefing_job(self, job_id: str) -> dict:
        with self._job_lock:
            job = self._finance_briefing_jobs.get(job_id)
            if job is None:
                raise ValidationError(f"Unknown finance briefing run '{job_id}'.")
            return dict(job)

    def start_workflow_run(
        self,
        workflow_name: str,
        payload: dict | None,
        app,
        *,
        reuse_active: bool = False,
    ) -> dict:
        workflow = self._workflow_catalog().get(workflow_name)
        if workflow is None:
            raise ValidationError(f"Unknown workflow '{workflow_name}'.")

        request_payload = payload or {}
        task = (request_payload.get("task") or "").strip() or workflow["default_task"]
        if reuse_active:
            active_job = self._find_active_workflow_job(workflow_name)
            if active_job is not None:
                return active_job
        job_id = uuid4().hex
        created_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        job = {
            "id": job_id,
            "status": "queued",
            "workflow_name": workflow_name,
            "task": task,
            "created_at": created_at,
            "started_at": None,
            "completed_at": None,
            "error": None,
            "result": None,
        }
        with self._job_lock:
            self._workflow_jobs[job_id] = job

        self._job_executor.submit(self._run_workflow_job, job_id, workflow_name, request_payload, app)
        return dict(job)

    def get_workflow_job(self, job_id: str) -> dict:
        with self._job_lock:
            job = self._workflow_jobs.get(job_id)
            if job is None:
                raise ValidationError(f"Unknown workflow run '{job_id}'.")
            return dict(job)

    def _find_active_workflow_job(self, workflow_name: str) -> dict | None:
        with self._job_lock:
            active_jobs = [
                dict(job)
                for job in self._workflow_jobs.values()
                if job.get("workflow_name") == workflow_name
                and job.get("status") in {"queued", "running"}
            ]
        if not active_jobs:
            return None
        active_jobs.sort(
            key=lambda item: (
                str(item.get("created_at") or ""),
                str(item.get("started_at") or ""),
                str(item.get("id") or ""),
            ),
            reverse=True,
        )
        return active_jobs[0]

    def list_workflows(self) -> list[dict]:
        return list(self._workflow_catalog().values())

    def list_runs(self, limit: int = 8) -> list[dict]:
        return self._agent_run_repository.list_runs(max(1, min(int(limit), 20)))

    def run_workflow(self, workflow_name: str, payload: dict | None = None) -> dict:
        workflow = self._workflow_catalog().get(workflow_name)
        if workflow is None:
            raise ValidationError(f"Unknown workflow '{workflow_name}'.")

        request_payload = payload or {}
        task = (request_payload.get("task") or "").strip() or workflow["default_task"]
        result = self._run_workflow_with_langgraph(workflow_name, workflow, task)
        return self._agent_run_repository.create_run(result)

    def run_finance_briefing(self, payload: dict | None = None) -> dict:
        request_payload = payload or {}
        task = (request_payload.get("task") or "").strip() or (
            "Prepare a CFO-style monthly briefing, include cash-flow risk, upcoming recurring costs, "
            "and draft an email summary for the user."
        )

        if self._looks_like_manual_action_command(task):
            return self._run_manual_action_command(task)

        if self._should_use_context_prompt():
            fallback_result = self._run_context_prompt(task)
            return {
                **fallback_result,
                "task": task,
                "model": self._ollama_client.model,
                "tools_used": fallback_result["tools_used"],
                "report_download_url": fallback_result["report_download_url"],
                "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            }

        messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    "You are a finance operations agent for a budget tracker application. "
                    "Use tools to inspect the user's finances before answering. "
                    "All money is in pounds sterling (GBP). Never use dollars or the $ symbol. "
                    "Return your final answer strictly as JSON with keys: "
                    "headline, summary, risk_level, recommended_actions, email_subject, email_draft."
                ),
            },
            {"role": "user", "content": task},
        ]
        tools = self._tool_definitions()
        tools_used: list[str] = []
        report_download_url: str | None = None
        used_tool_calling = False

        for _ in range(5):
            response = self._ollama_client.chat(messages, tools=tools)
            message = response.get("message") or {}
            assistant_message = {
                "role": message.get("role", "assistant"),
                "content": message.get("content", ""),
            }
            if message.get("tool_calls"):
                assistant_message["tool_calls"] = message["tool_calls"]
            messages.append(assistant_message)

            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                if not used_tool_calling:
                    fallback_result = self._run_context_prompt(task)
                    return {
                        **fallback_result,
                        "task": task,
                        "model": self._ollama_client.model,
                        "tools_used": fallback_result["tools_used"],
                        "report_download_url": fallback_result["report_download_url"],
                        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
                    }
                final_payload = self._parse_final_payload(message.get("content", ""))
                return {
                    **final_payload,
                    "task": task,
                    "model": self._ollama_client.model,
                    "tools_used": tools_used,
                    "report_download_url": report_download_url,
                    "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
                }

            used_tool_calling = True
            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                tool_name = function.get("name", "")
                raw_arguments = function.get("arguments", {})
                arguments = raw_arguments if isinstance(raw_arguments, dict) else {}
                tools_used.append(tool_name)
                tool_result = self._execute_tool(tool_name, arguments)
                if tool_name == "generate_monthly_report" and tool_result.get("available"):
                    report_download_url = tool_result.get("download_url")
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": json.dumps(tool_result),
                    }
                )

        raise ServiceUnavailableError(
            "The Ollama agent did not produce a final briefing in time."
        )

    def _run_finance_briefing_job(self, job_id: str, payload: dict, app) -> None:
        started_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        with self._job_lock:
            if job_id in self._finance_briefing_jobs:
                self._finance_briefing_jobs[job_id]["status"] = "running"
                self._finance_briefing_jobs[job_id]["started_at"] = started_at

        try:
            with app.app_context():
                result = self.run_finance_briefing(payload)
        except Exception as exc:
            logger.exception("Finance briefing background job failed | job_id=%s", job_id)
            completed_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
            with self._job_lock:
                if job_id in self._finance_briefing_jobs:
                    self._finance_briefing_jobs[job_id]["status"] = "failed"
                    self._finance_briefing_jobs[job_id]["completed_at"] = completed_at
                    self._finance_briefing_jobs[job_id]["error"] = (
                        exc.message if isinstance(exc, (ServiceUnavailableError, ValidationError)) else str(exc)
                    )
            return

        completed_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        with self._job_lock:
            if job_id in self._finance_briefing_jobs:
                self._finance_briefing_jobs[job_id]["status"] = "completed"
                self._finance_briefing_jobs[job_id]["completed_at"] = completed_at
                self._finance_briefing_jobs[job_id]["result"] = result

    def _run_workflow_job(self, job_id: str, workflow_name: str, payload: dict, app) -> None:
        started_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        with self._job_lock:
            if job_id in self._workflow_jobs:
                self._workflow_jobs[job_id]["status"] = "running"
                self._workflow_jobs[job_id]["started_at"] = started_at

        try:
            with app.app_context():
                result = self.run_workflow(workflow_name, payload)
        except Exception as exc:
            logger.exception("Workflow background job failed | job_id=%s workflow_name=%s", job_id, workflow_name)
            completed_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
            with self._job_lock:
                if job_id in self._workflow_jobs:
                    self._workflow_jobs[job_id]["status"] = "failed"
                    self._workflow_jobs[job_id]["completed_at"] = completed_at
                    self._workflow_jobs[job_id]["error"] = (
                        exc.message if isinstance(exc, (ServiceUnavailableError, ValidationError)) else str(exc)
                    )
            return

        completed_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        with self._job_lock:
            if job_id in self._workflow_jobs:
                self._workflow_jobs[job_id]["status"] = "completed"
                self._workflow_jobs[job_id]["completed_at"] = completed_at
                self._workflow_jobs[job_id]["result"] = result
    def _run_context_prompt(self, task: str) -> dict:
        dashboard = self._execute_tool("get_dashboard_summary", {})
        financial_pulse = self._execute_tool("get_financial_pulse", {})
        category_insights = self._execute_tool("get_category_insights", {})
        prediction = self._execute_tool("get_spending_prediction", {})
        recent_transactions = self._execute_tool("get_recent_transactions", {"limit": 5})
        upcoming_items = self._execute_tool("get_upcoming_recurring_items", {"days": 14})

        compact_payload = {
            "dashboard": {
                "month_label": dashboard.get("month_label"),
                "monthly_budget": dashboard.get("monthly_budget"),
                "monthly_income": dashboard.get("monthly_income"),
                "monthly_expenses": dashboard.get("monthly_expenses"),
                "net_cash_flow": dashboard.get("net_cash_flow"),
                "remaining_budget": dashboard.get("remaining_budget"),
                "status": dashboard.get("status"),
            },
            "financial_pulse": {
                "health_score": financial_pulse.get("health_score"),
                "spend_velocity": financial_pulse.get("spend_velocity"),
                "runway_days": financial_pulse.get("runway_days"),
                "cash_in": financial_pulse.get("cash_in"),
                "cash_out": financial_pulse.get("cash_out"),
                "income_coverage": financial_pulse.get("income_coverage"),
                "narrative": financial_pulse.get("narrative"),
            },
            "category_insights": {
                "top_categories": category_insights.get("top_categories", [])[:3],
                "bottom_categories": category_insights.get("bottom_categories", [])[:3],
                "total_spending": category_insights.get("total_spending"),
            },
            "prediction": prediction,
            "recent_transactions": recent_transactions.get("transactions", [])[:5],
            "upcoming_recurring_items": {
                "window_start": upcoming_items.get("window_start"),
                "window_end": upcoming_items.get("window_end"),
                "occurrence_count": len(upcoming_items.get("occurrences", [])),
                "next_occurrences": upcoming_items.get("occurrences", [])[:5],
            },
        }

        tools_used = [
            "dashboard",
            "financial_pulse",
            "category_insights",
            "prediction",
            "recent_transactions",
            "upcoming_recurring_items",
        ]
        report_download_url = None
        normalized_task = task.lower()
        if "report" in normalized_task or "pdf" in normalized_task:
            report_result = self._execute_tool("generate_monthly_report", {})
            compact_payload["report"] = report_result
            report_download_url = report_result.get("download_url")
            tools_used.append("report")

        response = self._ollama_client.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a finance analyst. Use the supplied finance context and return JSON only "
                        "with keys: headline, summary, risk_level, recommended_actions, email_subject, email_draft. "
                        "All money is in pounds sterling (GBP). Never use dollars or the $ symbol. "
                        "Keep the summary concise and action-oriented."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Task: {task}\n\nFinance context:\n{json.dumps(compact_payload)}",
                },
            ]
        )
        final_payload = self._parse_final_payload(
            (response.get("message") or {}).get("content", "")
        )
        return {
            **final_payload,
            "tools_used": tools_used,
            "report_download_url": report_download_url,
        }

    def _run_workflow_with_langgraph(self, workflow_name: str, workflow: dict, task: str) -> dict:
        class WorkflowState(TypedDict, total=False):
            task: str
            workflow_name: str
            workflow: dict
            workflow_context: dict
            automated_actions: list[str]
            tools_used: list[str]
            report_download_url: str | None
            result: dict

        graph = StateGraph(WorkflowState)

        for index, step in enumerate(workflow["steps"]):
            node_name = f"step_{index}_{step['tool']}"

            def make_step_node(current_step: dict):
                def step_node(state: WorkflowState):
                    tool_name = current_step["tool"]
                    result = self._execute_tool(tool_name, current_step.get("arguments", {}))
                    workflow_context = dict(state.get("workflow_context", {}))
                    workflow_context[tool_name] = result
                    tools_used = [*state.get("tools_used", []), tool_name]
                    automated_actions = [*state.get("automated_actions", []), current_step["action"]]
                    next_state: WorkflowState = {
                        "workflow_context": workflow_context,
                        "tools_used": tools_used,
                        "automated_actions": automated_actions,
                    }
                    if tool_name == "generate_monthly_report" and result.get("available"):
                        next_state["report_download_url"] = result.get("download_url")
                    return next_state

                return step_node

            graph.add_node(node_name, make_step_node(step))

        def final_node(state: WorkflowState):
            return {
                "result": self._run_workflow_prompt(
                    workflow=state["workflow"],
                    workflow_name=state["workflow_name"],
                    task=state["task"],
                    workflow_context=state.get("workflow_context", {}),
                    automated_actions=state.get("automated_actions", []),
                    tools_used=state.get("tools_used", []),
                    report_download_url=state.get("report_download_url"),
                )
            }

        graph.add_node("finalise", final_node)

        first_node = f"step_0_{workflow['steps'][0]['tool']}"
        graph.add_edge(START, first_node)
        for index, step in enumerate(workflow["steps"]):
            current_node = f"step_{index}_{step['tool']}"
            if index == len(workflow["steps"]) - 1:
                graph.add_edge(current_node, "finalise")
            else:
                next_step = workflow["steps"][index + 1]
                graph.add_edge(current_node, f"step_{index + 1}_{next_step['tool']}")
        graph.add_edge("finalise", END)

        compiled = graph.compile()
        result_state = compiled.invoke(
            {
                "task": task,
                "workflow_name": workflow_name,
                "workflow": workflow,
                "workflow_context": {},
                "automated_actions": [],
                "tools_used": [],
                "report_download_url": None,
            }
        )
        return result_state["result"]

    def _run_workflow_prompt(
        self,
        workflow: dict,
        workflow_name: str,
        task: str,
        workflow_context: dict,
        automated_actions: list[str],
        tools_used: list[str],
        report_download_url: str | None,
    ) -> dict:
        response = self._ollama_client.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a finance operations automation agent. You receive workflow context that has already "
                        "been gathered by backend tools. Return JSON only with keys: headline, summary, risk_level, "
                        "recommended_actions, email_subject, email_draft. All money is in pounds sterling (GBP). Never use dollars or the $ symbol."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Workflow: {workflow['label']}\n"
                        f"Automation focus: {workflow['automation_focus']}\n"
                        f"Task: {task}\n"
                        f"Automated actions already completed: {json.dumps(automated_actions)}\n\n"
                        f"Workflow context:\n{json.dumps(workflow_context)}"
                    ),
                },
            ]
        )
        final_payload = self._parse_final_payload(
            (response.get("message") or {}).get("content", "")
        )
        return {
            **final_payload,
            "workflow_name": workflow_name,
            "workflow_label": workflow["label"],
            "status": "completed",
            "automated_actions": automated_actions,
            "task": task,
            "model": self._ollama_client.model,
            "tools_used": tools_used,
            "report_download_url": report_download_url,
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }

    def _run_workflow_steps(self, workflow: dict) -> tuple[dict, list[str], list[str], str | None]:
        workflow_context: dict[str, dict] = {}
        automated_actions: list[str] = []
        tools_used: list[str] = []
        report_download_url: str | None = None

        for step in workflow["steps"]:
            tool_name = step["tool"]
            arguments = step.get("arguments", {})
            result = self._execute_tool(tool_name, arguments)
            workflow_context[tool_name] = result
            tools_used.append(tool_name)
            automated_actions.append(step["action"])
            if tool_name == "generate_monthly_report" and result.get("available"):
                report_download_url = result.get("download_url")

        return workflow_context, automated_actions, tools_used, report_download_url

    def _run_manual_action_command(self, task: str) -> dict:
        if self._agentic_command_runtime.is_available():
            try:
                return self._agentic_command_runtime.run(task)
            except Exception as exc:
                logger.warning("Primary MCP agent runtime failed; trying in-process fallback | task=%s error=%s", task[:120], exc)
                try:
                    return self._fallback_agentic_command_runtime.run(task)
                except Exception as fallback_exc:
                    logger.warning("Fallback agent runtime failed; falling back to legacy parser | task=%s error=%s", task[:120], fallback_exc)

        return self._run_manual_action_command_legacy(task)

    def _run_manual_action_command_legacy(self, task: str) -> dict:
        parsed = self._parse_manual_action_command(task)
        domain = parsed["domain"]

        if domain == "settings":
            return self._run_settings_command(task, parsed)
        if domain == "expense":
            return self._run_expense_command(task, parsed)
        if domain == "recurring":
            return self._run_reminder_command(task, parsed)

        raise ValidationError("The AI agent could not map that request to a supported action.")

    def _build_mcp_handlers(self) -> dict[str, callable]:
        return {
            "get_dashboard_summary": lambda arguments: self._execute_tool("get_dashboard_summary", arguments),
            "get_financial_pulse": lambda arguments: self._execute_tool("get_financial_pulse", arguments),
            "get_category_insights": lambda arguments: self._execute_tool("get_category_insights", arguments),
            "get_spending_prediction": lambda arguments: self._execute_tool("get_spending_prediction", arguments),
            "get_recent_transactions": lambda arguments: self._execute_tool("get_recent_transactions", arguments),
            "list_recurring_reminders": self._mcp_list_recurring_reminders,
            "get_upcoming_recurring_items": lambda arguments: self._execute_tool("get_upcoming_recurring_items", arguments),
            "set_monthly_budget": self._mcp_set_monthly_budget,
            "set_monthly_income": self._mcp_set_monthly_income,
            "create_transaction": self._mcp_create_transaction,
            "update_transaction_by_match": self._mcp_update_transaction_by_match,
            "delete_transaction_by_match": self._mcp_delete_transaction_by_match,
            "create_recurring_reminder": self._mcp_create_recurring_reminder,
            "update_recurring_reminder_by_match": self._mcp_update_recurring_reminder_by_match,
            "delete_recurring_reminder_by_match": self._mcp_delete_recurring_reminder_by_match,
            "replace_recurring_reminder": self._mcp_replace_recurring_reminder,
            "generate_monthly_report": lambda arguments: self._execute_tool("generate_monthly_report", arguments),
            "send_upcoming_bills_email_now": self._mcp_send_upcoming_bills_email_now,
            "send_month_end_email_now": self._mcp_send_month_end_email_now,
        }

    def _mcp_list_recurring_reminders(self, arguments: dict) -> dict:
        list_items = getattr(self._recurring_service, "list_items", None)
        items = list_items() if callable(list_items) else []
        return {"items": items}

    def _mcp_set_monthly_budget(self, arguments: dict) -> dict:
        return self._run_settings_command(
            "MCP tool: update monthly budget",
            {"setting_key": "monthly_budget", "value": arguments.get("monthly_budget")},
        )

    def _mcp_set_monthly_income(self, arguments: dict) -> dict:
        return self._run_settings_command(
            "MCP tool: update monthly income",
            {"setting_key": "monthly_income", "value": arguments.get("monthly_income"), "month": arguments.get("month")},
        )

    def _mcp_create_transaction(self, arguments: dict) -> dict:
        return self._run_expense_command(
            "MCP tool: create transaction",
            {"operation": "create", "entity": arguments, "target": {}},
        )

    def _mcp_update_transaction_by_match(self, arguments: dict) -> dict:
        return self._run_expense_command(
            "MCP tool: update transaction",
            {"operation": "update", "entity": arguments.get("entity") or {}, "target": arguments.get("target") or {}},
        )

    def _mcp_delete_transaction_by_match(self, arguments: dict) -> dict:
        return self._run_expense_command(
            "MCP tool: delete transaction",
            {"operation": "delete", "entity": {}, "target": arguments.get("target") or {}},
        )

    def _mcp_create_recurring_reminder(self, arguments: dict) -> dict:
        return self._run_reminder_command(
            "MCP tool: create recurring reminder",
            {"operation": "create", "target": {}, "reminder": self._parse_reminder_payload(arguments, datetime.now().strftime("%Y-%m-%d"))},
        )

    def _mcp_update_recurring_reminder_by_match(self, arguments: dict) -> dict:
        return self._run_reminder_command(
            "MCP tool: update recurring reminder",
            {
                "operation": "update",
                "target": arguments.get("target") or {},
                "reminder": self._parse_reminder_payload(arguments.get("reminder") or {}, datetime.now().strftime("%Y-%m-%d")),
            },
        )

    def _mcp_delete_recurring_reminder_by_match(self, arguments: dict) -> dict:
        return self._run_reminder_command(
            "MCP tool: delete recurring reminder",
            {"operation": "delete", "target": arguments.get("target") or {}, "reminder": None},
        )

    def _mcp_replace_recurring_reminder(self, arguments: dict) -> dict:
        return self._run_reminder_command(
            "MCP tool: replace recurring reminder",
            {
                "operation": "replace",
                "target": arguments.get("target") or {},
                "reminder": self._parse_reminder_payload(arguments.get("reminder") or {}, datetime.now().strftime("%Y-%m-%d")),
            },
        )

    def _mcp_send_upcoming_bills_email_now(self, arguments: dict) -> dict:
        if self._automation_service is None:
            raise ValidationError("Automation service is not attached to the agent runtime.")
        result = self._automation_service.run_upcoming_bills_email_now()
        result["report_download_url"] = result.get("report_download_url")
        result["action_result"] = {
            "type": "upcoming_bills_email_sent",
            "message": result["summary"],
            "payload": result,
        }
        return result

    def _mcp_send_month_end_email_now(self, arguments: dict) -> dict:
        if self._automation_service is None:
            raise ValidationError("Automation service is not attached to the agent runtime.")
        result = self._automation_service.run_month_end_email_now()
        result["report_download_url"] = result.get("report_download_url")
        result["action_result"] = {
            "type": "month_end_email_sent",
            "message": result["summary"],
            "payload": result,
        }
        return result

    def _run_settings_command(self, task: str, parsed: dict) -> dict:
        setting_key = parsed.get("setting_key")
        value = parsed.get("value")
        if setting_key == "monthly_budget":
            result = self._settings_service.update_monthly_budget({"monthly_budget": value})
            return self._build_action_response(
                headline="Monthly budget updated",
                summary=f"Monthly budget is now GBP {float(result['monthly_budget']):.2f}.",
                email_subject="Monthly budget updated",
                email_draft=f"Monthly budget updated to GBP {float(result['monthly_budget']):.2f}.",
                task=task,
                action_type="monthly_budget_updated",
                action_message="Monthly budget updated successfully.",
                payload={"monthly_budget": float(result["monthly_budget"]), "monthly_income": self._settings_service.get_monthly_income()},
            )
        if setting_key == "monthly_income":
            month = parsed.get("month")
            result = self._settings_service.update_monthly_income({"monthly_income": value, "month": month})
            income_month = result.get("income_month")
            return self._build_action_response(
                headline="Monthly income updated",
                summary=f"Monthly income for {income_month} is now GBP {float(result['monthly_income']):.2f}.",
                email_subject="Monthly income updated",
                email_draft=f"Monthly income for {income_month} was updated to GBP {float(result['monthly_income']):.2f}.",
                task=task,
                action_type="monthly_income_updated",
                action_message="Monthly income updated successfully.",
                payload={"monthly_income": float(result["monthly_income"]), "income_month": income_month, "monthly_budget": self._settings_service.get_monthly_budget()},
            )
        raise ValidationError("The settings command must target monthly budget or monthly income.")

    def _run_expense_command(self, task: str, parsed: dict) -> dict:
        operation = parsed.get("operation") or "create"
        entity = parsed.get("entity") or {}
        target = parsed.get("target") or {}

        if operation == "create":
            created = self._expense_service.create_expense(entity)
            return self._build_action_response(
                headline="Transaction created",
                summary=f"Created {created['entry_type']} transaction '{created['description']}' for GBP {float(created['amount']):.2f} on {created['date']}.",
                email_subject="Transaction created",
                email_draft=f"Created transaction {created['description']} for GBP {float(created['amount']):.2f}.",
                task=task,
                action_type="expense_created",
                action_message="Transaction created successfully.",
                payload=created,
            )

        if operation == "delete":
            deleted_count, deleted_item = self._delete_matching_expenses(target)
            return self._build_action_response(
                headline="Transaction deleted",
                summary=f"Deleted {deleted_count} transaction(s) matching {deleted_item['description']}.",
                email_subject="Transaction deleted",
                email_draft=f"Deleted transaction {deleted_item['description']}.",
                task=task,
                action_type="expense_deleted",
                action_message=f"Deleted {deleted_count} matching transaction(s).",
                payload=deleted_item,
            )

        updated = self._update_matching_expense(target, entity)
        return self._build_action_response(
            headline="Transaction updated",
            summary=f"Updated transaction '{updated['description']}' to GBP {float(updated['amount']):.2f} on {updated['date']}.",
            email_subject="Transaction updated",
            email_draft=f"Updated transaction {updated['description']} to GBP {float(updated['amount']):.2f}.",
            task=task,
            action_type="expense_updated",
            action_message="Transaction updated successfully.",
            payload=updated,
        )

    def _build_action_response(
        self,
        headline: str,
        summary: str,
        email_subject: str,
        email_draft: str,
        task: str,
        action_type: str,
        action_message: str,
        payload: dict,
    ) -> dict:
        return {
            "headline": headline,
            "summary": summary,
            "risk_level": "low",
            "recommended_actions": [
                "Review the updated dashboard values.",
                "Confirm the change in the relevant table or planner view.",
            ],
            "email_subject": email_subject,
            "email_draft": email_draft,
            "task": task,
            "model": self._ollama_client.model,
            "tools_used": [action_type],
            "report_download_url": None,
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "action_result": {
                "type": action_type,
                "message": action_message,
                "payload": payload,
            },
        }

    def _parse_manual_action_command(self, task: str) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        response = self._ollama_client.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a finance app command router. Return JSON only. "
                        "Supported domains: settings, expense, recurring. "
                        "Supported operations: create, update, delete, replace. "
                        "For settings commands, return domain=settings, operation=update, setting_key=monthly_budget or monthly_income, numeric value, and optional month in YYYY-MM when the user names a month. "
                        "For expense commands, return domain=expense, operation=create/update/delete, an entity object for the target transaction data, and an optional target object describing which existing transaction to update/delete. "
                        "Expense entity keys: date, category, description, amount, entry_type. Use entry_type expense unless income is explicit. "
                        "For recurring reminder commands, return domain=recurring and the same recurring schema as before: operation plus reminder and/or target objects. "
                        "All money is in pounds sterling (GBP). Never use dollars or the $ symbol. "
                        "Understand prompts like: set my monthly budget to 1600 pounds; set my monthly income for 2026-04 to 2400 pounds; add an expense for Tube fare of 6.40 pounds today under travel; remove weekly utility bills and replace them with monthly utility bills of 24.51 pounds on the 23rd of each month. "
                        f"Today's date is {today}. Use YYYY-MM-DD dates for transactions and YYYY-MM for month-specific income updates."
                    ),
                },
                {"role": "user", "content": task},
            ]
        )
        try:
            parsed = json.loads((response.get("message") or {}).get("content", ""))
        except json.JSONDecodeError as exc:
            raise ValidationError("The AI agent could not understand the requested action.") from exc

        normalized_task = task.lower()
        domain = str(parsed.get("domain") or "").strip().lower()
        operation = str(parsed.get("operation") or "create").strip().lower()
        if any(word in normalized_task for word in ("reminder", "recurring", "bill", "bills", "subscription", "cost", "costs")) and any(word in normalized_task for word in ("replace", "remove", "delete", "update", "change", "add", "create", "set up")):
            domain = "recurring"
        elif domain not in {"settings", "expense", "recurring"}:
            if any(word in normalized_task for word in ("budget", "income")):
                domain = "settings"
            elif any(word in normalized_task for word in ("reminder", "recurring", "bill", "bills", "subscription", "cost", "costs")):
                domain = "recurring"
            elif any(word in normalized_task for word in ("transaction", "expense", "income")):
                domain = "expense"
            else:
                raise ValidationError("The AI agent could not map that request to settings, transactions, or recurring reminders.")
        if operation not in {"create", "update", "delete", "replace"}:
            operation = "create"

        reminder = parsed.get("reminder")
        if domain == "recurring" and reminder is None:
            lifted = {
                key: parsed.get(key)
                for key in ("category", "description", "amount", "entry_type", "frequency", "start_date", "end_date", "active")
                if key in parsed
            }
            reminder = lifted or None

        target = parsed.get("target") or {}
        if domain == "recurring" and operation in {"replace", "delete", "update"} and not target:
            target = self._infer_recurring_target_from_task(task, reminder)

        result = {
            "domain": domain,
            "operation": operation,
            "setting_key": str(parsed.get("setting_key") or "").strip().lower(),
            "value": parsed.get("value"),
            "target": target,
            "entity": parsed.get("entity") or {},
            "reminder": reminder,
        }
        return result

    @staticmethod
    def _infer_recurring_target_from_task(task: str, reminder: dict | None) -> dict:
        normalized_task = task.lower()
        target: dict = {}
        if reminder:
            if reminder.get("description"):
                target["description"] = reminder["description"]
            if reminder.get("category"):
                target["category"] = reminder["category"]
            if reminder.get("entry_type"):
                target["entry_type"] = reminder["entry_type"]

        old_phrase = ""
        replace_match = re.search(
            r"(?:replace|remove|delete)\s+(?P<old>.+?)(?:\s+(?:with|and\s+replace\s+with)\s+|$)",
            normalized_task,
        )
        if replace_match:
            old_phrase = replace_match.group("old").strip(" .")

        if old_phrase:
            if "weekly" in old_phrase:
                target["frequency"] = "weekly"
            elif "monthly" in old_phrase:
                target["frequency"] = "monthly"
            elif "yearly" in old_phrase or "annual" in old_phrase:
                target["frequency"] = "yearly"
            elif "daily" in old_phrase:
                target["frequency"] = "daily"
        elif "weekly" in normalized_task:
            target["frequency"] = "weekly"
        elif reminder and reminder.get("frequency"):
            target["frequency"] = reminder["frequency"]

        cleaned_old_phrase = re.sub(
            r"\b(replace|remove|delete|weekly|monthly|daily|yearly|annual|recurring|reminder|bill|bills|cost|costs|subscription|the|a|an)\b",
            " ",
            old_phrase,
        )
        cleaned_old_phrase = re.sub(r"\s+", " ", cleaned_old_phrase).strip(" .")
        if cleaned_old_phrase and not target.get("description"):
            target["description"] = cleaned_old_phrase.title()

        if not target.get("category"):
            category_by_keyword = {
                "utility": "Utilities",
                "utilities": "Utilities",
                "rent": "Housing",
                "mortgage": "Housing",
                "train": "Transportation",
                "travel": "Transportation",
                "subscription": "Subscriptions",
                "gym": "Health",
            }
            for keyword, category in category_by_keyword.items():
                if keyword in (old_phrase or normalized_task):
                    target["category"] = category
                    break

        if any(word in (old_phrase or normalized_task) for word in ("bill", "bills", "cost", "costs", "rent", "mortgage", "utility", "utilities", "subscription")):
            target.setdefault("entry_type", "expense")

        return target
    def _run_reminder_command(self, task: str, parsed: dict | None = None) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        if parsed is None:
            response = self._ollama_client.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are a finance automation agent for recurring reminders. "
                            "Extract the user's intent and return JSON only. "
                            "Use operation=create, update, delete, or replace. "
                            "For create/update/replace, include a reminder object with keys: category, description, amount, entry_type, frequency, start_date, end_date, active. "
                            "For delete/replace, include a target object with any known keys from: category, description, amount, entry_type, frequency, start_date, end_date. "
                            "Use entry_type expense unless the user explicitly asks for income. "
                            "The start_date is the exact first due date and is always inclusive. "
                            "If the user gives a bounded range, include end_date as the final included due date unless they explicitly say the end is exclusive. "
                            "If no start date is given for a new reminder, use today's date. "
                            f"Today's date is {today}."
                        ),
                    },
                    {"role": "user", "content": task},
                ]
            )
            parsed = self._parse_recurring_command_payload((response.get("message") or {}).get("content", ""), today)
        reminder_payload = parsed.get("reminder")
        if reminder_payload is not None:
            reminder_payload = self._apply_reminder_schedule_from_task(task, reminder_payload, today)

        operation = parsed["operation"]
        if operation == "delete":
            deleted_count, deleted_item = self._delete_matching_reminders(parsed.get("target") or {})
            return self._build_recurring_command_response(
                headline="Recurring reminder deleted",
                summary=f"Removed {deleted_count} recurring reminder(s) matching {deleted_item['description']}.",
                email_subject="Recurring reminder deleted",
                email_draft=f"Recurring reminder deleted for {deleted_item['description']}.",
                task=task,
                action_type="recurring_item_deleted",
                action_message=f"Deleted {deleted_count} matching recurring reminder(s).",
                recurring_item=deleted_item,
            )

        if operation == "replace":
            replacement = reminder_payload or {}
            replaced, deleted_count = self._replace_matching_reminders(parsed.get("target") or {}, replacement)
            return self._build_recurring_command_response(
                headline="Recurring reminder replaced",
                summary=f"Replaced {deleted_count} recurring reminder(s) with {replaced['description']} starting {replaced['start_date']}.",
                email_subject="Recurring reminder replaced",
                email_draft=f"Recurring reminder updated to {replaced['description']} at GBP {replaced['amount']:.2f}.",
                task=task,
                action_type="recurring_item_replaced",
                action_message=f"Replaced {deleted_count} matching recurring reminder(s).",
                recurring_item=replaced,
            )

        if operation == "update" and parsed.get("target"):
            updated = self._update_matching_reminder(parsed.get("target") or {}, reminder_payload or {})
            return self._build_recurring_command_response(
                headline="Recurring reminder updated",
                summary=f"{updated['description']} is now scheduled as a {updated['frequency']} {updated['entry_type']} reminder starting {updated['start_date']}.",
                email_subject="Recurring reminder updated",
                email_draft=f"Recurring reminder updated for {updated['description']} at GBP {updated['amount']:.2f}.",
                task=task,
                action_type="recurring_item_updated",
                action_message="The existing recurring reminder was updated automatically.",
                recurring_item=updated,
            )

        created, action_type, action_message = self._upsert_matching_reminder(reminder_payload or {})
        return self._build_recurring_command_response(
            headline="Recurring reminder updated" if action_type == "recurring_item_updated" else "Recurring reminder created",
            summary=f"{created['description']} is now scheduled as a {created['frequency']} {created['entry_type']} reminder starting {created['start_date']}.",
            email_subject="Recurring reminder updated" if action_type == "recurring_item_updated" else "Recurring reminder created",
            email_draft=f"A recurring reminder has been saved for {created['description']} at GBP {created['amount']:.2f}.",
            task=task,
            action_type=action_type,
            action_message=action_message,
            recurring_item=created,
        )

    def _build_recurring_command_response(
        self,
        headline: str,
        summary: str,
        email_subject: str,
        email_draft: str,
        task: str,
        action_type: str,
        action_message: str,
        recurring_item: dict,
    ) -> dict:
        return {
            "headline": headline,
            "summary": summary,
            "risk_level": "low",
            "recommended_actions": [
                "Review the recurring planner calendar to confirm the next due date.",
                "Mark each occurrence as paid once the bill is cleared.",
            ],
            "email_subject": email_subject,
            "email_draft": email_draft,
            "task": task,
            "model": self._ollama_client.model,
            "tools_used": [action_type],
            "report_download_url": None,
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "action_result": {
                "type": action_type,
                "message": action_message,
                "recurring_item": recurring_item,
            },
        }

    def _parse_recurring_command_payload(self, content: str, fallback_date: str) -> dict:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValidationError("The AI agent could not understand the recurring command.") from exc

        operation = str(parsed.get("operation") or "create").strip().lower()
        if operation not in {"create", "update", "delete", "replace"}:
            operation = "create"

        reminder = parsed.get("reminder")
        if reminder is None and operation in {"create", "update", "replace"}:
            reminder = {
                key: parsed.get(key)
                for key in ("category", "description", "amount", "entry_type", "frequency", "start_date", "end_date", "active")
                if key in parsed
            }

        normalized_reminder = None
        if reminder is not None:
            normalized_reminder = self._parse_reminder_payload(reminder, fallback_date)

        target = parsed.get("target") or {}
        normalized_target = {
            "category": str(target.get("category") or "").strip(),
            "description": str(target.get("description") or "").strip(),
            "entry_type": str(target.get("entry_type") or "").strip().lower(),
            "frequency": str(target.get("frequency") or "").strip().lower(),
            "start_date": str(target.get("start_date") or "").strip(),
            "end_date": str(target.get("end_date") or "").strip(),
        }
        if target.get("amount") not in (None, ""):
            normalized_target["amount"] = round(float(target.get("amount")), 2)

        return {
            "operation": operation,
            "target": normalized_target,
            "reminder": normalized_reminder,
        }

    def _find_matching_reminders(self, criteria: dict) -> list[dict]:
        list_items = getattr(self._recurring_service, "list_items", None)
        existing_items = list_items() if callable(list_items) else []
        normalized_description = self._normalize_text_match(criteria.get("description", ""))
        normalized_category = self._normalize_text_match(criteria.get("category", ""))
        normalized_entry_type = criteria.get("entry_type", "").strip().lower()
        normalized_frequency = criteria.get("frequency", "").strip().lower()
        normalized_start_date = criteria.get("start_date", "").strip()
        normalized_amount = criteria.get("amount")

        matches = []
        for item in existing_items:
            item_description = self._normalize_text_match(item["description"])
            item_category = self._normalize_text_match(item["category"])
            if normalized_description and normalized_description not in item_description and item_description not in normalized_description:
                continue
            if normalized_category and normalized_category not in item_category and item_category not in normalized_category:
                continue
            if normalized_entry_type and normalized_entry_type != item["entry_type"]:
                continue
            if normalized_frequency and normalized_frequency != item["frequency"]:
                continue
            if normalized_start_date and normalized_start_date != item["start_date"]:
                continue
            if normalized_amount not in (None, "") and abs(float(item["amount"]) - float(normalized_amount)) >= 0.01:
                continue
            matches.append(item)
        return matches

    @staticmethod
    def _normalize_text_match(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized
    def _delete_matching_reminders(self, criteria: dict) -> tuple[int, dict]:
        matches = self._find_matching_reminders(criteria)
        if not matches:
            raise ValidationError("No matching recurring reminder was found to delete.")
        for item in matches:
            self._recurring_service.delete_item(item["id"])
        return len(matches), matches[0]

    def _replace_matching_reminders(self, criteria: dict, replacement_payload: dict) -> tuple[dict, int]:
        matches = self._find_matching_reminders(criteria)
        if not matches:
            raise ValidationError("No matching recurring reminder was found to replace.")
        for item in matches:
            self._recurring_service.delete_item(item["id"])
        created, _, _ = self._upsert_matching_reminder(replacement_payload)
        return created, len(matches)

    def _update_matching_reminder(self, criteria: dict, payload: dict) -> dict:
        matches = self._find_matching_reminders(criteria)
        if not matches:
            raise ValidationError("No matching recurring reminder was found to update.")
        primary_item = sorted(matches, key=lambda item: item["id"])[0]
        updated = self._recurring_service.update_item(primary_item["id"], payload)
        for duplicate in matches[1:]:
            self._recurring_service.delete_item(duplicate["id"])
        return updated

    def _find_matching_expenses(self, criteria: dict) -> list[dict]:
        expenses = self._expense_service.list_expenses("desc")
        normalized_description = str(criteria.get("description") or "").strip().lower()
        normalized_category = str(criteria.get("category") or "").strip().lower()
        normalized_entry_type = str(criteria.get("entry_type") or "").strip().lower()
        normalized_date = str(criteria.get("date") or "").strip()
        normalized_amount = criteria.get("amount")

        matches = []
        for expense in expenses:
            if normalized_description and normalized_description not in expense["description"].strip().lower():
                continue
            if normalized_category and normalized_category not in expense["category"].strip().lower():
                continue
            if normalized_entry_type and normalized_entry_type != expense["entry_type"]:
                continue
            if normalized_date and normalized_date != expense["date"]:
                continue
            if normalized_amount not in (None, "") and abs(float(expense["amount"]) - float(normalized_amount)) >= 0.01:
                continue
            matches.append(expense)
        return matches

    def _delete_matching_expenses(self, criteria: dict) -> tuple[int, dict]:
        matches = self._find_matching_expenses(criteria)
        if not matches:
            raise ValidationError("No matching transaction was found to delete.")
        for expense in matches:
            self._expense_service.delete_expense(int(expense["id"]))
        return len(matches), matches[0]

    def _update_matching_expense(self, criteria: dict, payload: dict) -> dict:
        matches = self._find_matching_expenses(criteria)
        if not matches:
            raise ValidationError("No matching transaction was found to update.")
        primary_expense = sorted(matches, key=lambda item: item["id"])[0]
        updated = self._expense_service.update_expense(int(primary_expense["id"]), payload)
        for duplicate in matches[1:]:
            self._expense_service.delete_expense(int(duplicate["id"]))
        return updated

    def _execute_tool(self, tool_name: str, arguments: dict) -> dict:
        if tool_name == "get_dashboard_summary":
            return self._analytics_service.dashboard()
        if tool_name == "get_financial_pulse":
            return self._analytics_service.financial_pulse()
        if tool_name == "get_spending_prediction":
            try:
                return self._prediction_service.predict_next_month()
            except ValidationError as exc:
                return {"error": exc.message}
        if tool_name == "get_category_insights":
            return self._analytics_service.category_insights()
        if tool_name == "get_recent_transactions":
            limit = max(1, min(int(arguments.get("limit", 8)), 15))
            return {"transactions": self._expense_service.list_expenses()[:limit]}
        if tool_name == "get_upcoming_recurring_items":
            days = max(1, min(int(arguments.get("days", 21)), 60))
            return self._recurring_service.upcoming_calendar(days)
        if tool_name == "generate_monthly_report":
            self._report_service.generate_monthly_report()
            return {
                "available": True,
                "download_url": "/api/reports/monthly",
            }
        return {"error": f"Unknown tool: {tool_name}"}

    @staticmethod
    def _workflow_catalog() -> dict[str, dict]:
        return {
            "month_end_close": {
                "id": "month_end_close",
                "label": "Month-end close",
                "description": "Generate the monthly report, review live KPIs, and produce an executive-ready close summary.",
                "automation_focus": "Automates the end-of-month review, report refresh, and briefing preparation.",
                "default_task": (
                    "Complete the month-end close workflow. Summarise budget performance, cash-flow risk, category "
                    "pressure, and provide an executive-ready follow-up email."
                ),
                "steps": [
                    {"tool": "get_dashboard_summary", "arguments": {}, "action": "Captured the latest dashboard KPIs for the close pack."},
                    {"tool": "get_financial_pulse", "arguments": {}, "action": "Reviewed financial pulse signals for budget and cash-flow pressure."},
                    {"tool": "get_category_insights", "arguments": {}, "action": "Analysed category concentration and spend drivers."},
                    {"tool": "get_spending_prediction", "arguments": {}, "action": "Checked the next-month spending forecast for forward risk."},
                    {"tool": "get_upcoming_recurring_items", "arguments": {"days": 30}, "action": "Scanned the next 30 days of recurring commitments."},
                    {"tool": "generate_monthly_report", "arguments": {}, "action": "Generated a fresh monthly PDF report for distribution."},
                ],
            },
            "upcoming_bills_check": {
                "id": "upcoming_bills_check",
                "label": "Upcoming bills check",
                "description": "Review near-term recurring spend, cash coverage, and reminder pressure before due dates arrive.",
                "automation_focus": "Automates recurring bill review and prepares reminder-ready finance summaries.",
                "default_task": (
                    "Run the upcoming bills workflow. Highlight due-soon recurring items, explain cash-flow impact, "
                    "and draft a concise reminder email."
                ),
                "steps": [
                    {"tool": "get_dashboard_summary", "arguments": {}, "action": "Captured the current month cash position before reminders are prepared."},
                    {"tool": "get_upcoming_recurring_items", "arguments": {"days": 21}, "action": "Scanned recurring items due in the next 21 days."},
                    {"tool": "get_recent_transactions", "arguments": {"limit": 8}, "action": "Reviewed recent transactions to add context for reminder messaging."},
                ],
            },
            "cash_flow_recovery_plan": {
                "id": "cash_flow_recovery_plan",
                "label": "Cash-flow recovery plan",
                "description": "Inspect cash-flow pressure and produce a prioritised action plan to stabilise the month.",
                "automation_focus": "Automates KPI review, risk assessment, and recovery-plan preparation for overspend scenarios.",
                "default_task": (
                    "Create a cash-flow recovery workflow summary. Explain the main risk signals, outline the fastest "
                    "actions to stabilise the month, and draft a crisp action-oriented email."
                ),
                "steps": [
                    {"tool": "get_dashboard_summary", "arguments": {}, "action": "Captured live spend, budget, and income KPIs."},
                    {"tool": "get_financial_pulse", "arguments": {}, "action": "Reviewed health score, spend velocity, and cash-flow runway."},
                    {"tool": "get_spending_prediction", "arguments": {}, "action": "Pulled the forecast to understand near-term overspend risk."},
                    {"tool": "get_category_insights", "arguments": {}, "action": "Checked the highest-pressure categories for recovery opportunities."},
                    {"tool": "get_recent_transactions", "arguments": {"limit": 10}, "action": "Reviewed recent transaction activity to support the recovery plan."},
                ],
            },
        }

    def _should_use_context_prompt(self) -> bool:
        model_name = self._ollama_client.model.lower()
        return "mistral" in model_name

    @staticmethod
    def _looks_like_manual_action_command(task: str) -> bool:
        normalized = task.lower()
        action_words = ("add", "create", "set up", "update", "change", "edit", "delete", "remove", "replace", "set")
        domain_words = ("reminder", "recurring", "bill", "bills", "cost", "costs", "subscription", "transaction", "expense", "income", "budget")
        return any(word in normalized for word in action_words) and any(word in normalized for word in domain_words)

    @staticmethod
    def _parse_final_payload(content: str) -> dict:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {
                "headline": "Finance briefing generated",
                "summary": content.strip() or "No summary returned.",
                "risk_level": "medium",
                "recommended_actions": [],
                "email_subject": "Monthly finance briefing",
                "email_draft": content.strip() or "No email draft returned.",
            }

        return {
            "headline": str(parsed.get("headline") or "Finance briefing generated"),
            "summary": str(parsed.get("summary") or "No summary returned."),
            "risk_level": str(parsed.get("risk_level") or "medium").lower(),
            "recommended_actions": AgentService._normalize_recommended_actions(parsed.get("recommended_actions")),
            "email_subject": str(parsed.get("email_subject") or "Monthly finance briefing"),
            "email_draft": str(parsed.get("email_draft") or "No email draft returned."),
        }

    @staticmethod
    def _parse_reminder_payload(content: str | dict, fallback_date: str) -> dict:
        if isinstance(content, dict):
            parsed = content
        else:
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as exc:
                raise ValidationError("The AI agent could not understand the reminder request.") from exc

        amount = parsed.get("amount")
        if amount in (None, ""):
            raise ValidationError("The reminder request must include an amount.")

        return {
            "category": str(parsed.get("category") or "General").strip(),
            "description": str(parsed.get("description") or "Recurring reminder").strip(),
            "amount": round(float(amount), 2),
            "entry_type": str(parsed.get("entry_type") or "expense").strip().lower(),
            "frequency": str(parsed.get("frequency") or "monthly").strip().lower(),
            "start_date": str(parsed.get("start_date") or fallback_date).strip(),
            "end_date": str(parsed.get("end_date") or "").strip() or None,
            "active": bool(parsed.get("active", True)),
        }

    def _upsert_matching_reminder(self, payload: dict) -> tuple[dict, str, str]:
        list_items = getattr(self._recurring_service, "list_items", None)
        existing_items = list_items() if callable(list_items) else []
        normalized_description = payload["description"].strip().lower()
        matching_items = [
            item
            for item in existing_items
            if item["description"].strip().lower() == normalized_description
            and item["frequency"] == payload["frequency"]
            and item["entry_type"] == payload["entry_type"]
            and abs(float(item["amount"]) - float(payload["amount"])) < 0.01
        ]
        if matching_items:
            primary_item = sorted(matching_items, key=lambda item: item["id"])[0]
            updated = self._recurring_service.update_item(primary_item["id"], payload)
            for duplicate in matching_items[1:]:
                self._recurring_service.delete_item(duplicate["id"])
            return updated, "recurring_item_updated", "The existing reminder was updated and duplicate weekly reminders were removed."

        created = self._recurring_service.create_item(payload)
        return created, "recurring_item_created", "The reminder was created automatically from your prompt."

    @staticmethod
    def _resolve_start_date_from_task(task: str, fallback_date: str) -> str:
        normalized = task.lower()
        base_date = datetime.now().date()

        explicit_date_match = re.search(r"(20\d{2}-\d{2}-\d{2})", normalized)
        if explicit_date_match:
            return explicit_date_match.group(1)

        day_of_month_match = re.search(r"(\d{1,2})(?:st|nd|rd|th) of (?:each|every) month", normalized)
        if day_of_month_match:
            target_day = max(1, min(int(day_of_month_match.group(1)), 31))
            year = base_date.year
            month = base_date.month
            if base_date.day > target_day:
                if month == 12:
                    year += 1
                    month = 1
                else:
                    month += 1
            return AgentService._build_monthly_due_date(year, month, target_day).isoformat()

        weekdays = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        mentioned_weekday = next((name for name in weekdays if name in normalized), None)
        if mentioned_weekday is None:
            return fallback_date

        days_ahead = (weekdays[mentioned_weekday] - base_date.weekday()) % 7
        if "next " in normalized:
            days_ahead = 7 if days_ahead == 0 else days_ahead
        resolved_date = base_date + timedelta(days=days_ahead)
        return resolved_date.isoformat()

    @staticmethod
    def _normalize_recommended_actions(value) -> list[str]:
        if isinstance(value, str):
            cleaned = value.strip()
            return [cleaned] if cleaned else []
        if not isinstance(value, list):
            return []
        if value and all(isinstance(item, str) and len(item) <= 1 for item in value):
            joined = "".join(item for item in value)
            cleaned = re.sub(r"\s+", " ", joined).strip()
            return [cleaned] if cleaned else []
        return [str(item).strip() for item in value if str(item).strip()]

    def _apply_reminder_schedule_from_task(self, task: str, payload: dict, fallback_date: str) -> dict:
        normalized_payload = dict(payload)
        normalized_payload["start_date"] = str(normalized_payload.get("start_date") or fallback_date).strip() or fallback_date
        schedule_bounds = self._resolve_task_schedule_bounds(
            task,
            normalized_payload.get("frequency") or "monthly",
            normalized_payload["start_date"],
            normalized_payload.get("end_date"),
        )
        normalized_payload["start_date"] = schedule_bounds["start_date"]
        normalized_payload["end_date"] = schedule_bounds.get("end_date")
        return normalized_payload

    def _resolve_task_schedule_bounds(
        self,
        task: str,
        frequency: str,
        fallback_start_date: str,
        explicit_end_date: str | None,
    ) -> dict:
        start_date = self._resolve_start_date_from_task(task, fallback_start_date)
        month_range = self._extract_month_range(task)
        if month_range and frequency == "monthly":
            target_day = self._extract_day_of_month(task)
            if target_day is None:
                target_day = datetime.strptime(start_date, "%Y-%m-%d").day
            start_year, start_month, end_year, end_month = month_range
            first_due = self._build_monthly_due_date(start_year, start_month, target_day)
            last_due = self._build_monthly_due_date(end_year, end_month, target_day)
            if self._is_end_exclusive(task):
                last_due = self._previous_due_date(last_due, frequency)
            if last_due < first_due:
                raise ValidationError("The reminder range does not include any due dates.")
            return {
                "start_date": first_due.isoformat(),
                "end_date": last_due.isoformat(),
            }

        end_date = str(explicit_end_date or "").strip() or None
        return {
            "start_date": start_date,
            "end_date": end_date,
        }

    @staticmethod
    def _extract_month_range(task: str) -> tuple[int, int, int, int] | None:
        normalized = task.lower()
        month_names = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }
        range_match = re.search(
            r"(?:from|between)\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(20\d{2})\s+(?:to|and|until|through)\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(20\d{2})",
            normalized,
        )
        if not range_match:
            return None
        start_month = month_names[range_match.group(1)]
        start_year = int(range_match.group(2))
        end_month = month_names[range_match.group(3)]
        end_year = int(range_match.group(4))
        return start_year, start_month, end_year, end_month

    @staticmethod
    def _extract_day_of_month(task: str) -> int | None:
        match = re.search(r"(\d{1,2})(?:st|nd|rd|th) of (?:each|every) month", task.lower())
        if not match:
            return None
        return max(1, min(int(match.group(1)), 31))

    @staticmethod
    def _is_end_exclusive(task: str) -> bool:
        normalized = task.lower()
        return any(
            phrase in normalized
            for phrase in ("exclusive", "excluding", "but not including", "not including the end")
        )

    @staticmethod
    def _build_monthly_due_date(year: int, month: int, target_day: int):
        while True:
            try:
                return datetime(year, month, target_day).date()
            except ValueError:
                target_day -= 1
                if target_day <= 0:
                    raise ValidationError("The reminder day-of-month could not be resolved.")

    @staticmethod
    def _previous_due_date(current_due_date, frequency: str):
        if frequency == "weekly":
            return current_due_date - timedelta(days=7)
        previous_month = current_due_date.replace(day=1) - timedelta(days=1)
        target_day = min(current_due_date.day, previous_month.day)
        return previous_month.replace(day=target_day)

    @staticmethod
    def _tool_definitions() -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_dashboard_summary",
                    "description": "Get the current budget, income, expense, and cash-flow dashboard summary.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_financial_pulse",
                    "description": "Get risk signals, spend velocity, cash flow, and health metrics.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_category_insights",
                    "description": "Get top and bottom spending categories for the current month.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_spending_prediction",
                    "description": "Get the predicted next-month spending forecast and budget comparison.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_recent_transactions",
                    "description": "Get the most recent transactions for evidence in the briefing.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "How many recent transactions to return.",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_upcoming_recurring_items",
                    "description": "Get upcoming recurring bills and income reminders.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days": {
                                "type": "integer",
                                "description": "Number of days to look ahead.",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_monthly_report",
                    "description": "Generate the detailed monthly PDF report and return its download path.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]










