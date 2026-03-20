import os
import sqlite3
import time
from typing import Optional


DEFAULT_DB_PATH = "database/cache.db"


def _get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cache (
            document_id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            timestamp INTEGER NOT NULL
        )
        """
    )
    return conn


def get_cached_doc(
    doc_id: str,
    max_age_seconds: int = 3600,
    db_path: str = DEFAULT_DB_PATH,
) -> Optional[str]:
    """Return cached content when fresh enough, else None."""
    now = int(time.time())
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT content FROM cache WHERE document_id = ? AND timestamp > ?",
            (doc_id, now - max_age_seconds),
        )
        row = cursor.fetchone()
    return row[0] if row else None


def cache_doc(doc_id: str, content: str, db_path: str = DEFAULT_DB_PATH) -> None:
    """Upsert content into SQLite cache with current timestamp."""
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "REPLACE INTO cache (document_id, content, timestamp) VALUES (?, ?, ?)",
            (doc_id, content, int(time.time())),
        )
        conn.commit()

