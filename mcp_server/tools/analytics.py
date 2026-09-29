import re
from typing import Dict, Any, Optional
from database.database import execute_query

def validate_month_format(month_str: str) -> bool:
    """Validate that month is in YYYY-MM format with valid month integer 01-12."""
    if not isinstance(month_str, str) or not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", month_str.strip()):
        return False
    return True

def execute_get_spending_by_category(
    month: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve total spending grouped by category for a given month or overall."""
    if month is not None:
        if not validate_month_format(month):
            return {
                "success": False,
                "error": "INVALID_ARGUMENT",
                "message": f"Invalid month format '{month}'. Must be YYYY-MM with month between 01 and 12 (e.g., '2026-09')."
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
