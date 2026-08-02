CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,          -- UUID
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL            -- hashed password (e.g., bcrypt)
);

CREATE TABLE IF NOT EXISTS boards (
    id      TEXT PRIMARY KEY,               -- UUID
    user_id TEXT NOT NULL,
    title   TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS columns (
    id        TEXT PRIMARY KEY,             -- UUID
    board_id  TEXT NOT NULL,
    title     TEXT NOT NULL,
    position  INTEGER NOT NULL,            -- ordering within a board
    FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cards (
    id        TEXT PRIMARY KEY,             -- UUID
    column_id TEXT NOT NULL,
    title     TEXT NOT NULL,
    details   TEXT,
    position  INTEGER NOT NULL,            -- ordering within a column
    FOREIGN KEY (column_id) REFERENCES columns(id) ON DELETE CASCADE
);
