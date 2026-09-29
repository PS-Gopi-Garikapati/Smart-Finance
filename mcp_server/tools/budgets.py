import re
from typing import Dict, Any, Optional
from database.database import execute_query

def validate_month_format(month_str: str) -> bool:
    """Validate that month is in YYYY-MM format with valid month integer 01-12."""
    if not isinstance(month_str, str) or not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", month_str.strip()):
        return False
    return True

def execute_get_budget(
    category: str,
    month: str,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve budget amount for a specific category and month."""
    if not category or not isinstance(category, str):
        return {
            "success": False,
            "error": "INVALID_ARGUMENT",
            "message": "Category must be a non-empty string."
        }

    if not month or not validate_month_format(month):
        return {
            "success": False,
            "error": "INVALID_ARGUMENT",
            "message": f"Invalid month format '{month}'. Must be a valid YYYY-MM format (e.g. '2026-09')."
        }

    query = "SELECT budget_amount FROM budgets WHERE LOWER(category) = LOWER(?) AND month = ?"
    try:
        rows = execute_query(query, (category.strip(), month.strip()), db_path=db_path)
        if not rows:
            return {
                "success": False,
                "error": "BUDGET_NOT_FOUND",
                "message": f"No budget found for category '{category}' in month '{month}'."
            }
        return {
            "success": True,
            "category": category,
            "month": month,
            "budget": rows[0]["budget_amount"]
        }
    except Exception as e:
        return {
            "success": False,
            "error": "DATABASE_ERROR",
            "message": f"Failed to fetch budget: {str(e)}"
        }

def execute_compare_budget(
    spent: float,
    budget: float
) -> Dict[str, Any]:
    """Compare actual spent amount against budget amount."""
    try:
        spent_val = float(spent)
        budget_val = float(budget)
    except (ValueError, TypeError):
        return {
            "success": False,
            "error": "INVALID_ARGUMENT",
            "message": "Both 'spent' and 'budget' must be valid numeric values."
        }

    if budget_val <= 0:
        percentage_used = 0.0
    else:
        percentage_used = round((spent_val / budget_val) * 100, 2)

    difference = round(spent_val - budget_val, 2)
    status = "OVER_BUDGET" if difference > 0 else "WITHIN_BUDGET"

    return {
        "success": True,
        "spent": spent_val,
        "budget": budget_val,
        "difference": difference,
        "status": status,
        "percentage_used": percentage_used
    }
