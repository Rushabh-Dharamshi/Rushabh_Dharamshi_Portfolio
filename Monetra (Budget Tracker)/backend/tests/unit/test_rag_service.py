from pathlib import Path

import pytest

from budget_tracker_api.errors import ValidationError
from budget_tracker_api.services.agent_memory_service import AgentMemoryService
from budget_tracker_api.services.rag_service import RagService


class StubExpenseService:
    def list_expenses(self, sort_direction="desc"):
        return [
            {"id": 1, "date": "2026-03-01", "category": "Food", "description": "Groceries", "amount": 65.25, "entry_type": "expense"},
            {"id": 2, "date": "2026-03-03", "category": "Travel", "description": "Train pass", "amount": 80.0, "entry_type": "expense"},
        ]


class StubRecurringService:
    def list_items(self):
        return [
            {"id": 10, "category": "Housing", "description": "Rent", "amount": 700.0, "entry_type": "expense", "frequency": "monthly", "start_date": "2026-03-15", "end_date": None, "active": True},
        ]

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
            "status": "within",
        }

    def financial_pulse(self):
        return {
            "narrative": "Healthy but with housing pressure.",
            "health_score": 82,
            "cash_in": 1500.0,
            "cash_out": 420.0,
            "net_cash_flow": 1080.0,
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
        return {"monthly_budget": 1050.0, "monthly_income": 1500.0, "income_month": month_key or "2026-03"}


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

    def upsert(self, ids, documents, metadatas, embeddings):
        self.ids = list(ids)
        self.documents = list(documents)
        self.metadatas = list(metadatas)
        self.embeddings = list(embeddings)

    def query(self, query_embeddings, n_results, include):
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
        self.deleted_collections = []

    def delete_collection(self, name):
        self.deleted_collections.append(name)

    def get_or_create_collection(self, name, metadata=None):
        return self.collection


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
    assert retrieval["sources"][0]["source_label"]
    assert answer["confidence"] == "high"
    assert answer["sources"]
    assert memory_items[0]["kind"] == "rag_query"


def test_rag_service_multi_query_includes_requested_month_recurring_occurrences(rag_service):
    service, _, _ = rag_service

    retrieval = service.retrieve_context("Do I have any bills due in the whole of May?", top_k=6)

    assert retrieval["sources"][0]["doc_type"] == "recurring_occurrence"
    assert any(source["doc_type"] == "recurring_occurrence" for source in retrieval["sources"])
    assert any("2026-05-15" in source["excerpt"] for source in retrieval["sources"])
    assert len(service._build_query_variants("Do I have any bills due in the whole of May?")) > 1
    assert service._rerank_sources("bills due in May", retrieval["sources"], 1)[0]["doc_type"] == "recurring_occurrence"


def test_rag_service_month_questions_are_exact_unless_through_scope_is_requested(rag_service):
    service, _, _ = rag_service

    june_retrieval = service.retrieve_context("Do I have any bills due in June?", top_k=6)
    june_occurrences = [source for source in june_retrieval["sources"] if source["doc_type"] == "recurring_occurrence"]

    assert june_occurrences
    assert {source["metadata"]["month_key"] for source in june_occurrences} == {"2026-06"}
    assert any("2026-06-15" in source["excerpt"] for source in june_occurrences)
    assert all("2026-05-15" not in source["excerpt"] for source in june_occurrences)

    through_retrieval = service.retrieve_context("Do I have any bills due till June?", top_k=6)
    through_months = {
        source["metadata"]["month_key"]
        for source in through_retrieval["sources"]
        if source["doc_type"] == "recurring_occurrence"
    }

    assert {"2026-05", "2026-06"}.issubset(through_months)


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
        "follow_up_questions": ["Are there any non-recurring bills above GBP 500 due in June?"],
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
        "follow_up_questions": ["next?"],
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
