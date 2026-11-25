import pytest

from app.services.fallback_service import parse_failure_header
from app.services.llm_service import ProviderUnavailable, completion
import app.services.llm_service as llm_module


class Usage:
    prompt_tokens = 25
    completion_tokens = 7


class Message:
    content = "real answer"


class Choice:
    message = Message()


class Response:
    choices = [Choice()]
    usage = Usage()
    _hidden_params = {}


class StatusError(Exception):
    status_code = 429


def test_parse_failure_header():
    failures = parse_failure_header("key_1=429,key_2=500", ["key_1", "key_2"])
    assert failures == {"key_1": 429, "key_2": 500}
    assert parse_failure_header("*=503", ["key_1", "key_2"]) == {
        "key_1": 503,
        "key_2": 503,
    }


def test_failover(monkeypatch):
    calls = {"count": 0}

    def fake_completion(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise StatusError()
        return Response()

    monkeypatch.setattr(llm_module.litellm, "completion", fake_completion)
    result = completion(
        "gemini/gemini-2.0-flash",
        [{"role": "user", "content": "hello"}],
        ["test-key-1", "test-key-2"],
        ["key_1", "key_2"],
        {},
        True,
    )
    assert result["key_id"] == "key_2"
    assert result["fallback_attempts"] == 1
    assert result["resolution_source"] == "LIVE_INFERENCE"


@pytest.mark.parametrize("failure_status", [429, 500])
def test_simulated_key_one_failure_uses_key_two(monkeypatch, failure_status):
    seen = []

    def fake_completion(**kwargs):
        seen.append(kwargs["api_key"])
        return Response()

    monkeypatch.setattr(llm_module.litellm, "completion", fake_completion)
    result = completion(
        "groq/llama-3.3-70b-versatile",
        [{"role": "user", "content": "hello"}],
        ["secret-one", "secret-two"],
        ["key_1", "key_2"],
        {"key_1": failure_status},
        True,
    )
    assert seen == ["secret-two"]
    assert result["key_id"] == "key_2"
    assert result["fallback_attempts"] == 1
    assert result["resolution_source"] == "LIVE_INFERENCE"


def test_simulated_all_fail():
    with pytest.raises(ProviderUnavailable):
        result = completion(
            "gemini/gemini-2.0-flash",
            [{"role": "user", "content": "hello"}],
            ["test-key-1", "test-key-2"],
            ["key_1", "key_2"],
            {"key_1": 429, "key_2": 503},
            True,
        )
