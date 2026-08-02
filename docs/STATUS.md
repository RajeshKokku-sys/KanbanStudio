# Project Status (compressed working summary)

Saved to preserve context. Everything below is DONE and verified as of Aug 2026.

## Stack / conventions
- Next.js frontend (React 19, TS, Tailwind v4, @dnd-kit, Vitest, Playwright) in `frontend/`
- FastAPI backend (Python 3.12, SQLite, Pydantic v2, uv) in `backend/`; Docker Compose; venv at repo root
- Auth: hard-coded `user` / `password`, flag `auth` in sessionStorage, `/` guarded -> redirect `/login`
- Board JSON contract (frontend `BoardData` == API response): `{ id, title, columns:[{id,title,cardIds}], cards:{id:{id,title,details}} }`
- Colors: accent `#ecad0a`, blue `#209dd7`, purple `#753991`, navy `#032147`, gray `#888888`
- Key files: `frontend/src/lib/kanban.ts` (types/seed/`moveCard`/`createId`), `frontend/src/lib/api.ts` (fetch client), `frontend/src/lib/BoardContext.tsx` (provider), `frontend/src/components/KanbanBoard.tsx` (consumes context), `backend/main.py`, `backend/schemas.py`, `backend/migrations/001_init.sql`

## Parts 1-5: COMPLETE
- PLAN.md + DB_SCHEMA.md approved; frontend/backend/scripts AGENTS.md exist
- Docker: backend Dockerfile (uv install), frontend Dockerfile (next export -> nginx), docker-compose, start/stop scripts in `scripts/`
- Fake login, Kanban demo, SQLite schema (users/boards/columns/cards, FK cascade, UUID TEXT PKs, position INT)

## Part 6: COMPLETE (verified)
Backend CRUD implemented in `backend/main.py` (lifespan startup, idempotent `init_db`):
- `GET /boards/{user_id}` -> 200 board JSON | 404 no board
- `POST /boards/{user_id}` -> 201 create | 200 replace (transaction; auto-creates user row via INSERT OR IGNORE; uses FK cascade)
- `PATCH /boards/{user_id}/cards/{card_id}` body `{title?, details?, column_id?, position?}` -> 200 updated card | 404 board/card | 400 invalid column
- `DELETE /boards/{user_id}/cards/{card_id}` -> 204 | 404
- `backend/schemas.py`: Pydantic Board/Column/Card/CardUpdate
- `backend/tests/test_api.py`: 13 TestClient tests (temp DB via monkeypatch of `DB_PATH`)
- `backend/__init__.py` added; dual-mode import (`if __package__: .schemas else: schemas`) so uvicorn from `backend/` and pytest from repo root both work
- Fixes: `001_init.sql` uses `CREATE TABLE IF NOT EXISTS` (old executescript crashed on existing db); requirements latest (fastapi 0.141.1, uvicorn 0.52.1, httpx 0.28.1), bogus `uv==0.1.0` removed; venv has deps installed; `*.db` gitignored; Playwright e2e tests updated with login helper (NOT executed)
- PLAN.md Part 6 checklists ticked

## Part 7: COMPLETE (verified)
Frontend now persists board state through the backend API:
- `frontend/src/lib/api.ts`: fetch client wrapping all four endpoints (`getBoard` 404 -> null, `saveBoard` POST, `updateCard` PATCH, `removeCard` DELETE); base URL `NEXT_PUBLIC_API_URL ?? "http://localhost:8000"`
- `frontend/src/lib/BoardContext.tsx`: `BoardProvider`/`useBoard`; loads board on mount (seeds `initialBoard` when GET returns null), exposes `renameColumn`/`addCard`/`moveCard`/`deleteCard`; optimistic local updates then persist (rename/add -> `saveBoard`, DnD move -> `updateCard` PATCH with column_id+position, delete -> `removeCard`); loading/error state
- `frontend/src/lib/kanban.ts`: `BoardData` now includes `id`/`title`; `initialData` renamed `initialBoard`; `findColumnId` exported
- `frontend/src/components/KanbanBoard.tsx`: consumes context instead of local mock; loading spinner + error alert; `src/app/page.tsx` wraps board in `BoardProvider`
- Backend: CORSMiddleware added (`allow_origins=["*"]`)
- Fixes discovered during e2e: `frontend/nginx.conf` added + wired in Dockerfile (`try_files $uri $uri.html $uri/`) so `/login` serves `login.html` (static export emits `<route>.html`); default nginx config 301'd `/login` -> `/login/` -> 403
- `src/test/vitest.d.ts` referenced `vitest` module types; changed to `vitest/globals` so `tsc --noEmit` is clean for test files using globals

## Verification results (all pass)
- Backend: `pytest -q` -> 14 passed
- Frontend unit/integration: `npm test` -> 25 passed (5 files: kanban, api, login, BoardContext, KanbanBoard)
- Frontend build: `npm run build` succeeds; `npx tsc --noEmit` and `npm run lint` clean
- Playwright e2e (`npx playwright test`): 3 passed against live Docker stack (load board, add card, DnD move) after DB seeded from empty via 404->POST
- Live browser checks: fresh login -> GET 404 -> POST 201 seed -> 5 columns render; DnD move card-1 to Review persisted in SQLite and survives a fresh browser session (reload shows same board state)

## Part 8: COMPLETE (verified)
OpenRouter AI connectivity implemented and verified live:
- `backend/ai_client.py`: thin httpx wrapper around OpenRouter chat completions. Reads `OPENROUTER_API_KEY` from env (Docker Compose `env_file`) or falls back to parsing the repo-root `.env`; model `openai/gpt-oss-120b`; `MAX_TOKENS=256`.
- `backend/main.py`: `GET /ai/ping` sends prompt `2+2`, returns `{"answer": "<model reply>"}`; returns 500 with detail if the key is missing.
- `backend/tests/test_ai.py`: 5 tests mocking httpx (no network): `ask` returns `"4"`, request shape (URL/auth header/model/messages/max_tokens), missing-key raises, endpoint returns `{"answer":"4"}`, missing-key endpoint returns 500.
- Root-cause fix (evidence: OpenRouter `402 {"error":{...,"can only afford 1244 tokens"}}`): `openai/gpt-oss-120b` defaults to 65536 output tokens, exceeding the account's remaining credit balance; capped `max_tokens=256`.

## Part 9: COMPLETE (verified)
Structured AI interaction implemented and verified live against OpenRouter:
- `backend/ai_schema.json`: the AI response JSON schema from PLAN.md (`message`, optional `boardUpdates` add/edit/move/delete with `cardId`/`columnId`/`payload {title,description,order}`, optional `conversationHistory`).
- `backend/ai_client.py`: new `ask_structured(board, question, history)` sends a system prompt embedding the schema + `{board, question}` as the user message, parses the reply with `_parse_json_content` (tolerates fenced JSON).
- `backend/services/ai_service.py`: validates the raw AI reply against Pydantic models (`AIResponse` etc. in `schemas.py`); raises `InvalidAIResponseError` for unparseable/out-of-schema output.
- `backend/main.py`: `POST /ai/ask` accepts `{question, history?}`, fetches the board for the hard-coded user from the DB, calls the service, applies `boardUpdates` atomically via `_apply_board_updates` (add/edit/move/delete, with `_unique_card_id` collision avoidance), returns `{message, boardUpdates}`. Errors: 404 no board, 500 missing API key, 502 invalid AI response.
- Root-cause fix (evidence: OpenRouter reply had `finish_reason: length` and truncated JSON): `gpt-oss-120b` is a reasoning model that burned ~200 of the old 256 `max_tokens` on reasoning. Raised `MAX_TOKENS` to 1024 and added `reasoning: {"effort": "low"}` (cut reasoning tokens 200 -> 35); pre-flight credit check still passes.
- `backend/services/__init__.py` added; dual-mode import in `ai_service.py` uses `"." in __package__` so it works both under uvicorn from `backend/` and pytest from repo root.
- `backend/tests/test_ai_ask.py`: 17 tests (request shape, JSON parsing, schema validation pass/fail, add/edit/move/delete applied, message-only, history passthrough, 404/500/502, atomic rollback on bad column).

## Verification results (all pass)
- Backend: `pytest -q` -> 36 passed
- uvicorn smoke test: server boots from `backend/`, `POST /ai/ask` returns real structured response from OpenRouter and DB reflects applied updates
- Live e2e (TestClient, temp DB): AI added a card to Backlog; `GET /boards/user` returned the new card

## Notes / not done
- Part 9 COMPLETE (structured AI interaction, verified live) — see section below
- Part 10 NOT started (AI chat sidebar UI)
- `tests/kanban.e2e.ts` is not matched by Playwright's default testMatch (`*.e2e.ts` != `*.spec.ts`/`*.test.ts`) and is dead/duplicate of `tests/kanban.spec.ts`; could be deleted or renamed
- A 500 from the backend does not carry `Access-Control-Allow-Origin` (Starlette error response bypasses CORSMiddleware); harmless in normal operation
- Docker backend container must be restarted after backend code changes (`docker compose restart backend`) since uvicorn runs without --reload
- Starlette emits harmless deprecation warning (httpx vs httpx2) in TestClient

## Commands
- Backend tests: `.\venv\Scripts\pytest.exe -q` (from repo root)
- Frontend tests: `npm test` (in frontend/)
- Frontend typecheck: `npx tsc --noEmit` (in frontend/)
- Playwright e2e: `npx playwright test` (in frontend/; reuses running dev/docker server on :3000 via `reuseExistingServer`)
- Run backend: from `backend/` run venv uvicorn (`..\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000`) or via docker
- Docker: `scripts/start.ps1` / `scripts/stop.ps1`; backend at :8000, frontend at :3000
