# Database Schema for Project Management MVP

This document describes the **SQLite** schema that will store all persistent data for the Kanban application. The schema is expressed both as a **relational model** (SQL `CREATE TABLE` statements) and as a **JSON representation** that can be used by the backend code or documentation tools.

---

## ER Diagram (textual)

```
[users] 1 ── * [boards] 1 ── * [columns] 1 ── * [cards]
```

* A **user** can own multiple **boards**.
* Each **board** contains an ordered list of **columns**.
* Each **column** contains an ordered list of **cards**.

All primary keys are UUID strings (`TEXT`). Foreign‑key constraints enforce the relationships.

---

## SQL Schema (SQLite)

```sql
CREATE TABLE users (
    id            TEXT PRIMARY KEY,          -- UUID
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL            -- hashed password (e.g., bcrypt)
);

CREATE TABLE boards (
    id      TEXT PRIMARY KEY,               -- UUID
    user_id TEXT NOT NULL,
    title   TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE columns (
    id        TEXT PRIMARY KEY,             -- UUID
    board_id  TEXT NOT NULL,
    title     TEXT NOT NULL,
    position  INTEGER NOT NULL,            -- ordering within a board
    FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
);

CREATE TABLE cards (
    id        TEXT PRIMARY KEY,             -- UUID
    column_id TEXT NOT NULL,
    title     TEXT NOT NULL,
    details   TEXT,
    position  INTEGER NOT NULL,            -- ordering within a column
    FOREIGN KEY (column_id) REFERENCES columns(id) ON DELETE CASCADE
);
```

---

## JSON Representation

The following JSON structure mirrors the relational model and can be used for documentation, seed data, or API contracts.

```json
{
  "users": [
    {
      "id": "<uuid>",
      "username": "string",
      "password_hash": "string"
    }
  ],
  "boards": [
    {
      "id": "<uuid>",
      "user_id": "<uuid>",
      "title": "string"
    }
  ],
  "columns": [
    {
      "id": "<uuid>",
      "board_id": "<uuid>",
      "title": "string",
      "position": 0
    }
  ],
  "cards": [
    {
      "id": "<uuid>",
      "column_id": "<uuid>",
      "title": "string",
      "details": "string",
      "position": 0
    }
  ]
}
```

*All `id` fields are UUID strings. `position` fields are zero‑based integers that define ordering.*

---

## Migration Script

The migration file `backend/migrations/001_init.sql` contains the exact SQL statements above and can be executed on container start‑up to ensure the database exists.

---

## Next Steps

1. Review this schema with the user and obtain sign‑off.
2. Add the migration script to the repository (see `backend/migrations/001_init.sql`).
3. Update the FastAPI backend to initialise the SQLite DB using this script on startup.

---

*Prepared by the assistant as part of Part 5 – Database Modeling.*