import pytest

from budget_tracker_api.services.rag_chunking import RagChunkingService


def test_chunk_document_builds_overlapping_chunks_and_metadata():
    service = RagChunkingService(chunk_size=220, chunk_overlap=60)
    text = " ".join([
        "Rent is due soon.",
        "Utilities increased this month.",
        "Travel spending is stable.",
        "Coffee spend is small.",
        "Insurance renewal is scheduled.",
        "Groceries are slightly higher than last month.",
        "Subscription spend is unchanged.",
        "Savings transfers remained consistent.",
        "Transport costs fell after remote work days.",
        "Dining out rose at the weekend.",
    ])

    chunks = service.chunk_document(
        document_id="doc-1",
        text=text,
        metadata={"doc_type": "summary"},
    )

    assert len(chunks) >= 2
    assert chunks[0]["id"] == "doc-1::chunk::0"
    assert chunks[0]["metadata"]["document_id"] == "doc-1"
    assert chunks[1]["metadata"]["chunk_index"] == 1
    assert chunks[1]["text"]


def test_chunk_document_handles_empty_and_long_sentence_paths():
    service = RagChunkingService(chunk_size=220, chunk_overlap=80)

    assert service.chunk_document("doc-empty", "   ", {"doc_type": "empty"}) == []

    long_sentence = "A" * 520
    chunks = service.chunk_document("doc-long", long_sentence, {"doc_type": "long"})

    assert len(chunks) >= 3
    assert all(chunk["text"] for chunk in chunks)
    assert chunks[0]["metadata"]["doc_type"] == "long"


def test_build_overlap_sentences_can_return_empty_when_disabled():
    service = RagChunkingService(chunk_size=220, chunk_overlap=0)
    assert service._build_overlap_sentences(["one", "two"]) == []


def test_normalize_and_split_sentences_are_resilient():
    service = RagChunkingService()
    normalized = service._normalize_text("Line one.\r\n\r\n\r\nLine two!   ")
    assert normalized == "Line one.\n\nLine two!"
    assert service._split_sentences(normalized) == ["Line one.", "Line two!"]

def test_chunk_document_returns_empty_when_sentence_splitter_returns_nothing(monkeypatch):
    service = RagChunkingService(chunk_size=220, chunk_overlap=40)
    monkeypatch.setattr(service, "_split_sentences", lambda text: [])

    assert service.chunk_document("doc-empty-sentences", "Text that normalizes.", {"doc_type": "test"}) == []


def test_chunk_long_sentence_skips_empty_parts():
    service = RagChunkingService(chunk_size=220, chunk_overlap=80)

    assert service._chunk_long_sentence("doc-space", " " * 500, {"doc_type": "blank"}, 0) == []
