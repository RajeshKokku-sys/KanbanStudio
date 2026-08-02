"""FastAPI application for the Project Management MVP.

Initialises the SQLite database on startup and exposes CRUD endpoints for the
Kanban board:

- ``GET /boards/{user_id}``        – fetch the user's board JSON.
- ``POST /boards/{user_id}``       – create or replace the user's board.
- ``PATCH /boards/{user_id}/cards/{card_id}`` – update a card.
- ``DELETE /boards/{user_id}/cards/{card_id}`` – delete a card.

The board JSON shape mirrors the frontend ``BoardData`` type so the UI can map
onto the API without transformation. Column and card ordering is derived from
the order of ``cardIds`` arrays; the integer ``position`` columns are
maintained implicitly by the endpoints.
"""

from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3
import uuid

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Dual-mode import: works when running ``uvicorn main:app`` from backend/ and
# when importing ``backend.main`` as a package (tests).
if __package__:
    from . import ai_client
    from .schemas import AiAsk, Board, BoardUpdate, Card, CardUpdate
    from .services import ai_service
else:
    import ai_client
    from schemas import AiAsk, Board, BoardUpdate, Card, CardUpdate
    from services import ai_service

# MVP: a single hard-coded user, matching the frontend (``user`` / ``password``).
USER_ID = "user"

# ---------------------------------------------------------------------------
# Database initialisation
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).parent / "app.db"
MIGRATION_PATH = Path(__file__).parent / "migrations" / "001_init.sql"


def init_db() -> None:
    """Create the SQLite database and apply the migration if it does not exist.

    The migration uses ``CREATE TABLE IF NOT EXISTS``, so it is safe to run
    repeatedly on an existing database file.
    """
    if not MIGRATION_PATH.is_file():
        raise FileNotFoundError(f"Migration script not found: {MIGRATION_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        with open(MIGRATION_PATH, "r", encoding="utf-8") as f:
            sql_script = f.read()
        conn.executescript(sql_script)
        conn.commit()
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

# Allow the statically-served frontend (localhost:3000) to call the API during
# local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _board_row(conn: sqlite3.Connection, user_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM boards WHERE user_id = ?", (user_id,)
    ).fetchone()


def _board_json(conn: sqlite3.Connection, board: sqlite3.Row) -> dict:
    columns = conn.execute(
        "SELECT * FROM columns WHERE board_id = ? ORDER BY position",
        (board["id"],),
    ).fetchall()
    column_list = []
    cards = {}
    for column in columns:
        column_cards = conn.execute(
            "SELECT * FROM cards WHERE column_id = ? ORDER BY position",
            (column["id"],),
        ).fetchall()
        column_list.append(
            {
                "id": column["id"],
                "title": column["title"],
                "cardIds": [c["id"] for c in column_cards],
            }
        )
        cards.update(
            {
                c["id"]: {
                    "id": c["id"],
                    "title": c["title"],
                    "details": c["details"] or "",
                }
                for c in column_cards
            }
        )
    return {
        "id": board["id"],
        "title": board["title"],
        "columns": column_list,
        "cards": cards,
    }


def _replace_board(conn: sqlite3.Connection, user_id: str, board: Board) -> None:
    # Ensure the referenced user exists (boards.user_id has a FK to users.id).
    conn.execute(
        "INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (?, ?, ?)",
        (user_id, user_id, ""),
    )
    conn.execute("DELETE FROM boards WHERE user_id = ?", (user_id,))
    conn.execute(
        "INSERT INTO boards (id, user_id, title) VALUES (?, ?, ?)",
        (board.id, user_id, board.title),
    )
    for position, column in enumerate(board.columns):
        conn.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            (column.id, board.id, column.title, position),
        )
        for card_position, card_id in enumerate(column.cardIds):
            card = board.cards.get(card_id)
            if card is None:
                continue
            conn.execute(
                "INSERT INTO cards (id, column_id, title, details, position) "
                "VALUES (?, ?, ?, ?, ?)",
                (card.id, column.id, card.title, card.details, card_position),
            )
    conn.commit()


def _rewrite_positions(
    conn: sqlite3.Connection, column_id: str, card_ids: list[str]
) -> None:
    for position, card_id in enumerate(card_ids):
        conn.execute(
            "UPDATE cards SET position = ? WHERE id = ?", (position, card_id)
        )


def _apply_card_move(
    conn: sqlite3.Connection,
    card_id: str,
    old_column_id: str,
    new_column_id: str,
    new_position: int | None,
) -> None:
    def ids_in(column_id: str) -> list[str]:
        rows = conn.execute(
            "SELECT id FROM cards WHERE column_id = ? ORDER BY position",
            (column_id,),
        ).fetchall()
        return [row["id"] for row in rows]

    old_ids = ids_in(old_column_id)
    if card_id in old_ids:
        old_ids.remove(card_id)

    if old_column_id == new_column_id:
        target = old_ids
    else:
        target = ids_in(new_column_id)
    if new_position is None:
        target.append(card_id)
    else:
        target.insert(min(new_position, len(target)), card_id)

    _rewrite_positions(conn, new_column_id, target)
    if old_column_id != new_column_id:
        _rewrite_positions(conn, old_column_id, old_ids)
        conn.execute(
            "UPDATE cards SET column_id = ? WHERE id = ?",
            (new_column_id, card_id),
        )


def _card_in_board(
    conn: sqlite3.Connection, board_id: str, card_id: str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT c.* FROM cards c JOIN columns col ON c.column_id = col.id "
        "WHERE c.id = ? AND col.board_id = ?",
        (card_id, board_id),
    ).fetchone()


def _unique_card_id(conn: sqlite3.Connection, preferred: str | None) -> str:
    """Return ``preferred`` if free, otherwise allocate a fresh unique card id."""
    candidate = preferred or f"card-{uuid.uuid4().hex[:12]}"
    for _ in range(50):
        if conn.execute("SELECT 1 FROM cards WHERE id = ?", (candidate,)).fetchone() is None:
            return candidate
        candidate = f"card-{uuid.uuid4().hex[:12]}"
    raise RuntimeError("Could not allocate a unique card id")


def _apply_board_updates(
    conn: sqlite3.Connection, board_id: str, updates: list[BoardUpdate]
) -> None:
    """Apply AI-generated board updates to the database atomically."""
    for update in updates:
        if update.type == "add":
            column_id = update.columnId
            if column_id is None:
                raise HTTPException(status_code=400, detail="columnId required for add")
            column = conn.execute(
                "SELECT * FROM columns WHERE id = ? AND board_id = ?",
                (column_id, board_id),
            ).fetchone()
            if column is None:
                raise HTTPException(status_code=400, detail="Column not found")
            card_id = _unique_card_id(conn, update.cardId)
            payload = update.payload
            title = (payload.title if payload else None) or "New card"
            details = (payload.description if payload else None) or ""
            column_cards = [
                row["id"]
                for row in conn.execute(
                    "SELECT id FROM cards WHERE column_id = ? ORDER BY position",
                    (column_id,),
                )
            ]
            order = (
                payload.order
                if payload and payload.order is not None
                else len(column_cards)
            )
            column_cards.insert(min(order, len(column_cards)), card_id)
            conn.execute(
                "INSERT INTO cards (id, column_id, title, details, position) "
                "VALUES (?, ?, ?, ?, ?)",
                (card_id, column_id, title, details, 0),
            )
            _rewrite_positions(conn, column_id, column_cards)
        elif update.type == "edit":
            card_id = update.cardId
            if card_id is None:
                raise HTTPException(status_code=400, detail="cardId required for edit")
            card = _card_in_board(conn, board_id, card_id)
            if card is None:
                raise HTTPException(status_code=404, detail="Card not found")
            payload = update.payload
            new_title = card["title"]
            new_details = card["details"] or ""
            if payload and payload.title is not None:
                new_title = payload.title
            if payload and payload.description is not None:
                new_details = payload.description
            conn.execute(
                "UPDATE cards SET title = ?, details = ? WHERE id = ?",
                (new_title, new_details, card_id),
            )
        elif update.type == "move":
            card_id = update.cardId
            if card_id is None:
                raise HTTPException(status_code=400, detail="cardId required for move")
            card = _card_in_board(conn, board_id, card_id)
            if card is None:
                raise HTTPException(status_code=404, detail="Card not found")
            column_id = update.columnId
            if column_id is None:
                raise HTTPException(status_code=400, detail="columnId required for move")
            column = conn.execute(
                "SELECT * FROM columns WHERE id = ? AND board_id = ?",
                (column_id, board_id),
            ).fetchone()
            if column is None:
                raise HTTPException(status_code=400, detail="Column not found")
            order = update.payload.order if update.payload else None
            _apply_card_move(conn, card_id, card["column_id"], column_id, order)
        elif update.type == "delete":
            card_id = update.cardId
            if card_id is None:
                raise HTTPException(status_code=400, detail="cardId required for delete")
            card = _card_in_board(conn, board_id, card_id)
            if card is None:
                raise HTTPException(status_code=404, detail="Card not found")
            conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/hello")
def hello() -> dict:
    return {"message": "hello world"}


@app.get("/")
def root() -> dict:
    return {"message": "Project Management MVP backend is running"}


@app.get("/ai/ping")
def ai_ping() -> dict:
    try:
        answer = ai_client.ask("2+2")
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"answer": answer}


@app.post("/ai/ask")
def ai_ask(payload: AiAsk) -> dict:
    conn = _connect()
    try:
        board_row = _board_row(conn, USER_ID)
        if board_row is None:
            raise HTTPException(status_code=404, detail="Board not found")
        board = _board_json(conn, board_row)
        try:
            response = ai_service.ask(
                board,
                payload.question,
                [item.model_dump() for item in payload.history],
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except ai_service.InvalidAIResponseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if response.boardUpdates:
            _apply_board_updates(conn, board_row["id"], response.boardUpdates)
        return {
            "message": response.message,
            "boardUpdates": [
                update.model_dump(exclude_none=True) for update in response.boardUpdates
            ],
        }
    finally:
        conn.close()


@app.get("/boards/{user_id}", response_model=Board)
def get_board(user_id: str) -> dict:
    conn = _connect()
    try:
        board = _board_row(conn, user_id)
        if board is None:
            raise HTTPException(status_code=404, detail="Board not found")
        return _board_json(conn, board)
    finally:
        conn.close()


@app.post("/boards/{user_id}", response_model=Board)
def save_board(user_id: str, board: Board) -> JSONResponse:
    conn = _connect()
    try:
        existed = _board_row(conn, user_id) is not None
        _replace_board(conn, user_id, board)
        saved = _board_json(conn, _board_row(conn, user_id))
        return JSONResponse(content=saved, status_code=200 if existed else 201)
    finally:
        conn.close()


@app.patch("/boards/{user_id}/cards/{card_id}", response_model=Card)
def update_card(user_id: str, card_id: str, update: CardUpdate) -> dict:
    conn = _connect()
    try:
        board = _board_row(conn, user_id)
        if board is None:
            raise HTTPException(status_code=404, detail="Board not found")
        card = _card_in_board(conn, board["id"], card_id)
        if card is None:
            raise HTTPException(status_code=404, detail="Card not found")

        new_column_id = (
            update.column_id if update.column_id is not None else card["column_id"]
        )
        if update.column_id is not None:
            target_column = conn.execute(
                "SELECT * FROM columns WHERE id = ? AND board_id = ?",
                (update.column_id, board["id"]),
            ).fetchone()
            if target_column is None:
                raise HTTPException(status_code=400, detail="Column not found")

        if update.column_id is not None or update.position is not None:
            _apply_card_move(
                conn,
                card_id,
                card["column_id"],
                new_column_id,
                update.position,
            )

        new_title = update.title if update.title is not None else card["title"]
        new_details = (
            update.details if update.details is not None else (card["details"] or "")
        )
        conn.execute(
            "UPDATE cards SET title = ?, details = ? WHERE id = ?",
            (new_title, new_details, card_id),
        )
        conn.commit()
        return {"id": card_id, "title": new_title, "details": new_details}
    finally:
        conn.close()


@app.delete("/boards/{user_id}/cards/{card_id}")
def delete_card(user_id: str, card_id: str) -> Response:
    conn = _connect()
    try:
        board = _board_row(conn, user_id)
        if board is None:
            raise HTTPException(status_code=404, detail="Board not found")
        card = _card_in_board(conn, board["id"], card_id)
        if card is None:
            raise HTTPException(status_code=404, detail="Card not found")
        conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        conn.commit()
        return Response(status_code=204)
    finally:
        conn.close()
