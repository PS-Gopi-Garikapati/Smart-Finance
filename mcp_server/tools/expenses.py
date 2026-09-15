from typing import Dict, Any, Optional
from database.database import execute_query

def execute_get_expenses(
    category: Optional[str] = None,
    month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve expense records from SQLite based on category, month, or date range."""
    # Validation
    if category is not None and not isinstance(category, str):
        return {
            "success": False,
            "error": "INVALID_ARGUMENT",
            "message": "Category must be a string."
        }
    
    if month is not None and not isinstance(month, str):
        return {
            "success": False,
            "error": "INVALID_ARGUMENT",
            "message": "Month must be a string in YYYY-MM format."
        }

    query = "SELECT id, date, category, amount, description FROM expenses WHERE 1=1"
    params = []

    if category:
        query += " AND LOWER(category) = LOWER(?)"
        params.append(category.strip())

    if month:
        query += " AND strftime('%Y-%m', date) = ?"
        params.append(month.strip())

    if start_date:
        query += " AND date >= ?"
        params.append(start_date.strip())

    if end_date:
        query += " AND date <= ?"
        params.append(end_date.strip())

    query += " ORDER BY date ASC"

    try:
        rows = execute_query(query, tuple(params), db_path=db_path)
        total = sum(r["amount"] for r in rows)
        return {
            "success": True,
            "category": category,
            "month": month,
            "expenses": rows,
            "count": len(rows),
            "total": total
        }
    except Exception as e:
        return {
            "success": False,
            "error": "DATABASE_ERROR",
            "message": f"Failed to fetch expenses: {str(e)}"
        }
