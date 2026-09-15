import sqlite3
import os
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "finance.db")

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a thread-safe connection to the SQLite database with Row factory enabled."""
    target_path = db_path or os.getenv("DB_PATH", DEFAULT_DB_PATH)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(query: str, params: tuple = (), db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Execute a read query and return results as a list of dictionaries."""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise RuntimeError(f"Database query error: {str(e)}")

def execute_statement(query: str, params: tuple = (), db_path: Optional[str] = None) -> int:
    """Execute a insert/update/delete statement and return affected row count."""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    except sqlite3.Error as e:
        raise RuntimeError(f"Database statement error: {str(e)}")
