import json
import logging
import socket
import time
from urllib import error, request

from budget_tracker_api.errors import ServiceUnavailableError


logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout_seconds: int):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def timeout_seconds(self) -> int:
        return self._timeout_seconds

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        payload: dict = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        body = json.dumps(payload).encode("utf-8")
        endpoint = f"{self._base_url}/api/chat"
        http_request = request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        started = time.perf_counter()
        logger.info(
            "Ollama chat request started | model=%s tools=%s timeout_seconds=%s",
            self._model,
            bool(tools),
            self._timeout_seconds,
        )
        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                raw_payload = response.read().decode("utf-8")
            logger.info(
                "Ollama chat request completed | model=%s duration_ms=%.1f",
                self._model,
                (time.perf_counter() - started) * 1000,
            )
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")
            logger.exception("Ollama HTTP error.")
            raise ServiceUnavailableError(
                f"Ollama request failed with HTTP {exc.code}. {details}".strip()
            ) from exc
        except error.URLError as exc:
            logger.exception("Ollama connection error.")
            raise ServiceUnavailableError(
                "Could not reach Ollama. Make sure Ollama is running locally."
            ) from exc
        except (TimeoutError, socket.timeout) as exc:
            logger.exception("Ollama timeout.")
            raise ServiceUnavailableError(
                "Ollama timed out. Try a smaller local model or increase OLLAMA_TIMEOUT_SECONDS."
            ) from exc

        try:
            return json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            logger.exception("Ollama returned invalid JSON.")
            raise ServiceUnavailableError("Ollama returned an invalid response.") from exc
