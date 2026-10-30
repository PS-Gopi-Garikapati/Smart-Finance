#Shows how much you spent on Food, Shopping, Transport, and other categories.
from typing import Dict, Any, Optional
from database.database import execute_query
from mcp_server.tools.validators import (
    GetSpendingByCategoryInput,
    validation_error,
    database_error,
    validate_month_format
)
#This function retrieves spending totals grouped by category.
def execute_get_spending_by_category(
    month: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve total spending grouped by category for a given month or overall."""
    try:
        validated = GetSpendingByCategoryInput(month=month)
    except Exception as e:
        msg = str(e)
        if "Value error, " in msg:
            msg = msg.split("Value error, ")[-1]
        return validation_error(msg)

    query = """
        SELECT category, SUM(amount) as total_spent, COUNT(*) as transaction_count
        FROM expenses
        WHERE 1=1
    """
    params = []
#Apply the month filter
    if validated.month:
        query += " AND strftime('%Y-%m', date) = ?"
        params.append(validated.month)

    query += " GROUP BY category ORDER BY total_spent DESC"

    try:
        rows = execute_query(query, tuple(params), db_path=db_path)
        highest = rows[0] if rows else None
        grand_total = round(sum(r["total_spent"] for r in rows), 2)

        return {
            "success": True,
            "month": validated.month,
            "categories": rows,
            "grand_total": grand_total,
            "highest_category": highest["category"] if highest else None,
            "highest_amount": round(highest["total_spent"], 2) if highest else 0.0
        }
    except Exception as e:
        return database_error(str(e))
