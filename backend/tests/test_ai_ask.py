import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pytest
from fastapi.testclient import TestClient

import backend.ai_client as ai_client
import backend.main as main_module
from backend.schemas import AIResponse, BoardUpdate, UpdatePayload
from backend.services import ai_service

SAMPLE_BOARD = {
    "id": "board-1",
    "title": "Kanban Studio",
    "columns": [
        {"id": "col-1", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
        {"id": "col-2", "title": "Done", "cardIds": []},
    ],
    "cards": {
        "card-1": {"id": "card-1", "title": "First", "details": "A task"},
        "card-2": {"id": "card-2", "title": "Second", "details": ""},
    },
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "DB_PATH", tmp_path / "test.db")
    main_module.init_db()
    with TestClient(main_module.app) as test_client:
        yield test_client


@pytest.fixture
def board(client):
    resp = client.post("/boards/user", json=SAMPLE_BOARD)
    assert resp.status_code == 201


def _fake_response(content: str):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": content}}]}

    return FakeResponse()


# ---------------------------------------------------------------------------
# ai_client.ask_structured: request shape and JSON parsing
# ---------------------------------------------------------------------------
def test_ask_structured_sends_board_question_and_history(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["json"] = kwargs["json"]
        return _fake_response(json.dumps({"message": "ok", "boardUpdates": []}))

    monkeypatch.setattr(ai_client.httpx, "post", fake_post)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    board = {"id": "b1", "columns": [], "cards": {}}
    ai_client.ask_structured(
        board, "Add a card", [{"role": "user", "content": "hello"}]
    )

    messages = captured["json"]["messages"]
    assert messages[0]["role"] == "system"
    assert "boardUpdates" in messages[0]["content"]
    user_msg = json.loads(messages[-1]["content"])
    assert user_msg["board"] == board
    assert user_msg["question"] == "Add a card"
    assert messages[-2] == {"role": "user", "content": "hello"}


def test_parse_json_content_handles_code_fences():
    content = '```json\n{"message": "ok", "boardUpdates": []}\n```'
    assert ai_client._parse_json_content(content) == {"message": "ok", "boardUpdates": []}


def test_parse_json_content_plain_json():
    assert ai_client._parse_json_content('{"message": "ok"}') == {"message": "ok"}


# ---------------------------------------------------------------------------
# ai_service: schema validation
# ---------------------------------------------------------------------------
def test_service_validates_valid_response(monkeypatch):
    monkeypatch.setattr(
        ai_client,
        "ask_structured",
        lambda *a, **k: {"message": "ok", "boardUpdates": [], "conversationHistory": []},
    )
    result = ai_service.ask({}, "q", [])
    assert result.message == "ok"
    assert result.boardUpdates == []


def test_service_rejects_missing_message(monkeypatch):
    monkeypatch.setattr(
        ai_client, "ask_structured", lambda *a, **k: {"boardUpdates": []}
    )
    with pytest.raises(ai_service.InvalidAIResponseError):
        ai_service.ask({}, "q", [])


def test_service_rejects_invalid_update_type(monkeypatch):
    monkeypatch.setattr(
        ai_client,
        "ask_structured",
        lambda *a, **k: {"message": "ok", "boardUpdates": [{"type": "nuke"}]},
    )
    with pytest.raises(ai_service.InvalidAIResponseError):
        ai_service.ask({}, "q", [])


def test_service_rejects_unparseable_content(monkeypatch):
    monkeypatch.setattr(
        ai_client, "ask_structured", lambda *a, **k: (_ for _ in ()).throw(ValueError("bad json"))
    )
    with pytest.raises(ai_service.InvalidAIResponseError):
        ai_service.ask({}, "q", [])


# ---------------------------------------------------------------------------
# POST /ai/ask: endpoint behaviour
# ---------------------------------------------------------------------------
def test_ask_returns_message_and_applied_add(client, board, monkeypatch):
    response = AIResponse(
        message="Added the card.",
        boardUpdates=[
            BoardUpdate(
                type="add",
                cardId="card-9",
                columnId="col-1",
                payload=UpdatePayload(title="New task", description="Desc", order=0),
            )
        ],
    )
    monkeypatch.setattr(ai_service, "ask", lambda *a, **k: response)

    resp = client.post("/ai/ask", json={"question": "Add a card"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "Added the card."
    assert body["boardUpdates"][0]["cardId"] == "card-9"

    board_json = client.get("/boards/user").json()
    assert board_json["cards"]["card-9"] == {
        "id": "card-9",
        "title": "New task",
        "details": "Desc",
    }
    assert board_json["columns"][0]["cardIds"][0] == "card-9"


def test_ask_applies_edit_update(client, board, monkeypatch):
    response = AIResponse(
        message="Renamed the card.",
        boardUpdates=[
            BoardUpdate(
                type="edit",
                cardId="card-1",
                payload=UpdatePayload(title="Renamed", description="New details"),
            )
        ],
    )
    monkeypatch.setattr(ai_service, "ask", lambda *a, **k: response)

    resp = client.post("/ai/ask", json={"question": "Rename card 1"})
    assert resp.status_code == 200
    card = client.get("/boards/user").json()["cards"]["card-1"]
    assert card["title"] == "Renamed"
    assert card["details"] == "New details"


def test_ask_applies_move_update(client, board, monkeypatch):
    response = AIResponse(
        message="Moved it.",
        boardUpdates=[
            BoardUpdate(type="move", cardId="card-1", columnId="col-2")
        ],
    )
    monkeypatch.setattr(ai_service, "ask", lambda *a, **k: response)

    resp = client.post("/ai/ask", json={"question": "Move card 1 to Done"})
    assert resp.status_code == 200
    done = client.get("/boards/user").json()["columns"][1]
    assert done["cardIds"] == ["card-1"]


def test_ask_applies_delete_update(client, board, monkeypatch):
    response = AIResponse(
        message="Deleted it.",
        boardUpdates=[BoardUpdate(type="delete", cardId="card-1")],
    )
    monkeypatch.setattr(ai_service, "ask", lambda *a, **k: response)

    resp = client.post("/ai/ask", json={"question": "Delete card 1"})
    assert resp.status_code == 200
    board_json = client.get("/boards/user").json()
    assert "card-1" not in board_json["cards"]
    assert board_json["columns"][0]["cardIds"] == ["card-2"]


def test_ask_without_updates_returns_message_only(client, board, monkeypatch):
    response = AIResponse(message="Nothing changed.")
    monkeypatch.setattr(ai_service, "ask", lambda *a, **k: response)

    resp = client.post("/ai/ask", json={"question": "Hi"})
    assert resp.status_code == 200
    assert resp.json() == {"message": "Nothing changed.", "boardUpdates": []}
    assert client.get("/boards/user").json() == SAMPLE_BOARD


def test_ask_passes_history_and_question(client, board, monkeypatch):
    captured = {}

    def fake_ask(board_json, question, history):
        captured["question"] = question
        captured["history"] = history
        return AIResponse(message="ok")

    monkeypatch.setattr(ai_service, "ask", fake_ask)

    resp = client.post(
        "/ai/ask",
        json={
            "question": "What is in progress?",
            "history": [{"role": "user", "content": "hello"}],
        },
    )
    assert resp.status_code == 200
    assert captured["question"] == "What is in progress?"
    assert captured["history"] == [{"role": "user", "content": "hello"}]
    assert captured["history"] is not None


def test_ask_invalid_schema_returns_502(client, board, monkeypatch):
    monkeypatch.setattr(
        ai_service,
        "ask",
        lambda *a, **k: (_ for _ in ()).throw(
            ai_service.InvalidAIResponseError("AI response does not match schema")
        ),
    )
    resp = client.post("/ai/ask", json={"question": "Hi"})
    assert resp.status_code == 502
    assert "schema" in resp.json()["detail"]


def test_ask_missing_api_key_returns_500(client, board, monkeypatch):
    monkeypatch.setattr(
        ai_service,
        "ask",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("OPENROUTER_API_KEY is not set")),
    )
    resp = client.post("/ai/ask", json={"question": "Hi"})
    assert resp.status_code == 500
    assert resp.json() == {"detail": "OPENROUTER_API_KEY is not set"}


def test_ask_no_board_returns_404(client):
    resp = client.post("/ai/ask", json={"question": "Hi"})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Board not found"}


def test_ask_bad_type_in_update_rolls_back(client, board, monkeypatch):
    response = AIResponse(
        message="Moved and edited.",
        boardUpdates=[
            BoardUpdate(type="edit", cardId="card-1", payload=UpdatePayload(title="X")),
            BoardUpdate(type="move", cardId="card-1", columnId="col-missing"),
        ],
    )
    monkeypatch.setattr(ai_service, "ask", lambda *a, **k: response)

    resp = client.post("/ai/ask", json={"question": "Move card 1 somewhere"})
    assert resp.status_code == 400
    assert client.get("/boards/user").json() == SAMPLE_BOARD
