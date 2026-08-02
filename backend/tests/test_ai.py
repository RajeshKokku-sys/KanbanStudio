import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pytest
from fastapi.testclient import TestClient

import backend.ai_client as ai_client
import backend.main as main_module


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")


def _fake_response(content: str):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": content}}]}

    return FakeResponse()


def test_ask_returns_model_answer(monkeypatch):
    monkeypatch.setattr(ai_client.httpx, "post", lambda *a, **k: _fake_response("4"))
    assert ai_client.ask("2+2") == "4"


def test_ask_sends_expected_request(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return _fake_response("4")

    monkeypatch.setattr(ai_client.httpx, "post", fake_post)
    ai_client.ask("2+2")

    assert captured["url"] == ai_client.OPENROUTER_URL
    assert (
        captured["kwargs"]["headers"]["Authorization"]
        == f"Bearer {ai_client.get_api_key()}"
    )
    assert captured["kwargs"]["json"]["model"] == ai_client.MODEL
    assert captured["kwargs"]["json"]["max_tokens"] == ai_client.MAX_TOKENS
    assert captured["kwargs"]["json"]["messages"] == [
        {"role": "user", "content": "2+2"}
    ]


def test_ask_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(ai_client, "_load_env_file", lambda: None)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY is not set"):
        ai_client.ask("2+2")


def test_ai_ping_endpoint_returns_answer(monkeypatch):
    monkeypatch.setattr(ai_client, "ask", lambda prompt: "4")
    client = TestClient(main_module.app)
    try:
        resp = client.get("/ai/ping")
    finally:
        client.close()
    assert resp.status_code == 200
    assert resp.json() == {"answer": "4"}


def test_ai_ping_missing_key_returns_500(monkeypatch):
    monkeypatch.setattr(
        ai_client,
        "ask",
        lambda prompt: (_ for _ in ()).throw(RuntimeError("OPENROUTER_API_KEY is not set")),
    )
    client = TestClient(main_module.app)
    try:
        resp = client.get("/ai/ping")
    finally:
        client.close()
    assert resp.status_code == 500
    assert resp.json() == {"detail": "OPENROUTER_API_KEY is not set"}
