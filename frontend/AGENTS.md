# Frontend (Next.js Kanban demo)

This directory contains the Next.js frontend for the Project Management MVP.

## Overview

- `src/app/page.tsx` – the main Kanban board page. Guards the `/` route: unauthenticated
  users (no `auth` flag in `sessionStorage`) are redirected to `/login`. Contains a logout
  button that clears the flag.
- `src/app/login/page.tsx` – fake sign-in page validating against hard-coded credentials
  (`user` / `password`). On success stores `auth=true` in `sessionStorage` and redirects to `/`.
- `src/components/KanbanBoard.tsx` – the interactive board: columns, drag-and-drop via
  `@dnd-kit`, card add/delete, and column rename. It consumes board state from
  `BoardContext` (Part 7 removed the static mock data).
- `src/components/KanbanColumn.tsx`, `KanbanCard.tsx`, `KanbanCardPreview.tsx`,
  `NewCardForm.tsx` – board building blocks.
- `src/lib/kanban.ts` – types (`BoardData`, `Column`, `Card`), the `initialBoard` seed
  (used to create a board on first load), the `moveCard` drag logic, `findColumnId`, and
  `createId`. This is the canonical board shape the backend API mirrors.
- `src/lib/api.ts` – fetch client for the backend: `getBoard` (404 -> null), `saveBoard`
  (POST), `updateCard` (PATCH), `removeCard` (DELETE), `askAi` (POST `/ai/ask` with
  `{question, history}`). Base URL:
  `NEXT_PUBLIC_API_URL ?? "http://localhost:8000"`.
- `src/lib/BoardContext.tsx` – `BoardProvider`/`useBoard`: loads the board for the
  hard-coded `user` on mount (seeding `initialBoard` when the board does not exist yet)
  and exposes `renameColumn` / `addCard` / `moveCard` / `deleteCard` / `refreshBoard`.
  Actions update the UI optimistically and then persist (moves via the PATCH endpoint,
  the rest via a full board POST); `refreshBoard` re-fetches from the API (used by the
  AI sidebar after board updates).
- `src/components/AIChatSidebar.tsx` – collapsible AI chat drawer (Part 10). Toggles a
  hidden-on-mount fixed button, POSTs `{question, history}` to `/ai/ask` via `askAi`,
  renders user/assistant bubbles plus a loading spinner, and calls board context
  `refreshBoard()` whenever the AI returns `boardUpdates`.
- `src/app/globals.css` – global styles and the project colour palette
  (accent yellow `#ecad0a`, blue `#209dd7`, purple `#753991`, navy `#032147`, gray `#888888`).

## Conventions

- `"use client"` components, React 19, TypeScript, Tailwind CSS v4.
- Tests live next to source files as `*.test.tsx` and run with Vitest (`npm test`).
  Playwright e2e tests are in `tests/` (`npm run test:e2e`).
- Static export mode is configured in `next.config.ts` (`output: "export"`); the Docker
  build serves the exported `out/` directory via nginx.
