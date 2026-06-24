from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from budget_tracker_api.errors import NotFoundError, ServiceUnavailableError, ValidationError
from budget_tracker_api.services.agent_memory_service import AgentMemoryService
from budget_tracker_api.services.metric_registry import FinanceIntent, FinanceIntentRouter, MetricRegistry
from budget_tracker_api.services.rag_chunking import RagChunkingService


class RagService:
    def __init__(
        self,
        *,
        expense_service,
        recurring_service,
        analytics_service,
        prediction_service,
        settings_service,
        agent_run_repository,
        embedding_client,
        answer_client,
        memory_service: AgentMemoryService,
        persist_directory: Path,
        manifest_path: Path,
        collection_name: str,
        chunk_size: int,
        chunk_overlap: int,
        top_k: int = 6,
        chroma_http_host: str = "",
        chroma_http_port: int = 8000,
        chroma_http_ssl: bool = False,
        user_id_provider=None,
        chroma_client_factory=None,
    ):
        self._expense_service = expense_service
        self._recurring_service = recurring_service
        self._analytics_service = analytics_service
        self._prediction_service = prediction_service
        self._settings_service = settings_service
        self._agent_run_repository = agent_run_repository
        self._embedding_client = embedding_client
        self._answer_client = answer_client
        self._memory_service = memory_service
        self._persist_directory = Path(persist_directory)
        self._manifest_path = Path(manifest_path)
        self._collection_name = collection_name
        self._chunker = RagChunkingService(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self._top_k = max(1, min(int(top_k), 12))
        self._chroma_http_host = str(chroma_http_host or "").strip()
        self._chroma_http_port = int(chroma_http_port)
        self._chroma_http_ssl = bool(chroma_http_ssl)
        self._user_id_provider = user_id_provider
        self._chroma_client_factory = chroma_client_factory or self._default_chroma_client_factory
        self._retrieval_cache: dict[tuple[str, str, str, int], dict] = {}
        self._answer_cache: dict[tuple[str, str, str], dict] = {}
        self._intent_router = FinanceIntentRouter()
        self._metric_registry = self._build_metric_registry()

    def status(self) -> dict:
        manifest = self._load_manifest()
        return {
            "available": True,
            "collection_name": self._scoped_collection_name(),
            "indexed_at": manifest.get("indexed_at"),
            "document_count": int(manifest.get("document_count", 0)),
            "chunk_count": int(manifest.get("chunk_count", 0)),
            "signature": manifest.get("signature"),
        }

    def reindex(self, force: bool = False) -> dict:
        scope_key = self._scope_key()
        collection_name = self._scoped_collection_name()
        manifest_path = self._scoped_manifest_path()
        source_documents = self._build_source_documents()
        chunks = self._build_chunks(source_documents)
        signature = self._build_signature(source_documents)
        manifest = self._load_manifest(manifest_path)
        if not force and manifest.get("signature") == signature:
            return {
                **self.status(),
                "reindexed": False,
            }

        self._persist_directory.mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        client = self._create_chroma_client()
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        if chunks:
            embeddings = self._embedding_client.embed_texts([chunk["text"] for chunk in chunks])
            collection.upsert(
                ids=[chunk["id"] for chunk in chunks],
                documents=[chunk["text"] for chunk in chunks],
                metadatas=[chunk["metadata"] for chunk in chunks],
                embeddings=embeddings,
            )

        payload = {
            "indexed_at": self._utc_now(),
            "document_count": len(source_documents),
            "chunk_count": len(chunks),
            "signature": signature,
            "scope": scope_key,
        }
        manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._clear_scope_cache(scope_key)
        return {
            **payload,
            "available": True,
            "collection_name": collection_name,
            "reindexed": True,
        }

    def retrieve_context(self, question: str, top_k: int | None = None) -> dict:
        normalized_question = str(question or "").strip()
        if not normalized_question:
            raise ValidationError("question is required.")
        index_status = self.reindex(force=False)
        scope_key = self._scope_key()
        collection_name = self._scoped_collection_name()
        signature = str(index_status.get("signature") or "")
        client = self._create_chroma_client()
        collection = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
        n_results = max(1, min(int(top_k or self._top_k), 12))
        cache_key = (scope_key, signature, normalized_question, n_results)
        cached = self._retrieval_cache.get(cache_key)
        if cached is not None:
            return json.loads(json.dumps(cached))
        scoped_bill_question = self._is_bill_question(normalized_question) and self._extract_requested_month_scope(normalized_question) is not None
        query_variants = self._build_query_variants(normalized_question)
        query_embeddings = self._embedding_client.embed_texts(query_variants)
        merged_sources: dict[str, dict] = {}
        for query_embedding in query_embeddings:
            result = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
            for source in self._sources_from_query_result(result):
                key = f"{source['document_id']}::{source['metadata'].get('chunk_index', '')}"
                existing = merged_sources.get(key)
                if existing is None or source["score"] > existing["score"]:
                    merged_sources[key] = source

        calendar_sources = self._calendar_month_sources(collection, normalized_question)
        if scoped_bill_question:
            merged_sources = {}
            if calendar_sources:
                for source in calendar_sources:
                    key = f"{source['document_id']}::{source['metadata'].get('chunk_index', '')}"
                    merged_sources[key] = source
            else:
                no_match_source = self._no_calendar_match_source(normalized_question)
                merged_sources[no_match_source["document_id"]] = no_match_source
        else:
            for source in calendar_sources:
                key = f"{source['document_id']}::{source['metadata'].get('chunk_index', '')}"
                merged_sources[key] = source
            for source in self._essential_finance_sources(collection):
                key = f"{source['document_id']}::{source['metadata'].get('chunk_index', '')}"
                merged_sources.setdefault(key, source)

        sources = self._rerank_sources(normalized_question, list(merged_sources.values()), n_results)
        retrieval = {
            "question": normalized_question,
            "sources": sources,
            "retrieved_count": len(sources),
            "query_count": len(query_variants),
            "indexed_at": self._load_manifest().get("indexed_at"),
            "signature": signature,
        }
        self._retrieval_cache[cache_key] = json.loads(json.dumps(retrieval))
        return retrieval

    def answer_question(self, question: str) -> dict:
        normalized_question = str(question or "").strip()
        structured = self._structured_answer(normalized_question)
        if structured is not None:
            scope_key = self._scope_key()
            signature = self._current_source_signature()
            cache_key = (scope_key, signature, normalized_question)
            cached = self._answer_cache.get(cache_key)
            if cached is not None:
                return json.loads(json.dumps(cached))

            answer = {
                "question": question,
                "answer": structured["answer"],
                "confidence": "high",
                "follow_up_questions": [],
                "sources": structured["sources"],
                "generated_at": self._utc_now(),
                "signature": signature,
            }
            self._memory_service.remember(
                kind="rag_query",
                task=question,
                summary=structured["answer"],
                tools_used=structured["tools_used"],
                metadata={"confidence": "high", "answer_mode": "deterministic_registry"},
            )
            self._answer_cache[cache_key] = json.loads(json.dumps(answer))
            return answer

        retrieval = self.retrieve_context(question)
        scope_key = self._scope_key()
        signature = str(retrieval.get("signature") or "")
        cache_key = (scope_key, signature, normalized_question)
        cached = self._answer_cache.get(cache_key)
        if cached is not None:
            return json.loads(json.dumps(cached))

        if not retrieval["sources"]:
            raise ValidationError("No indexed finance knowledge is available yet.")

        context_lines = []
        for index, source in enumerate(retrieval["sources"], start=1):
            context_lines.append(f"[{index}] {source['source_label']}: {source['excerpt']}")
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Monetra's retrieval-augmented finance analyst. "
                    "Answer only from the retrieved finance context. "
                    "All currency is GBP. If the context is insufficient, say that clearly. "
                    "For recurring bills, use every retrieved recurring occurrence date as evidence. "
                    "For exact totals, dates, transaction IDs, and recurring reminders, prefer structured transaction and recurring source lines over agent memory. "
                    "Do arithmetic internally and show only the final concise calculation. "
                    "Use 'Cost: <value>' only for expenses, recurring bills, and payments. Use 'Monthly income: <value>' for income settings. "
                    "For non-exact analytical questions, write like a helpful finance assistant speaking to the user: natural, calm, specific, and practical. "
                    "Avoid robotic phrases such as 'based on the provided context' unless the context is genuinely limited. "
                    "Use short paragraphs, explain what the pattern means, and give one or two grounded next steps when the retrieved data supports them. "
                    "Do not invent missing figures, dates, categories, or recommendations. "
                    "Do not say 'planned expenses' unless the retrieved context explicitly names planned, recurring, or upcoming expenses; otherwise call them actual monthly expenses. "
                    "Return JSON with keys: answer, confidence, follow_up_questions. Always return follow_up_questions as an empty array."
                ),
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nRetrieved context:\n" + "\n".join(context_lines),
            },
        ]
        response = self._answer_client.chat(messages)
        content = ((response or {}).get("message") or {}).get("content", "")
        parsed = self._parse_answer_payload(content)
        answer = {
            "question": question,
            "answer": parsed["answer"],
            "confidence": parsed["confidence"],
            "follow_up_questions": parsed["follow_up_questions"],
            "sources": retrieval["sources"],
            "generated_at": self._utc_now(),
            "signature": signature,
        }
        self._memory_service.remember(
            kind="rag_query",
            task=question,
            summary=parsed["answer"],
            tools_used=["retrieve_finance_context"],
            metadata={"confidence": parsed["confidence"]},
        )
        self._answer_cache[cache_key] = json.loads(json.dumps(answer))
        return answer

    def _structured_answer(self, question: str) -> dict | None:
        normalized = str(question or "").lower()
        registry_answer = self._metric_registry.execute(self._intent_router.classify(normalized), normalized)
        if registry_answer is not None:
            return registry_answer
        expense_id = self._extract_expense_id_question(normalized)
        if expense_id is not None:
            return self._expense_id_answer(expense_id)
        recurring_id = self._extract_recurring_id_question(normalized)
        if recurring_id is not None:
            return self._recurring_id_answer(recurring_id)
        if self._is_latest_expense_question(normalized):
            return self._latest_expense_answer()
        if self._is_next_payment_due_question(normalized):
            return self._next_payment_due_answer()
        if self._is_late_reminder_question(normalized):
            return self._late_reminder_answer()
        if self._is_recurring_reminder_question(normalized):
            return self._recurring_reminder_answer(normalized)
        if self._is_spending_total_question(normalized):
            return self._spending_total_answer(question)
        return None

    def _build_metric_registry(self) -> MetricRegistry:
        return MetricRegistry(
            {
                FinanceIntent.CASH_FLOW: lambda _: self._cash_flow_answer(),
                FinanceIntent.MONTHLY_EXPENSES: lambda _: self._dashboard_metric_answer("monthly_expenses"),
                FinanceIntent.MONTHLY_BUDGET: lambda question: self._monthly_budget_answer(question),
                FinanceIntent.WEEKLY_SPENDING: lambda _: self._dashboard_metric_answer("weekly_spending"),
                FinanceIntent.BUDGET_STATUS: lambda _: self._dashboard_metric_answer("budget_status"),
                FinanceIntent.AVERAGE_DAILY_BURN: lambda _: self._kpi_studio_metric_answer("average daily burn"),
                FinanceIntent.MONTH_END_FORECAST: lambda _: self._kpi_studio_metric_answer("month end forecast"),
                FinanceIntent.LARGEST_CATEGORY_SHARE: lambda _: self._kpi_studio_metric_answer("largest category share"),
                FinanceIntent.CURRENT_MONTH_TRANSACTIONS: lambda _: self._kpi_studio_metric_answer("current month transactions"),
                FinanceIntent.REMAINING_BUDGET: lambda _: self._remaining_budget_answer(),
                FinanceIntent.BUDGET_USAGE: lambda _: self._budget_consumption_answer(),
                FinanceIntent.MONTHLY_INCOME: lambda question: self._monthly_income_answer(question),
                FinanceIntent.FINANCIAL_STATUS: lambda _: self._financial_status_answer(),
                FinanceIntent.AVERAGE_TRANSACTION: lambda _: self._financial_pulse_metric_answer("average transaction"),
                FinanceIntent.SPEND_VELOCITY: lambda _: self._financial_pulse_metric_answer("spend velocity"),
                FinanceIntent.INCOME_COVERAGE: lambda _: self._financial_pulse_metric_answer("income coverage"),
                FinanceIntent.TOP_CATEGORY_SHARE: lambda _: self._financial_pulse_metric_answer("top category share"),
                FinanceIntent.BUDGET_RUNWAY: lambda _: self._financial_pulse_metric_answer("budget runway"),
                FinanceIntent.HEALTH_SCORE: lambda _: self._financial_pulse_metric_answer("health score"),
                FinanceIntent.CURRENT_PERIOD: lambda _: self._comparison_metric_answer("current period"),
                FinanceIntent.AVERAGE_SPEND: lambda _: self._comparison_metric_answer("average spend"),
                FinanceIntent.STRONGEST_PERIOD: lambda _: self._comparison_metric_answer("strongest period"),
                FinanceIntent.CHANGE_VS_PREVIOUS: lambda _: self._comparison_metric_answer("change vs previous"),
                FinanceIntent.PIGGY_BANK_BALANCE: lambda _: self._piggy_bank_answer("balance"),
                FinanceIntent.PIGGY_BANK_CONTRIBUTION: lambda _: self._piggy_bank_answer("contribution"),
                FinanceIntent.PIGGY_BANK_CARRYOVER: lambda _: self._piggy_bank_answer("carryover"),
                FinanceIntent.MONTHLY_TOP_CATEGORIES: lambda _: self._monthly_category_insights_answer("top"),
                FinanceIntent.MONTHLY_BOTTOM_CATEGORIES: lambda _: self._monthly_category_insights_answer("bottom"),
                FinanceIntent.MONTHLY_CATEGORY_INSIGHTS: lambda _: self._monthly_category_insights_answer("summary"),
                FinanceIntent.MONTHLY_SPEND_EXTREMES: lambda _: self._monthly_spend_extremes_answer(),
                FinanceIntent.CATEGORY_SPEND_EXTREMES: lambda question: self._category_spend_extremes_answer(question),
            }
        )

    def _current_source_signature(self) -> str:
        return self._build_signature(self._build_source_documents())

    def _scope_key(self) -> str:
        if self._user_id_provider is None:
            return "global"
        try:
            user_id = int(self._user_id_provider() or 1)
        except (TypeError, ValueError):
            user_id = 1
        return f"user-{max(user_id, 1)}"

    def _scoped_collection_name(self) -> str:
        scope_key = self._scope_key()
        if scope_key == "global":
            return self._collection_name
        return f"{self._collection_name}_{scope_key.replace('-', '_')}"

    def _scoped_manifest_path(self) -> Path:
        scope_key = self._scope_key()
        if scope_key == "global":
            return self._manifest_path
        suffix = self._manifest_path.suffix or ".json"
        return self._manifest_path.with_name(f"{self._manifest_path.stem}.{scope_key}{suffix}")

    def _clear_scope_cache(self, scope_key: str) -> None:
        self._retrieval_cache = {
            cache_key: value for cache_key, value in self._retrieval_cache.items() if cache_key[0] != scope_key
        }
        self._answer_cache = {
            cache_key: value for cache_key, value in self._answer_cache.items() if cache_key[0] != scope_key
        }

    def _monthly_income_answer(self, question: str = "") -> dict:
        requested_month = self._extract_requested_month_key(question)
        settings = self._settings_service.get_settings(requested_month)
        income = self._format_gbp(settings.get("monthly_income"))
        month_key = str(settings.get("income_month") or requested_month or "the current month")
        month_label = self._month_label(month_key)
        answer = f"Your monthly income for {month_label} is {income}."
        return {
            "answer": answer,
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    f"Budget settings {month_key}",
                    "settings",
                    f"settings::{month_key}",
                    f"Monthly income: {income}. Income month: {month_key}.",
                    {"month_key": month_key},
                )
            ],
            "tools_used": ["settings_lookup"],
        }

    def _monthly_budget_answer(self, question: str = "") -> dict:
        requested_month = self._extract_requested_month_key(question)
        settings = self._settings_service.get_settings(requested_month)
        month_key = str(settings.get("budget_month") or requested_month or settings.get("income_month") or "the current month")
        month_label = self._month_label(month_key)
        monthly_budget = self._format_gbp(settings.get("monthly_budget"))
        return {
            "answer": (
                f"Monthly budget for {month_label}: {monthly_budget}. "
                "This is the planned living-cost estimate for that month, not your income."
            ),
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    f"Budget settings {month_key}",
                    "settings",
                    f"settings::{month_key}",
                    f"Monthly budget: {monthly_budget}. Budget month: {month_key}.",
                    {"month_key": month_key},
                )
            ],
            "tools_used": ["settings_lookup"],
        }

    def _cash_flow_answer(self) -> dict:
        dashboard = self._analytics_service.dashboard()
        pulse = self._analytics_service.financial_pulse()
        month_key = str(dashboard.get("month_key") or "the current month")
        month_label = str(dashboard.get("month_label") or month_key)
        income = self._format_gbp(dashboard.get("monthly_income") or pulse.get("cash_in"))
        spending = self._format_gbp(dashboard.get("current_month_total") or pulse.get("cash_out"))
        net_cash_flow = self._format_gbp(dashboard.get("net_cash_flow") or pulse.get("net_cash_flow"))
        status = str(dashboard.get("status") or "").strip()
        answer = f"Your cash flow for {month_label} is {net_cash_flow}. Income: {income}. Spending: {spending}."
        if status:
            answer += f" Budget status: {status}."
        return {
            "answer": answer,
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    f"Dashboard cash flow {month_key}",
                    "dashboard",
                    f"dashboard::{month_key}",
                    f"Net cash flow: {net_cash_flow}. Income: {income}. Spending: {spending}. Budget status: {status or 'unknown'}.",
                    {"month_key": month_key},
                )
            ],
            "tools_used": ["dashboard_cash_flow_lookup"],
        }

    def _dashboard_metric_answer(self, metric: str) -> dict:
        dashboard = self._analytics_service.dashboard()
        month_key = str(dashboard.get("month_key") or "the current month")
        month_label = str(dashboard.get("month_label") or month_key)
        monthly_expenses = self._dashboard_monthly_expenses(dashboard)
        definitions = {
            "monthly_expenses": {
                "label": "Monthly expenses",
                "value": self._format_gbp(monthly_expenses),
                "meaning": "This is the actual expense total recorded for the current dashboard month.",
            },
            "monthly_budget": {
                "label": "Monthly budget",
                "value": self._format_gbp(dashboard.get("monthly_budget")),
                "meaning": "This is your planned living-cost estimate for the month, not your income.",
            },
            "weekly_spending": {
                "label": "Weekly spending",
                "value": self._format_gbp(dashboard.get("weekly_spending")),
                "meaning": "This is the expense total recorded in the current week.",
            },
            "budget_status": {
                "label": "Budget status",
                "value": str(dashboard.get("status") or "unknown"),
                "meaning": "This compares actual monthly expenses with the monthly budget.",
            },
        }
        selected = definitions[metric]
        answer = f"{selected['label']} for {month_label}: {selected['value']}. {selected['meaning']}"
        return {
            "answer": answer,
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    f"Budget overview {month_key}",
                    "dashboard",
                    f"dashboard::{month_key}",
                    (
                        f"Monthly budget: {self._format_gbp(dashboard.get('monthly_budget'))}. "
                        f"Monthly expenses: {self._format_gbp(monthly_expenses)}. "
                        f"Monthly income: {self._format_gbp(dashboard.get('monthly_income'))}. "
                        f"Net cash flow: {self._format_gbp(dashboard.get('net_cash_flow'))}. "
                        f"Remaining budget: {self._format_gbp(dashboard.get('remaining_budget'))}. "
                        f"Weekly spending: {self._format_gbp(dashboard.get('weekly_spending'))}. "
                        f"Budget status: {dashboard.get('status') or 'unknown'}."
                    ),
                    {"month_key": month_key},
                )
            ],
            "tools_used": ["dashboard_metric_lookup"],
        }

    def _piggy_bank_answer(self, metric: str) -> dict:
        dashboard = self._analytics_service.dashboard()
        month_key = str(dashboard.get("month_key") or datetime.now().strftime("%Y-%m"))
        month_label = str(dashboard.get("month_label") or month_key)
        monthly_income = self._as_float(dashboard.get("monthly_income"))
        monthly_expenses = self._dashboard_monthly_expenses(dashboard)
        monthly_budget = self._as_float(dashboard.get("monthly_budget"))
        current_cash_flow = monthly_income - monthly_expenses
        previous_carryover = self._previous_piggy_bank_carryover(month_key)
        piggy_bank_balance = max(previous_carryover + current_cash_flow, 0.0)
        positive_current_flow = max(current_cash_flow, 0.0)
        contribution_percent = (positive_current_flow / monthly_income * 100) if monthly_income > 0 else 0.0
        definitions = {
            "balance": (
                "Total piggy-bank balance",
                self._format_gbp(piggy_bank_balance),
                (
                    f"Calculation: {self._format_gbp(previous_carryover)} previous carryover + "
                    f"{self._format_gbp(current_cash_flow)} current-month cash flow, floored at GBP 0.00."
                ),
            ),
            "contribution": (
                "This month's piggy-bank impact",
                self._format_gbp(current_cash_flow),
                (
                    f"Calculation: {self._format_gbp(monthly_income)} monthly income - "
                    f"{self._format_gbp(monthly_expenses)} monthly expenses = {self._format_gbp(current_cash_flow)} cash flow. "
                    "Positive cash flow increases the piggy bank; negative cash flow reduces the existing buffer."
                ),
            ),
            "carryover": (
                "Previous carryover",
                self._format_gbp(previous_carryover),
                "This is the accumulated positive cash flow from months before the current dashboard month.",
            ),
        }
        label, value, meaning = definitions[metric]
        answer = (
            f"{label} for {month_label}: {value}. {meaning} "
            f"The monthly budget is {self._format_gbp(monthly_budget)} and is treated as a living-cost estimate, not the piggy-bank calculation."
        )
        return {
            "answer": answer,
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    f"Piggy bank {month_key}",
                    "piggy_bank",
                    f"piggy-bank::{month_key}",
                    (
                        f"Piggy bank balance: {self._format_gbp(piggy_bank_balance)}. "
                        f"Previous carryover: {self._format_gbp(previous_carryover)}. "
                        f"Monthly income: {self._format_gbp(monthly_income)}. "
                        f"Monthly expenses: {self._format_gbp(monthly_expenses)}. "
                        f"Current cash flow: {self._format_gbp(current_cash_flow)}. "
                        f"This month's impact: {self._format_gbp(current_cash_flow)}. "
                        f"Income flowing into piggy bank: {contribution_percent:.1f}%."
                    ),
                    {"month_key": month_key},
                )
            ],
            "tools_used": ["piggy_bank_metric_lookup"],
        }

    def _monthly_category_insights_answer(self, mode: str) -> dict:
        dashboard = self._analytics_service.dashboard()
        categories = self._analytics_service.category_insights()
        month_key = str(dashboard.get("month_key") or "the current month")
        month_label = str(dashboard.get("month_label") or month_key)
        top_categories = categories.get("top_categories") or []
        bottom_categories = categories.get("bottom_categories") or []

        def describe(items: list[dict]) -> str:
            if not items:
                return "No category data for this month."
            return ", ".join(f"{item.get('category')}: {self._format_gbp(item.get('amount'))}" for item in items)

        if mode == "top":
            answer = f"Top categories for {month_label}: {describe(top_categories)}"
        elif mode == "bottom":
            answer = f"Bottom categories for {month_label}: {describe(bottom_categories)}"
        else:
            answer = (
                f"Monthly insights for {month_label}: top categories are {describe(top_categories)}. "
                f"Bottom categories are {describe(bottom_categories)}. "
                f"Total spending in the category analysis is {self._format_gbp(categories.get('total_spending'))}."
            )
        return {
            "answer": answer,
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    f"Monthly category insights {month_key}",
                    "category_insights",
                    f"category-insights::{month_key}",
                    (
                        f"Top categories: {describe(top_categories)}. "
                        f"Bottom categories: {describe(bottom_categories)}. "
                        f"Total spending: {self._format_gbp(categories.get('total_spending'))}."
                    ),
                    {"month_key": month_key},
                )
            ],
            "tools_used": ["category_insights_lookup"],
        }

    def _monthly_spend_extremes_answer(self) -> dict:
        monthly_totals: dict[str, float] = {}
        for expense in self._expense_service.list_expenses(sort_direction="desc"):
            if str(expense.get("entry_type") or "expense") != "expense":
                continue
            expense_date = self._parse_date(expense.get("date"))
            if expense_date is None:
                continue
            month_key = expense_date.isoformat()[:7]
            monthly_totals[month_key] = monthly_totals.get(month_key, 0.0) + self._as_float(expense.get("amount"))

        if not monthly_totals:
            return {
                "answer": "I could not find any expense transactions to compare monthly spending.",
                "follow_up_questions": [],
                "sources": [self._structured_source("Monthly spend extremes", "monthly_spend_extremes", "monthly-spend-extremes::empty", "No expense transactions were found.")],
                "tools_used": ["monthly_spend_extremes_lookup"],
            }

        rounded_totals = {month: round(total, 2) for month, total in monthly_totals.items()}
        highest_month, highest_total = max(rounded_totals.items(), key=lambda item: (item[1], item[0]))
        lowest_month, lowest_total = min(rounded_totals.items(), key=lambda item: (item[1], item[0]))
        answer = (
            f"Your highest-spend month is {self._month_label(highest_month)} at {self._format_gbp(highest_total)}. "
            f"Your lowest-spend month is {self._month_label(lowest_month)} at {self._format_gbp(lowest_total)}. "
            "This uses expense transactions only; income records are excluded."
        )
        return {
            "answer": answer,
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    "Monthly spending totals",
                    "monthly_spend_extremes",
                    "monthly-spend-extremes::all",
                    "; ".join(f"{self._month_label(month)}: {self._format_gbp(total)}" for month, total in sorted(rounded_totals.items())),
                )
            ],
            "tools_used": ["monthly_spend_extremes_lookup"],
        }

    def _category_spend_extremes_answer(self, normalized_question: str) -> dict:
        scope = self._extract_requested_month_scope(normalized_question)
        dashboard = self._analytics_service.dashboard()
        if scope is None and not self._contains_any(normalized_question, "overall", "all time", "across all", "historical"):
            month_key = str(dashboard.get("month_key") or datetime.now().strftime("%Y-%m"))
            scope = {"start_month": month_key, "end_month": month_key}

        category_totals: dict[str, float] = {}
        for expense in self._expense_service.list_expenses(sort_direction="desc"):
            if str(expense.get("entry_type") or "expense") != "expense":
                continue
            expense_date = self._parse_date(expense.get("date"))
            if expense_date is None:
                continue
            month_key = expense_date.isoformat()[:7]
            if scope and month_key not in self._month_keys_between(scope["start_month"], scope["end_month"]):
                continue
            category = str(expense.get("category") or "Uncategorised")
            category_totals[category] = category_totals.get(category, 0.0) + self._as_float(expense.get("amount"))

        scope_text = "overall" if scope is None else self._scope_label(scope)
        if not category_totals:
            return {
                "answer": f"I could not find any expense categories to compare for {scope_text}.",
                "follow_up_questions": [],
                "sources": [self._structured_source("Category spend extremes", "category_spend_extremes", "category-spend-extremes::empty", f"No expense category totals were found for {scope_text}.")],
                "tools_used": ["category_spend_extremes_lookup"],
            }

        rounded_totals = {category: round(total, 2) for category, total in category_totals.items()}
        highest_category, highest_total = max(rounded_totals.items(), key=lambda item: (item[1], item[0]))
        lowest_category, lowest_total = min(rounded_totals.items(), key=lambda item: (item[1], item[0]))
        answer = (
            f"For {scope_text}, your highest-spend category is {highest_category} at {self._format_gbp(highest_total)}. "
            f"Your lowest-spend category is {lowest_category} at {self._format_gbp(lowest_total)}. "
            "This uses expense transactions only; income records are excluded."
        )
        return {
            "answer": answer,
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    f"Category spending totals {scope_text}",
                    "category_spend_extremes",
                    f"category-spend-extremes::{scope_text}",
                    "; ".join(f"{category}: {self._format_gbp(total)}" for category, total in sorted(rounded_totals.items())),
                    {"scope": scope_text},
                )
            ],
            "tools_used": ["category_spend_extremes_lookup"],
        }

    def _financial_pulse_metric_answer(self, normalized_question: str) -> dict:
        dashboard = self._analytics_service.dashboard()
        pulse = self._analytics_service.financial_pulse()
        metric = self._financial_pulse_metric(normalized_question) or "financial_pulse"
        month_key = str(dashboard.get("month_key") or "the current month")
        month_label = str(dashboard.get("month_label") or month_key)
        definitions = {
            "average_transaction": {
                "label": "Average transaction",
                "value": self._format_gbp(pulse.get("average_transaction")),
                "meaning": "This is the average size of recorded income and expense transactions counted this month.",
            },
            "spend_velocity": {
                "label": "Spend velocity",
                "value": f"{self._format_gbp(pulse.get('spend_velocity'))}/day",
                "meaning": "This is the current daily expense rate for the month so far.",
            },
            "income_coverage": {
                "label": "Income coverage",
                "value": f"{self._as_float(pulse.get('income_coverage')):.1f}%",
                "meaning": "This is monthly income divided by monthly expenses. A very high percentage usually means expenses are still low compared with income.",
            },
            "top_category_share": {
                "label": "Top category share",
                "value": f"{self._as_float(pulse.get('top_category_share')):.1f}%",
                "meaning": "This is the share of monthly expenses coming from the largest spending category.",
            },
            "budget_runway": {
                "label": "Budget runway",
                "value": f"{pulse.get('runway_days')} days" if pulse.get("runway_days") is not None else "Stable",
                "meaning": "This estimates how many days the remaining budget would last at the current daily spend rate.",
            },
            "health_score": {
                "label": "Health score",
                "value": f"{int(self._as_float(pulse.get('health_score')))} out of 100",
                "meaning": "This combines budget utilisation, spending concentration, cash flow, and transaction activity into one score.",
            },
        }
        selected = definitions[metric]
        answer = f"{selected['label']} for {month_label}: {selected['value']}. {selected['meaning']}"
        return {
            "answer": answer,
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    f"Financial pulse {month_key}",
                    "financial_pulse",
                    f"financial-pulse::{month_key}",
                    (
                        f"Average transaction: {self._format_gbp(pulse.get('average_transaction'))}. "
                        f"Spend velocity: {self._format_gbp(pulse.get('spend_velocity'))}/day. "
                        f"Income coverage: {self._as_float(pulse.get('income_coverage')):.1f}%. "
                        f"Top category share: {self._as_float(pulse.get('top_category_share')):.1f}%. "
                        f"Budget runway: {pulse.get('runway_days')} days. "
                        f"Health score: {int(self._as_float(pulse.get('health_score')))}."
                    ),
                    {"month_key": month_key},
                )
            ],
            "tools_used": ["financial_pulse_metric_lookup"],
        }

    def _kpi_studio_metric_answer(self, normalized_question: str) -> dict:
        dashboard = self._analytics_service.dashboard()
        month_key = str(dashboard.get("month_key") or datetime.now().strftime("%Y-%m"))
        month_label = str(dashboard.get("month_label") or month_key)
        metric = self._kpi_studio_metric(normalized_question) or "kpi_studio"
        expenses = [
            expense
            for expense in self._expense_service.list_expenses(sort_direction="desc")
            if str(expense.get("entry_type") or "expense") == "expense"
            and str(expense.get("date") or "").startswith(month_key)
        ]
        monthly_total = self._as_float(dashboard.get("current_month_total") or dashboard.get("monthly_expenses"))
        today = datetime.now()
        days_elapsed = max(today.day, 1)
        days_in_month = (date(today.year + int(today.month == 12), 1 if today.month == 12 else today.month + 1, 1) - timedelta(days=1)).day
        average_daily_burn = monthly_total / days_elapsed if monthly_total else 0.0
        month_end_forecast = average_daily_burn * days_in_month
        category_totals: dict[str, float] = {}
        for expense in expenses:
            category = str(expense.get("category") or "Uncategorised")
            category_totals[category] = category_totals.get(category, 0.0) + self._as_float(expense.get("amount"))
        top_category, top_amount = max(category_totals.items(), key=lambda item: item[1], default=("No category", 0.0))
        largest_category_share = (top_amount / monthly_total * 100) if monthly_total else 0.0
        definitions = {
            "month_end_forecast": (
                "Month-end forecast",
                self._format_gbp(month_end_forecast),
                f"Calculation: {self._format_gbp(monthly_total)} current-month expenses / {days_elapsed} elapsed days * {days_in_month} days in the month.",
            ),
            "largest_category_share": (
                "Largest category share",
                f"{largest_category_share:.1f}%",
                f"{top_category} is the largest current-month category. Calculation: {self._format_gbp(top_amount)} / {self._format_gbp(monthly_total)} * 100.",
            ),
            "average_daily_burn": (
                "Average daily burn",
                f"{self._format_gbp(average_daily_burn)}/day",
                f"Calculation: {self._format_gbp(monthly_total)} current-month expenses / {days_elapsed} elapsed days.",
            ),
            "current_month_transactions": (
                "Current-month transactions",
                str(len(expenses)),
                "This counts expense transactions dated in the current month.",
            ),
        }
        label, value, meaning = definitions[metric]
        answer = f"{label} for {month_label}: {value}. {meaning}"
        return {
            "answer": answer,
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    f"KPI studio {month_key}",
                    "kpi_studio",
                    f"kpi-studio::{month_key}",
                    (
                        f"Month-end forecast: {self._format_gbp(month_end_forecast)}. "
                        f"Largest category share: {largest_category_share:.1f}%. "
                        f"Average daily burn: {self._format_gbp(average_daily_burn)}/day. "
                        f"Current-month transactions: {len(expenses)}."
                    ),
                    {"month_key": month_key},
                )
            ],
            "tools_used": ["kpi_studio_metric_lookup"],
        }

    def _comparison_metric_answer(self, normalized_question: str) -> dict:
        metric = self._comparison_metric(normalized_question) or "comparison"
        expenses = [
            expense
            for expense in self._expense_service.list_expenses(sort_direction="desc")
            if str(expense.get("entry_type") or "expense") == "expense"
        ]
        now = datetime.now()
        current_month_start = date(now.year, now.month, 1)
        periods = []
        for index in range(3, -1, -1):
            month_start = self._add_months(current_month_start, -index)
            month_key = month_start.isoformat()[:7]
            total = sum(self._as_float(expense.get("amount")) for expense in expenses if str(expense.get("date") or "").startswith(month_key))
            periods.append(
                {
                    "key": month_key,
                    "label": month_start.strftime("%B %Y"),
                    "total": round(total, 2),
                }
            )
        current = periods[-1]
        previous = periods[-2] if len(periods) > 1 else None
        strongest = max(periods, key=lambda item: item["total"]) if periods else {"label": "No data", "total": 0.0}
        average_spend = sum(item["total"] for item in periods) / len(periods) if periods else 0.0
        change = None
        if previous and previous["total"] > 0:
            change = ((current["total"] - previous["total"]) / previous["total"]) * 100
        definitions = {
            "current_period": (
                "Current period",
                current["label"],
                "This is the latest month in the default monthly Comparison Lab window.",
            ),
            "average_spend": (
                "Average spend",
                self._format_gbp(average_spend),
                "This is the average expense spend across the four visible monthly comparison periods.",
            ),
            "strongest_period": (
                "Strongest period",
                f"{strongest['label']} | {self._format_gbp(strongest['total'])}",
                "This is the visible comparison period with the highest recorded expense spend.",
            ),
            "change_vs_previous": (
                "Change vs previous",
                "No baseline" if change is None else f"{change:+.1f}%",
                "This compares the current month with the immediately previous month.",
            ),
        }
        label, value, meaning = definitions[metric]
        answer = f"{label}: {value}. {meaning}"
        return {
            "answer": answer,
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    "Comparison lab default monthly window",
                    "comparison_lab",
                    "comparison-lab::monthly-default",
                    "; ".join(f"{item['label']}: {self._format_gbp(item['total'])}" for item in periods),
                )
            ],
            "tools_used": ["comparison_lab_metric_lookup"],
        }

    def _financial_status_answer(self) -> dict:
        dashboard = self._analytics_service.dashboard()
        pulse = self._analytics_service.financial_pulse()
        categories = self._analytics_service.category_insights()
        month_key = str(dashboard.get("month_key") or "the current month")
        month_label = str(dashboard.get("month_label") or month_key)
        income = self._format_gbp(dashboard.get("monthly_income") or pulse.get("cash_in"))
        expenses = self._format_gbp(dashboard.get("current_month_total") or pulse.get("cash_out"))
        net_cash_flow = self._format_gbp(dashboard.get("net_cash_flow") or pulse.get("net_cash_flow"))
        remaining_budget = self._format_gbp(dashboard.get("remaining_budget"))
        health_score = int(self._as_float(pulse.get("health_score")))
        status = str(dashboard.get("status") or "unknown").strip()
        narrative = str(pulse.get("narrative") or "").strip()
        top_categories = categories.get("top_categories") or []
        top_category = str((top_categories[0] or {}).get("category") or "").strip() if top_categories else ""

        answer_parts = [
            f"Your financial status looks {status} for {month_label}, with a health score of {health_score}/100.",
            f"The key numbers are: income {income}, actual monthly expenses {expenses}, net cash flow {net_cash_flow}, and remaining budget {remaining_budget}.",
        ]
        if top_category:
            answer_parts.append(f"Right now, {top_category} is where spending is most concentrated.")
        if narrative:
            answer_parts.append(narrative)
        answer_parts.append("One thing to note: planned expenses are separate from actual monthly expenses. This status is based on what is currently recorded in your dashboard.")
        return {
            "answer": " ".join(answer_parts),
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    f"Dashboard financial status {month_key}",
                    "dashboard",
                    f"dashboard::{month_key}",
                    f"Status: {status}. Income: {income}. Expenses: {expenses}. Net cash flow: {net_cash_flow}. Remaining budget: {remaining_budget}.",
                    {"month_key": month_key},
                ),
                self._structured_source(
                    f"Financial pulse {month_key}",
                    "financial_pulse",
                    f"financial-pulse::{month_key}",
                    f"Health score: {health_score}/100. Narrative: {narrative or 'none'}.",
                    {"month_key": month_key},
                ),
            ],
            "tools_used": ["dashboard_financial_status_lookup"],
        }

    def _remaining_budget_answer(self) -> dict:
        dashboard = self._analytics_service.dashboard()
        month_key = str(dashboard.get("month_key") or "the current month")
        month_label = str(dashboard.get("month_label") or month_key)
        monthly_budget = self._as_float(dashboard.get("monthly_budget"))
        expenses = self._as_float(dashboard.get("current_month_total") or dashboard.get("monthly_expenses"))
        remaining_budget = monthly_budget - expenses
        status = str(dashboard.get("status") or "").strip()
        budget_text = self._format_gbp(monthly_budget)
        expenses_text = self._format_gbp(expenses)
        remaining_text = self._format_gbp(remaining_budget)
        answer = (
            f"Your remaining budget for {month_label} is {remaining_text}. "
            f"Calculation: {budget_text} monthly budget - {expenses_text} monthly expenses = {remaining_text}. "
            "This is different from net cash flow, which is monthly income minus monthly expenses."
        )
        if status:
            answer += f" Budget status: {status}."
        return {
            "answer": answer,
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    f"Dashboard remaining budget {month_key}",
                    "dashboard",
                    f"dashboard::{month_key}",
                    f"Remaining budget: {remaining_text}. Monthly budget: {budget_text}. Monthly expenses: {expenses_text}.",
                    {"month_key": month_key},
                )
            ],
            "tools_used": ["dashboard_remaining_budget_lookup"],
        }

    def _budget_consumption_answer(self) -> dict:
        dashboard = self._analytics_service.dashboard()
        month_key = str(dashboard.get("month_key") or "the current month")
        month_label = str(dashboard.get("month_label") or month_key)
        monthly_budget = self._as_float(dashboard.get("monthly_budget"))
        expenses = self._as_float(dashboard.get("current_month_total") or dashboard.get("monthly_expenses"))
        percent_spent = self._as_float(dashboard.get("percent_spent"))
        if monthly_budget > 0 and "percent_spent" not in dashboard:
            percent_spent = (expenses / monthly_budget) * 100
        elif monthly_budget > 0:
            percent_spent = (expenses / monthly_budget) * 100

        budget_text = self._format_gbp(monthly_budget)
        expenses_text = self._format_gbp(expenses)
        percentage_text = f"{percent_spent:.2f}%"
        if monthly_budget <= 0:
            answer = "Budget consumption cannot be calculated because the monthly budget is GBP 0.00."
        else:
            answer = (
                f"Your budget consumption for {month_label} is {percentage_text}. "
                f"Calculation: {expenses_text} expenses / {budget_text} monthly budget * 100 = {percentage_text}."
            )
        return {
            "answer": answer,
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    f"Dashboard budget consumption {month_key}",
                    "dashboard",
                    f"dashboard::{month_key}",
                    f"Budget consumption: {percentage_text}. Expenses: {expenses_text}. Monthly budget: {budget_text}.",
                    {"month_key": month_key},
                )
            ],
            "tools_used": ["dashboard_budget_consumption_lookup"],
        }

    def _latest_expense_answer(self) -> dict | None:
        expenses = [
            expense
            for expense in self._expense_service.list_expenses("desc")
            if expense.get("entry_type") == "expense" and self._parse_date(expense.get("date")) is not None
        ]
        today = date.today()
        expenses = [
            expense
            for expense in expenses
            if (self._parse_date(expense.get("date")) or today) <= today
        ]
        if not expenses:
            return {
                "answer": "I could not find any completed expense transactions in the structured ledger.",
                "follow_up_questions": ["Do you want to review imported transactions for missing expense dates?"],
                "sources": [self._structured_source("Structured expense ledger", "expense_search", "expense-search::latest", "No completed expense transactions were found.")],
                "tools_used": ["find_latest_expense"],
            }
        latest = sorted(expenses, key=lambda item: (str(item.get("date") or ""), int(item.get("id") or 0)), reverse=True)[0]
        cost = self._format_gbp(latest.get("amount"))
        excerpt = (
            f"Transaction #{latest.get('id')} on {latest.get('date')}. Category {latest.get('category')}. "
            f"Description {latest.get('description')}. Cost: {cost}. Entry type expense."
        )
        latest_display_id = latest.get("user_expense_id", latest.get("id"))
        return {
            "answer": (
                f"The most recent expense is Transaction #{latest_display_id} on {latest.get('date')}. "
                f"Category: {latest.get('category')}. Description: {latest.get('description')}. Cost: {cost}."
            ),
            "follow_up_questions": ["Do you want the largest expenses for the same month?"],
            "sources": [self._structured_source(f"Transaction #{latest_display_id}", "expense", f"expense::{latest.get('id')}", excerpt, {"date": latest.get("date"), "category": latest.get("category"), "entry_type": "expense", "user_expense_id": latest_display_id})],
            "tools_used": ["find_latest_expense"],
        }

    def _expense_id_answer(self, expense_id: int) -> dict:
        try:
            expense = self._expense_service.get_expense_by_user_expense_id(expense_id)
        except NotFoundError:
            answer = f"I could not find an expense with ID {expense_id} for your signed-in account."
            return {
                "answer": answer,
                "follow_up_questions": [],
                "sources": [
                    self._structured_source(
                        f"Expense ID {expense_id}",
                        "expense_lookup",
                        f"expense::{expense_id}",
                        answer,
                        {"expense_id": expense_id, "found": False},
                    )
                ],
                "tools_used": ["expense_id_lookup"],
            }

        cost = self._format_gbp(expense.get("amount"))
        date_value = expense.get("date")
        category = expense.get("category")
        description = expense.get("description")
        display_id = expense.get("user_expense_id", expense_id)
        excerpt = (
            f"Expense ID {display_id} on {date_value}. Category {category}. "
            f"Description {description}. Cost: {cost}. Entry type expense."
        )
        return {
            "answer": (
                f"Expense ID {display_id} is {description}: {cost} on {date_value} "
                f"under {category}."
            ),
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    f"Expense ID {display_id}",
                    "expense",
                    f"expense::{expense.get('id', expense_id)}",
                    excerpt,
                    {
                        "expense_id": expense.get("id", expense_id),
                        "user_expense_id": display_id,
                        "date": date_value,
                        "category": category,
                        "entry_type": "expense",
                    },
                )
            ],
            "tools_used": ["expense_id_lookup"],
        }

    def _recurring_id_answer(self, recurring_id: int) -> dict:
        try:
            item = self._recurring_service.get_item(recurring_id)
        except NotFoundError:
            answer = f"I could not find a recurring reminder with ID {recurring_id} for your signed-in account."
            return {
                "answer": answer,
                "follow_up_questions": [],
                "sources": [
                    self._structured_source(
                        f"Recurring reminder ID {recurring_id}",
                        "recurring_lookup",
                        f"recurring::{recurring_id}",
                        answer,
                        {"recurring_id": recurring_id, "found": False},
                    )
                ],
                "tools_used": ["recurring_id_lookup"],
            }

        cost = self._format_gbp(item.get("amount"))
        active_text = "active" if item.get("active") else "paused"
        end_date = item.get("end_date") or "no end date"
        excerpt = (
            f"Recurring reminder ID {recurring_id}. Description {item.get('description')}. "
            f"Category {item.get('category')}. Cost: {cost}. Entry type {item.get('entry_type')}. "
            f"Frequency {item.get('frequency')}. Starts {item.get('start_date')}. Ends {end_date}. "
            f"Status {active_text}."
        )
        return {
            "answer": (
                f"Recurring reminder ID {recurring_id} is {item.get('description')}: {cost}, "
                f"{item.get('frequency')}, starting {item.get('start_date')}. Status: {active_text}."
            ),
            "follow_up_questions": [],
            "sources": [
                self._structured_source(
                    f"Recurring reminder ID {recurring_id}",
                    "recurring",
                    f"recurring::{recurring_id}",
                    excerpt,
                    {
                        "recurring_id": recurring_id,
                        "category": item.get("category"),
                        "entry_type": item.get("entry_type"),
                        "active": bool(item.get("active")),
                    },
                )
            ],
            "tools_used": ["recurring_id_lookup"],
        }

    def _next_payment_due_answer(self) -> dict:
        calendar = self._recurring_service.upcoming_calendar(90)
        reminders = [
            item
            for item in calendar.get("occurrences", [])
            if item.get("entry_type") == "expense" and self._parse_date(item.get("date")) is not None
        ]
        if not reminders:
            return {
                "answer": "I could not find any upcoming expense payments in the structured recurring calendar.",
                "follow_up_questions": ["Do you want to add a recurring payment reminder?"],
                "sources": [self._structured_source("Recurring calendar", "recurring_occurrence_search", "recurring-occurrence-search::next-payment", "No upcoming expense payment occurrences were found.")],
                "tools_used": ["find_next_payment_due"],
            }

        next_due_date = min(str(item.get("date") or "") for item in reminders)
        next_items = sorted(
            [item for item in reminders if str(item.get("date") or "") == next_due_date],
            key=lambda item: str(item.get("description") or ""),
        )
        first = next_items[0]
        cost = self._format_gbp(first.get("amount"))
        answer = (
            f"The next payment due is on {next_due_date} for {first.get('description')}. "
            f"Category: {first.get('category')}. Cost: {cost}."
        )
        if len(next_items) > 1:
            other_descriptions = ", ".join(str(item.get("description") or "Unnamed payment") for item in next_items[1:])
            answer += f" Other payments are also due on that date: {other_descriptions}."

        sources = []
        for item in next_items:
            item_cost = self._format_gbp(item.get("amount"))
            sources.append(
                self._structured_source(
                    f"Recurring due {item.get('date')}: {item.get('description')}",
                    "recurring_occurrence",
                    f"recurring-occurrence::{item.get('recurring_item_id')}::{item.get('date')}",
                    (
                        f"Recurring bill occurrence due on {item.get('date')}. "
                        f"Description {item.get('description')}. Category {item.get('category')}. "
                        f"Cost: {item_cost}. Entry type expense. Frequency {item.get('frequency')}."
                    ),
                    {
                        "date": item.get("date"),
                        "category": item.get("category"),
                        "entry_type": item.get("entry_type"),
                        "description": item.get("description"),
                    },
                )
            )
        return {
            "answer": answer,
            "follow_up_questions": ["Do you want to see all payments due today plus the next 7 days?"],
            "sources": sources,
            "tools_used": ["find_next_payment_due"],
        }

    def _recurring_reminder_answer(self, normalized_question: str) -> dict | None:
        if "next week" in normalized_question or "7 days" in normalized_question:
            calendar = self._recurring_service.upcoming_calendar(7)
            reminders = [
                item
                for item in calendar.get("occurrences", [])
                if item.get("entry_type") == "expense" and int(item.get("days_until_due") or 0) <= 7
            ]
            label = "Recurring reminders due next week"
            tools_used = ["get_recurring_reminders_due_next_week"]
        else:
            reminders = [
                item
                for item in self._recurring_service.list_items()
                if item.get("active") and item.get("entry_type") == "expense"
            ]
            label = "Recurring reminders"
            tools_used = ["list_recurring_reminders"]
        if not reminders:
            return {
                "answer": f"{label}: none found in the structured recurring reminder data.",
                "follow_up_questions": ["Do you want to add a recurring reminder?"],
                "sources": [self._structured_source(label, "recurring_search", "recurring-search::none", f"{label}: no active expense reminders found.")],
                "tools_used": tools_used,
            }
        lines = [f"{label}:"]
        sources = []
        for item in sorted(reminders, key=lambda value: (str(value.get("date") or value.get("start_date") or ""), str(value.get("description") or ""))):
            due_text = f"due {item.get('date')}" if item.get("date") else f"starts {item.get('start_date')}"
            end_text = f" | ends {item.get('end_date')}" if item.get("end_date") else ""
            cost = self._format_gbp(item.get("amount"))
            lines.append(
                f"- {item.get('description')}: {item.get('category')} | {item.get('frequency')} | {due_text}{end_text}. Cost: {cost}."
            )
            document_id = f"recurring::{item.get('id') or item.get('recurring_item_id')}"
            if item.get("date"):
                document_id = f"recurring-occurrence::{item.get('recurring_item_id')}::{item.get('date')}"
            sources.append(
                self._structured_source(
                    str(item.get("description") or "Recurring reminder"),
                    "recurring_occurrence" if item.get("date") else "recurring",
                    document_id,
                    f"{item.get('description')} {due_text}. Category {item.get('category')}. Frequency {item.get('frequency')}. Cost: {cost}.",
                    {"category": item.get("category"), "date": item.get("date") or item.get("start_date"), "entry_type": item.get("entry_type")},
                )
            )
        return {
            "answer": "\n".join(lines),
            "follow_up_questions": ["Which reminders are due next week?"],
            "sources": sources,
            "tools_used": tools_used,
        }

    def _late_reminder_answer(self) -> dict:
        calendar = self._recurring_service.upcoming_calendar(35)
        reminders = [
            item
            for item in calendar.get("late_occurrences", [])
            if item.get("entry_type") == "expense"
        ]
        if not reminders:
            return {
                "answer": "You do not have any late reminders in the current month.",
                "follow_up_questions": [],
                "sources": [
                    self._structured_source(
                        "Late reminders",
                        "recurring_late_search",
                        "recurring-late-search::none",
                        "No unpaid expense reminders are past their due date in the current month.",
                    )
                ],
                "tools_used": ["get_late_recurring_reminders"],
            }

        sorted_reminders = sorted(
            reminders,
            key=lambda value: (
                str(value.get("date") or ""),
                str(value.get("description") or ""),
                str(value.get("recurring_item_id") or value.get("id") or ""),
            ),
        )
        plural = "" if len(sorted_reminders) == 1 else "s"
        lines = [f"You currently have {len(sorted_reminders)} late reminder{plural}:"]
        sources = []
        for item in sorted_reminders:
            due_date = item.get("date")
            description = item.get("description") or "Recurring reminder"
            cost = self._format_gbp(item.get("amount"))
            lines.append(f"- {description}: {cost} due {due_date}.")
            sources.append(
                self._structured_source(
                    str(description),
                    "recurring_late_occurrence",
                    f"recurring-late-occurrence::{item.get('recurring_item_id') or item.get('id')}::{due_date}",
                    f"{description}: late unpaid reminder. Category {item.get('category')}. Due date {due_date}. Cost: {cost}.",
                    {
                        "category": item.get("category"),
                        "date": due_date,
                        "entry_type": item.get("entry_type"),
                        "status": "late",
                    },
                )
            )
        return {
            "answer": "\n".join(lines),
            "follow_up_questions": [],
            "sources": sources,
            "tools_used": ["get_late_recurring_reminders"],
        }

    def _spending_total_answer(self, question: str) -> dict | None:
        scope = self._extract_requested_month_scope(question)
        expenses = [
            expense
            for expense in self._expense_service.list_expenses("desc")
            if expense.get("entry_type") == "expense"
        ]
        category = self._matching_category(question, expenses)
        if scope is None and category is None:
            return None
        filtered = []
        for expense in expenses:
            expense_date = self._parse_date(expense.get("date"))
            if expense_date is None:
                continue
            month_key = expense_date.isoformat()[:7]
            if scope and month_key not in self._month_keys_between(scope["start_month"], scope["end_month"]):
                continue
            if category and str(expense.get("category") or "").lower() != category.lower():
                continue
            filtered.append(expense)
        total = round(sum(float(item.get("amount") or 0) for item in filtered), 2)
        month_text = ""
        if scope and scope["start_month"] == scope["end_month"]:
            month_text = f" in {scope['end_month']}"
        elif scope:
            month_text = f" from {scope['start_month']} through {scope['end_month']}"
        category_text = f" for {category}" if category else ""
        answer = f"Total spent{category_text}{month_text}: {self._format_gbp(total)} across {len(filtered)} expense transaction{'' if len(filtered) == 1 else 's'}."
        sources = [
            self._structured_source(
                f"Transaction #{expense.get('id')}",
                "expense",
                f"expense::{expense.get('id')}",
                f"Transaction #{expense.get('id')} on {expense.get('date')}. Category {expense.get('category')}. Description {expense.get('description')}. Cost: {self._format_gbp(expense.get('amount'))}.",
                {"date": expense.get("date"), "category": expense.get("category"), "entry_type": "expense"},
            )
            for expense in filtered[:12]
        ] or [self._structured_source("Structured expense total", "expense_total", "expense-total::empty", answer)]
        return {
            "answer": answer,
            "follow_up_questions": ["Do you want this broken down by transaction?"],
            "sources": sources,
            "tools_used": ["calculate_structured_expense_total"],
        }

    @staticmethod
    def _is_latest_expense_question(question: str) -> bool:
        return ("expense" in question or "transaction" in question) and any(term in question for term in ("most recent", "latest", "last expense", "last transaction"))

    @staticmethod
    def _extract_expense_id_question(question: str) -> int | None:
        normalized = str(question or "").lower()
        if "expense" not in normalized and "transaction" not in normalized:
            return None
        patterns = (
            r"\b(?:expense|transaction)\s+(?:with\s+)?id\s*#?\s*(\d+)\b",
            r"\b(?:expense|transaction)\s+(?:number|no\.?)\s*#?\s*(\d+)\b",
            r"\b(?:expense|transaction)\s*#\s*(\d+)\b",
            r"\bid\s*#?\s*(\d+)\b",
        )
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def _extract_recurring_id_question(question: str) -> int | None:
        normalized = str(question or "").lower()
        if not any(term in normalized for term in ("recurring", "reminder", "subscription", "bill")):
            return None
        patterns = (
            r"\b(?:recurring reminder|reminder|recurring item|subscription|bill)\s+(?:with\s+)?id\s*#?\s*(\d+)\b",
            r"\b(?:recurring reminder|reminder|recurring item|subscription|bill)\s+(?:number|no\.?)\s*#?\s*(\d+)\b",
            r"\b(?:recurring reminder|reminder|recurring item|subscription|bill)\s*#\s*(\d+)\b",
        )
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def _is_recurring_reminder_question(question: str) -> bool:
        return any(term in question for term in ("recurring reminder", "recurring reminders", "subscriptions", "subscription", "upcoming reminders"))

    @staticmethod
    def _is_late_reminder_question(question: str) -> bool:
        return any(
            term in question
            for term in (
                "late reminder",
                "late reminders",
                "overdue reminder",
                "overdue reminders",
                "past due reminder",
                "past-due reminder",
                "unpaid reminders past",
            )
        )

    @staticmethod
    def _is_next_payment_due_question(question: str) -> bool:
        return (
            any(term in question for term in ("next payment", "next bill", "next recurring", "next subscription"))
            or ("payment" in question and "due" in question and "next" in question)
            or ("bill" in question and "due" in question and "next" in question)
        )

    @staticmethod
    def _is_spending_total_question(question: str) -> bool:
        return any(term in question for term in ("how much", "total", "spent", "spend")) and not RagService._is_recurring_reminder_question(question)

    @staticmethod
    def _is_cash_flow_question(question: str) -> bool:
        return "cashflow" in question or "cash flow" in question or ("cash" in question and "flow" in question)

    @staticmethod
    def _financial_pulse_metric(question: str) -> str | None:
        if "average transaction" in question or "avg transaction" in question:
            return "average_transaction"
        if "spend velocity" in question or "spending velocity" in question:
            return "spend_velocity"
        if "income coverage" in question:
            return "income_coverage"
        if "top category share" in question or "category share" in question:
            return "top_category_share"
        if "budget runway" in question or "runway" in question:
            return "budget_runway"
        if "health score" in question:
            return "health_score"
        return None

    @staticmethod
    def _kpi_studio_metric(question: str) -> str | None:
        if "month-end forecast" in question or "month end forecast" in question or "forecast" in question:
            return "month_end_forecast"
        if "largest category share" in question:
            return "largest_category_share"
        if "average daily burn" in question or "daily burn" in question:
            return "average_daily_burn"
        if "current-month transactions" in question or "current month transactions" in question:
            return "current_month_transactions"
        return None

    @staticmethod
    def _comparison_metric(question: str) -> str | None:
        if "current period" in question:
            return "current_period"
        if "average spend" in question:
            return "average_spend"
        if "strongest period" in question:
            return "strongest_period"
        if "change vs previous" in question or "change versus previous" in question:
            return "change_vs_previous"
        return None

    @staticmethod
    def _is_financial_status_question(question: str) -> bool:
        return (
            "financial status" in question
            or "finance status" in question
            or "financial health" in question
            or "how am i doing financially" in question
            or ("how" in question and "financially" in question)
        )

    @staticmethod
    def _is_remaining_budget_question(question: str) -> bool:
        return (
            "remaining budget" in question
            or "budget remaining" in question
            or "left in my budget" in question
            or "budget left" in question
        )

    @staticmethod
    def _is_budget_consumption_question(question: str) -> bool:
        return (
            "budget consumption" in question
            or "budget utilisation" in question
            or "budget utilization" in question
            or "percent spent" in question
            or "percentage spent" in question
            or ("budget" in question and "percentage" in question)
        )

    @staticmethod
    def _is_monthly_income_question(question: str) -> bool:
        return "income" in question and not any(term in question for term in ("expense", "spend", "spent", "cost", "payment", "bill"))

    @staticmethod
    def _matching_category(question: str, expenses: list[dict]) -> str | None:
        normalized = str(question or "").lower()
        categories = sorted({str(expense.get("category") or "") for expense in expenses if expense.get("category")}, key=len, reverse=True)
        for category in categories:
            if category.lower() in normalized:
                return category
        return None

    @staticmethod
    def _format_gbp(value: object) -> str:
        try:
            amount = float(value or 0)
        except (TypeError, ValueError):
            amount = 0.0
        return f"GBP {amount:.2f}"

    @staticmethod
    def _as_float(value: object) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _contains_any(value: str, *needles: str) -> bool:
        return any(needle in value for needle in needles)

    @staticmethod
    def _month_label(month_key: str) -> str:
        try:
            return datetime.strptime(f"{month_key}-01", "%Y-%m-%d").strftime("%B %Y")
        except (TypeError, ValueError):
            return str(month_key)

    @classmethod
    def _scope_label(cls, scope: dict) -> str:
        start_month = str(scope.get("start_month") or "")
        end_month = str(scope.get("end_month") or start_month)
        if start_month == end_month:
            return cls._month_label(end_month)
        return f"{cls._month_label(start_month)} through {cls._month_label(end_month)}"

    def _dashboard_monthly_expenses(self, dashboard: dict) -> float:
        if dashboard.get("current_month_total") is not None:
            return self._as_float(dashboard.get("current_month_total"))
        return self._as_float(dashboard.get("monthly_expenses"))

    def _previous_piggy_bank_carryover(self, current_month_key: str) -> float:
        monthly_expenses: dict[str, float] = {}
        for item in self._expense_service.list_expenses(sort_direction="desc"):
            month_key = str(item.get("date") or "")[:7]
            if not month_key or month_key >= current_month_key:
                continue
            amount = self._as_float(item.get("amount"))
            if str(item.get("entry_type") or "expense") == "expense":
                monthly_expenses[month_key] = monthly_expenses.get(month_key, 0.0) + amount

        income_records = self._settings_service.list_monthly_income_records(current_month_key)
        monthly_income = {
            str(item.get("month_key")): self._as_float(item.get("monthly_income"))
            for item in income_records
            if str(item.get("month_key") or "") < current_month_key
        }

        carryover = 0.0
        for month_key in sorted(set(monthly_income) | set(monthly_expenses)):
            month_cash_flow = monthly_income.get(month_key, 0.0) - monthly_expenses.get(month_key, 0.0)
            carryover = max(carryover + month_cash_flow, 0.0)
        return carryover

    @staticmethod
    def _add_months(value: date, month_count: int) -> date:
        month_index = value.month - 1 + month_count
        year = value.year + month_index // 12
        month = month_index % 12 + 1
        return date(year, month, 1)

    @staticmethod
    def _structured_source(source_label: str, doc_type: str, document_id: str, excerpt: str, metadata: dict | None = None) -> dict:
        source_metadata = {"doc_type": doc_type, **(metadata or {})}
        return {
            "source_label": source_label,
            "doc_type": doc_type,
            "document_id": document_id,
            "excerpt": excerpt,
            "score": 1.0,
            "metadata": source_metadata,
        }

    def _build_source_documents(self) -> list[dict]:
        dashboard = self._analytics_service.dashboard()
        pulse = self._analytics_service.financial_pulse()
        categories = self._analytics_service.category_insights()
        settings = self._settings_service.get_settings(dashboard.get("month_key"))
        try:
            prediction = self._prediction_service.predict_next_month()
        except Exception:
            prediction = None
        expenses = self._expense_service.list_expenses("desc")
        recurring_items = self._recurring_service.list_items()
        recurring_calendar = self._recurring_service.upcoming_calendar(90)
        agent_runs = self._agent_run_repository.list_runs(20)
        memories = self._memory_service.recall(20)

        documents: list[dict] = [
            {
                "id": f"dashboard::{dashboard.get('month_key', 'current')}",
                "text": (
                    f"Dashboard summary for {dashboard.get('month_label')}. "
                    f"Monthly budget: GBP {dashboard.get('monthly_budget')}. "
                    f"Expenses this month: GBP {dashboard.get('current_month_total')}. "
                    f"Monthly income: GBP {dashboard.get('monthly_income')}. "
                    f"Net cash flow: GBP {dashboard.get('net_cash_flow')}. "
                    f"Remaining budget: GBP {dashboard.get('remaining_budget')}. "
                    f"Budget status is {dashboard.get('status')}."
                ),
                "metadata": {
                    "doc_type": "dashboard",
                    "source_label": f"Dashboard {dashboard.get('month_label')}",
                    "month_key": dashboard.get("month_key") or "current",
                },
            },
            {
                "id": f"financial-pulse::{dashboard.get('month_key', 'current')}",
                "text": (
                    f"Financial pulse narrative: {pulse.get('narrative')}. "
                    f"Health score {pulse.get('health_score')}. "
                    f"Cash in: GBP {pulse.get('cash_in')}. Cash out: GBP {pulse.get('cash_out')}. "
                    f"Net cash flow: GBP {pulse.get('net_cash_flow')}. Runway days: {pulse.get('runway_days')}."
                ),
                "metadata": {
                    "doc_type": "financial_pulse",
                    "source_label": "Financial pulse",
                    "month_key": dashboard.get("month_key") or "current",
                },
            },
            {
                "id": f"category-insights::{dashboard.get('month_key', 'current')}",
                "text": (
                    "Category insights. Top categories: "
                    + "; ".join(
                        f"{item.get('category')} Cost: GBP {item.get('amount')}" for item in categories.get("top_categories", [])
                    )
                    + ". Bottom categories: "
                    + "; ".join(
                        f"{item.get('category')} Cost: GBP {item.get('amount')}" for item in categories.get("bottom_categories", [])
                    )
                    + f". Total spending: GBP {categories.get('total_spending')}."
                ),
                "metadata": {
                    "doc_type": "category_insights",
                    "source_label": "Category insights",
                    "month_key": dashboard.get("month_key") or "current",
                },
            },
            {
                "id": f"settings::{dashboard.get('month_key', 'current')}",
                "text": (
                    f"Budget settings. Monthly budget: GBP {settings.get('monthly_budget')}. "
                    f"Monthly income: GBP {settings.get('monthly_income')} for {settings.get('income_month') or dashboard.get('month_key')}."
                ),
                "metadata": {
                    "doc_type": "settings",
                    "source_label": "Budget settings",
                    "month_key": settings.get("income_month") or dashboard.get("month_key") or "current",
                },
            },
        ]
        if prediction:
            documents.append(
                {
                    "id": f"prediction::{prediction.get('next_month')}",
                    "text": (
                        f"Prediction for {prediction.get('next_month')}. "
                        f"Predicted spending: GBP {prediction.get('predicted_spending')}. "
                        f"Budget exceeded {prediction.get('is_budget_exceeded')}. "
                        f"Budget baseline: GBP {prediction.get('monthly_budget')}."
                    ),
                    "metadata": {
                        "doc_type": "prediction",
                        "source_label": f"Prediction {prediction.get('next_month')}",
                        "month_key": prediction.get("next_month"),
                    },
                }
            )
        for expense in expenses:
            documents.append(
                {
                    "id": f"expense::{expense['id']}",
                    "text": (
                        f"Transaction on {expense['date']}. Category {expense['category']}. "
                        f"Description {expense['description']}. Cost: GBP {expense['amount']}. "
                        f"Entry type {expense['entry_type']}."
                    ),
                    "metadata": {
                        "doc_type": "expense",
                        "source_label": f"Transaction #{expense['id']}",
                        "date": expense["date"],
                        "category": expense["category"],
                        "entry_type": expense["entry_type"],
                    },
                }
            )
        for item in recurring_items:
            documents.append(
                {
                    "id": f"recurring::{item['id']}",
                    "text": (
                        f"Recurring reminder {item['description']}. Category {item['category']}. "
                        f"Cost: GBP {item['amount']}. Frequency {item['frequency']}. "
                        f"Start date {item['start_date']}. End date {item.get('end_date') or 'open ended'}. "
                        f"Active {item['active']}."
                    ),
                    "metadata": {
                        "doc_type": "recurring",
                        "source_label": f"Recurring #{item['id']}",
                        "start_date": item["start_date"],
                        "category": item["category"],
                        "frequency": item["frequency"],
                    },
                }
            )
        occurrence_map = {
            (item.get("recurring_item_id"), item.get("date")): dict(item, is_paid=False)
            for item in self._build_recurring_occurrences_for_index(recurring_items)
        }
        for item in recurring_calendar.get("occurrences", []):
            occurrence_map[(item.get("recurring_item_id"), item.get("date"))] = dict(item, is_paid=False)
        for item in recurring_calendar.get("completed_occurrences", []):
            occurrence_map[(item.get("recurring_item_id"), item.get("date"))] = dict(item, is_paid=True)
        all_occurrences = sorted(
            occurrence_map.values(),
            key=lambda item: (str(item.get("date") or ""), str(item.get("description") or ""), int(item.get("recurring_item_id") or 0)),
        )
        if all_occurrences:
            documents.append(
                {
                    "id": "recurring-calendar::upcoming-90-days",
                    "text": (
                        f"Recurring calendar from {recurring_calendar.get('window_start')} to {recurring_calendar.get('window_end')}. "
                        + " ".join(
                            f"{item.get('description')} is due on {item.get('date')}. Cost: GBP {item.get('amount')} "
                            f"as {item.get('entry_type')} and paid status is {bool(item.get('is_paid'))}."
                            for item in all_occurrences
                        )
                    ),
                    "metadata": {
                        "doc_type": "recurring_calendar",
                        "source_label": "Recurring calendar upcoming 90 days",
                    },
                }
            )
        for occurrence in all_occurrences:
            date_value = str(occurrence.get("date") or "")
            month_key = date_value[:7] if len(date_value) >= 7 else ""
            is_paid = bool(occurrence.get("is_paid"))
            documents.append(
                {
                    "id": f"recurring-occurrence::{occurrence.get('recurring_item_id')}::{date_value}",
                    "text": (
                        f"Recurring bill occurrence due on {date_value}. "
                        f"Description {occurrence.get('description')}. Category {occurrence.get('category')}. "
                        f"Cost: GBP {occurrence.get('amount')}. Entry type {occurrence.get('entry_type')}. "
                        f"Frequency {occurrence.get('frequency')}. Days until due {occurrence.get('days_until_due')}. "
                        f"Paid {is_paid}."
                    ),
                    "metadata": {
                        "doc_type": "recurring_occurrence",
                        "source_label": f"Recurring due {date_value}: {occurrence.get('description')}",
                        "document_id": f"recurring-occurrence::{occurrence.get('recurring_item_id')}::{date_value}",
                        "date": date_value,
                        "month_key": month_key,
                        "description": occurrence.get("description"),
                        "entry_type": occurrence.get("entry_type"),
                        "is_paid": is_paid,
                    },
                }
            )
        for run in agent_runs:
            documents.append(
                {
                    "id": f"agent-run::{run['id']}",
                    "text": (
                        f"Workflow run {run['workflow_label']} completed with status {run['status']}. "
                        f"Headline {run['headline']}. Summary {run['summary']}. "
                        f"Recommended actions: {'; '.join(run.get('recommended_actions', [])) or 'None'}."
                    ),
                    "metadata": {
                        "doc_type": "agent_run",
                        "source_label": f"Workflow run #{run['id']}",
                        "workflow_name": run["workflow_name"],
                        "generated_at": run["generated_at"],
                    },
                }
            )
        for index, memory in enumerate(memories):
            documents.append(
                {
                    "id": f"agent-memory::{index}::{memory.get('kind', 'memory')}",
                    "text": (
                        f"Agent memory kind {memory.get('kind')}. Task {memory.get('task')}. "
                        f"Summary {memory.get('summary')}. Tools used {'; '.join(memory.get('tools_used') or []) or 'None'}."
                    ),
                    "metadata": {
                        "doc_type": "agent_memory",
                        "source_label": f"Agent memory {memory.get('kind') or index}",
                        "kind": memory.get("kind") or "memory",
                    },
                }
            )
        return documents

    def _build_chunks(self, source_documents: list[dict]) -> list[dict]:
        chunks: list[dict] = []
        for document in source_documents:
            chunks.extend(
                self._chunker.chunk_document(
                    document_id=document["id"],
                    text=document["text"],
                    metadata=self._sanitize_metadata(document["metadata"]),
                )
            )
        return chunks

    @classmethod
    def _build_query_variants(cls, question: str) -> list[str]:
        variants = [question]
        normalized = question.lower()
        if cls._is_bill_question(normalized):
            variants.extend(
                [
                    f"{question} recurring bill occurrences due dates",
                    f"{question} upcoming recurring expense reminders",
                    f"{question} monthly recurring bills calendar",
                ]
            )
        if any(term in normalized for term in ("expense", "transaction", "spending", "spent", "category", "categories")):
            variants.extend(
                [
                    f"{question} exact transaction ledger entries categories amounts dates",
                    f"{question} dashboard category insights expense records",
                ]
            )
        if any(term in normalized for term in ("report", "briefing", "workflow", "automation")):
            variants.extend(
                [
                    f"{question} monthly report workflow run automation history",
                    f"{question} agent run summary recommended actions",
                ]
            )
        if any(term in normalized for term in ("income", "budget", "cash flow", "cashflow", "piggy bank")):
            variants.append(f"{question} dashboard settings monthly income budget cash flow")
        month_scope = cls._extract_requested_month_scope(question)
        if month_scope:
            variants.append(f"recurring bill occurrences due from {month_scope['start_month']} to {month_scope['end_month']}")
        deduped: list[str] = []
        for variant in variants:
            if variant not in deduped:
                deduped.append(variant)
        return deduped[:5]

    @classmethod
    def _calendar_month_sources(cls, collection, question: str) -> list[dict]:
        month_scope = cls._extract_requested_month_scope(question)
        if not month_scope or not cls._is_bill_question(question):
            return []
        sources = []
        for month_key in cls._month_keys_between(month_scope["start_month"], month_scope["end_month"]):
            try:
                result = collection.get(where={"month_key": month_key}, include=["documents", "metadatas"])
            except Exception:
                continue
            documents = result.get("documents") or []
            metadatas = result.get("metadatas") or []
            for index, document in enumerate(documents):
                metadata = metadatas[index] if index < len(metadatas) else {}
                if metadata.get("doc_type") != "recurring_occurrence":
                    continue
                if str(metadata.get("entry_type") or "") != "expense":
                    continue
                sources.append(
                    {
                        "source_label": metadata.get("source_label") or metadata.get("document_id") or "Knowledge chunk",
                        "doc_type": metadata.get("doc_type") or "knowledge",
                        "document_id": metadata.get("document_id") or "unknown",
                        "excerpt": document,
                        "score": 1.0,
                        "metadata": metadata,
                    }
                )
        return sources

    @classmethod
    def _no_calendar_match_source(cls, question: str) -> dict:
        month_scope = cls._extract_requested_month_scope(question)
        if month_scope and month_scope["start_month"] == month_scope["end_month"]:
            window = month_scope["start_month"]
        elif month_scope:
            window = f"{month_scope['start_month']} through {month_scope['end_month']}"
        else:
            window = "the requested period"
        return {
            "source_label": f"Recurring bill due-date search for {window}",
            "doc_type": "recurring_occurrence_search",
            "document_id": f"recurring-occurrence-search::{window}",
            "excerpt": f"No recurring expense bill occurrences are indexed for {window}.",
            "score": 1.0,
            "metadata": {"doc_type": "recurring_occurrence_search", "document_id": f"recurring-occurrence-search::{window}"},
        }

    @staticmethod
    def _essential_finance_sources(collection) -> list[dict]:
        try:
            result = collection.get(include=["documents", "metadatas"])
        except Exception:
            return []
        essential_doc_types = {
            "dashboard",
            "financial_pulse",
            "category_insights",
            "settings",
            "prediction",
            "recurring_calendar",
        }
        sources = []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        for index, document in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) else {}
            if metadata.get("doc_type") not in essential_doc_types:
                continue
            sources.append(
                {
                    "source_label": metadata.get("source_label") or metadata.get("document_id") or "Knowledge chunk",
                    "doc_type": metadata.get("doc_type") or "knowledge",
                    "document_id": metadata.get("document_id") or "unknown",
                    "excerpt": document,
                    "score": 0.72,
                    "metadata": metadata,
                }
            )
        return sources

    @staticmethod
    def _sources_from_query_result(result: dict) -> list[dict]:
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        sources = []
        for index, document in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) else {}
            distance = distances[index] if index < len(distances) else None
            score = 1.0 if distance in (None, "") else max(0.0, round(1 - float(distance), 4))
            sources.append(
                {
                    "source_label": metadata.get("source_label") or metadata.get("document_id") or "Knowledge chunk",
                    "doc_type": metadata.get("doc_type") or "knowledge",
                    "document_id": metadata.get("document_id") or "unknown",
                    "excerpt": document,
                    "score": score,
                    "metadata": metadata,
                }
            )
        return sources

    @classmethod
    def _rerank_sources(cls, question: str, sources: list[dict], limit: int) -> list[dict]:
        month_scope = cls._extract_requested_month_scope(question)
        question_tokens = cls._tokenize(question)
        bill_question = cls._is_bill_question(question)

        def score(source: dict) -> tuple[float, str]:
            metadata = source.get("metadata") or {}
            excerpt = str(source.get("excerpt") or "")
            source_tokens = cls._tokenize(
                " ".join(
                    [
                        excerpt,
                        str(source.get("source_label") or ""),
                        str(metadata.get("description") or ""),
                        str(metadata.get("doc_type") or ""),
                    ]
                )
            )
            overlap = len(question_tokens & source_tokens) / max(1, len(question_tokens))
            rerank_score = float(source.get("score") or 0.0)
            rerank_score += overlap * 0.35
            if month_scope and metadata.get("month_key") in cls._month_keys_between(month_scope["start_month"], month_scope["end_month"]):
                rerank_score += 0.35
            if bill_question and metadata.get("doc_type") == "recurring_occurrence":
                rerank_score += 0.45
            if bill_question and str(metadata.get("entry_type") or "") == "expense":
                rerank_score += 0.15
            if metadata.get("date") and str(metadata.get("date")) in question:
                rerank_score += 0.2
            return round(rerank_score, 6), str(source.get("document_id") or "")

        ranked = sorted(sources, key=score, reverse=True)
        return ranked[: max(1, int(limit))]

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        stop_words = {"the", "a", "an", "in", "of", "for", "to", "do", "i", "have", "any", "whole", "is", "are"}
        return {
            token
            for token in re.findall(r"[a-z0-9]+", str(text or "").lower())
            if len(token) > 1 and token not in stop_words
        }

    @staticmethod
    def _extract_requested_month_key(question: str) -> str | None:
        scope = RagService._extract_requested_month_scope(question)
        return scope["end_month"] if scope else None

    @staticmethod
    def _extract_requested_month_scope(question: str) -> dict | None:
        normalized = str(question or "").lower()
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
        explicit = re.search(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", normalized)
        if explicit:
            month_key = explicit.group(0)
            start_month = date.today().replace(day=1).isoformat()[:7] if RagService._is_through_month_question(normalized) else month_key
            return {"start_month": start_month, "end_month": month_key}
        for name, month in month_names.items():
            if name in normalized:
                year_match = re.search(rf"{name}\s+(20\d{{2}})", normalized)
                year = int(year_match.group(1)) if year_match else datetime.now().year
                month_key = f"{year:04d}-{month:02d}"
                start_month = date.today().replace(day=1).isoformat()[:7] if RagService._is_through_month_question(normalized) else month_key
                return {"start_month": start_month, "end_month": month_key}
        return None

    @staticmethod
    def _is_bill_question(question: str) -> bool:
        return any(term in str(question or "").lower() for term in ("bill", "bills", "due", "recurring", "reminder"))

    @staticmethod
    def _is_through_month_question(question: str) -> bool:
        normalized = str(question or "").lower()
        return any(phrase in normalized for phrase in ("till ", "until ", "through ", "up to ", "from now to", "between now and"))

    @staticmethod
    def _month_keys_between(start_month: str, end_month: str) -> list[str]:
        start_year, start_month_number = (int(part) for part in start_month.split("-", 1))
        end_year, end_month_number = (int(part) for part in end_month.split("-", 1))
        current = date(start_year, start_month_number, 1)
        end = date(end_year, end_month_number, 1)
        if current > end:
            current, end = end, current
        keys = []
        while current <= end:
            keys.append(current.isoformat()[:7])
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)
        return keys

    @classmethod
    def _build_recurring_occurrences_for_index(cls, recurring_items: list[dict]) -> list[dict]:
        today = date.today()
        window_start = today.replace(day=1)
        window_end = today + timedelta(days=90)
        occurrences: list[dict] = []
        for item in recurring_items:
            if not item.get("active"):
                continue
            start_date = cls._parse_date(item.get("start_date"))
            if start_date is None:
                continue
            end_date = cls._parse_date(item.get("end_date")) or window_end
            due_date = start_date
            while due_date < window_start:
                due_date = cls._next_recurring_due_date(due_date, str(item.get("frequency") or "monthly"))
            while due_date <= window_end and due_date <= end_date:
                occurrences.append(
                    {
                        "recurring_item_id": item.get("id"),
                        "date": due_date.isoformat(),
                        "category": item.get("category"),
                        "description": item.get("description"),
                        "amount": item.get("amount"),
                        "entry_type": item.get("entry_type"),
                        "frequency": item.get("frequency"),
                        "days_until_due": (due_date - today).days,
                    }
                )
                due_date = cls._next_recurring_due_date(due_date, str(item.get("frequency") or "monthly"))
        return occurrences

    @staticmethod
    def _parse_date(value: object) -> date | None:
        if not value:
            return None
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def _next_recurring_due_date(current_due_date: date, frequency: str) -> date:
        if frequency == "weekly":
            return current_due_date + timedelta(days=7)
        next_month = current_due_date.replace(day=28) + timedelta(days=4)
        month_start = next_month.replace(day=1)
        month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        return month_start.replace(day=min(current_due_date.day, month_end.day))

    @staticmethod
    def _build_signature(source_documents: list[dict]) -> str:
        signature_documents = [
            document
            for document in source_documents
            if (document.get("metadata") or {}).get("doc_type") != "agent_memory"
        ]
        payload = json.dumps(signature_documents, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _load_manifest(self, manifest_path: Path | None = None) -> dict[str, Any]:
        resolved_path = manifest_path or self._scoped_manifest_path()
        if not resolved_path.exists():
            return {}
        try:
            payload = json.loads(resolved_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _sanitize_metadata(metadata: dict) -> dict:
        sanitized = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            else:
                sanitized[key] = json.dumps(value, sort_keys=True, ensure_ascii=False)
        return sanitized

    @staticmethod
    def _parse_answer_payload(content: str) -> dict:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            cleaned = RagService._clean_answer_json_payload(content)
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                return {
                    "answer": cleaned or "I could not produce a grounded answer from the retrieved finance context.",
                    "confidence": "medium",
                    "follow_up_questions": [],
                }
        answer = str(parsed.get("answer") or "").strip()
        if not answer:
            raise ValidationError("The RAG answer was empty.")
        confidence = str(parsed.get("confidence") or "medium").strip().lower()
        if confidence not in {"low", "medium", "high"}:
            confidence = "medium"
        return {
            "answer": answer,
            "confidence": confidence,
            "follow_up_questions": [],
        }

    @staticmethod
    def _clean_answer_json_payload(content: str) -> str:
        cleaned = str(content or "").strip()
        fence_match = re.search(r"```(?:json)?\.?\s*(.*?)\s*```\.?", cleaned, flags=re.IGNORECASE | re.DOTALL)
        if fence_match:
            cleaned = fence_match.group(1).strip()
        cleaned = re.sub(r"^\s*json\.?\s*", "", cleaned, flags=re.IGNORECASE)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start : end + 1]
        lines = []
        for line in cleaned.splitlines():
            line = re.sub(r"(?<=[\{\}\],])\.\s*$", "", line.rstrip())
            lines.append(line)
        return "\n".join(lines).strip()

    def _create_chroma_client(self):
        if self._chroma_http_host:
            return self._http_chroma_client_factory()
        return self._chroma_client_factory(self._persist_directory)

    def _http_chroma_client_factory(self):
        try:
            import chromadb
        except Exception as exc:
            raise ServiceUnavailableError(
                "ChromaDB HTTP client is not installed for Monetra RAG. "
                "Install chromadb-client when using a separate Chroma server."
            ) from exc
        return chromadb.HttpClient(
            host=self._chroma_http_host,
            port=self._chroma_http_port,
            ssl=self._chroma_http_ssl,
        )

    @staticmethod
    def _default_chroma_client_factory(path: Path):
        try:
            import chromadb
        except Exception as exc:
            raise ServiceUnavailableError(
                "ChromaDB is not installed for Monetra RAG. "
                "Run the backend in Docker or install Microsoft C++ Build Tools before installing chromadb locally on Windows."
            ) from exc
        if not hasattr(chromadb, "PersistentClient"):
            raise ServiceUnavailableError(
                "The installed Chroma package is the HTTP-only client. "
                "Set CHROMA_HTTP_HOST and run a Chroma server, or install the full chromadb package for embedded storage."
            )
        return chromadb.PersistentClient(path=str(path))

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
