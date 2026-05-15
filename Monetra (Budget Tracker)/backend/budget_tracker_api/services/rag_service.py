from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from budget_tracker_api.errors import ServiceUnavailableError, ValidationError
from budget_tracker_api.services.agent_memory_service import AgentMemoryService
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
        self._chroma_client_factory = chroma_client_factory or self._default_chroma_client_factory

    def status(self) -> dict:
        manifest = self._load_manifest()
        return {
            "available": True,
            "collection_name": self._collection_name,
            "indexed_at": manifest.get("indexed_at"),
            "document_count": int(manifest.get("document_count", 0)),
            "chunk_count": int(manifest.get("chunk_count", 0)),
            "signature": manifest.get("signature"),
        }

    def reindex(self, force: bool = False) -> dict:
        source_documents = self._build_source_documents()
        chunks = self._build_chunks(source_documents)
        signature = self._build_signature(source_documents)
        manifest = self._load_manifest()
        if not force and manifest.get("signature") == signature and int(manifest.get("chunk_count", 0)) == len(chunks):
            return {
                **self.status(),
                "reindexed": False,
            }

        self._persist_directory.mkdir(parents=True, exist_ok=True)
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)

        client = self._create_chroma_client()
        try:
            client.delete_collection(self._collection_name)
        except Exception:
            pass
        collection = client.get_or_create_collection(
            name=self._collection_name,
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
        }
        self._manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {
            **payload,
            "available": True,
            "collection_name": self._collection_name,
            "reindexed": True,
        }

    def retrieve_context(self, question: str, top_k: int | None = None) -> dict:
        normalized_question = str(question or "").strip()
        if not normalized_question:
            raise ValidationError("question is required.")
        self.reindex(force=False)
        client = self._create_chroma_client()
        collection = client.get_or_create_collection(name=self._collection_name, metadata={"hnsw:space": "cosine"})
        n_results = max(1, min(int(top_k or self._top_k), 12))
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
        return {
            "question": normalized_question,
            "sources": sources,
            "retrieved_count": len(sources),
            "indexed_at": self._load_manifest().get("indexed_at"),
        }

    def answer_question(self, question: str) -> dict:
        retrieval = self.retrieve_context(question)
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
                    "Return JSON with keys: answer, confidence, follow_up_questions."
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
        }
        self._memory_service.remember(
            kind="rag_query",
            task=question,
            summary=parsed["answer"],
            tools_used=["retrieve_finance_context"],
            metadata={"confidence": parsed["confidence"]},
        )
        return answer

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
                    f"Monthly budget is GBP {dashboard.get('monthly_budget')}. "
                    f"Expenses this month are GBP {dashboard.get('current_month_total')}. "
                    f"Monthly income is GBP {dashboard.get('monthly_income')}. "
                    f"Net cash flow is GBP {dashboard.get('net_cash_flow')}. "
                    f"Remaining budget is GBP {dashboard.get('remaining_budget')}. "
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
                    f"Cash in GBP {pulse.get('cash_in')}. Cash out GBP {pulse.get('cash_out')}. "
                    f"Net cash flow GBP {pulse.get('net_cash_flow')}. Runway days {pulse.get('runway_days')}."
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
                        f"{item.get('category')} GBP {item.get('amount')}" for item in categories.get("top_categories", [])
                    )
                    + ". Bottom categories: "
                    + "; ".join(
                        f"{item.get('category')} GBP {item.get('amount')}" for item in categories.get("bottom_categories", [])
                    )
                    + f". Total spending GBP {categories.get('total_spending')}."
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
                    f"Budget settings. Monthly budget GBP {settings.get('monthly_budget')}. "
                    f"Monthly income GBP {settings.get('monthly_income')} for {settings.get('income_month') or dashboard.get('month_key')}."
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
                        f"Predicted spending GBP {prediction.get('predicted_spending')}. "
                        f"Budget exceeded {prediction.get('is_budget_exceeded')}. "
                        f"Budget baseline GBP {prediction.get('monthly_budget')}."
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
                        f"Description {expense['description']}. Amount GBP {expense['amount']}. "
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
                        f"Amount GBP {item['amount']}. Frequency {item['frequency']}. "
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
                            f"{item.get('description')} is due on {item.get('date')} for GBP {item.get('amount')} "
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
                        f"Amount GBP {occurrence.get('amount')}. Entry type {occurrence.get('entry_type')}. "
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
        payload = json.dumps(source_documents, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _load_manifest(self) -> dict[str, Any]:
        if not self._manifest_path.exists():
            return {}
        try:
            payload = json.loads(self._manifest_path.read_text(encoding="utf-8"))
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
        follow_up_questions = [
            str(item).strip()
            for item in parsed.get("follow_up_questions", [])
            if str(item).strip()
        ]
        return {
            "answer": answer,
            "confidence": confidence,
            "follow_up_questions": follow_up_questions,
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
                "Set CHROMA_HTTP_HOST and run a Chroma server, or install the full chromadb package for embedded local storage."
            )
        return chromadb.PersistentClient(path=str(path))

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
