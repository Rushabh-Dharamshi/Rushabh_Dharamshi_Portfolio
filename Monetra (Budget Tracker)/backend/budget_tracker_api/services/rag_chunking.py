from __future__ import annotations

import re
from collections.abc import Iterable


class RagChunkingService:
    def __init__(self, chunk_size: int = 700, chunk_overlap: int = 120):
        self._chunk_size = max(200, int(chunk_size))
        self._chunk_overlap = max(0, min(int(chunk_overlap), self._chunk_size // 2))

    def chunk_document(self, document_id: str, text: str, metadata: dict) -> list[dict]:
        normalized = self._normalize_text(text)
        if not normalized:
            return []

        sentences = self._split_sentences(normalized)
        if not sentences:
            return []

        chunks: list[dict] = []
        current_sentences: list[str] = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)
            if current_sentences and current_length + 1 + sentence_length > self._chunk_size:
                chunks.append(self._build_chunk(document_id, len(chunks), current_sentences, metadata))
                current_sentences = self._build_overlap_sentences(current_sentences)
                current_length = len(" ".join(current_sentences))

            if sentence_length > self._chunk_size and not current_sentences:
                chunks.extend(self._chunk_long_sentence(document_id, sentence, metadata, len(chunks)))
                current_sentences = []
                current_length = 0
                continue

            current_sentences.append(sentence)
            current_length = len(" ".join(current_sentences))

        if current_sentences:
            chunks.append(self._build_chunk(document_id, len(chunks), current_sentences, metadata))

        return chunks

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = re.sub(r"\r\n?", "\n", str(text or ""))
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        normalized = re.sub(r"[ \t]+", " ", normalized)
        return normalized.strip()

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
        sentences: list[str] = []
        for paragraph in paragraphs:
            parts = re.split(r"(?<=[.!?])\s+", paragraph)
            cleaned = [part.strip() for part in parts if part.strip()]
            if cleaned:
                sentences.extend(cleaned)
        return sentences

    def _chunk_long_sentence(self, document_id: str, sentence: str, metadata: dict, start_index: int) -> list[dict]:
        chunks = []
        step = max(1, self._chunk_size - self._chunk_overlap)
        for offset, start in enumerate(range(0, len(sentence), step)):
            part = sentence[start : start + self._chunk_size].strip()
            if not part:
                continue
            chunks.append(
                self._build_chunk(document_id, start_index + offset, [part], metadata)
            )
        return chunks

    def _build_overlap_sentences(self, sentences: list[str]) -> list[str]:
        if self._chunk_overlap <= 0:
            return []
        overlap: list[str] = []
        for sentence in reversed(sentences):
            proposed = [sentence, *overlap]
            if len(" ".join(proposed)) > self._chunk_overlap and overlap:
                break
            overlap = proposed
            if len(" ".join(overlap)) >= self._chunk_overlap:
                break
        return overlap

    @staticmethod
    def _build_chunk(document_id: str, index: int, sentences: Iterable[str], metadata: dict) -> dict:
        text = " ".join(sentences).strip()
        return {
            "id": f"{document_id}::chunk::{index}",
            "text": text,
            "metadata": {
                **metadata,
                "document_id": document_id,
                "chunk_index": index,
            },
        }
