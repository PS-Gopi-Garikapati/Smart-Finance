import re
from datetime import datetime
from typing import Dict, Any, Optional
from database.database import execute_query

def validate_month_format(month_str: str) -> bool:
    """Validate that month is in YYYY-MM format with valid month integer 01-12."""
    if not isinstance(month_str, str) or not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", month_str.strip()):
        return False
    return True

def validate_date_format(date_str: str) -> bool:
    """Validate that date is a valid ISO date YYYY-MM-DD."""
    if not isinstance(date_str, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str.strip()):
        return False
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False

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
    
    if month is not None:
        if not validate_month_format(month):
            return {
                "success": False,
                "error": "INVALID_ARGUMENT",
                "message": f"Invalid month format '{month}'. Must be YYYY-MM with month between 01 and 12 (e.g., '2026-09')."
            }

    if start_date is not None:
        if not validate_date_format(start_date):
            return {
                "success": False,
                "error": "INVALID_ARGUMENT",
                "message": f"Invalid start_date format '{start_date}'. Must be a valid YYYY-MM-DD date."
            }

    if end_date is not None:
        if not validate_date_format(end_date):
            return {
                "success": False,
                "error": "INVALID_ARGUMENT",
                "message": f"Invalid end_date format '{end_date}'. Must be a valid YYYY-MM-DD date."
            }

    if start_date and end_date:
        if start_date.strip() > end_date.strip():
            return {
                "success": False,
                "error": "INVALID_ARGUMENT",
                "message": f"Invalid date range: start_date '{start_date}' cannot be after end_date '{end_date}'."
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
