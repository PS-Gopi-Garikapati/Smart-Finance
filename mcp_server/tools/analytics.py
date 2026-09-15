from typing import Dict, Any, Optional
from database.database import execute_query

def execute_get_spending_by_category(
    month: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve total spending grouped by category for a given month or overall."""
    if month is not None and not isinstance(month, str):
        return {
            "success": False,
            "error": "INVALID_ARGUMENT",
            "message": "Month must be a string in YYYY-MM format."
        }

    query = """
        SELECT category, SUM(amount) as total_spent, COUNT(*) as transaction_count
        FROM expenses
        WHERE 1=1
    """
    params = []

    if month:
        query += " AND strftime('%Y-%m', date) = ?"
        params.append(month.strip())

    query += " GROUP BY category ORDER BY total_spent DESC"

    try:
        rows = execute_query(query, tuple(params), db_path=db_path)
        highest = rows[0] if rows else None
        grand_total = sum(r["total_spent"] for r in rows)

        return {
            "success": True,
            "month": month,
            "categories": rows,
            "grand_total": grand_total,
            "highest_category": highest["category"] if highest else None,
            "highest_amount": highest["total_spent"] if highest else 0.0
        }
    except Exception as e:
        return {
            "success": False,
            "error": "DATABASE_ERROR",
            "message": f"Failed to calculate category analytics: {str(e)}"
        }
