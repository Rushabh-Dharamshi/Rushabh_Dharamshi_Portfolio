import json
import logging
import socket
import time
from urllib import error, request

from budget_tracker_api.errors import ServiceUnavailableError


logger = logging.getLogger(__name__)


class OllamaEmbeddingClient:
    def __init__(self, base_url: str, model: str, timeout_seconds: int):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    @property
    def model(self) -> str:
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            return self._call_embed_endpoint("/api/embed", texts)
        except ServiceUnavailableError:
            return self._call_legacy_embeddings_endpoint(texts)

    def _call_embed_endpoint(self, path: str, texts: list[str]) -> list[list[float]]:
        payload = {
            "model": self._model,
            "input": texts,
        }
        body = json.dumps(payload).encode("utf-8")
        endpoint = f"{self._base_url}{path}"
        http_request = request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        started = time.perf_counter()
        logger.info(
            "Ollama embedding request started | model=%s inputs=%s timeout_seconds=%s",
            self._model,
            len(texts),
            self._timeout_seconds,
        )
        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                raw_payload = response.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")
            logger.exception("Ollama embedding HTTP error.")
            raise ServiceUnavailableError(
                f"Ollama embedding request failed with HTTP {exc.code}. {details}".strip()
            ) from exc
        except error.URLError as exc:
            logger.exception("Ollama embedding connection error.")
            raise ServiceUnavailableError(
                "Could not reach Ollama embeddings. Make sure Ollama is running locally."
            ) from exc
        except (TimeoutError, socket.timeout) as exc:
            logger.exception("Ollama embedding timeout.")
            raise ServiceUnavailableError(
                "Ollama embeddings timed out. Try a smaller local model or reduce the indexed corpus."
            ) from exc

        logger.info(
            "Ollama embedding request completed | model=%s duration_ms=%.1f",
            self._model,
            (time.perf_counter() - started) * 1000,
        )
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            logger.exception("Ollama embedding returned invalid JSON.")
            raise ServiceUnavailableError("Ollama embedding returned an invalid response.") from exc

        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list):
            raise ServiceUnavailableError("Ollama embedding response did not include embeddings.")
        return embeddings

    def _call_legacy_embeddings_endpoint(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            payload = {
                "model": self._model,
                "prompt": text,
            }
            body = json.dumps(payload).encode("utf-8")
            endpoint = f"{self._base_url}/api/embeddings"
            http_request = request.Request(
                endpoint,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                    raw_payload = response.read().decode("utf-8")
                parsed = json.loads(raw_payload)
            except Exception as exc:
                raise ServiceUnavailableError("Ollama embeddings are unavailable.") from exc
            embedding = parsed.get("embedding")
            if not isinstance(embedding, list):
                raise ServiceUnavailableError("Ollama legacy embedding response did not include an embedding.")
            embeddings.append(embedding)
        return embeddings
