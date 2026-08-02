import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pytest
from fastapi.testclient import TestClient

import backend.main as main_module

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


def column(client, board, column_id):
    columns = client.get(f"/boards/{board}").json()["columns"]
    return next(c for c in columns if c["id"] == column_id)


def test_hello(client):
    resp = client.get("/hello")
    assert resp.status_code == 200
    assert resp.json() == {"message": "hello world"}


def test_get_board_missing_returns_404(client):
    resp = client.get("/boards/user-1")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Board not found"}


def test_post_then_get_board_roundtrip(client):
    created = client.post("/boards/user-1", json=SAMPLE_BOARD)
    assert created.status_code == 201
    got = client.get("/boards/user-1")
    assert got.status_code == 200
    assert got.json() == SAMPLE_BOARD


def test_post_replaces_existing_board(client):
    client.post("/boards/user-1", json=SAMPLE_BOARD)
    renamed = {**SAMPLE_BOARD, "title": "Renamed Board"}
    resp = client.post("/boards/user-1", json=renamed)
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Renamed Board"
    assert len(body["columns"]) == 2
    assert set(body["cards"]) == {"card-1", "card-2"}


def test_boards_are_scoped_per_user(client):
    client.post("/boards/user-1", json=SAMPLE_BOARD)
    assert client.get("/boards/user-2").status_code == 404


def test_patch_card_title_and_details(client):
    client.post("/boards/user-1", json=SAMPLE_BOARD)
    resp = client.patch(
        "/boards/user-1/cards/card-1",
        json={"title": "Updated", "details": "New details"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"id": "card-1", "title": "Updated", "details": "New details"}


def test_patch_card_moves_to_another_column(client):
    client.post("/boards/user-1", json=SAMPLE_BOARD)
    resp = client.patch("/boards/user-1/cards/card-1", json={"column_id": "col-2"})
    assert resp.status_code == 200
    done = column(client, "user-1", "col-2")
    backlog = column(client, "user-1", "col-1")
    assert done["cardIds"] == ["card-1"]
    assert "card-1" not in backlog["cardIds"]


def test_patch_card_reorders_within_column(client):
    client.post("/boards/user-1", json=SAMPLE_BOARD)
    resp = client.patch("/boards/user-1/cards/card-2", json={"position": 0})
    assert resp.status_code == 200
    backlog = column(client, "user-1", "col-1")
    assert backlog["cardIds"] == ["card-2", "card-1"]


def test_patch_card_missing_board_returns_404(client):
    resp = client.patch("/boards/user-x/cards/card-1", json={"title": "x"})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Board not found"}


def test_patch_card_missing_card_returns_404(client):
    client.post("/boards/user-1", json=SAMPLE_BOARD)
    resp = client.patch("/boards/user-1/cards/card-999", json={"title": "x"})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Card not found"}


def test_patch_card_invalid_column_returns_400(client):
    client.post("/boards/user-1", json=SAMPLE_BOARD)
    resp = client.patch(
        "/boards/user-1/cards/card-1", json={"column_id": "col-other"}
    )
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Column not found"}


def test_delete_card(client):
    client.post("/boards/user-1", json=SAMPLE_BOARD)
    resp = client.delete("/boards/user-1/cards/card-1")
    assert resp.status_code == 204
    body = client.get("/boards/user-1").json()
    assert "card-1" not in body["cards"]
    assert "card-1" not in column(client, "user-1", "col-1")["cardIds"]


def test_delete_card_missing_returns_404(client):
    client.post("/boards/user-1", json=SAMPLE_BOARD)
    resp = client.delete("/boards/user-1/cards/card-999")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Card not found"}
