from typing import Dict, Any, Optional
from database.database import execute_query

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

    if not month or not isinstance(month, str):
        return {
            "success": False,
            "error": "INVALID_ARGUMENT",
            "message": "Month must be a non-empty string in YYYY-MM format."
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
