from typing import Dict, Any, Optional
from database.database import execute_query
from mcp_server.tools.validators import (
    GetBudgetInput,
    CompareBudgetInput,
    validation_error,
    database_error,
    validate_month_format
)

def execute_get_budget(
    category: str,
    month: str,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve budget amount for a specific category and month."""
    try:
        validated = GetBudgetInput(category=category, month=month)
    except Exception as e:
        msg = str(e)
        if "Value error, " in msg:
            msg = msg.split("Value error, ")[-1]
        return validation_error(msg)

    query = "SELECT budget_amount FROM budgets WHERE LOWER(category) = LOWER(?) AND month = ?"
    try:
        rows = execute_query(query, (validated.category, validated.month), db_path=db_path)
        if not rows:
            return {
                "success": False,
                "error": "BUDGET_NOT_FOUND",
                "message": f"No budget found for category '{validated.category}' in month '{validated.month}'."
            }
        return {
            "success": True,
            "category": validated.category,
            "month": validated.month,
            "budget": float(rows[0]["budget_amount"])
        }
    except Exception as e:
        return database_error(str(e))

def execute_compare_budget(
    spent: float,
    budget: float
) -> Dict[str, Any]:
    """Compare actual spent amount against budget amount."""
    try:
        validated = CompareBudgetInput(spent=spent, budget=budget)
        spent_val = float(validated.spent)
        budget_val = float(validated.budget)
    except Exception as e:
        msg = str(e)
        if "Value error, " in msg:
            msg = msg.split("Value error, ")[-1]
        return validation_error(msg)

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
