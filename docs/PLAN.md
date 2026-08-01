# High level steps for project

## Part 1 – Planning & Approval

**Goal:** Produce a concrete, test‑driven plan that can be reviewed and approved before any code is written.

**Checklist**
1. Review business requirements (sign‑in, Kanban board, AI chat).
2. Define user stories and acceptance criteria.
3. Draft the SQLite data model (users, boards, columns, cards).
4. List required API endpoints (CRUD for boards, columns, cards; auth stub).
5. Outline frontend flow (login guard, board view, AI sidebar).
6. Specify test strategy (combined Vitest/Pytest suite, integration tests).
7. Define AI response JSON schema (see Part 9).
8. Create `frontend/AGENTS.md` with an overview of existing code and extension guidance.
9. Write the enriched PLAN (this file) with sub‑steps and success criteria.
10. **User approval** – present the plan and obtain sign‑off.

**Success criteria**
* All checklist items are ticked.
* The user explicitly approves the plan.

---

## Part 2 – Scaffolding (Docker & Backend Skeleton)

**Goal:** Provide a reproducible development environment with separate containers for backend and frontend.

**Checklist**
1. Add `backend/Dockerfile` (Python 3.12, uv, FastAPI, uvicorn).
2. Add `frontend/Dockerfile` (Node 20, build static assets, serve with nginx).
3. Create `docker-compose.yml` defining two services: `backend` (port 8000) and `frontend` (port 3000).
4. Write start/stop scripts in `scripts/` for Windows (`.ps1`) and Unix (`.sh`).
5. Implement a minimal FastAPI app with a **Hello World** endpoint (`GET /hello`).
6. Add a static HTML file (`frontend/public/hello.html`) served by the frontend container.
7. Verify that `docker compose up` builds both containers and the endpoints are reachable.

**Success criteria**
* `docker compose up` completes without errors.
* `http://localhost:3000/hello.html` returns the static page.
* `http://localhost:8000/hello` returns JSON `{"message": "hello world"}`.

---

## Part 3 – Frontend Build & Kanban Demo

**Goal:** Serve the existing Next.js demo as a static site and ensure the Kanban board renders.

**Checklist**
1. Configure `next.config.ts` for static export (`output: "export"`).
2. Add `npm run build && npm run start` scripts that use the Docker frontend image.
3. Run Vitest unit tests for existing components (`KanbanBoard`, `KanbanColumn`, `KanbanCard`).
4. Add an integration test that loads `/` and checks that a column header is present.

**Success criteria**
* `npm run build` succeeds and produces a `out/` directory.
* The Docker frontend container serves the built site at `http://localhost:3000/`.
* All Vitest tests pass (`npm test` exits with code 0).

---

## Part 4 – Fake Sign‑In Experience

**Goal:** Guard the Kanban board behind a simple login screen using hard‑coded credentials.

**Checklist**
1. Create a `/login` page with a form (username, password). ✅
2. Implement client‑side validation against `user` / `password`. ✅
3. Store an auth flag in `sessionStorage` and protect the `/` route with a guard component. ✅
4. Add a logout button that clears the flag and redirects to `/login`. ✅
5. Write Vitest tests for the login flow and the guard. ✅

**Success criteria**
* Unauthenticated users are redirected to `/login`.
* Correct credentials allow access to the Kanban board.
* Logout returns the user to the login page.
* All new tests pass.
* ✅ Part 4 completed.

---

## Part 5 – Database Modeling

**Goal:** Define a persistent SQLite schema that can store multiple users and their Kanban data.

**Checklist**
1. Draft an ER diagram and JSON representation of the schema.
2. Create `docs/DB_SCHEMA.md` describing tables: `users`, `boards`, `columns`, `cards`.
3. Include migration script (`backend/migrations/001_init.sql`).
4. Obtain user sign‑off on the schema.

**Success criteria**
* Schema document is approved by the user.
* Migration script can be executed to create the DB without errors.

---

## Part 6 – Backend API Implementation

**Goal:** Provide fully‑tested CRUD endpoints for the Kanban board.

**Checklist**
1. Initialise the SQLite DB on FastAPI startup (create if missing).
2. Implement endpoints:
	 * `GET /boards/{user_id}` – fetch board JSON.
	 * `POST /boards/{user_id}` – create/replace board.
	 * `PATCH /boards/{user_id}/cards/{card_id}` – update a card.
	 * `DELETE /boards/{user_id}/cards/{card_id}` – delete a card.
3. Add Pydantic models for request/response validation.
4. Write Pytest unit tests covering each endpoint, including error cases.
5. Ensure the backend container can be started with `uvicorn main:app --host 0.0.0.0 --port 8000`.

**Success criteria**
* All endpoints return the expected status codes and JSON payloads.
* Pytest suite passes (`pytest -q` exits with 0).
* The DB file is created on first run.

---

## Part 7 – Frontend ↔ Backend Integration

**Goal:** Persist board state via the API and keep the UI in sync.

**Checklist**
1. Replace static mock data with calls to the backend (`fetch` or `axios`).
2. Store board state in a React context/provider.
3. Add optimistic UI updates for drag‑and‑drop actions.
4. Write integration tests that mock the API and verify UI updates.

**Success criteria**
* Reloading the page shows the same board state (persistence).
* Drag‑and‑drop moves cards and persists the change.
* All integration tests pass.

---

## Part 8 – AI Connectivity (OpenRouter)

**Goal:** Verify that the backend can call the OpenRouter LLM.

**Checklist**
1. Add a thin wrapper (`backend/ai_client.py`) that reads `OPENROUTER_API_KEY` from `.env`.
2. Implement a test endpoint `GET /ai/ping` that sends the prompt `2+2` and returns the model's answer.
3. Write a Pytest that mocks the HTTP request and asserts the response is `4` (or the model’s numeric answer).

**Success criteria**
* The endpoint returns a numeric answer for the simple arithmetic prompt.
* Test suite validates the wrapper without making a real network call.

---

## Part 9 – Structured AI Interaction

**Goal:** Exchange the full board JSON and user query with the LLM, receiving a structured response that may include board updates.

**Checklist**
1. Define the JSON schema (see below) and add it to `backend/ai_schema.json`.
2. Extend `ai_client.py` to send `{board, question, history}` and parse the structured output.
3. Implement a service layer (`backend/services/ai_service.py`) that validates the response against the schema.
4. Add endpoint `POST /ai/ask` that accepts `{question}` and returns `{message, boardUpdates}`.
5. Write comprehensive tests covering:
	 * Valid structured response → board updates applied.
	 * Missing `boardUpdates` → only message returned.
	 * Invalid schema → error handling.

**Success criteria**
* The endpoint returns a JSON object matching the schema.
* When `boardUpdates` are present, the DB is updated accordingly.
* All tests pass.

**Proposed AI response schema**
```json
{
	"message": "string",
	"boardUpdates": [
		{
			"type": "add|edit|move|delete",
			"cardId": "string",
			"columnId": "string",
			"payload": { "title": "string", "description": "string", "order": "number" }
		}
	],
	"conversationHistory": [
		{ "role": "user|assistant", "content": "string" }
	]
}
```

---

## Part 10 – AI Chat Sidebar UI

**Goal:** Provide a polished, responsive sidebar for chatting with the LLM and automatically applying board updates.

**Checklist**
1. Create `components/AIChatSidebar.tsx` with a collapsible drawer (styled using the project colour palette).
2. Hook the sidebar to the `/ai/ask` endpoint, display the assistant’s `message`, and show a loading spinner.
3. When `boardUpdates` are present, dispatch actions to the board context to refresh the UI.
4. Add unit tests for the sidebar component (mock fetch, verify UI changes).
5. Ensure the sidebar is accessible (keyboard navigation, ARIA labels).

**Success criteria**
* The sidebar can be opened/closed and sends queries to the backend.
* Responses appear in the chat view.
* Board updates are reflected instantly without a full page reload.
* All component tests pass and the UI follows the defined colour scheme.

---

**Next steps**
* Review this enriched plan with the user.
* Once approved, begin implementation starting with Part 2 scaffolding.

Part 1: Plan

Enrich this document to plan out each of these parts in detail, with substeps listed out as a checklist to be checked off by the agent, and with tests and success critieria for each. Also create an AGENTS.md file inside the frontend directory that describes the existing code there. Ensure the user checks and approves the plan.

Part 2: Scaffolding

Set up the Docker infrastructure, the backend in backend/ with FastAPI, and write the start and stop scripts in the scripts/ directory. This should serve example static HTML to confirm that a 'hello world' example works running locally and also make an API call.

Part 3: Add in Frontend

Now update so that the frontend is statically built and served, so that the app has the demo Kanban board displayed at /. Comprehensive unit and integration tests.

Part 4: Add in a fake user sign in experience

Now update so that on first hitting /, you need to log in with dummy credentials ("user", "password") in order to see the Kanban, and you can log out. Comprehensive tests.

Part 5: Database modeling

Now propose a database schema for the Kanban, saving it as JSON. Document the database approach in docs/ and get user sign off.

Part 6: Backend

Now add API routes to allow the backend to read and change the Kanban for a given user; test this thoroughly with backend unit tests. The database should be created if it doesn't exist.

Part 7: Frontend + Backend

Now have the frontend actually use the backend API, so that the app is a proper persistent Kanban board. Test very throughly.

Part 8: AI connectivity

Now allow the backend to make an AI call via OpenRouter. Test connectivity with a simple "2+2" test and ensure the AI call is working.

Part 9: Now extend the backend call so that it always calls the AI with the JSON of the Kanban board, plus the user's question (and conversation history). The AI should respond with Structured Outputs that includes the response to the user and optionaly an update to the Kanban. Test thoroughly.

Part 10: Now add a beautiful sidebar widget to the UI supporting full AI chat, and allowing the LLM (as it determines) to update the Kanban based on its Structured Outputs. If the AI updates the Kanban, then the UI should refresh automatically.