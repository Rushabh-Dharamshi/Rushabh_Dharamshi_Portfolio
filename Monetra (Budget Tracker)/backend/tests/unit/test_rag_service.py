from pathlib import Path

import pytest

from budget_tracker_api.errors import NotFoundError, ValidationError
from budget_tracker_api.services.agent_memory_service import AgentMemoryService
from budget_tracker_api.services.metric_registry import FinanceIntent, FinanceIntentRouter, MetricRegistry
from budget_tracker_api.services.rag_service import RagService


class StubExpenseService:
    def list_expenses(self, sort_direction="desc"):
        return [
            {"id": 10, "date": "2026-01-05", "category": "Income", "description": "January income", "amount": 1200.0, "entry_type": "income"},
            {"id": 11, "date": "2026-01-08", "category": "Food", "description": "January groceries", "amount": 300.0, "entry_type": "expense"},
            {"id": 12, "date": "2026-02-05", "category": "Income", "description": "February income", "amount": 900.0, "entry_type": "income"},
            {"id": 13, "date": "2026-02-09", "category": "Travel", "description": "February travel", "amount": 1100.0, "entry_type": "expense"},
            {"id": 1, "date": "2026-03-01", "category": "Food", "description": "Groceries", "amount": 65.25, "entry_type": "expense"},
            {"id": 2, "date": "2026-03-03", "category": "Travel", "description": "Train pass", "amount": 80.0, "entry_type": "expense"},
        ]

    def get_expense(self, expense_id):
        for expense in self.list_expenses():
            if expense["id"] == expense_id and expense["entry_type"] == "expense":
                return expense
        raise NotFoundError(f"Expense with id {expense_id} was not found.")

    def get_expense_by_user_expense_id(self, user_expense_id):
        return self.get_expense(user_expense_id)


class StubRecurringService:
    def list_items(self):
        return [
            {"id": 10, "category": "Housing", "description": "Rent", "amount": 700.0, "entry_type": "expense", "frequency": "monthly", "start_date": "2026-03-15", "end_date": None, "active": True},
        ]

    def get_item(self, item_id):
        for item in self.list_items():
            if item["id"] == item_id:
                return item
        raise NotFoundError(f"Recurring item with id {item_id} was not found.")

    def upcoming_calendar(self, days):
        return {
            "window_start": "2026-05-04",
            "window_end": "2026-08-01",
            "occurrences": [
                {
                    "recurring_item_id": 10,
                    "date": "2026-05-15",
                    "category": "Housing",
                    "description": "Rent",
                    "amount": 700.0,
                    "entry_type": "expense",
                    "frequency": "monthly",
                    "days_until_due": 11,
                }
            ],
            "completed_occurrences": [],
        }


class StubAnalyticsService:
    def dashboard(self):
        return {
            "month_key": "2026-03",
            "month_label": "March 2026",
            "monthly_budget": 1050.0,
            "current_month_total": 420.0,
            "monthly_income": 1500.0,
            "net_cash_flow": 1080.0,
            "remaining_budget": 630.0,
            "weekly_spending": 145.25,
            "percent_spent": 40.0,
            "status": "within",
        }

    def financial_pulse(self):
        return {
            "narrative": "Healthy but with housing pressure.",
            "health_score": 82,
            "average_transaction": 96.0,
            "spend_velocity": 14.0,
            "top_category_share": 55.0,
            "cash_in": 1500.0,
            "cash_out": 420.0,
            "net_cash_flow": 1080.0,
            "income_coverage": 357.14,
            "runway_days": 18,
        }

    def category_insights(self):
        return {
            "top_categories": [{"category": "Housing", "amount": 700.0}],
            "bottom_categories": [{"category": "Food", "amount": 65.25}],
            "total_spending": 420.0,
        }


class StubPredictionService:
    def __init__(self, fail=False):
        self.fail = fail

    def predict_next_month(self):
        if self.fail:
            raise RuntimeError("prediction unavailable")
        return {
            "next_month": "2026-04",
            "predicted_spending": 880.0,
            "is_budget_exceeded": False,
            "monthly_budget": 1050.0,
        }


class StubSettingsService:
    def get_settings(self, month_key=None):
        resolved_month = month_key or "2026-03"
        if resolved_month == "2026-05":
            return {"monthly_budget": 950.0, "monthly_income": 1800.0, "income_month": "2026-05", "budget_month": "2026-05"}
        return {"monthly_budget": 1050.0, "monthly_income": 1500.0, "income_month": resolved_month, "budget_month": resolved_month}

    def list_monthly_income_records(self, before_month=None):
        return [
            {"month_key": "2026-01", "monthly_income": 1200.0},
            {"month_key": "2026-02", "monthly_income": 900.0},
        ]


class StubAgentRunRepository:
    def list_runs(self, limit):
        return [
            {
                "id": 5,
                "workflow_name": "month_end_close",
                "workflow_label": "Month-end close",
                "status": "completed",
                "headline": "Month-end pack ready",
                "summary": "March pack generated.",
                "recommended_actions": ["Share the report"],
                "generated_at": "2026-03-21T10:00:00Z",
            }
        ]


class StubEmbeddingClient:
    model = "nomic-embed-text"

    def embed_texts(self, texts):
        return [[float(index + 1), 0.5] for index, _ in enumerate(texts)]


class StubAnswerClient:
    def __init__(self, content=None):
        self._content = content or '{"answer":"Housing is the largest cost center.","confidence":"high","follow_up_questions":["Which reminders are due next?"]}'
        self.messages = []

    def chat(self, messages):
        self.messages.append(messages)
        return {"message": {"content": self._content}}


class FakeCollection:
    def __init__(self):
        self.ids = []
        self.documents = []
        self.metadatas = []
        self.embeddings = []
        self.query_calls = 0

    def upsert(self, ids, documents, metadatas, embeddings):
        self.ids = list(ids)
        self.documents = list(documents)
        self.metadatas = list(metadatas)
        self.embeddings = list(embeddings)

    def query(self, query_embeddings, n_results, include):
        self.query_calls += 1
        return {
            "documents": [self.documents[:n_results]],
            "metadatas": [self.metadatas[:n_results]],
            "distances": [[0.05 for _ in self.documents[:n_results]]],
        }

    def get(self, where=None, include=None):
        month_key = (where or {}).get("month_key")
        documents = []
        metadatas = []
        for document, metadata in zip(self.documents, self.metadatas):
            if month_key is None or metadata.get("month_key") == month_key:
                documents.append(document)
                metadatas.append(metadata)
        return {"documents": documents, "metadatas": metadatas}


class FakeChromaClient:
    def __init__(self):
        self.collection = FakeCollection()
        self.collections = {}
        self.deleted_collections = []

    def delete_collection(self, name):
        self.deleted_collections.append(name)
        self.collections.pop(name, None)

    def get_or_create_collection(self, name, metadata=None):
        if name == "monetra-finance-knowledge":
            self.collections.setdefault(name, self.collection)
            return self.collections[name]
        self.collections.setdefault(name, FakeCollection())
        return self.collections[name]


@pytest.fixture()
def rag_service(tmp_path):
    fake_client = FakeChromaClient()
    memory = AgentMemoryService(tmp_path / "memory.json")
    service = RagService(
        expense_service=StubExpenseService(),
        recurring_service=StubRecurringService(),
        analytics_service=StubAnalyticsService(),
        prediction_service=StubPredictionService(),
        settings_service=StubSettingsService(),
        agent_run_repository=StubAgentRunRepository(),
        embedding_client=StubEmbeddingClient(),
        answer_client=StubAnswerClient(),
        memory_service=memory,
        persist_directory=tmp_path / "chroma",
        manifest_path=tmp_path / "rag-manifest.json",
        collection_name="monetra-finance-knowledge",
        chunk_size=120,
        chunk_overlap=20,
        top_k=4,
        chroma_client_factory=lambda path: fake_client,
    )
    return service, fake_client, memory


def test_rag_service_reindexes_and_reports_status(rag_service):
    service, fake_client, _ = rag_service

    result = service.reindex(force=True)
    status = service.status()

    assert result["reindexed"] is True
    assert result["document_count"] >= 6
    assert result["chunk_count"] >= result["document_count"]
    assert fake_client.deleted_collections == ["monetra-finance-knowledge"]
    assert status["indexed_at"] == result["indexed_at"]
    assert status["chunk_count"] == result["chunk_count"]


def test_rag_service_scopes_chroma_collection_and_manifest_by_user(tmp_path):
    fake_client = FakeChromaClient()
    current_user_id = 7
    service = RagService(
        expense_service=StubExpenseService(),
        recurring_service=StubRecurringService(),
        analytics_service=StubAnalyticsService(),
        prediction_service=StubPredictionService(),
        settings_service=StubSettingsService(),
        agent_run_repository=StubAgentRunRepository(),
        embedding_client=StubEmbeddingClient(),
        answer_client=StubAnswerClient(),
        memory_service=AgentMemoryService(tmp_path / "memory.json"),
        persist_directory=tmp_path / "chroma",
        manifest_path=tmp_path / "rag-manifest.json",
        collection_name="monetra-finance-knowledge",
        chunk_size=120,
        chunk_overlap=20,
        top_k=4,
        user_id_provider=lambda: current_user_id,
        chroma_client_factory=lambda path: fake_client,
    )

    first = service.reindex(force=True)
    current_user_id = 8
    second = service.reindex(force=True)

    assert first["collection_name"] == "monetra-finance-knowledge_user_7"
    assert second["collection_name"] == "monetra-finance-knowledge_user_8"
    assert fake_client.deleted_collections == [
        "monetra-finance-knowledge_user_7",
        "monetra-finance-knowledge_user_8",
    ]
    assert (tmp_path / "rag-manifest.user-7.json").exists()
    assert (tmp_path / "rag-manifest.user-8.json").exists()

    current_user_id = "not-a-user-id"
    assert service._scope_key() == "user-1"


def test_rag_service_skips_reindex_when_signature_has_not_changed(rag_service):
    service, _, _ = rag_service

    first = service.reindex(force=True)
    second = service.reindex(force=False)

    assert first["reindexed"] is True
    assert second["reindexed"] is False
    assert second["signature"] == first["signature"]


def test_rag_service_retrieves_context_and_answers_questions(rag_service):
    service, _, memory = rag_service

    retrieval = service.retrieve_context("What is driving spending?", top_k=2)
    answer = service.answer_question("What is driving spending?")
    memory_items = memory.recall(limit=5)

    assert retrieval["retrieved_count"] == 2
    assert retrieval["query_count"] > 1
    assert retrieval["sources"][0]["source_label"]
    assert answer["confidence"] == "high"
    assert answer["follow_up_questions"] == []
    assert answer["signature"]
    assert answer["sources"]
    assert memory_items[0]["kind"] == "rag_query"


def test_rag_service_multi_query_includes_requested_month_recurring_occurrences(rag_service):
    service, _, _ = rag_service

    retrieval = service.retrieve_context("Do I have any bills due in the whole of May?", top_k=6)

    assert retrieval["sources"][0]["doc_type"] == "recurring_occurrence"
    assert any(source["doc_type"] == "recurring_occurrence" for source in retrieval["sources"])
    assert any("2026-05-15" in source["excerpt"] for source in retrieval["sources"])
    assert retrieval["query_count"] > 1
    assert len(service._build_query_variants("Do I have any bills due in the whole of May?")) > 1
    assert service._rerank_sources("bills due in May", retrieval["sources"], 1)[0]["doc_type"] == "recurring_occurrence"


def test_rag_service_query_variants_cover_reports_workflows_and_settings(rag_service):
    service, _, _ = rag_service

    report_variants = service._build_query_variants("Summarise my latest report and workflow automation")
    settings_variants = service._build_query_variants("Explain my budget and cash flow")

    assert any("monthly report workflow run automation history" in variant for variant in report_variants)
    assert any("agent run summary recommended actions" in variant for variant in report_variants)
    assert any("dashboard settings monthly income budget cash flow" in variant for variant in settings_variants)


def test_rag_service_caches_retrieval_and_answers_when_signature_is_unchanged(rag_service):
    service, fake_client, _ = rag_service

    first_retrieval = service.retrieve_context("What is driving spending?", top_k=2)
    query_calls_after_first = fake_client.collection.query_calls
    second_retrieval = service.retrieve_context("What is driving spending?", top_k=2)

    assert second_retrieval == first_retrieval
    assert fake_client.collection.query_calls == query_calls_after_first

    first_answer = service.answer_question("What is driving spending?")
    answer_calls_after_first = len(service._answer_client.messages)
    cached_answer = service.answer_question("What is driving spending?")

    assert cached_answer == first_answer
    assert len(service._answer_client.messages) == answer_calls_after_first

    service.reindex(force=True)
    service.retrieve_context("What is driving spending?", top_k=2)

    assert fake_client.collection.query_calls > query_calls_after_first


def test_rag_service_documents_and_prompt_use_cost_colon_format(rag_service):
    service, _, _ = rag_service

    docs = service._build_source_documents()
    assert any("Cost: GBP" in document["text"] for document in docs)

    service.answer_question("What is driving spending?")
    system_prompt = service._answer_client.messages[-1][0]["content"]
    assert "Cost: <value>" in system_prompt
    assert "helpful finance assistant speaking to the user" in system_prompt
    assert "Avoid robotic phrases" in system_prompt
    assert "Do not invent missing figures" in system_prompt
    assert "Do not say 'planned expenses'" in system_prompt


def test_rag_service_answers_monthly_income_from_settings(rag_service):
    service, _, memory = rag_service

    answer = service.answer_question("What is my monthly income?")

    assert answer["confidence"] == "high"
    assert "monthly income" in answer["answer"].lower()
    assert "1500" in answer["answer"].replace(",", "")
    assert "Cost:" not in answer["answer"]
    assert answer["follow_up_questions"] == []
    assert answer["sources"][0]["doc_type"] == "settings"
    assert answer["sources"][0]["document_id"] == "settings::2026-03"
    assert service._answer_client.messages == []
    assert memory.recall(1)[0]["tools_used"] == ["settings_lookup"]


def test_rag_service_answers_cash_flow_from_dashboard(rag_service):
    service, _, memory = rag_service

    answer = service.answer_question("What is my cash flow?")

    assert answer["confidence"] == "high"
    assert "cash flow" in answer["answer"].lower()
    assert "1080" in answer["answer"].replace(",", "")
    assert "Income:" in answer["answer"]
    assert "Spending:" in answer["answer"]
    assert "Monthly income:" not in answer["answer"]
    assert answer["follow_up_questions"] == []
    assert answer["sources"][0]["doc_type"] == "dashboard"
    assert answer["sources"][0]["document_id"] == "dashboard::2026-03"
    assert service._answer_client.messages == []
    assert memory.recall(1)[0]["tools_used"] == ["dashboard_cash_flow_lookup"]


def test_rag_service_answers_financial_status_from_dashboard_and_pulse(rag_service):
    service, _, memory = rag_service

    answer = service.answer_question("How is my financial status?")

    assert answer["confidence"] == "high"
    assert "financial status" in answer["answer"].lower()
    assert "Your financial status looks within for March 2026" in answer["answer"]
    assert "82/100" in answer["answer"]
    assert "income GBP 1500.00" in answer["answer"]
    assert "actual monthly expenses GBP 420.00" in answer["answer"]
    assert "net cash flow GBP 1080.00" in answer["answer"]
    assert "remaining budget GBP 630.00" in answer["answer"]
    assert "planned expenses are separate from actual monthly expenses" in answer["answer"]
    assert "no planned expenses" not in answer["answer"].lower()
    assert answer["follow_up_questions"] == []
    assert answer["sources"][0]["doc_type"] == "dashboard"
    assert answer["sources"][1]["doc_type"] == "financial_pulse"
    assert service._answer_client.messages == []
    assert memory.recall(1)[0]["tools_used"] == ["dashboard_financial_status_lookup"]


def test_rag_service_answers_remaining_budget_from_dashboard(rag_service):
    service, _, memory = rag_service

    answer = service.answer_question("What is my remaining budget after expenses?")

    assert answer["confidence"] == "high"
    assert "remaining budget" in answer["answer"].lower()
    assert "GBP 630.00" in answer["answer"]
    assert "GBP 1050.00 monthly budget - GBP 420.00 monthly expenses = GBP 630.00" in answer["answer"]
    assert "different from net cash flow" in answer["answer"]
    assert "monthly income minus monthly expenses" in answer["answer"]
    assert "GBP 1080.00" not in answer["answer"]
    assert answer["follow_up_questions"] == []
    assert answer["sources"][0]["doc_type"] == "dashboard"
    assert answer["sources"][0]["document_id"] == "dashboard::2026-03"
    assert service._answer_client.messages == []
    assert memory.recall(1)[0]["tools_used"] == ["dashboard_remaining_budget_lookup"]


def test_rag_service_answers_budget_consumption_from_dashboard(rag_service):
    service, _, memory = rag_service

    answer = service.answer_question("What is my budget consumption as a percentage? how is this calculated?")

    assert answer["confidence"] == "high"
    assert "budget consumption" in answer["answer"].lower()
    assert "40.00%" in answer["answer"]
    assert "GBP 420.00 expenses / GBP 1050.00 monthly budget * 100 = 40.00%" in answer["answer"]
    assert answer["follow_up_questions"] == []
    assert answer["sources"][0]["doc_type"] == "dashboard"
    assert answer["sources"][0]["document_id"] == "dashboard::2026-03"
    assert service._answer_client.messages == []
    assert memory.recall(1)[0]["tools_used"] == ["dashboard_budget_consumption_lookup"]


def test_rag_service_answers_budget_overview_metrics_deterministically(rag_service):
    service, fake_client, memory = rag_service

    monthly_expenses = service.answer_question("What are my monthly expenses?")
    monthly_budget = service.answer_question("What is my monthly budget?")
    weekly_spending = service.answer_question("What is my weekly spending?")
    budget_status = service.answer_question("What is my budget status?")

    assert "Monthly expenses for March 2026: GBP 420.00" in monthly_expenses["answer"]
    assert "Monthly budget for March 2026: GBP 1050.00" in monthly_budget["answer"]
    assert "planned living-cost estimate" in monthly_budget["answer"]
    assert "Weekly spending for March 2026: GBP 145.25" in weekly_spending["answer"]
    assert "Budget status for March 2026: within" in budget_status["answer"]
    assert monthly_expenses["sources"][0]["doc_type"] == "dashboard"
    assert service._answer_client.messages == []
    assert fake_client.collection.query_calls == 0
    assert memory.recall(1)[0]["tools_used"] == ["dashboard_metric_lookup"]


def test_rag_service_answers_piggy_bank_metrics_deterministically(rag_service):
    service, fake_client, memory = rag_service

    balance = service.answer_question("What is my piggy bank balance?")
    contribution = service.answer_question("How much is added this month to the piggy bank?")
    carryover = service.answer_question("What is my previous carryover?")

    assert "Total piggy-bank balance for March 2026: GBP 1780.00" in balance["answer"]
    assert "GBP 700.00 previous carryover + GBP 1080.00 current-month cash flow" in balance["answer"]
    assert "This month's piggy-bank impact for March 2026: GBP 1080.00" in contribution["answer"]
    assert "GBP 1500.00 monthly income - GBP 420.00 monthly expenses" in contribution["answer"]
    assert "Previous carryover for March 2026: GBP 700.00" in carryover["answer"]
    assert balance["sources"][0]["doc_type"] == "piggy_bank"
    assert service._answer_client.messages == []
    assert fake_client.collection.query_calls == 0
    assert memory.recall(1)[0]["tools_used"] == ["piggy_bank_metric_lookup"]


def test_rag_service_answers_monthly_category_insights_deterministically(rag_service):
    service, fake_client, memory = rag_service

    summary = service.answer_question("What are my monthly insights?")
    top = service.answer_question("What are my top categories?")
    bottom = service.answer_question("What are my bottom categories?")

    assert "Monthly insights for March 2026" in summary["answer"]
    assert "Housing: GBP 700.00" in summary["answer"]
    assert "Food: GBP 65.25" in summary["answer"]
    assert "Top categories for March 2026: Housing: GBP 700.00" in top["answer"]
    assert "Bottom categories for March 2026: Food: GBP 65.25" in bottom["answer"]
    assert summary["sources"][0]["doc_type"] == "category_insights"
    assert service._answer_client.messages == []
    assert fake_client.collection.query_calls == 0
    assert memory.recall(1)[0]["tools_used"] == ["category_insights_lookup"]


def test_rag_service_answers_spend_extremes_deterministically(rag_service):
    service, fake_client, memory = rag_service

    month_extremes = service.answer_question("Which month do I spend the most and least?")
    category_extremes = service.answer_question("Which categories do I spend most and least?")
    overall_category_extremes = service.answer_question("Which categories do I spend most and least overall?")

    assert "highest-spend month is February 2026 at GBP 1100.00" in month_extremes["answer"]
    assert "lowest-spend month is March 2026 at GBP 145.25" in month_extremes["answer"]
    assert "expense transactions only; income records are excluded" in month_extremes["answer"]
    assert month_extremes["sources"][0]["doc_type"] == "monthly_spend_extremes"

    assert "For March 2026, your highest-spend category is Travel at GBP 80.00" in category_extremes["answer"]
    assert "lowest-spend category is Food at GBP 65.25" in category_extremes["answer"]
    assert category_extremes["sources"][0]["doc_type"] == "category_spend_extremes"

    assert "For overall, your highest-spend category is Travel at GBP 1180.00" in overall_category_extremes["answer"]
    assert "lowest-spend category is Food at GBP 365.25" in overall_category_extremes["answer"]
    assert service._answer_client.messages == []
    assert fake_client.collection.query_calls == 0
    assert memory.recall(1)[0]["tools_used"] == ["category_spend_extremes_lookup"]


def test_rag_service_answers_financial_pulse_metrics_deterministically(rag_service):
    service, _, memory = rag_service

    income_coverage = service.answer_question("What does income coverage mean?")
    runway = service.answer_question("What is my budget runway?")
    top_category_share = service.answer_question("What is top category share?")
    spend_velocity = service.answer_question("What is spend velocity?")
    average_transaction = service.answer_question("What is my average transaction?")

    assert "Income coverage for March 2026: 357.1%" in income_coverage["answer"]
    assert "monthly income divided by monthly expenses" in income_coverage["answer"]
    assert "Budget runway for March 2026: 18 days" in runway["answer"]
    assert "remaining budget would last" in runway["answer"]
    assert "Top category share for March 2026: 55.0%" in top_category_share["answer"]
    assert "largest spending category" in top_category_share["answer"]
    assert "Spend velocity for March 2026: GBP 14.00/day" in spend_velocity["answer"]
    assert "Average transaction for March 2026: GBP 96.00" in average_transaction["answer"]
    assert income_coverage["sources"][0]["doc_type"] == "financial_pulse"
    assert service._answer_client.messages == []
    assert memory.recall(1)[0]["tools_used"] == ["financial_pulse_metric_lookup"]


def test_rag_service_answers_kpi_and_comparison_metrics_deterministically(rag_service):
    service, fake_client, memory = rag_service

    daily_burn = service.answer_question("What is my average daily burn and how is it calculated?")
    month_end_forecast = service.answer_question("What is my month-end forecast?")
    current_transactions = service.answer_question("What are my current-month transactions?")
    strongest_period = service.answer_question("What is the strongest period in Comparison Lab?")
    average_spend = service.answer_question("What is the average spend in Comparison Lab?")

    assert "Average daily burn for March 2026" in daily_burn["answer"]
    assert "current-month expenses" in daily_burn["answer"]
    assert "Month-end forecast for March 2026" in month_end_forecast["answer"]
    assert "Current-month transactions for March 2026: 2" in current_transactions["answer"]
    assert "Strongest period:" in strongest_period["answer"]
    assert "Average spend:" in average_spend["answer"]
    assert daily_burn["sources"][0]["doc_type"] == "kpi_studio"
    assert strongest_period["sources"][0]["doc_type"] == "comparison_lab"
    assert service._answer_client.messages == []
    assert fake_client.collection.query_calls == 0
    assert memory.recall(1)[0]["tools_used"] == ["comparison_lab_metric_lookup"]


def test_rag_service_routes_paraphrased_metric_questions_through_registry(rag_service):
    service, fake_client, memory = rag_service

    daily_burn = service.answer_question("How fast am I spending each day?")
    remaining = service.answer_question("How much money do I have left to spend this month?")
    usage = service.answer_question("What percentage of my budget have I used?")
    cash_flow = service.answer_question("What is my net position from income vs expenses?")

    assert "Average daily burn for March 2026" in daily_burn["answer"]
    assert "remaining budget" in remaining["answer"].lower()
    assert "budget consumption" in usage["answer"].lower()
    assert "cash flow" in cash_flow["answer"].lower()
    assert service._answer_client.messages == []
    assert fake_client.collection.query_calls == 0
    assert memory.recall(1)[0]["tools_used"] == ["dashboard_cash_flow_lookup"]


def test_rag_service_uses_structured_answers_for_exact_finance_questions(rag_service):
    service, _, memory = rag_service

    monthly_budget_for_month = service.answer_question("What is my monthly budget for May 2026?")
    monthly_income_for_month = service.answer_question("What is my monthly income for May 2026?")

    assert "Monthly budget for May 2026: GBP 950.00" in monthly_budget_for_month["answer"]
    assert "planned living-cost estimate" in monthly_budget_for_month["answer"]
    assert monthly_budget_for_month["sources"][0]["doc_type"] == "settings"
    assert "Your monthly income for May 2026 is GBP 1800.00." == monthly_income_for_month["answer"]
    assert monthly_income_for_month["sources"][0]["document_id"] == "settings::2026-05"
    assert service._answer_client.messages == []

    expense_by_id = service.answer_question("What is expense ID 2? please check?")

    assert "Expense ID 2 is Train pass: GBP 80.00 on 2026-03-03 under Travel." == expense_by_id["answer"]
    assert expense_by_id["confidence"] == "high"
    assert expense_by_id["follow_up_questions"] == []
    assert expense_by_id["sources"][0]["document_id"] == "expense::2"
    assert expense_by_id["sources"][0]["doc_type"] == "expense"
    assert service._answer_client.messages == []
    assert memory.recall(1)[0]["tools_used"] == ["expense_id_lookup"]

    missing_expense = service.answer_question("What is transaction #999?")

    assert "could not find an expense with ID 999" in missing_expense["answer"]
    assert missing_expense["sources"][0]["doc_type"] == "expense_lookup"
    assert service._answer_client.messages == []

    recurring_by_id = service.answer_question("What is recurring reminder ID 10?")

    assert "Recurring reminder ID 10 is Rent: GBP 700.00, monthly, starting 2026-03-15. Status: active." == recurring_by_id["answer"]
    assert recurring_by_id["sources"][0]["document_id"] == "recurring::10"
    assert recurring_by_id["sources"][0]["doc_type"] == "recurring"
    assert service._answer_client.messages == []

    missing_recurring = service.answer_question("What is reminder id 999?")

    assert "could not find a recurring reminder with ID 999" in missing_recurring["answer"]
    assert missing_recurring["sources"][0]["doc_type"] == "recurring_lookup"
    assert service._answer_client.messages == []

    latest = service.answer_question("What is my most recent expense?")

    assert "Transaction #2" in latest["answer"]
    assert "Cost: GBP 80.00" in latest["answer"]
    assert latest["sources"][0]["document_id"] == "expense::2"
    assert service._answer_client.messages == []
    assert memory.recall(1)[0]["tools_used"] == ["find_latest_expense"]

    recurring = service.answer_question("Show my recurring reminders")

    assert recurring["answer"].startswith("Recurring reminders:")
    assert "Rent" in recurring["answer"]
    assert recurring["sources"][0]["doc_type"] == "recurring"

    total = service.answer_question("How much did I spend on Food in March 2026?")

    assert "Total spent for Food in 2026-03: GBP 65.25" in total["answer"]
    assert total["sources"][0]["document_id"] == "expense::1"


def test_rag_service_answers_late_reminders_from_calendar(tmp_path):
    class LateRecurringService(StubRecurringService):
        def upcoming_calendar(self, days):
            return {
                "window_start": "2026-06-01",
                "window_end": "2026-07-06",
                "occurrences": [],
                "completed_occurrences": [],
                "late_occurrences": [
                    {
                        "recurring_item_id": 31,
                        "date": "2026-06-10",
                        "category": "Bills",
                        "description": "Monthly Test Late Bill Reminder",
                        "amount": 12.5,
                        "entry_type": "expense",
                        "frequency": "monthly",
                        "days_until_due": -6,
                    },
                    {
                        "recurring_item_id": 32,
                        "date": "2026-06-10",
                        "category": "Income",
                        "description": "Monthly Test Late Deposit Reminder",
                        "amount": 12.5,
                        "entry_type": "expense",
                        "frequency": "monthly",
                        "days_until_due": -6,
                    },
                ],
            }

    fake_client = FakeChromaClient()
    service = RagService(
        expense_service=StubExpenseService(),
        recurring_service=LateRecurringService(),
        analytics_service=StubAnalyticsService(),
        prediction_service=StubPredictionService(),
        settings_service=StubSettingsService(),
        agent_run_repository=StubAgentRunRepository(),
        embedding_client=StubEmbeddingClient(),
        answer_client=StubAnswerClient(),
        memory_service=AgentMemoryService(tmp_path / "late-memory.json"),
        persist_directory=tmp_path / "late-chroma",
        manifest_path=tmp_path / "late-manifest.json",
        collection_name="monetra-finance-knowledge",
        chunk_size=120,
        chunk_overlap=20,
        top_k=4,
        chroma_client_factory=lambda path: fake_client,
    )

    answer = service.answer_question("Do I have any late reminders? and how many?")

    assert "2 late reminders" in answer["answer"]
    assert "Monthly Test Late Bill Reminder" in answer["answer"]
    assert "Monthly Test Late Deposit Reminder" in answer["answer"]
    assert answer["follow_up_questions"] == []
    assert answer["sources"][0]["doc_type"] == "recurring_late_occurrence"
    assert answer["sources"][1]["doc_type"] == "recurring_late_occurrence"
    assert service._answer_client.messages == []
    assert fake_client.collection.query_calls == 0


def test_rag_service_structured_answer_empty_and_next_week_edges(tmp_path):
    class EmptyExpenseService:
        def list_expenses(self, sort_direction="desc"):
            return []

    class EmptyRecurringService:
        def list_items(self):
            return []

        def upcoming_calendar(self, days):
            return {"window_start": "2026-05-18", "window_end": "2026-05-25", "occurrences": [], "completed_occurrences": []}

    class NextWeekRecurringService(StubRecurringService):
        def upcoming_calendar(self, days):
            return {
                "window_start": "2026-05-18",
                "window_end": "2026-05-25",
                "occurrences": [
                    {
                        "recurring_item_id": 20,
                        "date": "2026-05-20",
                        "category": "Subscription",
                        "description": "Gemini Pro Subscription",
                        "amount": 18.99,
                        "entry_type": "expense",
                        "frequency": "monthly",
                        "days_until_due": 2,
                    }
                ],
                "completed_occurrences": [],
            }

    empty_service = RagService(
        expense_service=EmptyExpenseService(),
        recurring_service=EmptyRecurringService(),
        analytics_service=StubAnalyticsService(),
        prediction_service=StubPredictionService(),
        settings_service=StubSettingsService(),
        agent_run_repository=StubAgentRunRepository(),
        embedding_client=StubEmbeddingClient(),
        answer_client=StubAnswerClient(),
        memory_service=AgentMemoryService(tmp_path / "empty-memory.json"),
        persist_directory=tmp_path / "empty-chroma",
        manifest_path=tmp_path / "empty-manifest.json",
        collection_name="monetra-finance-knowledge",
        chunk_size=120,
        chunk_overlap=20,
        top_k=4,
        chroma_client_factory=lambda path: FakeChromaClient(),
    )
    assert "could not find" in empty_service.answer_question("latest expense")["answer"]
    assert "none found" in empty_service.answer_question("recurring reminders")["answer"]
    assert "GBP 0.00" in empty_service.answer_question("total groceries in May 2026")["answer"]
    assert empty_service._structured_answer("general finance health") is None
    assert empty_service._matching_category("unknown category", []) is None
    assert empty_service._format_gbp("not-a-number") == "GBP 0.00"

    next_week_service = RagService(
        expense_service=StubExpenseService(),
        recurring_service=NextWeekRecurringService(),
        analytics_service=StubAnalyticsService(),
        prediction_service=StubPredictionService(),
        settings_service=StubSettingsService(),
        agent_run_repository=StubAgentRunRepository(),
        embedding_client=StubEmbeddingClient(),
        answer_client=StubAnswerClient(),
        memory_service=AgentMemoryService(tmp_path / "next-week-memory.json"),
        persist_directory=tmp_path / "next-week-chroma",
        manifest_path=tmp_path / "next-week-manifest.json",
        collection_name="monetra-finance-knowledge",
        chunk_size=120,
        chunk_overlap=20,
        top_k=4,
        chroma_client_factory=lambda path: FakeChromaClient(),
    )
    next_week = next_week_service.answer_question("Which recurring reminders are due next week?")
    assert next_week["answer"].startswith("Recurring reminders due next week:")
    assert "Gemini Pro Subscription" in next_week["answer"]
    assert next_week["sources"][0]["doc_type"] == "recurring_occurrence"


def test_rag_service_next_payment_due_uses_earliest_recurring_occurrence(tmp_path):
    class MultipleUpcomingRecurringService(StubRecurringService):
        def upcoming_calendar(self, days):
            return {
                "window_start": "2099-06-04",
                "window_end": "2099-09-01",
                "occurrences": [
                    {
                        "recurring_item_id": 20,
                        "date": "2099-06-07",
                        "category": "Subscription",
                        "description": "Chat GPT Plus",
                        "amount": 21.99,
                        "entry_type": "expense",
                        "frequency": "monthly",
                        "days_until_due": 3,
                    },
                    {
                        "recurring_item_id": 21,
                        "date": "2099-06-06",
                        "category": "Subscription",
                        "description": "Gemini Pro Subscription",
                        "amount": 18.99,
                        "entry_type": "expense",
                        "frequency": "monthly",
                        "days_until_due": 2,
                    },
                ],
                "completed_occurrences": [],
            }

    service = RagService(
        expense_service=StubExpenseService(),
        recurring_service=MultipleUpcomingRecurringService(),
        analytics_service=StubAnalyticsService(),
        prediction_service=StubPredictionService(),
        settings_service=StubSettingsService(),
        agent_run_repository=StubAgentRunRepository(),
        embedding_client=StubEmbeddingClient(),
        answer_client=StubAnswerClient(),
        memory_service=AgentMemoryService(tmp_path / "next-payment-memory.json"),
        persist_directory=tmp_path / "next-payment-chroma",
        manifest_path=tmp_path / "next-payment-manifest.json",
        collection_name="monetra-finance-knowledge",
        chunk_size=120,
        chunk_overlap=20,
        top_k=4,
        chroma_client_factory=lambda path: FakeChromaClient(),
    )

    answer = service.answer_question("What is my next payment due?")

    assert "2099-06-06" in answer["answer"]
    assert "Gemini Pro Subscription" in answer["answer"]
    assert "Chat GPT Plus" not in answer["answer"]
    assert answer["sources"][0]["document_id"] == "recurring-occurrence::21::2099-06-06"
    assert service._answer_client.messages == []


def test_rag_service_structured_total_skips_bad_dates_and_formats_ranges(tmp_path):
    class MixedExpenseService:
        def list_expenses(self, sort_direction="desc"):
            return [
                {"id": 1, "date": "bad-date", "category": "Food", "description": "Broken import", "amount": 99.0, "entry_type": "expense"},
                {"id": 2, "date": "2026-03-03", "category": "Food", "description": "March shop", "amount": 12.0, "entry_type": "expense"},
                {"id": 3, "date": "2026-06-03", "category": "Food", "description": "June shop", "amount": 15.5, "entry_type": "expense"},
            ]

    service = RagService(
        expense_service=MixedExpenseService(),
        recurring_service=StubRecurringService(),
        analytics_service=StubAnalyticsService(),
        prediction_service=StubPredictionService(),
        settings_service=StubSettingsService(),
        agent_run_repository=StubAgentRunRepository(),
        embedding_client=StubEmbeddingClient(),
        answer_client=StubAnswerClient(),
        memory_service=AgentMemoryService(tmp_path / "range-memory.json"),
        persist_directory=tmp_path / "range-chroma",
        manifest_path=tmp_path / "range-manifest.json",
        collection_name="monetra-finance-knowledge",
        chunk_size=120,
        chunk_overlap=20,
        top_k=4,
        chroma_client_factory=lambda path: FakeChromaClient(),
    )

    june = service._spending_total_answer("How much did I spend on Food in June 2026?")
    assert june["answer"] == "Total spent for Food in 2026-06: GBP 15.50 across 1 expense transaction."

    through = service._spending_total_answer("How much did I spend until July 2026?")
    assert "from 2026-06 through 2026-07" in through["answer"]


def test_rag_service_month_questions_are_exact_unless_through_scope_is_requested(rag_service):
    service, _, _ = rag_service

    june_retrieval = service.retrieve_context("Do I have any bills due in June?", top_k=6)
    june_occurrences = [source for source in june_retrieval["sources"] if source["doc_type"] == "recurring_occurrence"]

    assert june_occurrences
    assert {source["metadata"]["month_key"] for source in june_occurrences} == {"2026-06"}
    assert any("2026-06-15" in source["excerpt"] for source in june_occurrences)
    assert all("2026-05-15" not in source["excerpt"] for source in june_occurrences)

    through_retrieval = service.retrieve_context("Do I have any bills due till July?", top_k=6)
    through_months = {
        source["metadata"]["month_key"]
        for source in through_retrieval["sources"]
        if source["doc_type"] == "recurring_occurrence"
    }

    assert {"2026-06", "2026-07"}.issubset(through_months)


def test_rag_service_handles_prediction_failure_and_parsing_edges(tmp_path):
    service = RagService(
        expense_service=StubExpenseService(),
        recurring_service=StubRecurringService(),
        analytics_service=StubAnalyticsService(),
        prediction_service=StubPredictionService(fail=True),
        settings_service=StubSettingsService(),
        agent_run_repository=StubAgentRunRepository(),
        embedding_client=StubEmbeddingClient(),
        answer_client=StubAnswerClient("plain text answer"),
        memory_service=AgentMemoryService(tmp_path / "memory.json"),
        persist_directory=tmp_path / "chroma",
        manifest_path=tmp_path / "rag-manifest.json",
        collection_name="monetra-finance-knowledge",
        chunk_size=120,
        chunk_overlap=20,
        top_k=4,
        chroma_client_factory=lambda path: FakeChromaClient(),
    )

    docs = service._build_source_documents()
    assert all(doc["metadata"]["doc_type"] != "prediction" for doc in docs)
    assert service._parse_answer_payload("plain text answer")["confidence"] == "medium"
    fenced_json_answer = """```json.
{.
"answer": "No recurring bills above GBP 500 are due in June. The only recurring bill found is due on 2026-06-23.",.
"confidence": "High",.
"follow_up_questions": [
"Are there any non-recurring bills above GBP 500 due in June?"
].
}.
```."""
    assert service._parse_answer_payload(fenced_json_answer) == {
        "answer": "No recurring bills above GBP 500 are due in June. The only recurring bill found is due on 2026-06-23.",
        "confidence": "high",
        "follow_up_questions": [],
    }

    with pytest.raises(ValidationError, match="empty"):
        service._parse_answer_payload('{"answer":"  ","confidence":"high","follow_up_questions":[]}')

    with pytest.raises(ValidationError, match="question is required"):
        service.retrieve_context("   ")

def test_rag_service_answer_question_requires_sources(rag_service):
    service, fake_client, _ = rag_service
    service.reindex(force=True)
    fake_client.collection.documents = []
    fake_client.collection.metadatas = []

    with pytest.raises(ValidationError, match="No indexed finance knowledge"):
        service.answer_question("What changed?")


def test_rag_service_manifest_and_confidence_edge_paths(tmp_path):
    manifest_path = tmp_path / "rag-manifest.json"
    manifest_path.write_text("not-json", encoding="utf-8")

    service = RagService(
        expense_service=StubExpenseService(),
        recurring_service=StubRecurringService(),
        analytics_service=StubAnalyticsService(),
        prediction_service=StubPredictionService(),
        settings_service=StubSettingsService(),
        agent_run_repository=StubAgentRunRepository(),
        embedding_client=StubEmbeddingClient(),
        answer_client=StubAnswerClient('{"answer":"Grounded","confidence":"uncertain","follow_up_questions":["next?"]}'),
        memory_service=AgentMemoryService(tmp_path / "memory.json"),
        persist_directory=tmp_path / "chroma",
        manifest_path=manifest_path,
        collection_name="monetra-finance-knowledge",
        chunk_size=120,
        chunk_overlap=20,
        top_k=4,
        chroma_client_factory=lambda path: FakeChromaClient(),
    )

    assert service._load_manifest() == {}
    assert service._parse_answer_payload('{"answer":"Grounded","confidence":"uncertain","follow_up_questions":["next?"]}') == {
        "answer": "Grounded",
        "confidence": "medium",
        "follow_up_questions": [],
    }


def test_rag_service_reindex_ignores_delete_collection_errors(rag_service):
    service, fake_client, _ = rag_service

    def raising_delete(_name):
        raise RuntimeError("cannot delete")

    fake_client.delete_collection = raising_delete
    result = service.reindex(force=True)

    assert result["reindexed"] is True
    assert fake_client.collection.ids


def test_rag_service_default_chroma_factory_paths(monkeypatch, tmp_path):
    import builtins
    import sys
    import types

    fake_module = types.SimpleNamespace(PersistentClient=lambda path: {"path": path})
    monkeypatch.setitem(sys.modules, "chromadb", fake_module)
    assert RagService._default_chroma_client_factory(tmp_path) == {"path": str(tmp_path)}

    monkeypatch.delitem(sys.modules, "chromadb", raising=False)
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "chromadb":
            raise ImportError("missing chroma")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(Exception, match="ChromaDB is not installed"):
        RagService._default_chroma_client_factory(tmp_path)


def test_rag_service_remaining_retrieval_document_and_helper_edges(monkeypatch, tmp_path):
    import builtins
    import sys
    import types
    from datetime import date

    class CompletedRecurringService(StubRecurringService):
        def upcoming_calendar(self, days):
            payload = super().upcoming_calendar(days)
            payload["completed_occurrences"] = [
                {
                    "recurring_item_id": 10,
                    "date": "2026-06-15",
                    "category": "Housing",
                    "description": "Rent",
                    "amount": 700.0,
                    "entry_type": "expense",
                    "frequency": "monthly",
                    "days_until_due": 31,
                    "transaction_id": 99,
                    "updated_at": "2026-06-15T08:00:00Z",
                }
            ]
            return payload

    fake_client = FakeChromaClient()
    memory = AgentMemoryService(tmp_path / "memory.json")
    memory.remember(
        kind="rag_query",
        task="previous question",
        summary="previous answer",
        tools_used=["retrieve_finance_context"],
    )
    service = RagService(
        expense_service=StubExpenseService(),
        recurring_service=CompletedRecurringService(),
        analytics_service=StubAnalyticsService(),
        prediction_service=StubPredictionService(),
        settings_service=StubSettingsService(),
        agent_run_repository=StubAgentRunRepository(),
        embedding_client=StubEmbeddingClient(),
        answer_client=StubAnswerClient(""),
        memory_service=memory,
        persist_directory=tmp_path / "chroma",
        manifest_path=tmp_path / "rag-manifest.json",
        collection_name="monetra-finance-knowledge",
        chunk_size=120,
        chunk_overlap=20,
        top_k=4,
        chroma_client_factory=lambda path: fake_client,
    )

    docs = service._build_source_documents()
    assert any("Paid True" in doc["text"] for doc in docs)
    assert any(doc["metadata"]["doc_type"] == "agent_memory" for doc in docs)

    no_match = service.retrieve_context("Do I have bills due in December 2099?", top_k=4)
    assert no_match["sources"][0]["doc_type"] == "recurring_occurrence_search"

    injected_source = {
        "source_label": "Injected calendar",
        "doc_type": "recurring_occurrence",
        "document_id": "recurring-occurrence::99::2026-05-20",
        "excerpt": "Injected bill due on 2026-05-20.",
        "score": 1.0,
        "metadata": {"doc_type": "recurring_occurrence", "chunk_index": 0},
    }
    monkeypatch.setattr(
        RagService,
        "_calendar_month_sources",
        classmethod(lambda cls, collection, question: [injected_source]),
    )
    injected = service.retrieve_context("What changed in my finances?", top_k=4)
    assert any(source["source_label"] == "Injected calendar" for source in injected["sources"])

    class RaisingCollection:
        def get(self, *args, **kwargs):
            raise RuntimeError("collection unavailable")

    assert RagService._calendar_month_sources(RaisingCollection(), "Do I have bills due in 2026-05?") == [
        injected_source
    ]
    monkeypatch.undo()
    assert RagService._calendar_month_sources(RaisingCollection(), "Do I have bills due in 2026-05?") == []
    assert RagService._essential_finance_sources(RaisingCollection()) == []

    class MixedCollection:
        def get(self, where=None, include=None):
            return {
                "documents": ["dashboard", "income reminder", "expense reminder"],
                "metadatas": [
                    {"doc_type": "dashboard", "document_id": "dashboard::1"},
                    {"doc_type": "recurring_occurrence", "entry_type": "income", "document_id": "income::1"},
                    {
                        "doc_type": "recurring_occurrence",
                        "entry_type": "expense",
                        "document_id": "expense::1",
                        "source_label": "Expense reminder",
                    },
                ],
            }

    month_sources = RagService._calendar_month_sources(MixedCollection(), "Do I have bills due in May 2026?")
    assert [source["document_id"] for source in month_sources] == ["expense::1"]

    assert "through" in RagService._no_calendar_match_source("Do I have bills due until 2026-07?")["excerpt"]
    assert "requested period" in RagService._no_calendar_match_source("Do I have any bills?")["excerpt"]
    assert RagService._extract_requested_month_key("Do I have bills due in 2026-07?") == "2026-07"
    assert RagService._extract_requested_month_scope("Do I have bills due until 2026-07?")["end_month"] == "2026-07"
    assert RagService._month_keys_between("2026-07", "2026-05") == ["2026-05", "2026-06", "2026-07"]
    assert RagService._month_keys_between("2026-12", "2027-01") == ["2026-12", "2027-01"]

    ranked = RagService._rerank_sources(
        "Is rent due on 2026-05-20?",
        [
            {
                "source_label": "Rent",
                "doc_type": "recurring_occurrence",
                "document_id": "rent",
                "excerpt": "Rent due.",
                "score": 0.1,
                "metadata": {"doc_type": "recurring_occurrence", "entry_type": "expense", "date": "2026-05-20"},
            }
        ],
        1,
    )
    assert ranked[0]["document_id"] == "rent"

    occurrences = RagService._build_recurring_occurrences_for_index(
        [
            {"active": False, "start_date": "2026-05-01", "frequency": "monthly"},
            {"active": True, "start_date": "bad-date", "frequency": "monthly"},
            {
                "id": 50,
                "active": True,
                "start_date": "2026-05-01",
                "end_date": "2026-05-15",
                "frequency": "weekly",
                "description": "Weekly gym",
                "category": "Health",
                "amount": 12.0,
                "entry_type": "expense",
            },
        ]
    )
    assert all(item["recurring_item_id"] == 50 for item in occurrences)
    assert RagService._parse_date("bad-date") is None
    assert RagService._next_recurring_due_date(date(2026, 5, 1), "weekly") == date(2026, 5, 8)
    assert RagService._sanitize_metadata({"skip": None, "plain": "value", "nested": {"a": 1}}) == {
        "plain": "value",
        "nested": '{"a": 1}',
    }
    assert service._parse_answer_payload("")["answer"].startswith("I could not produce")

    http_service = RagService(
        expense_service=StubExpenseService(),
        recurring_service=StubRecurringService(),
        analytics_service=StubAnalyticsService(),
        prediction_service=StubPredictionService(),
        settings_service=StubSettingsService(),
        agent_run_repository=StubAgentRunRepository(),
        embedding_client=StubEmbeddingClient(),
        answer_client=StubAnswerClient(),
        memory_service=AgentMemoryService(tmp_path / "http-memory.json"),
        persist_directory=tmp_path / "http-chroma",
        manifest_path=tmp_path / "http-manifest.json",
        collection_name="monetra-finance-knowledge",
        chunk_size=120,
        chunk_overlap=20,
        top_k=4,
        chroma_http_host="chroma",
        chroma_http_port=8000,
    )
    monkeypatch.setattr(http_service, "_http_chroma_client_factory", lambda: "http-client")
    assert http_service._create_chroma_client() == "http-client"
    monkeypatch.undo()

    fake_chroma = types.SimpleNamespace(HttpClient=lambda host, port, ssl: {"host": host, "port": port, "ssl": ssl})
    monkeypatch.setitem(sys.modules, "chromadb", fake_chroma)
    assert http_service._http_chroma_client_factory() == {"host": "chroma", "port": 8000, "ssl": False}

    monkeypatch.setitem(sys.modules, "chromadb", types.SimpleNamespace())
    with pytest.raises(Exception, match="HTTP-only client"):
        RagService._default_chroma_client_factory(tmp_path)

    monkeypatch.delitem(sys.modules, "chromadb", raising=False)
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "chromadb":
            raise ImportError("missing chroma")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(Exception, match="ChromaDB HTTP client is not installed"):
        http_service._http_chroma_client_factory()


def test_rag_service_remaining_structured_answer_edges(rag_service, tmp_path):
    service, _, _ = rag_service

    first = service.answer_question("What is my cash flow?")
    second = service.answer_question("What is my cash flow?")
    assert first == second

    class EmptyAnalytics(StubAnalyticsService):
        def dashboard(self):
            payload = super().dashboard()
            payload.pop("percent_spent", None)
            payload["monthly_budget"] = 0.0
            payload["current_month_total"] = 0.0
            payload["monthly_expenses"] = 0.0
            return payload

        def category_insights(self):
            return {"top_categories": [], "bottom_categories": [], "total_spending": 0.0}

        def financial_pulse(self):
            payload = super().financial_pulse()
            payload["runway_days"] = "bad"
            return payload

    class EmptyExpenseService(StubExpenseService):
        def list_expenses(self, sort_direction="desc"):
            return [
                {"id": 1, "date": "bad-date", "category": "Food", "description": "Bad", "amount": "bad", "entry_type": "expense"},
                {"id": 2, "date": "2026-03-02", "category": "Income", "description": "Income", "amount": 100, "entry_type": "income"},
            ]

    class EmptyRecurringService(StubRecurringService):
        def upcoming_calendar(self, days):
            return {"window_start": "2026-06-01", "window_end": "2026-06-30", "occurrences": [], "late_occurrences": [], "completed_occurrences": []}

    empty_service = RagService(
        expense_service=EmptyExpenseService(),
        recurring_service=EmptyRecurringService(),
        analytics_service=EmptyAnalytics(),
        prediction_service=StubPredictionService(),
        settings_service=StubSettingsService(),
        agent_run_repository=StubAgentRunRepository(),
        embedding_client=StubEmbeddingClient(),
        answer_client=StubAnswerClient(),
        memory_service=AgentMemoryService(tmp_path / "edge-memory.json"),
        persist_directory=tmp_path / "edge-chroma",
        manifest_path=tmp_path / "edge-manifest.json",
        collection_name="monetra-finance-knowledge",
        chunk_size=120,
        chunk_overlap=20,
        top_k=4,
        chroma_client_factory=lambda path: FakeChromaClient(),
    )

    assert "No category data" in empty_service.answer_question("What are my top categories?")["answer"]
    assert "could not find any expense transactions" in empty_service.answer_question("Which month do I spend the most and least?")["answer"]
    assert "could not find any expense categories" in empty_service.answer_question("Which categories do I spend most and least?")["answer"]
    assert "cannot be calculated" in empty_service.answer_question("What is my budget consumption as a percentage?")["answer"].lower()
    assert "could not find any upcoming expense payments" in empty_service.answer_question("What is the next payment due?")["answer"]
    assert "do not have any late reminders" in empty_service.answer_question("Do I have late reminders?")["answer"]

    class MultiRecurringService(StubRecurringService):
        def upcoming_calendar(self, days):
            return {
                "window_start": "2026-06-01",
                "window_end": "2026-06-30",
                "occurrences": [
                    {"recurring_item_id": 1, "date": "2026-06-10", "category": "Subscription", "description": "Gemini", "amount": 18.99, "entry_type": "expense", "frequency": "monthly", "days_until_due": 1},
                    {"recurring_item_id": 2, "date": "2026-06-10", "category": "Subscription", "description": "ChatGPT", "amount": 21.99, "entry_type": "expense", "frequency": "monthly", "days_until_due": 1},
                ],
                "late_occurrences": [],
                "completed_occurrences": [],
            }

    multi_service = RagService(
        expense_service=StubExpenseService(),
        recurring_service=MultiRecurringService(),
        analytics_service=StubAnalyticsService(),
        prediction_service=StubPredictionService(),
        settings_service=StubSettingsService(),
        agent_run_repository=StubAgentRunRepository(),
        embedding_client=StubEmbeddingClient(),
        answer_client=StubAnswerClient(),
        memory_service=AgentMemoryService(tmp_path / "multi-memory.json"),
        persist_directory=tmp_path / "multi-chroma",
        manifest_path=tmp_path / "multi-manifest.json",
        collection_name="monetra-finance-knowledge",
        chunk_size=120,
        chunk_overlap=20,
        top_k=4,
        chroma_client_factory=lambda path: FakeChromaClient(),
    )
    assert "Other payments are also due" in multi_service.answer_question("What is the next payment due?")["answer"]

    class PositiveComparisonExpenseService(StubExpenseService):
        def list_expenses(self, sort_direction="desc"):
            return [
                {"id": 1, "date": "2026-05-01", "category": "Food", "description": "May", "amount": 100, "entry_type": "expense"},
                {"id": 2, "date": "2026-06-01", "category": "Food", "description": "June", "amount": 150, "entry_type": "expense"},
            ]

    class NoPercentAnalytics(StubAnalyticsService):
        def dashboard(self):
            payload = super().dashboard()
            payload.pop("percent_spent", None)
            payload["monthly_budget"] = 200.0
            payload["current_month_total"] = 50.0
            payload["monthly_expenses"] = 50.0
            return payload

    positive_service = RagService(
        expense_service=PositiveComparisonExpenseService(),
        recurring_service=StubRecurringService(),
        analytics_service=NoPercentAnalytics(),
        prediction_service=StubPredictionService(),
        settings_service=StubSettingsService(),
        agent_run_repository=StubAgentRunRepository(),
        embedding_client=StubEmbeddingClient(),
        answer_client=StubAnswerClient(),
        memory_service=AgentMemoryService(tmp_path / "positive-memory.json"),
        persist_directory=tmp_path / "positive-chroma",
        manifest_path=tmp_path / "positive-manifest.json",
        collection_name="monetra-finance-knowledge",
        chunk_size=120,
        chunk_overlap=20,
        top_k=4,
        chroma_client_factory=lambda path: FakeChromaClient(),
    )
    assert "+50.0%" in positive_service.answer_question("What is change vs previous?")["answer"]
    assert "25.00%" in positive_service.answer_question("What is my budget consumption as a percentage?")["answer"]

    assert RagService._is_cash_flow_question("cash and flow") is True
    assert RagService._financial_pulse_metric("What is my health score?") == "health_score"
    assert RagService._financial_pulse_metric("What is my income coverage?") == "income_coverage"
    assert RagService._financial_pulse_metric("What is my top category share?") == "top_category_share"
    assert RagService._financial_pulse_metric("What is my budget runway?") == "budget_runway"
    assert RagService._financial_pulse_metric("unknown metric") is None
    assert RagService._kpi_studio_metric("month end forecast") == "month_end_forecast"
    assert RagService._kpi_studio_metric("largest category share") == "largest_category_share"
    assert RagService._kpi_studio_metric("average daily burn") == "average_daily_burn"
    assert RagService._kpi_studio_metric("current month transactions") == "current_month_transactions"
    assert RagService._kpi_studio_metric("unknown metric") is None
    assert RagService._comparison_metric("current period") == "current_period"
    assert RagService._comparison_metric("average spend") == "average_spend"
    assert RagService._comparison_metric("strongest period") == "strongest_period"
    assert RagService._comparison_metric("change versus previous") == "change_vs_previous"
    assert RagService._comparison_metric("unknown metric") is None
    assert RagService._is_financial_status_question("how healthy are my finances") is False
    assert RagService._is_remaining_budget_question("budget left") is True
    assert RagService._is_budget_consumption_question("budget as a percentage") is True
    assert RagService._is_monthly_income_question("income and bill") is False
    assert RagService._as_float(object()) == 0.0
    assert RagService._month_label("bad") == "bad"
    assert RagService._scope_label({"start_month": "2026-01", "end_month": "2026-03"}) == "January 2026 through March 2026"
    assert empty_service._dashboard_monthly_expenses({"monthly_expenses": 12.5}) == 12.5


def test_metric_registry_and_router_remaining_intents():
    registry = MetricRegistry({FinanceIntent.CASH_FLOW: lambda question: {"answer": question}})
    assert registry.execute(FinanceIntent.OPEN_ENDED, "anything") is None
    assert registry.execute(FinanceIntent.MONTHLY_BUDGET, "missing handler") is None
    assert registry.execute(FinanceIntent.CASH_FLOW, "cash flow") == {"answer": "cash flow"}

    router = FinanceIntentRouter()
    cases = {
        "monthly transaction count": FinanceIntent.CURRENT_MONTH_TRANSACTIONS,
        "largest category share": FinanceIntent.LARGEST_CATEGORY_SHARE,
        "income coverage": FinanceIntent.INCOME_COVERAGE,
        "category share": FinanceIntent.TOP_CATEGORY_SHARE,
        "runway": FinanceIntent.BUDGET_RUNWAY,
        "health score": FinanceIntent.HEALTH_SCORE,
        "spending velocity": FinanceIntent.SPEND_VELOCITY,
        "avg transaction": FinanceIntent.AVERAGE_TRANSACTION,
        "current period": FinanceIntent.CURRENT_PERIOD,
        "average spend": FinanceIntent.AVERAGE_SPEND,
        "strongest period": FinanceIntent.STRONGEST_PERIOD,
        "change versus previous": FinanceIntent.CHANGE_VS_PREVIOUS,
        "piggy bank contribution": FinanceIntent.PIGGY_BANK_CONTRIBUTION,
        "piggy bank carryover": FinanceIntent.PIGGY_BANK_CARRYOVER,
        "piggy bank": FinanceIntent.PIGGY_BANK_BALANCE,
        "which categories had the highest and lowest spend": FinanceIntent.CATEGORY_SPEND_EXTREMES,
        "which months did I spend the most and least": FinanceIntent.MONTHLY_SPEND_EXTREMES,
        "top categories": FinanceIntent.MONTHLY_TOP_CATEGORIES,
        "bottom categories": FinanceIntent.MONTHLY_BOTTOM_CATEGORIES,
        "monthly insights": FinanceIntent.MONTHLY_CATEGORY_INSIGHTS,
        "what is my income": FinanceIntent.MONTHLY_INCOME,
    }
    for question, expected in cases.items():
        assert router.classify(question) is expected
