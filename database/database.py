import sqlite3
import os
import queue
import threading
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "finance.db")

class SQLiteConnectionPool:
    """
    Thread-safe connection pool for SQLite databases.
    Maintains a pool of reusable connections per database path,
    enables WAL mode for concurrent reads/writes, and recycles connections.
    """

    def __init__(self, max_connections: int = 10, timeout: float = 30.0):
        self.max_connections = max_connections
        self.timeout = timeout
        self._pools: Dict[str, queue.Queue] = {}
        self._created_counts: Dict[str, int] = {}
        self._lock = threading.Lock()

    def _get_queue(self, path: str) -> queue.Queue:
        with self._lock:
            if path not in self._pools:
                self._pools[path] = queue.Queue(maxsize=self.max_connections)
                self._created_counts[path] = 0
            return self._pools[path]

    def _create_connection(self, path: str) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        conn = sqlite3.connect(path, timeout=self.timeout, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        return conn

    def get_connection(self, db_path: Optional[str] = None) -> "PooledSQLiteConnection":
        target_path = os.path.abspath(db_path or os.getenv("DB_PATH", DEFAULT_DB_PATH))
        q = self._get_queue(target_path)

        try:
            raw_conn = q.get_nowait()
        except queue.Empty:
            with self._lock:
                if self._created_counts[target_path] < self.max_connections:
                    raw_conn = self._create_connection(target_path)
                    self._created_counts[target_path] += 1
                else:
                    raw_conn = None
            if raw_conn is None:
                raw_conn = q.get(timeout=self.timeout)

        return PooledSQLiteConnection(raw_conn, self, target_path)

    def return_connection(self, raw_conn: sqlite3.Connection, target_path: str):
        try:
            raw_conn.rollback()
        except Exception:
            pass

        q = self._get_queue(target_path)
        try:
            q.put_nowait(raw_conn)
        except queue.Full:
            try:
                raw_conn.close()
            except Exception:
                pass
            with self._lock:
                if self._created_counts[target_path] > 0:
                    self._created_counts[target_path] -= 1

    def close_all(self):
        """Close all connections across all pools."""
        with self._lock:
            for path, q in self._pools.items():
                while not q.empty():
                    try:
                        conn = q.get_nowait()
                        conn.close()
                    except Exception:
                        pass
                self._created_counts[path] = 0

class PooledSQLiteConnection:
    """Wrapper around sqlite3.Connection that returns connection to pool on close() or context exit."""

    def __init__(self, conn: sqlite3.Connection, pool: SQLiteConnectionPool, path: str):
        self._conn = conn
        self._pool = pool
        self._path = path
        self._returned = False

    def close(self):
        if not self._returned:
            self._returned = True
            self._pool.return_connection(self._conn, self._path)

    def __enter__(self):
        return self._conn.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        res = self._conn.__exit__(exc_type, exc_val, exc_tb)
        self.close()
        return res

    def __getattr__(self, name: str):
        return getattr(self._conn, name)

# Global pool instance
pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
pool_timeout = float(os.getenv("DB_POOL_TIMEOUT", "30.0"))
db_pool = SQLiteConnectionPool(max_connections=pool_size, timeout=pool_timeout)

def get_db_connection(db_path: Optional[str] = None) -> PooledSQLiteConnection:
    """Return a thread-safe pooled connection to the SQLite database with Row factory and WAL enabled."""
    return db_pool.get_connection(db_path)

def execute_query(query: str, params: tuple = (), db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Execute a read query using a pooled connection and return results as a list of dictionaries."""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise RuntimeError(f"Database query error: {str(e)}")

def execute_statement(query: str, params: tuple = (), db_path: Optional[str] = None) -> int:
    """Execute an insert/update/delete statement using a pooled connection and return affected row count."""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    except sqlite3.Error as e:
        raise RuntimeError(f"Database statement error: {str(e)}")
