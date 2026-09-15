import os
import sqlite3
from database.database import get_db_connection, DEFAULT_DB_PATH

def init_database(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize database tables for expenses and budgets."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        month TEXT NOT NULL,
        budget_amount REAL NOT NULL,
        UNIQUE(category, month)
    )
    """)

    # Create indexes for performant lookups
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_budgets_cat_month ON budgets(category, month)")

    conn.commit()
    conn.close()
    print(f"Database initialized successfully at: {db_path}")

if __name__ == "__main__":
    init_database()
