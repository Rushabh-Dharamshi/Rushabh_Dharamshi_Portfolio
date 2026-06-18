from urllib import error

import pytest

from budget_tracker_api.errors import ServiceUnavailableError
from budget_tracker_api.services.ollama_client import OllamaClient


class FakeResponse:
    def __init__(self, payload: str):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._payload.encode("utf-8")


class FakeHttpError(error.HTTPError):
    def __init__(self):
        super().__init__("http://localhost", 500, "boom", hdrs=None, fp=None)

    def read(self):
        return b"bad things"


def test_ollama_client_properties_and_chat(monkeypatch):
    captured = {}

    def fake_urlopen(http_request, timeout):
        captured["url"] = http_request.full_url
        captured["timeout"] = timeout
        captured["body"] = http_request.data.decode("utf-8")
        return FakeResponse('{"message": {"content": "ok"}}')

    monkeypatch.setattr("budget_tracker_api.services.ollama_client.request.urlopen", fake_urlopen)
    client = OllamaClient("http://localhost:11434/", "qwen2.5:7b", 45)

    result = client.chat([{"role": "user", "content": "hello"}], tools=[{"type": "function"}])

    assert client.base_url == "http://localhost:11434"
    assert client.model == "qwen2.5:7b"
    assert client.timeout_seconds == 45
    assert result == {"message": {"content": "ok"}}
    assert captured["url"].endswith("/api/chat")
    assert '"tools": [{"type": "function"}]' in captured["body"]


@pytest.mark.parametrize(
    ("side_effect", "message"),
    [
        (FakeHttpError(), "HTTP 500"),
        (error.URLError("down"), "Could not reach Ollama"),
        (TimeoutError(), "timed out"),
    ],
)
def test_ollama_client_maps_transport_errors(monkeypatch, side_effect, message):
    monkeypatch.setattr(
        "budget_tracker_api.services.ollama_client.request.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(side_effect),
    )
    client = OllamaClient("http://localhost:11434", "qwen2.5:7b", 45)

    with pytest.raises(ServiceUnavailableError, match=message):
        client.chat([{"role": "user", "content": "hello"}])


def test_ollama_client_rejects_invalid_json(monkeypatch):
    monkeypatch.setattr(
        "budget_tracker_api.services.ollama_client.request.urlopen",
        lambda *args, **kwargs: FakeResponse("not-json"),
    )
    client = OllamaClient("http://localhost:11434", "qwen2.5:7b", 45)

    with pytest.raises(ServiceUnavailableError, match="invalid response"):
        client.chat([{"role": "user", "content": "hello"}])


def test_ollama_client_classifies_finance_intent(monkeypatch):
    captured = {}

    def fake_urlopen(http_request, timeout):
        captured["body"] = http_request.data.decode("utf-8")
        return FakeResponse('{"message": {"content": "METRIC_AVERAGE_DAILY_BURN\\n"}}')

    monkeypatch.setattr("budget_tracker_api.services.ollama_client.request.urlopen", fake_urlopen)
    client = OllamaClient("http://localhost:11434", "qwen2.5:7b", 45)

    intent = client.classify_finance_intent("How fast am I spending each day?")

    assert intent == "METRIC_AVERAGE_DAILY_BURN"
    assert "Allowed tokens" in captured["body"]
    assert "How fast am I spending each day?" in captured["body"]
