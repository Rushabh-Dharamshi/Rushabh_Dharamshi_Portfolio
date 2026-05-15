import json
from urllib import error

import pytest

from budget_tracker_api.errors import ServiceUnavailableError
from budget_tracker_api.services.ollama_embedding_client import OllamaEmbeddingClient


class StubResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_embedding_client_returns_empty_for_empty_input():
    client = OllamaEmbeddingClient("http://ollama", "nomic-embed-text", 30)
    assert client.embed_texts([]) == []


def test_embedding_client_uses_embed_endpoint(monkeypatch):
    client = OllamaEmbeddingClient("http://ollama", "nomic-embed-text", 30)

    monkeypatch.setattr(
        "budget_tracker_api.services.ollama_embedding_client.request.urlopen",
        lambda request_obj, timeout=None: StubResponse({"embeddings": [[0.1, 0.2], [0.3, 0.4]]}),
    )

    assert client.embed_texts(["rent", "coffee"]) == [[0.1, 0.2], [0.3, 0.4]]


def test_embedding_client_falls_back_to_legacy_endpoint(monkeypatch):
    client = OllamaEmbeddingClient("http://ollama", "nomic-embed-text", 30)
    calls = []

    def fake_urlopen(request_obj, timeout=None):
        calls.append(request_obj.full_url)
        if request_obj.full_url.endswith("/api/embed"):
            raise error.URLError("down")
        body = json.loads(request_obj.data.decode("utf-8"))
        return StubResponse({"embedding": [float(len(body["prompt"])), 1.0]})

    monkeypatch.setattr(
        "budget_tracker_api.services.ollama_embedding_client.request.urlopen",
        fake_urlopen,
    )

    embeddings = client.embed_texts(["rent", "travel"])

    assert embeddings == [[4.0, 1.0], [6.0, 1.0]]
    assert calls[0].endswith("/api/embed")
    assert calls[1].endswith("/api/embeddings")


def test_call_embed_endpoint_raises_for_invalid_json(monkeypatch):
    client = OllamaEmbeddingClient("http://ollama", "nomic-embed-text", 30)

    class BadResponse:
        def read(self):
            return b"not-json"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "budget_tracker_api.services.ollama_embedding_client.request.urlopen",
        lambda request_obj, timeout=None: BadResponse(),
    )

    with pytest.raises(ServiceUnavailableError, match="invalid response"):
        client._call_embed_endpoint("/api/embed", ["rent"])


def test_embedding_client_legacy_path_raises_when_embedding_missing(monkeypatch):
    client = OllamaEmbeddingClient("http://ollama", "nomic-embed-text", 30)
    monkeypatch.setattr(client, "_call_embed_endpoint", lambda path, texts: (_ for _ in ()).throw(ServiceUnavailableError("down")))
    monkeypatch.setattr(
        "budget_tracker_api.services.ollama_embedding_client.request.urlopen",
        lambda request_obj, timeout=None: StubResponse({"unexpected": []}),
    )

    with pytest.raises(ServiceUnavailableError, match="did not include an embedding"):
        client.embed_texts(["rent"])

def test_embedding_client_exposes_model_property():
    client = OllamaEmbeddingClient("http://ollama", "nomic-embed-text", 30)
    assert client.model == "nomic-embed-text"


def test_call_embed_endpoint_raises_for_http_error(monkeypatch):
    client = OllamaEmbeddingClient("http://ollama", "nomic-embed-text", 30)

    class HttpFailure(error.HTTPError):
        def __init__(self):
            super().__init__("http://ollama/api/embed", 503, "unavailable", hdrs=None, fp=None)

        def read(self):
            return b"service down"

    monkeypatch.setattr(
        "budget_tracker_api.services.ollama_embedding_client.request.urlopen",
        lambda request_obj, timeout=None: (_ for _ in ()).throw(HttpFailure()),
    )

    with pytest.raises(ServiceUnavailableError, match="HTTP 503"):
        client._call_embed_endpoint("/api/embed", ["rent"])


def test_call_embed_endpoint_raises_for_timeout(monkeypatch):
    client = OllamaEmbeddingClient("http://ollama", "nomic-embed-text", 30)

    monkeypatch.setattr(
        "budget_tracker_api.services.ollama_embedding_client.request.urlopen",
        lambda request_obj, timeout=None: (_ for _ in ()).throw(TimeoutError("slow")),
    )

    with pytest.raises(ServiceUnavailableError, match="timed out"):
        client._call_embed_endpoint("/api/embed", ["rent"])


def test_call_embed_endpoint_raises_when_embeddings_are_missing(monkeypatch):
    client = OllamaEmbeddingClient("http://ollama", "nomic-embed-text", 30)

    monkeypatch.setattr(
        "budget_tracker_api.services.ollama_embedding_client.request.urlopen",
        lambda request_obj, timeout=None: StubResponse({"embedding": [0.1, 0.2]}),
    )

    with pytest.raises(ServiceUnavailableError, match="did not include embeddings"):
        client._call_embed_endpoint("/api/embed", ["rent"])


def test_embedding_client_legacy_path_wraps_generic_failure(monkeypatch):
    client = OllamaEmbeddingClient("http://ollama", "nomic-embed-text", 30)
    monkeypatch.setattr(client, "_call_embed_endpoint", lambda path, texts: (_ for _ in ()).throw(ServiceUnavailableError("down")))
    monkeypatch.setattr(
        "budget_tracker_api.services.ollama_embedding_client.request.urlopen",
        lambda request_obj, timeout=None: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(ServiceUnavailableError, match="embeddings are unavailable"):
        client.embed_texts(["rent"])
