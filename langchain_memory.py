import sqlite3
from pathlib import Path
from threading import Lock

from config import get_env


def _get_int_env(name, default):
    try:
        return int(get_env(name, default))
    except (TypeError, ValueError):
        return int(default)


ROOT_DIR = Path(__file__).parent
LOG_DIR = ROOT_DIR / "logs"
DB_PATH = LOG_DIR / "chat_memory.sqlite3"
MAX_HISTORY_MESSAGES = max(2, _get_int_env("CHAT_MEMORY_MESSAGES", 8))
MAX_PERSISTED_MESSAGES = max(
    MAX_HISTORY_MESSAGES,
    _get_int_env("CHAT_MEMORY_PERSISTED_MESSAGES", 24),
)
_DB_LOCK = Lock()


def get_history_messages(session_id):
    normalized_session = _normalize_session_id(session_id)
    with _DB_LOCK:
        _ensure_schema()
        rows = _fetch_recent_rows(normalized_session, limit=MAX_HISTORY_MESSAGES)

    messages = []
    for role, content in rows:
        message = _row_to_message(role, content)
        if message is not None:
            messages.append(message)
    return messages


def append_messages(session_id, *messages):
    normalized_session = _normalize_session_id(session_id)
    serializable_messages = [
        bundle
        for bundle in (_message_to_row(message) for message in messages)
        if bundle is not None
    ]
    if not serializable_messages:
        return

    with _DB_LOCK:
        _ensure_schema()
        with sqlite3.connect(DB_PATH) as connection:
            connection.executemany(
                """
                INSERT INTO chat_messages (session_id, role, content)
                VALUES (?, ?, ?)
                """,
                [
                    (normalized_session, role, content)
                    for role, content in serializable_messages
                ],
            )
            _trim_session_history(connection, normalized_session)
            connection.commit()


def clear_history(session_id):
    normalized_session = _normalize_session_id(session_id)
    with _DB_LOCK:
        _ensure_schema()
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute(
                "DELETE FROM chat_messages WHERE session_id = ?",
                (normalized_session,),
            )
            connection.commit()


def _ensure_schema():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id_id
            ON chat_messages (session_id, id)
            """
        )
        connection.commit()


def _fetch_recent_rows(session_id, *, limit):
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            """
            SELECT role, content
            FROM (
                SELECT role, content, id
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
            ORDER BY id ASC
            """,
            (session_id, limit),
        ).fetchall()
    return rows


def _trim_session_history(connection, session_id):
    connection.execute(
        """
        DELETE FROM chat_messages
        WHERE session_id = ?
          AND id NOT IN (
              SELECT id
              FROM chat_messages
              WHERE session_id = ?
              ORDER BY id DESC
              LIMIT ?
          )
        """,
        (session_id, session_id, MAX_PERSISTED_MESSAGES),
    )


def _message_to_row(message):
    try:
        from langchain_core.messages import AIMessage, HumanMessage
    except ImportError:
        return None

    if isinstance(message, HumanMessage):
        return ("human", str(message.content or ""))
    if isinstance(message, AIMessage):
        return ("ai", str(message.content or ""))
    return None


def _row_to_message(role, content):
    try:
        from langchain_core.messages import AIMessage, HumanMessage
    except ImportError:
        return None

    if role == "human":
        return HumanMessage(content=content)
    if role == "ai":
        return AIMessage(content=content)
    return None


def _normalize_session_id(session_id):
    value = str(session_id or "").strip()
    return value or "anonymous"
