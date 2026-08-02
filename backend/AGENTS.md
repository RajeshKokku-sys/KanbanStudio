# Backend (FastAPI Kanban API)

This directory contains the FastAPI backend for the Project Management MVP.

## Overview

- `main.py` – FastAPI app. On startup it creates the SQLite database if missing
  (`init_db`, applying `migrations/001_init.sql`). Exposes the board CRUD API for a
  single Kanban board per user:
  - `GET /boards/{user_id}` – fetch the user's board JSON (404 if none).
  - `POST /boards/{user_id}` – create (201) or replace (200) the board.
  - `PATCH /boards/{user_id}/cards/{card_id}` – update a card
    (`{title?, details?, column_id?, position?}`).
  - `DELETE /boards/{user_id}/cards/{card_id}` – delete a card (204).
  - `GET /ai/ping` – sends the prompt `2+2` to OpenRouter and returns `{"answer": "..."}`.
  - `POST /ai/ask` – accepts `{question, history?}`, calls the AI with the board JSON
    for the hard-coded `user`, applies any returned `boardUpdates` to the DB, and returns
    `{message, boardUpdates}` (404 no board, 500 missing key, 502 invalid AI response).
  - `GET /hello` – health/hello check.
- `ai_client.py` – thin httpx wrapper around the OpenRouter chat completions API
  (`openai/gpt-oss-120b`, `max_tokens=1024`, `reasoning: {"effort": "low"}`); reads
  `OPENROUTER_API_KEY` from env or the repo-root `.env`. `ask` is the plain text call
  (used by `/ai/ping`); `ask_structured(board, question, history)` embeds the schema
  in the system prompt and parses the fenced-JSON reply.
- `ai_schema.json` – the JSON schema the AI must respond with
  (`message`, optional `boardUpdates` of type `add|edit|move|delete`, optional
  `conversationHistory`).
- `services/ai_service.py` – service layer: calls `ai_client.ask_structured`, validates
  the reply against the Pydantic `AIResponse` model, and raises `InvalidAIResponseError`
  on unparseable/out-of-schema output.
- `schemas.py` – Pydantic v2 models (`Board`, `Column`, `Card`, `CardUpdate`) matching
  the frontend `BoardData` shape, plus the AI models (`AIResponse`, `BoardUpdate`,
  `UpdatePayload`, `HistoryItem`, `AiAsk`).
- `migrations/001_init.sql` – schema for `users`, `boards`, `columns`, `cards`
  (UUID TEXT PKs, FK cascade, integer `position` for ordering).
- `tests/test_api.py` – pytest suite covering every endpoint and its error cases,
  using a temp DB (`monkeypatch` of `DB_PATH`).
- `tests/test_ai.py` / `tests/test_ai_ask.py` – mocked-httpx tests for the AI client
  and comprehensive `/ai/ask` tests (updates applied, message-only, invalid schema,
  404/500/502, atomic rollback).

## Conventions

- The app stores board/card ordering as `position` integers but derives the JSON
  ordering from the `cardIds` arrays / column order (maintained implicitly by endpoints).
- CORS is open (`allow_origins=["*"]`) for the locally-served frontend.
- The database file is `app.db` in this directory (`*.db` is gitignored).
- Run from repo root with `.\venv\Scripts\pytest.exe -q`, or with uvicorn from
  `backend/` (`..\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000`).
- Note: the Docker backend runs uvicorn without `--reload`, so restart the container
  after code changes (`docker compose restart backend`).
