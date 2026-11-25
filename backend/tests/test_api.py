import os
import tempfile
from pathlib import Path

os.environ["LLM_API_KEYS"] = "test-key-1,test-key-2"
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000"
os.environ["ENABLE_FAILURE_SIMULATION"] = "true"
os.environ["LLM_MODEL"] = "groq/llama-3.3-70b-versatile"
os.environ["CACHE_ENABLED"] = "true"

import litellm
import pytest
from fastapi.testclient import TestClient

from app.main import app


class MockUsage:
    prompt_tokens = 42
    completion_tokens = 9


class MockMessage:
    content = ""


class MockChoice:
    def __init__(self, content):
        self.message = MockMessage()
        self.message.content = content


class MockResponse:
    def __init__(self, content, cache_hit=False):
        self.choices = [MockChoice(content)]
        self.usage = MockUsage()
        self._hidden_params = {"cache_hit": cache_hit}


@pytest.fixture
def client(monkeypatch):
    calls = {"count": 0}

    def fake_completion(**kwargs):
        calls["count"] += 1
        messages = kwargs["messages"]
        last = messages[-1]["content"]
        if calls["count"] == 1:
            return MockResponse(f"answer:{last}")
        return MockResponse(f"answer:{last}", cache_hit=True)

    monkeypatch.setattr(litellm, "completion", fake_completion)
    monkeypatch.setattr(litellm, "token_counter", lambda **kwargs: 42)
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["keys_configured"] == 2
    assert response.json()["cache_enabled"] is True


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"session_id": "", "message": "hello"},
        {"session_id": "s1", "message": ""},
        {"session_id": "s1", "message": "x" * 4001},
    ],
)
def test_validation(client, payload):
    response = client.post("/chat", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_malformed_json(client):
    response = client.post(
        "/chat",
        content="{",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_chat_and_history(client):
    first = client.post("/chat", json={"session_id": "session-1", "message": "hello"})
    assert first.status_code == 200
    body = first.json()
    assert body["session_id"] == "session-1"
    assert body["reply"]
    assert set(body["metadata"]) >= {
        "resolution_source", "model", "latency_ms", "input_tokens",
        "output_tokens", "key_id", "fallback_attempts"
    }

    history = client.get("/sessions/session-1/messages")
    assert history.status_code == 200
    messages = history.json()["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "hello"
    assert "metadata" not in messages[0]


def test_unknown_session(client):
    response = client.get("/sessions/does-not-exist/messages")
    assert response.status_code == 404
    assert response.json() == {"detail": "session not found"}
