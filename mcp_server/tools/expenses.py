from typing import Dict, Any, Optional
from database.database import execute_query
from mcp_server.tools.validators import (
    GetExpensesInput,
    validation_error,
    database_error,
    validate_month_format,
    validate_date_format
)

def execute_get_expenses(
    category: Optional[str] = None,
    month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve expense records from SQLite based on category, month, or date range."""
    try:
        validated = GetExpensesInput(
            category=category,
            month=month,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        msg = str(e)
        if "Value error, " in msg:
            msg = msg.split("Value error, ")[-1]
        return validation_error(msg)

    query = "SELECT id, date, category, amount, description FROM expenses WHERE 1=1"
    params = []

    if validated.category:
        query += " AND LOWER(category) = LOWER(?)"
        params.append(validated.category)

    if validated.month:
        query += " AND strftime('%Y-%m', date) = ?"
        params.append(validated.month)

    if validated.start_date:
        query += " AND date >= ?"
        params.append(validated.start_date)

    if validated.end_date:
        query += " AND date <= ?"
        params.append(validated.end_date)

    query += " ORDER BY date ASC"

    try:
        rows = execute_query(query, tuple(params), db_path=db_path)
        total = round(sum(r["amount"] for r in rows), 2)
        return {
            "success": True,
            "category": validated.category,
            "month": validated.month,
            "expenses": rows,
            "count": len(rows),
            "total": total
        }
    except Exception as e:
        return database_error(str(e))
