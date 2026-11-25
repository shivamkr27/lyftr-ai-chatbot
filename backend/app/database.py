import sqlite3
from pathlib import Path
from typing import Optional


def sqlite_path(database_url: str) -> str:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise RuntimeError("DATABASE_URL must use SQLite")
    path = database_url[len(prefix):]
    if path.startswith("/"):
        return path
    return str(Path(path).resolve())


def connect(database_url: str) -> sqlite3.Connection:
    path = sqlite_path(database_url)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(database_url: str) -> None:
    connection = connect(database_url)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session_created "
            "ON messages(session_id, created_at, id)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS session_prompts (
                session_id TEXT PRIMARY KEY,
                system_prompt TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()
