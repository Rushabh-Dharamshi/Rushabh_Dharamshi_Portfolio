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
from budget_tracker_api.security import background_user_context
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
        rag_service = None,
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
        self._rag_service = rag_service
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
        recipient = self._recipient_from_payload(request_payload)

        if self._looks_like_manual_action_command(task):
            return self._run_manual_action_command(task, recipient=recipient)

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
                    "headline, summary, risk_level, recommended_actions, email_subject, email_draft. "
                    "Every email_draft must end exactly with: Kind Regards, followed by Monetra Organisation on the next line."
                ),
            },
            {"role": "user", "content": task},
        ]
        tools = self._tool_definitions()
        tools_used: list[str] = []
        tool_context: dict[str, dict] = {}
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
                final_payload = self._enrich_sparse_cfo_briefing(final_payload, tool_context, task)
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
                if not isinstance(tool_call, dict):
                    raise ValidationError("The Ollama agent returned an invalid tool call.")
                function = tool_call.get("function", {})
                if not isinstance(function, dict):
                    raise ValidationError("The Ollama agent returned an invalid tool function.")
                tool_name = function.get("name", "")
                raw_arguments = function.get("arguments", {})
                arguments = raw_arguments if isinstance(raw_arguments, dict) else {}
                tools_used.append(tool_name)
                tool_result = self._execute_tool(tool_name, arguments)
                tool_context[tool_name] = tool_result
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
                result = self._run_with_payload_user_context(
                    payload,
                    lambda: self.run_finance_briefing(payload),
                )
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
                result = self._run_with_payload_user_context(
                    payload,
                    lambda: self.run_workflow(workflow_name, payload),
                )
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
                        "Keep the summary concise and action-oriented. "
                        "Every email_draft must end exactly with: Kind Regards, followed by Monetra Organisation on the next line."
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
        final_payload = self._enrich_sparse_cfo_briefing(final_payload, compact_payload, task)
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
                        "recommended_actions, email_subject, email_draft. All money is in pounds sterling (GBP). Never use dollars or the $ symbol. "
                        "Every email_draft must end exactly with: Kind Regards, followed by Monetra Organisation on the next line."
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

    @staticmethod
    def _recipient_from_payload(payload: dict) -> str | None:
        recipient = str(payload.get("recipient") or payload.get("recipient_email") or "").strip()
        return recipient or None

    @staticmethod
    def _user_id_from_payload(payload: dict) -> int | None:
        try:
            return int(payload.get("user_id"))
        except (TypeError, ValueError):
            return None

    def _run_with_payload_user_context(self, payload: dict, callback):
        user_id = self._user_id_from_payload(payload)
        if user_id is None:
            return callback()
        with background_user_context(user_id):
            return callback()

    def _run_manual_action_command(self, task: str, recipient: str | None = None) -> dict:
        direct_email_result = self._run_direct_email_dispatch_if_requested(task, recipient=recipient)
        if direct_email_result is not None:
            return direct_email_result

        direct_report_result = self._run_direct_report_generation_if_requested(task)
        if direct_report_result is not None:
            return direct_report_result

        direct_prompt_result = self._run_direct_prompt_command_if_requested(task)
        if direct_prompt_result is not None:
            return direct_prompt_result

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

    def _run_direct_prompt_command_if_requested(self, task: str) -> dict | None:
        parsed = self._parse_direct_prompt_command(task)
        if parsed is None:
            return None

        domain = parsed["domain"]
        if domain == "settings":
            return self._run_settings_command(task, parsed)
        if domain == "expense":
            return self._run_expense_command(task, parsed)
        if domain == "recurring":
            return self._run_reminder_command(task, parsed)
        return None

    def _parse_direct_prompt_command(self, task: str) -> dict | None:
        normalized = re.sub(r"\s+", " ", str(task or "").strip().lower())
        if not normalized:
            return None

        settings_match = re.search(
            r"\bset\s+my\s+monthly\s+(?P<setting>budget|income)(?:\s+for\s+(?P<month>20\d{2}-\d{2}))?\s+to\s+(?P<amount>\d+(?:\.\d{1,2})?)\s*(?:pounds|gbp|£)?",
            normalized,
        )
        if settings_match:
            return {
                "domain": "settings",
                "operation": "update",
                "setting_key": f"monthly_{settings_match.group('setting')}",
                "value": round(float(settings_match.group("amount")), 2),
                "month": settings_match.group("month"),
                "target": {},
                "entity": {},
                "reminder": None,
            }

        if re.search(r"\badd\s+an?\s+income\s+transaction\b", normalized):
            raise ValidationError("Income is recorded with monthly income settings, not as a transaction. Use 'Set my monthly income to ...' instead.")

        if re.search(r"\badd\s+an?\s+expense\b", normalized):
            created = self._parse_direct_transaction_create(task, entry_type="expense")
            return created

        transaction_update = self._parse_direct_transaction_update(task)
        if transaction_update:
            return transaction_update

        transaction_delete = self._parse_direct_transaction_delete(task)
        if transaction_delete:
            return transaction_delete

        recurring_command = self._parse_direct_recurring_command(task)
        if recurring_command:
            return recurring_command

        return None

    def _parse_direct_transaction_create(self, task: str, entry_type: str = "expense") -> dict | None:
        normalized = str(task or "").strip()
        amount_match = re.search(r"\bof\s+(?P<amount>\d+(?:\.\d{1,2})?)\s*(?:pounds|gbp|£)?", normalized, flags=re.IGNORECASE)
        category_match = re.search(r"\bunder\s+(?P<category>[A-Za-z][A-Za-z\s&-]+?)\.?$", normalized, flags=re.IGNORECASE)
        date_match = re.search(r"\bon\s+(?P<date>20\d{2}-\d{2}-\d{2})\b", normalized, flags=re.IGNORECASE)
        if not amount_match:
            return None

        description = re.sub(
            r"^add\s+an?\s+expense\s+for\s+",
            "",
            normalized,
            flags=re.IGNORECASE,
        )
        description = re.split(r"\s+of\s+\d+(?:\.\d{1,2})?\s*(?:pounds|gbp|£)?", description, maxsplit=1, flags=re.IGNORECASE)[0]
        description = description.strip(" .") or "Transaction"
        date_value = date_match.group("date") if date_match else datetime.now().strftime("%Y-%m-%d")
        category = (category_match.group("category") if category_match else "General").strip(" .")
        return {
            "domain": "expense",
            "operation": "create",
            "target": {},
            "entity": {
                "date": date_value,
                "category": category.title(),
                "description": description[:1].upper() + description[1:],
                "amount": round(float(amount_match.group("amount")), 2),
                "entry_type": "expense",
            },
            "reminder": None,
        }

    def _parse_direct_transaction_update(self, task: str) -> dict | None:
        match = re.search(
            r"\bupdate\s+the\s+(?P<category>[A-Za-z][A-Za-z\s&-]+?)\s+expense\s+called\s+(?P<description>.+?)\s+to\s+(?P<amount>\d+(?:\.\d{1,2})?)\s*(?:pounds|gbp|£)?(?:\s+on\s+(?P<date>20\d{2}-\d{2}-\d{2}))?",
            str(task or "").strip(),
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        date_value = match.group("date")
        entity = {
            "category": match.group("category").strip().title(),
            "description": match.group("description").strip(" ."),
            "amount": round(float(match.group("amount")), 2),
            "entry_type": "expense",
        }
        if date_value:
            entity["date"] = date_value
        return {
            "domain": "expense",
            "operation": "update",
            "target": {
                "description": match.group("description").strip(" ."),
                "category": match.group("category").strip().title(),
                "entry_type": "expense",
            },
            "entity": entity,
            "reminder": None,
        }

    def _parse_direct_transaction_delete(self, task: str) -> dict | None:
        normalized = str(task or "").strip()
        if re.search(r"\bremove\s+all\s+expenses\b", normalized, flags=re.IGNORECASE):
            return {"domain": "expense", "operation": "delete", "target": {}, "entity": {}, "reminder": None}

        match = re.search(
            r"\bdelete\s+the\s+expense\s+matching\s+(?P<description>.+?)(?:\s+under\s+(?P<category>[A-Za-z][A-Za-z\s&-]+?))?\.?$",
            normalized,
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        target = {"description": match.group("description").strip(" ."), "entry_type": "expense"}
        if match.group("category"):
            target["category"] = match.group("category").strip(" .").title()
        return {"domain": "expense", "operation": "delete", "target": target, "entity": {}, "reminder": None}

    def _parse_direct_recurring_command(self, task: str) -> dict | None:
        normalized = str(task or "").strip()
        lowered = normalized.lower()
        if "reminder" not in lowered and "utility bills" not in lowered and "rent" not in lowered:
            return None

        scheduled_match = re.search(
            r"\b(?:add|create|set(?:\s+up)?)\s+(?:a\s+)?(?P<frequency>weekly|monthly)\s+reminder\s+for\s+(?P<description>.+?)\s+of\s+(?P<amount>\d+(?:\.\d{1,2})?)\s*(?:pounds|gbp|£|Â£)?(?:\s+(?:from|starting|starting\s+on|on)\s+(?P<start_date>today|20\d{2}-\d{2}-\d{2}))?(?:\s+(?:to|until|through)\s+(?P<end_date>20\d{2}-\d{2}-\d{2}))?(?:\s+(?P<bound_type>inclusive|exclusive))?(?:\s+(?:under|in)\s+(?P<category>[A-Za-z][A-Za-z\s&-]+?))?\.?$",
            normalized,
            flags=re.IGNORECASE,
        )
        if scheduled_match:
            raw_start = (scheduled_match.group("start_date") or "").strip().lower()
            start_date = datetime.now().strftime("%Y-%m-%d") if raw_start in {"", "today"} else raw_start
            description = scheduled_match.group("description").strip(" .").title()
            category = (scheduled_match.group("category") or "").strip(" .")
            category = re.sub(r"\s+(?:inclusive|exclusive)\s*$", "", category, flags=re.IGNORECASE).strip(" .")
            if not category and "rent" in description.lower():
                category = "Housing"
            return {
                "domain": "recurring",
                "operation": "create",
                "target": {},
                "entity": {},
                "reminder": self._parse_reminder_payload(
                    {
                        "category": (category or "General").title(),
                        "description": description,
                        "amount": scheduled_match.group("amount"),
                        "entry_type": "expense",
                        "frequency": scheduled_match.group("frequency").lower(),
                        "start_date": start_date,
                        "end_date": (scheduled_match.group("end_date") or "").strip() or None,
                        "active": True,
                    },
                    datetime.now().strftime("%Y-%m-%d"),
                ),
            }

        one_time_match = re.search(
            r"\badd\s+(?:a\s+)?(?:(?:one[-\s]?time|one[-\s]?off|once)\s+)?reminder\s+for\s+(?P<description>.+?)\s+of\s+(?P<amount>\d+(?:\.\d{1,2})?)\s*(?:pounds|gbp|Â£)?(?:\s+(?:(?:for|on|due|starting|from)\s+)?(?P<date>today|20\d{2}-\d{2}-\d{2}))?(?:\s+to\s+(?P<end_date>20\d{2}-\d{2}-\d{2}))?(?:\s+(?:under|in)\s+(?P<category>[A-Za-z][A-Za-z\s&-]+?))?\.?$",
            normalized,
            flags=re.IGNORECASE,
        )
        if one_time_match:
            raw_date = (one_time_match.group("date") or "").strip().lower()
            start_date = datetime.now().strftime("%Y-%m-%d") if raw_date in {"", "today"} else raw_date
            end_date = (one_time_match.group("end_date") or "").strip()
            if end_date and end_date != start_date:
                return None
            return {
                "domain": "recurring",
                "operation": "create",
                "target": {},
                "entity": {},
                "reminder": self._parse_reminder_payload(
                    {
                        "category": (one_time_match.group("category") or "General").strip(" .").title(),
                        "description": one_time_match.group("description").strip(" .").title(),
                        "amount": one_time_match.group("amount"),
                        "entry_type": "expense",
                        "frequency": "once",
                        "start_date": start_date,
                        "active": True,
                    },
                    datetime.now().strftime("%Y-%m-%d"),
                ),
            }

        if lowered.startswith("set a monthly reminder for university house rent"):
            amount = self._extract_money_amount(normalized, preferred_prefixes=("at", "for", "of", "to"))
            if amount is None:
                return None
            return {
                "domain": "recurring",
                "operation": "create",
                "target": {},
                "entity": {},
                "reminder": self._parse_reminder_payload(
                    {
                        "category": "Housing",
                        "description": "University House Rent",
                        "amount": amount,
                        "entry_type": "expense",
                        "frequency": "monthly",
                        "active": True,
                    },
                    datetime.now().strftime("%Y-%m-%d"),
                ),
            }

        weekly_rent_match = re.search(
            r"\badd\s+a\s+weekly\s+reminder\s+for\s+rent\s+of\s+(?P<amount>\d+(?:\.\d{1,2})?)\s*(?:pounds|gbp|£)?\s+starting\s+(?P<date>20\d{2}-\d{2}-\d{2})",
            normalized,
            flags=re.IGNORECASE,
        )
        if weekly_rent_match:
            return {
                "domain": "recurring",
                "operation": "create",
                "target": {},
                "entity": {},
                "reminder": self._parse_reminder_payload(
                    {
                        "category": "Housing",
                        "description": "Rent",
                        "amount": weekly_rent_match.group("amount"),
                        "entry_type": "expense",
                        "frequency": "weekly",
                        "start_date": weekly_rent_match.group("date"),
                        "active": True,
                    },
                    datetime.now().strftime("%Y-%m-%d"),
                ),
            }

        if "replace weekly utility bills with monthly utility bills" in lowered:
            amount = self._extract_money_amount(normalized, preferred_prefixes=("of", "to", "at", "for"))
            if amount is None:
                return None
            return {
                "domain": "recurring",
                "operation": "replace",
                "target": {"description": "Utility Bills", "category": "Utilities", "entry_type": "expense", "frequency": "weekly"},
                "entity": {},
                "reminder": self._parse_reminder_payload(
                    {
                        "category": "Utilities",
                        "description": "Utility Bills",
                        "amount": amount,
                        "entry_type": "expense",
                        "frequency": "monthly",
                        "active": True,
                    },
                    datetime.now().strftime("%Y-%m-%d"),
                ),
            }

        if "remove the weekly utility bills reminder" in lowered:
            return {
                "domain": "recurring",
                "operation": "delete",
                "target": {"description": "Utility Bills", "category": "Utilities", "entry_type": "expense", "frequency": "weekly"},
                "entity": {},
                "reminder": None,
            }

        if "update the utility bills reminder" in lowered:
            amount = self._extract_money_amount(normalized, preferred_prefixes=("to", "of", "at", "for"))
            date_match = re.search(r"\bfrom\s+(20\d{2}-\d{2}-\d{2})\b", normalized, flags=re.IGNORECASE)
            if amount is None:
                return None
            return {
                "domain": "recurring",
                "operation": "update",
                "target": {"description": "Utility Bills", "category": "Utilities", "entry_type": "expense"},
                "entity": {},
                "reminder": self._parse_reminder_payload(
                    {
                        "category": "Utilities",
                        "description": "Utility Bills",
                        "amount": amount,
                        "entry_type": "expense",
                        "frequency": "monthly",
                        "start_date": date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d"),
                        "active": True,
                    },
                    datetime.now().strftime("%Y-%m-%d"),
                ),
            }

        return None

    @staticmethod
    def _extract_money_amount(task: str, preferred_prefixes: tuple[str, ...] = ("of", "to", "at", "for")) -> float | None:
        for prefix in preferred_prefixes:
            match = re.search(
                rf"\b{re.escape(prefix)}\s+(?P<amount>\d+(?:\.\d{{1,2}})?)\s*(?:pounds|gbp|£)?\b",
                task,
                flags=re.IGNORECASE,
            )
            if match:
                return round(float(match.group("amount")), 2)
        fallback_match = re.search(r"\b(?P<amount>\d+(?:\.\d{1,2})?)\s*(?:pounds|gbp|£)\b", task, flags=re.IGNORECASE)
        if fallback_match:
            return round(float(fallback_match.group("amount")), 2)
        return None

    def _run_direct_email_dispatch_if_requested(self, task: str, recipient: str | None = None) -> dict | None:
        normalized = str(task or "").lower()
        if not self._looks_like_email_dispatch_command(normalized):
            return None

        if self._looks_like_all_upcoming_bills_email_command(normalized):
            return self._mcp_send_all_upcoming_bills_email_now({"recipient": recipient})

        if self._looks_like_upcoming_bills_email_command(normalized):
            return self._mcp_send_upcoming_bills_email_now({"recipient": recipient})

        if self._looks_like_financial_report_email_command(normalized):
            return self._mcp_send_month_end_email_now({"recipient": recipient})

        return None

    def _run_direct_report_generation_if_requested(self, task: str) -> dict | None:
        normalized = str(task or "").lower()
        if self._looks_like_email_dispatch_command(normalized) or not self._looks_like_report_generation_command(normalized):
            return None

        report_result = self._execute_tool("generate_monthly_report", {})
        dashboard = self._analytics_service.dashboard()
        category_insights = self._analytics_service.category_insights()
        top_categories = category_insights.get("top_categories") or []
        top_category = top_categories[0] if top_categories else {}
        net_cash_flow = dashboard.get("net_cash_flow")

        pressure_parts = []
        if net_cash_flow is not None:
            pressure_parts.append(f"net cash flow is GBP {float(net_cash_flow):.2f}")
        if top_category.get("category") and top_category.get("amount") is not None:
            pressure_parts.append(
                f"top spending pressure is {top_category['category']} at GBP {float(top_category['amount']):.2f}"
            )
        pressure_summary = "; ".join(pressure_parts) if pressure_parts else "budget pressure points were refreshed from the current dashboard"

        result = self._build_action_response(
            headline="Monthly report generated",
            summary=f"Generated the current monthly PDF report and refreshed the main budget pressure context: {pressure_summary}.",
            email_subject="Monthly report generated",
            email_draft=(
                "The current monthly finance report has been generated. "
                f"Main pressure context: {pressure_summary}."
            ),
            task=task,
            action_type="monthly_report_generated",
            action_message="Monthly report generated successfully.",
            payload={
                "available": bool(report_result.get("available")),
                "download_url": report_result.get("download_url"),
                "net_cash_flow": net_cash_flow,
                "top_categories": top_categories[:3],
            },
        )
        result["tools_used"] = ["generate_monthly_report", "get_dashboard_summary", "get_category_insights"]
        result["report_download_url"] = report_result.get("download_url")
        result["recommended_actions"] = [
            "Open the generated report from the report link.",
            "Review the top spending categories before sending or sharing the summary.",
        ]
        return result

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
            "retrieve_finance_context": self._mcp_retrieve_finance_context,
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
            "send_all_upcoming_bills_email_now": self._mcp_send_all_upcoming_bills_email_now,
            "send_month_end_email_now": self._mcp_send_month_end_email_now,
        }

    def _mcp_retrieve_finance_context(self, arguments: dict) -> dict:
        if self._rag_service is None:
            raise ValidationError("RAG service is not attached to the agent runtime.")
        question = str(arguments.get("question") or "").strip()
        top_k = arguments.get("top_k")
        return self._rag_service.retrieve_context(question, top_k=top_k)

    def _mcp_list_recurring_reminders(self, arguments: dict) -> dict:
        list_items = getattr(self._recurring_service, "list_items", None)
        items = list_items() if callable(list_items) else []
        return {"items": items}

    def _mcp_set_monthly_budget(self, arguments: dict) -> dict:
        return self._run_settings_command(
            "MCP tool: update monthly budget",
            {"setting_key": "monthly_budget", "value": arguments.get("monthly_budget"), "month": arguments.get("month")},
        )

    def _mcp_set_monthly_income(self, arguments: dict) -> dict:
        return self._run_settings_command(
            "MCP tool: update monthly income",
            {"setting_key": "monthly_income", "value": arguments.get("monthly_income"), "month": arguments.get("month")},
        )

    def _mcp_create_transaction(self, arguments: dict) -> dict:
        entity = {**arguments, "entry_type": "expense"}
        return self._run_expense_command(
            "MCP tool: create transaction",
            {"operation": "create", "entity": entity, "target": {}},
        )

    def _mcp_update_transaction_by_match(self, arguments: dict) -> dict:
        entity = {**(arguments.get("entity") or {}), "entry_type": "expense"}
        return self._run_expense_command(
            "MCP tool: update transaction",
            {"operation": "update", "entity": entity, "target": arguments.get("target") or {}},
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
        recipient = str(arguments.get("recipient") or arguments.get("recipient_email") or "").strip() or None
        result = self._automation_service.run_upcoming_bills_email_now(recipient=recipient)
        result["report_download_url"] = result.get("report_download_url")
        action_type = "upcoming_bills_email_skipped" if "no upcoming bills email sent" in str(result.get("headline") or "").lower() else "upcoming_bills_email_sent"
        action_payload = dict(result)
        result["action_result"] = {
            "type": action_type,
            "message": result["summary"],
            "payload": action_payload,
        }
        return result

    def _mcp_send_all_upcoming_bills_email_now(self, arguments: dict) -> dict:
        if self._automation_service is None:
            raise ValidationError("Automation service is not attached to the agent runtime.")
        recipient = str(arguments.get("recipient") or arguments.get("recipient_email") or "").strip() or None
        result = self._automation_service.run_all_upcoming_bills_email_now(recipient=recipient)
        result["report_download_url"] = result.get("report_download_url")
        action_type = "upcoming_bills_email_skipped" if "no upcoming bills email sent" in str(result.get("headline") or "").lower() else "upcoming_bills_email_sent"
        action_payload = dict(result)
        result["action_result"] = {
            "type": action_type,
            "message": result["summary"],
            "payload": action_payload,
        }
        return result

    def _mcp_send_month_end_email_now(self, arguments: dict) -> dict:
        if self._automation_service is None:
            raise ValidationError("Automation service is not attached to the agent runtime.")
        recipient = str(arguments.get("recipient") or arguments.get("recipient_email") or "").strip() or None
        result = self._automation_service.run_month_end_email_now(recipient=recipient)
        result["report_download_url"] = result.get("report_download_url")
        action_payload = dict(result)
        result["action_result"] = {
            "type": "month_end_email_sent",
            "message": result["summary"],
            "payload": action_payload,
        }
        return result

    def _run_settings_command(self, task: str, parsed: dict) -> dict:
        setting_key = parsed.get("setting_key")
        value = parsed.get("value")
        if setting_key == "monthly_budget":
            month = parsed.get("month")
            result = self._settings_service.update_monthly_budget({"monthly_budget": value, "month": month})
            budget_month = result.get("budget_month")
            return self._build_action_response(
                headline="Monthly budget updated",
                summary=f"Monthly budget for {budget_month} is now GBP {float(result['monthly_budget']):.2f}.",
                email_subject="Monthly budget updated",
                email_draft=f"Monthly budget for {budget_month} was updated to GBP {float(result['monthly_budget']):.2f}.",
                task=task,
                action_type="monthly_budget_updated",
                action_message="Monthly budget updated successfully.",
                payload={
                    "monthly_budget": float(result["monthly_budget"]),
                    "budget_month": budget_month,
                    "monthly_income": self._settings_service.get_monthly_income(budget_month),
                },
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
                payload={"monthly_income": float(result["monthly_income"]), "income_month": income_month, "monthly_budget": self._settings_service.get_monthly_budget(income_month)},
            )
        raise ValidationError("The settings command must target monthly budget or monthly income.")

    def _run_expense_command(self, task: str, parsed: dict) -> dict:
        operation = parsed.get("operation") or "create"
        entity = parsed.get("entity") or {}
        target = parsed.get("target") or {}

        if operation == "create":
            created = self._expense_service.create_expense(entity)
            return self._build_action_response(
                headline="Expense created",
                summary=f"Created expense '{created['description']}' for GBP {float(created['amount']):.2f} on {created['date']}.",
                email_subject="Expense created",
                email_draft=f"Created expense {created['description']} for GBP {float(created['amount']):.2f}.",
                task=task,
                action_type="expense_created",
                action_message="Expense created successfully.",
                payload=created,
            )

        if operation == "delete":
            target = self._normalize_expense_delete_target(task, target)
            deleted_count, deleted_item = self._delete_matching_expenses(target)
            deleted_description = deleted_item.get("criteria_label") or deleted_item.get("description") or "the requested criteria"
            return self._build_action_response(
                headline="Transaction deleted",
                summary=f"Deleted {deleted_count} transaction(s) matching {deleted_description}.",
                email_subject="Transaction deleted",
                email_draft=f"Deleted {deleted_count} transaction(s) matching {deleted_description}.",
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
            "email_draft": self._with_standard_email_signoff(email_draft),
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
                        "For expense commands, return domain=expense, operation=create/update/delete, an entity object for the target expense data, and an optional target object describing which existing expense to update/delete. "
                        "Expense entity keys: date, category, description, amount. Never create income transactions; income is only recorded through monthly income settings. "
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
        if isinstance(parsed, list):
            if len(parsed) == 1 and isinstance(parsed[0], dict):
                parsed = parsed[0]
            elif all(isinstance(item, dict) for item in parsed):
                parsed = {"domain": "expense", "operation": "delete", "target": parsed}
            else:
                raise ValidationError("The AI agent returned an invalid command object.")
        if not isinstance(parsed, dict):
            raise ValidationError("The AI agent returned an invalid command object.")

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
        if result["domain"] == "expense":
            result["entity"]["entry_type"] = "expense"
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
                        "Use frequency once for one-time or one-off reminders. Use weekly or monthly only when the user asks for a repeated schedule. "
                        "Always use entry_type expense; recurring income reminders are not supported. "
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
            "email_draft": self._with_standard_email_signoff(email_draft),
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
        normalized_identity = self._normalize_text_match(
            " ".join(
                part
                for part in (
                    str(criteria.get("description") or "").strip(),
                    str(criteria.get("category") or "").strip(),
                )
                if part
            )
        )
        normalized_entry_type = criteria.get("entry_type", "").strip().lower()
        normalized_frequency = criteria.get("frequency", "").strip().lower()
        normalized_start_date = criteria.get("start_date", "").strip()
        normalized_amount = criteria.get("amount")
        has_text_identity = bool(normalized_description or normalized_category)

        matches = []
        for item in existing_items:
            item_description = self._normalize_text_match(item["description"])
            item_category = self._normalize_text_match(item["category"])
            item_identity = self._normalize_text_match(f"{item['description']} {item['category']}")
            if normalized_identity and not self._normalized_text_matches(normalized_identity, item_identity):
                continue
            if normalized_entry_type and normalized_entry_type != item["entry_type"]:
                continue
            if normalized_frequency and normalized_frequency != item["frequency"]:
                continue
            if normalized_start_date and normalized_start_date != item["start_date"]:
                continue
            if (
                not has_text_identity
                and normalized_amount not in (None, "")
                and abs(float(item["amount"]) - float(normalized_amount)) >= 0.01
            ):
                continue
            matches.append(item)
        return matches

    @staticmethod
    def _normalize_text_match(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    @staticmethod
    def _normalized_text_matches(needle: str, haystack: str) -> bool:
        needle_tokens = set(needle.split())
        haystack_tokens = set(haystack.split())
        required_plan_tokens = needle_tokens & {"plus", "pro", "free"}
        if required_plan_tokens and not required_plan_tokens.issubset(haystack_tokens):
            return False
        compact_needle = needle.replace(" ", "")
        compact_haystack = haystack.replace(" ", "")
        return (
            needle_tokens.issubset(haystack_tokens)
            or haystack_tokens.issubset(needle_tokens)
            or needle in haystack
            or haystack in needle
            or compact_needle in compact_haystack
            or compact_haystack in compact_needle
        )

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

    def _find_matching_expenses(self, criteria: dict | list) -> list[dict]:
        expenses = self._expense_service.list_expenses("desc")
        criteria_items = self._normalize_expense_criteria_items(criteria)
        matched_by_id: dict[int, dict] = {}
        for item in criteria_items:
            for expense in expenses:
                if self._expense_matches_criteria(expense, item):
                    matched_by_id[int(expense["id"])] = expense
        return list(matched_by_id.values())

    @staticmethod
    def _normalize_expense_criteria_items(criteria: dict | list | None) -> list[dict]:
        if isinstance(criteria, list):
            items = [item for item in criteria if isinstance(item, dict)]
            if len(items) != len(criteria):
                raise ValidationError("Expense match criteria must be an object or a list of objects.")
            return items or [{}]
        if criteria is None:
            return [{}]
        if not isinstance(criteria, dict):
            raise ValidationError("Expense match criteria must be an object.")
        return [criteria]

    def _expense_matches_criteria(self, expense: dict, criteria: dict) -> bool:
        normalized_description = str(criteria.get("description") or "").strip().lower()
        normalized_category = str(criteria.get("category") or "").strip().lower()
        normalized_entry_type = str(criteria.get("entry_type") or "").strip().lower()
        normalized_date = str(criteria.get("date") or "").strip()
        normalized_amount = criteria.get("amount")
        normalized_month = str(criteria.get("month") or "").strip()
        date_from = str(criteria.get("date_from") or criteria.get("start_date") or "").strip()
        date_to = str(criteria.get("date_to") or criteria.get("end_date") or "").strip()
        date_after = str(criteria.get("date_after") or "").strip()
        date_before = str(criteria.get("date_before") or "").strip()
        expense_date = str(expense.get("date") or "").strip()

        if normalized_description and normalized_description not in expense["description"].strip().lower():
            return False
        if normalized_category and normalized_category not in expense["category"].strip().lower():
            return False
        if normalized_entry_type and normalized_entry_type != expense["entry_type"]:
            return False
        if normalized_date and normalized_date != expense_date:
            return False
        if normalized_month and not expense_date.startswith(normalized_month):
            return False
        if date_from and expense_date < date_from:
            return False
        if date_to and expense_date > date_to:
            return False
        if date_after and expense_date <= date_after:
            return False
        if date_before and expense_date >= date_before:
            return False
        if normalized_amount not in (None, "") and abs(float(expense["amount"]) - float(normalized_amount)) >= 0.01:
            return False
        return True

    def _normalize_expense_delete_target(self, task: str, target: dict | list | None) -> dict | list:
        criteria_items = self._normalize_expense_criteria_items(target)
        normalized_task = task.lower()
        inferred_items: list[dict] = []

        for year, month in self._extract_named_months(normalized_task):
            inferred_items.append({"month": f"{year:04d}-{month:02d}"})

        relative_date = self._extract_relative_expense_date(normalized_task)
        if relative_date:
            date_key, date_value = relative_date
            inferred_items.append({date_key: date_value})

        if inferred_items:
            criteria_items = [
                item for item in criteria_items if self._has_expense_match_fields(item)
            ] + inferred_items

        if "expense" in normalized_task:
            for item in criteria_items:
                item.setdefault("entry_type", "expense")

        return criteria_items[0] if len(criteria_items) == 1 else criteria_items

    @staticmethod
    def _has_expense_match_fields(criteria: dict) -> bool:
        return any(
            criteria.get(key) not in (None, "")
            for key in (
                "description",
                "category",
                "entry_type",
                "date",
                "amount",
                "month",
                "date_from",
                "date_to",
                "date_after",
                "date_before",
                "start_date",
                "end_date",
            )
        )

    @staticmethod
    def _extract_named_months(task: str) -> list[tuple[int, int]]:
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
        current_year = datetime.now().year
        matches = []
        for match in re.finditer(
            r"\b(january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+(20\d{2}))?\b",
            task,
        ):
            prefix = task[max(0, match.start() - 12):match.start()]
            if re.search(r"\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?$", prefix):
                continue
            month = month_names[match.group(1)]
            year = int(match.group(2) or current_year)
            matches.append((year, month))
        return matches

    @staticmethod
    def _extract_relative_expense_date(task: str) -> tuple[str, str] | None:
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
        match = re.search(
            r"\b(after|beyond|past|before)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+(20\d{2}))?\b",
            task,
        )
        if not match:
            return None
        operator = match.group(1)
        day = max(1, min(int(match.group(2)), 31))
        month = month_names[match.group(3)]
        year = int(match.group(4) or datetime.now().year)
        try:
            resolved = datetime(year, month, day).date().isoformat()
        except ValueError as exc:
            raise ValidationError("The expense date range could not be resolved.") from exc
        if operator == "before":
            return "date_before", resolved
        return "date_after", resolved

    def _delete_matching_expenses(self, criteria: dict | list) -> tuple[int, dict]:
        matches = self._find_matching_expenses(criteria)
        if not matches:
            raise ValidationError("No matching transaction was found to delete.")
        for expense in matches:
            self._expense_service.delete_expense(int(expense["id"]))
        return len(matches), {**matches[0], "criteria_label": self._expense_criteria_label(criteria)}

    @staticmethod
    def _expense_criteria_label(criteria: dict | list) -> str:
        if isinstance(criteria, list):
            labels = [AgentService._expense_criteria_label(item) for item in criteria if isinstance(item, dict)]
            return " or ".join(label for label in labels if label) or "the requested criteria"
        if not isinstance(criteria, dict):
            return "the requested criteria"
        if criteria.get("month"):
            return f"month {criteria['month']}"
        if criteria.get("date_after"):
            return f"dates after {criteria['date_after']}"
        if criteria.get("date_before"):
            return f"dates before {criteria['date_before']}"
        if criteria.get("date_from") or criteria.get("date_to"):
            return f"date range {criteria.get('date_from', '')} to {criteria.get('date_to', '')}".strip()
        return str(criteria.get("description") or criteria.get("category") or "the requested criteria")

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
        if tool_name == "retrieve_finance_context":
            if self._rag_service is None:
                return {"error": "RAG service is not available."}
            return self._rag_service.retrieve_context(str(arguments.get("question") or "").strip(), top_k=arguments.get("top_k"))
        if tool_name == "get_upcoming_recurring_items":
            if arguments.get("current_month_only"):
                today = datetime.now(UTC).date()
                next_month = today.replace(day=28) + timedelta(days=4)
                month_end = next_month.replace(day=1) - timedelta(days=1)
                days = max(1, (month_end - today).days + 1)
            else:
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
                "description": "Review late unpaid reminders plus recurring bills due from today through the end of the current month. Today is included.",
                "automation_focus": "Automates the current-month recurring bill review. This is not the all-bills email and not only the 7-day email window.",
                "default_task": (
                    "Run the current-month upcoming bills workflow. Highlight late unpaid reminders and bills due from today through "
                    "the end of the current month, explain cash-flow impact, and draft a concise reminder email. Today is included."
                ),
                "steps": [
                    {"tool": "get_dashboard_summary", "arguments": {}, "action": "Captured the current month cash position before reminders are prepared."},
                    {"tool": "get_upcoming_recurring_items", "arguments": {"current_month_only": True}, "action": "Scanned late unpaid reminders and current-month recurring items from today through month end."},
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
        if AgentService._looks_like_email_dispatch_command(normalized):
            return True
        action_words = ("add", "create", "generate", "set up", "update", "change", "edit", "delete", "remove", "replace", "set", "send")
        domain_words = ("reminder", "recurring", "bill", "bills", "cost", "costs", "subscription", "transaction", "expense", "income", "budget", "email", "report")
        return any(word in normalized for word in action_words) and any(word in normalized for word in domain_words)

    @staticmethod
    def _looks_like_report_generation_command(task: str) -> bool:
        normalized = task.lower()
        return "report" in normalized and any(
            word in normalized for word in ("generate", "create", "build", "prepare", "refresh", "summarise", "summarize")
        )

    @staticmethod
    def _looks_like_email_dispatch_command(task: str) -> bool:
        normalized = task.lower()
        dispatch_requested = (
            re.search(r"\b(send|mail)\b", normalized) is not None
            or "email me" in normalized
            or "email the" in normalized
            or "email my" in normalized
            or "email this" in normalized
        )
        return dispatch_requested and any(
            word in normalized for word in ("report", "briefing", "summary", "bill", "bills", "due", "financial", "finance", "month-end", "month end", "upcoming")
        )

    @staticmethod
    def _looks_like_upcoming_bills_email_command(task: str) -> bool:
        normalized = task.lower()
        return any(word in normalized for word in ("bill", "bills", "due", "upcoming")) and not any(
            phrase in normalized for phrase in ("financial report", "finance report", "month-end", "month end")
        )

    @staticmethod
    def _looks_like_all_upcoming_bills_email_command(task: str) -> bool:
        normalized = task.lower()
        return (
            any(phrase in normalized for phrase in ("all upcoming bills", "all projected upcoming bills", "all bills"))
            and AgentService._looks_like_upcoming_bills_email_command(normalized)
        )

    @staticmethod
    def _looks_like_financial_report_email_command(task: str) -> bool:
        normalized = task.lower()
        return any(phrase in normalized for phrase in ("financial report", "finance report", "current report", "month-end", "month end")) or (
            "report" in normalized and any(word in normalized for word in ("financial", "finance", "current", "monthly", "email", "send"))
        )

    @staticmethod
    def _parse_final_payload(content: str) -> dict:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = AgentService._parse_python_style_payload(content) or AgentService._parse_relaxed_json_payload(content) or {
                "headline": "Finance briefing generated",
                "summary": content.strip() or "No summary returned.",
                "risk_level": "medium",
                "recommended_actions": [],
                "email_subject": "Monthly finance briefing",
                "email_draft": content.strip() or "No email draft returned.",
            }

        return {
            "headline": str(parsed.get("headline") or "Finance briefing generated"),
            "summary": AgentService._format_structured_summary(parsed),
            "risk_level": str(parsed.get("risk_level") or "medium").lower(),
            "recommended_actions": AgentService._normalize_recommended_actions(parsed.get("recommended_actions")),
            "email_subject": str(parsed.get("email_subject") or "Monthly finance briefing"),
            "email_draft": AgentService._with_standard_email_signoff(
                str(parsed.get("email_draft") or AgentService._build_email_ready_summary(parsed))
            ),
        }

    @staticmethod
    def _enrich_sparse_cfo_briefing(payload: dict, context: dict, task: str) -> dict:
        if not AgentService._looks_like_briefing_request(task):
            return payload
        if (
            not AgentService._briefing_payload_is_sparse(payload)
            and not AgentService._full_cfo_briefing_is_incomplete(payload, task)
        ):
            return payload

        enriched = AgentService._build_cfo_briefing_from_context(context)
        merged = dict(payload)
        merged["headline"] = enriched["headline"]
        merged["summary"] = enriched["summary"]
        merged["risk_level"] = enriched["risk_level"]
        existing_actions = AgentService._normalize_recommended_actions(payload.get("recommended_actions"))
        enriched_actions = AgentService._normalize_recommended_actions(enriched.get("recommended_actions"))
        merged["recommended_actions"] = list(dict.fromkeys([*existing_actions, *enriched_actions]))[:5]
        merged["email_subject"] = enriched["email_subject"]
        merged["email_draft"] = AgentService._with_standard_email_signoff(enriched["email_draft"])
        return merged

    @staticmethod
    def _looks_like_briefing_request(task: str) -> bool:
        normalized = str(task or "").lower()
        return any(
            phrase in normalized
            for phrase in (
                "briefing",
                "cfo",
                "cash-flow risk",
                "cash flow risk",
                "recurring bill pressure",
                "email-ready summary",
                "email ready summary",
            )
        )

    @staticmethod
    def _briefing_payload_is_sparse(payload: dict) -> bool:
        summary = str(payload.get("summary") or "").strip()
        email_draft = str(payload.get("email_draft") or "").strip()
        generic_email = re.search(r"(?i)\bmonthly finance briefing\.?\b", email_draft) is not None
        cash_flow_only = re.fullmatch(r"(?is)\s*cash flow:\s*[-+]?[\d,.]+\.?\s*", summary) is not None
        placeholder_summary = summary.lower() in {
            "no summary returned.",
            "task completed successfully.",
            "request completed.",
        }
        return cash_flow_only or generic_email or placeholder_summary

    @staticmethod
    def _full_cfo_briefing_is_incomplete(payload: dict, task: str) -> bool:
        normalized_task = str(task or "").lower()
        requires_full_cfo = (
            "cfo" in normalized_task
            or "cash-flow risk" in normalized_task
            or "cash flow risk" in normalized_task
            or "recurring bill pressure" in normalized_task
            or "email-ready summary" in normalized_task
            or "email ready summary" in normalized_task
        )
        if not requires_full_cfo:
            return False

        summary = str(payload.get("summary") or "").lower()
        email_draft = str(payload.get("email_draft") or "").lower()
        actions = AgentService._normalize_recommended_actions(payload.get("recommended_actions"))
        required_summary_sections = (
            "cash-flow risk:",
            "recurring bill pressure:",
        )
        has_required_summary = all(section in summary for section in required_summary_sections)
        has_email_format = "dear user" in email_draft and "kind regards" in email_draft and "monetra organisation" in email_draft
        return not has_required_summary or not actions or not has_email_format

    @staticmethod
    def _build_cfo_briefing_from_context(context: dict) -> dict:
        dashboard = AgentService._context_block(context, "dashboard", "get_dashboard_summary")
        pulse = AgentService._context_block(context, "financial_pulse", "get_financial_pulse")
        category_insights = AgentService._context_block(context, "category_insights", "get_category_insights")
        prediction = AgentService._context_block(context, "prediction", "get_spending_prediction")
        recurring = AgentService._context_block(context, "upcoming_recurring_items", "get_upcoming_recurring_items")

        month_label = str(dashboard.get("month_label") or "current month")
        budget = AgentService._as_float(dashboard.get("monthly_budget"))
        income = AgentService._as_float(dashboard.get("monthly_income") or pulse.get("cash_in"))
        expenses = AgentService._as_float(dashboard.get("monthly_expenses") or pulse.get("cash_out"))
        net_cash_flow = AgentService._as_float(dashboard.get("net_cash_flow"))
        remaining_budget = AgentService._as_float(dashboard.get("remaining_budget"))
        status = str(dashboard.get("status") or "").strip().lower()

        risk_level = "low"
        if net_cash_flow is not None and net_cash_flow < 0:
            risk_level = "high"
        elif (remaining_budget is not None and remaining_budget < 0) or status in {"over", "over_budget", "over budget"}:
            risk_level = "medium"

        cash_flow_line = AgentService._cash_flow_risk_line(net_cash_flow, income, expenses)
        budget_line = AgentService._budget_pressure_line(expenses, budget, remaining_budget, status)
        recurring_line = AgentService._recurring_pressure_line(recurring)
        category_line = AgentService._category_pressure_line(category_insights)
        forecast_line = AgentService._forecast_line(prediction, budget)

        summary_lines = [
            cash_flow_line,
            budget_line,
            recurring_line,
            category_line,
            forecast_line,
        ]
        actions = AgentService._cfo_recommended_actions(risk_level, recurring, category_insights, prediction)
        subject = f"[Monetra] {month_label.title()} Monthly Finance Briefing"
        email_draft = AgentService._compose_cfo_email(subject, summary_lines, actions)
        return {
            "headline": f"{month_label.title()} CFO-style finance briefing",
            "summary": "\n".join(summary_lines),
            "risk_level": risk_level,
            "recommended_actions": actions,
            "email_subject": subject,
            "email_draft": email_draft,
        }

    @staticmethod
    def _context_block(context: dict, compact_key: str, tool_key: str) -> dict:
        value = context.get(compact_key) or context.get(tool_key) or {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _cash_flow_risk_line(net_cash_flow: float | None, income: float | None, expenses: float | None) -> str:
        if net_cash_flow is None:
            return "Cash-flow risk: Monetra reviewed the available dashboard context, but net cash flow was not returned by the backend tools."
        if net_cash_flow < 0:
            stance = "high because spending is currently greater than recorded income"
        elif expenses is not None and income and expenses > income * 0.8:
            stance = "moderate because spending is using a large share of recorded income"
        else:
            stance = "low because recorded income is comfortably above current spending"
        detail = f"net cash flow is {AgentService._format_gbp(net_cash_flow)}"
        if income is not None and expenses is not None:
            detail += f" after {AgentService._format_gbp(income)} income and {AgentService._format_gbp(expenses)} expenses"
        return f"Cash-flow risk: {stance}; {detail}."

    @staticmethod
    def _budget_pressure_line(
        expenses: float | None,
        budget: float | None,
        remaining_budget: float | None,
        status: str,
    ) -> str:
        if expenses is None or budget is None:
            return "Budget pressure: Monetra could not calculate utilisation because budget or expense totals were unavailable."
        utilisation = (expenses / budget * 100) if budget else 0.0
        status_text = "within budget" if status in {"", "within", "on_track", "on track"} else status.replace("_", " ")
        remaining = (
            f", leaving {AgentService._format_gbp(remaining_budget)} remaining"
            if remaining_budget is not None
            else ""
        )
        return (
            "Budget pressure: Current spend is "
            f"{AgentService._format_gbp(expenses)} against a {AgentService._format_gbp(budget)} monthly budget "
            f"({utilisation:.1f}% used){remaining}; status is {status_text}."
        )

    @staticmethod
    def _recurring_pressure_line(recurring: dict) -> str:
        late_items = AgentService._recurring_items(recurring, "late_occurrences", "late_reminders")
        upcoming_items = AgentService._recurring_items(recurring, "next_occurrences", "occurrences", "items")
        if late_items:
            examples = "; ".join(AgentService._format_recurring_item(item) for item in late_items[:3])
            return f"Recurring bill pressure: {len(late_items)} late unpaid reminder(s) need attention: {examples}."
        if upcoming_items:
            examples = "; ".join(AgentService._format_recurring_item(item) for item in upcoming_items[:3])
            return f"Recurring bill pressure: {len(upcoming_items)} upcoming reminder(s) are in the review window: {examples}."
        return "Recurring bill pressure: No late or upcoming recurring reminders were returned in the review window."

    @staticmethod
    def _category_pressure_line(category_insights: dict) -> str:
        top_categories = category_insights.get("top_categories") or []
        if not isinstance(top_categories, list) or not top_categories:
            return "Spending pressure: No category concentration was returned for this month."
        formatted = []
        for item in top_categories[:3]:
            if not isinstance(item, dict):
                continue
            category = str(item.get("category") or item.get("name") or "Uncategorised")
            amount = AgentService._format_gbp(AgentService._as_float(item.get("amount") or item.get("total")) or 0.0)
            formatted.append(f"{category} at {amount}")
        return f"Spending pressure: The largest categories are {', '.join(formatted)}." if formatted else "Spending pressure: No category concentration was returned for this month."

    @staticmethod
    def _forecast_line(prediction: dict, budget: float | None) -> str:
        if prediction.get("error"):
            return f"Forecast: Prediction was unavailable because {prediction['error']}"
        predicted = AgentService._as_float(
            prediction.get("predicted_spending")
            or prediction.get("predicted_total")
            or prediction.get("forecast")
        )
        if predicted is None:
            return "Forecast: No next-month forecast was returned by the prediction tool."
        comparison = ""
        if budget is not None:
            comparison = " and sits within budget" if predicted <= budget else " and is above the current monthly budget"
        return f"Forecast: Next-month spending is projected at {AgentService._format_gbp(predicted)}{comparison}."

    @staticmethod
    def _cfo_recommended_actions(
        risk_level: str,
        recurring: dict,
        category_insights: dict,
        prediction: dict,
    ) -> list[str]:
        actions: list[str] = []
        if risk_level == "high":
            actions.append("Reduce or defer non-essential spending until cash flow returns positive.")
        elif risk_level == "medium":
            actions.append("Review discretionary spending before adding more commitments this month.")
        else:
            actions.append("Keep current spend controls in place while cash flow remains positive.")

        late_items = AgentService._recurring_items(recurring, "late_occurrences", "late_reminders")
        upcoming_items = AgentService._recurring_items(recurring, "next_occurrences", "occurrences", "items")
        if late_items:
            actions.append("Verify or pay late reminders so recurring commitments do not stay overdue.")
        elif upcoming_items:
            actions.append("Check upcoming reminders before their due dates and verify paid transactions once completed.")

        top_categories = category_insights.get("top_categories") or []
        if isinstance(top_categories, list) and top_categories:
            category = str((top_categories[0] or {}).get("category") or "the largest category")
            actions.append(f"Monitor {category} because it is the largest current spending pressure.")

        if prediction and not prediction.get("error"):
            actions.append("Compare the next-month forecast against the monthly budget before carrying over savings.")
        return actions[:4]

    @staticmethod
    def _compose_cfo_email(subject: str, summary_lines: list[str], actions: list[str]) -> str:
        cash_flow = summary_lines[0] if len(summary_lines) > 0 else "Cash-flow risk: Not available."
        budget = summary_lines[1] if len(summary_lines) > 1 else "Budget pressure: Not available."
        recurring = summary_lines[2] if len(summary_lines) > 2 else "Recurring bill pressure: Not available."
        category = summary_lines[3] if len(summary_lines) > 3 else "Spending pressure: Not available."
        forecast = summary_lines[4] if len(summary_lines) > 4 else "Forecast: Not available."
        lines = [
            f"Subject: {subject}",
            "",
            "Dear User,",
            "",
            "Please find below your CFO-style monthly finance briefing.",
            "",
            "Cash-flow and budget position:",
            f"- {cash_flow}",
            f"- {budget}",
            "",
            "Recurring bill pressure:",
            f"- {recurring}",
            "",
            "Spending and forecast:",
            f"- {category}",
            f"- {forecast}",
        ]
        if actions:
            lines.extend(["", "Recommended actions:"])
            lines.extend(f"- {action}" for action in actions)
        return "\n".join(lines)

    @staticmethod
    def _recurring_items(recurring: dict, *keys: str) -> list[dict]:
        for key in keys:
            value = recurring.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []

    @staticmethod
    def _format_recurring_item(item: dict) -> str:
        description = str(item.get("description") or item.get("name") or "Recurring reminder")
        due_date = str(item.get("due_date") or item.get("date") or item.get("occurrence_date") or "").strip()
        amount = AgentService._as_float(item.get("amount") or item.get("cost"))
        amount_text = f" for {AgentService._format_gbp(amount)}" if amount is not None else ""
        due_text = f" due {due_date}" if due_date else ""
        return f"{description}{amount_text}{due_text}"

    @staticmethod
    def _as_float(value) -> float | None:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _format_gbp(value: float) -> str:
        return f"GBP {float(value):,.2f}"

    @staticmethod
    def _parse_python_style_payload(content: str) -> dict | None:
        try:
            import ast

            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end <= start:
                return None
            parsed = ast.literal_eval(content[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    @staticmethod
    def _parse_relaxed_json_payload(content: str) -> dict | None:
        raw = str(content or "").strip()
        if "{" not in raw or "}" not in raw:
            return None

        keys = (
            "headline",
            "summary",
            "risk_level",
            "recommended_actions",
            "email_subject",
            "email_draft",
        )
        parsed: dict[str, object] = {}
        for index, key in enumerate(keys):
            following_keys = "|".join(re.escape(next_key) for next_key in keys[index + 1 :])
            if following_keys:
                pattern = rf'"{re.escape(key)}"\s*:\s*(?P<value>.*?)(?=,\s*"({following_keys})"\s*:|\s*}}\s*$)'
            else:
                pattern = rf'"{re.escape(key)}"\s*:\s*(?P<value>.*?)(?=\s*}}\s*$)'
            match = re.search(pattern, raw, flags=re.DOTALL)
            if not match:
                continue
            value = match.group("value").strip().rstrip(",").strip()
            parsed[key] = AgentService._parse_relaxed_json_value(value)

        return parsed if parsed else None

    @staticmethod
    def _parse_relaxed_json_value(value: str):
        cleaned = str(value or "").strip()
        if len(cleaned) >= 2 and cleaned[0] == '"' and cleaned[-1] == '"':
            cleaned = cleaned[1:-1]
            cleaned = cleaned.replace('\\"', '"').replace("\\n", "\n").replace("\\r", "\r")
            return cleaned.strip()
        if cleaned.startswith("[") and cleaned.endswith("]"):
            try:
                parsed = json.loads(cleaned)
                return parsed
            except json.JSONDecodeError:
                items = re.findall(r'"([^"]+)"', cleaned, flags=re.DOTALL)
                return [item.strip() for item in items if item.strip()]
        return cleaned.strip('"').strip()

    @staticmethod
    def _format_structured_summary(parsed: dict) -> str:
        summary = str(parsed.get("summary") or "").strip()
        structured_keys = (
            "cash_flow",
            "recurring_bills",
            "budget_pressure",
            "spending_pressure",
            "forecast",
        )
        if summary and not any(str(parsed.get(key) or "").strip() for key in structured_keys):
            return summary

        sections = [
            ("Cash flow", parsed.get("cash_flow")),
            ("Recurring bill pressure", parsed.get("recurring_bills")),
            ("Budget pressure", parsed.get("budget_pressure")),
            ("Spending pressure", parsed.get("spending_pressure")),
            ("Forecast", parsed.get("forecast")),
            ("Summary", summary),
        ]
        lines = [f"{label}: {value}" for label, value in sections if str(value or "").strip()]
        return "\n".join(lines) if lines else "No summary returned."

    @staticmethod
    def _build_email_ready_summary(parsed: dict) -> str:
        lines = [
            str(parsed.get("email_subject") or "Monthly finance briefing"),
            "",
            str(parsed.get("cash_flow") or "").strip(),
            str(parsed.get("recurring_bills") or "").strip(),
        ]
        actions = AgentService._normalize_recommended_actions(parsed.get("recommended_actions"))
        if actions:
            lines.extend(["", "Recommended actions:"])
            lines.extend(f"- {action}" for action in actions)
        return "\n".join(line for line in lines if line or line == "")

    @staticmethod
    def _with_standard_email_signoff(email_draft: str) -> str:
        cleaned = str(email_draft or "").strip()
        cleaned = re.sub(
            r"(?is)\n*\s*(best regards|kind regards|regards),?\s*\n+.*$",
            "",
            cleaned,
        ).strip()
        cleaned = re.sub(
            r"(?is)\s*(best regards|kind regards|regards),?\s*(?:\n|\r|\s)*(?:monetra organisation|rushabh dharamshi|the finance operations team|the finance team)?\s*$",
            "",
            cleaned,
        ).strip()
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        if not cleaned:
            return "Kind Regards,\nMonetra Organisation"
        return f"{cleaned}\n\nKind Regards,\nMonetra Organisation"

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
        frequency = str(parsed.get("frequency") or "monthly").strip().lower()
        if frequency in {"one-time", "one time", "one-off", "one off", "single", "once"}:
            frequency = "once"

        return {
            "category": str(parsed.get("category") or "General").strip(),
            "description": str(parsed.get("description") or "Recurring reminder").strip(),
            "amount": round(float(amount), 2),
            "entry_type": "expense",
            "frequency": frequency,
            "start_date": str(parsed.get("start_date") or fallback_date).strip(),
            "end_date": str(parsed.get("end_date") or "").strip() or None,
            "active": bool(parsed.get("active", True)),
        }

    def _upsert_matching_reminder(self, payload: dict) -> tuple[dict, str, str]:
        matching_items = self._find_matching_reminders(
            {
                "description": payload.get("description"),
                "category": payload.get("category"),
                "frequency": payload.get("frequency"),
                "entry_type": payload.get("entry_type"),
            }
        )
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
        if frequency == "once":
            return {
                "start_date": start_date,
                "end_date": start_date,
            }

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
        if end_date and self._is_end_exclusive(task):
            end_date = (datetime.strptime(end_date, "%Y-%m-%d").date() - timedelta(days=1)).isoformat()
            if end_date < start_date:
                raise ValidationError("The reminder range does not include any due dates.")
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
                    "name": "retrieve_finance_context",
                    "description": "Retrieve semantically relevant finance context for grounded question answering.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The finance question to ground against the RAG knowledge base.",
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "How many relevant knowledge chunks to retrieve.",
                            }
                        },
                        "required": ["question"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_upcoming_recurring_items",
                    "description": "Get upcoming recurring expense reminders.",
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
