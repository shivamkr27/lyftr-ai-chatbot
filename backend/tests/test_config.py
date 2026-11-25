from app.config import get_settings


def test_default_model_matches_selected_groq_model(monkeypatch):
    monkeypatch.setenv("LLM_API_KEYS", "test-key-1,test-key-2")
    monkeypatch.delenv("LLM_MODEL", raising=False)

    assert get_settings().llm_model == "groq/openai/gpt-oss-120b"
