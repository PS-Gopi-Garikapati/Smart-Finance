import os
import sys
from typing import List, Optional
from mcp.server.mcpserver import MCPServer

# Add root directory to sys.path for internal imports
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from mcp_server.tools.expenses import execute_get_expenses
from mcp_server.tools.budgets import execute_get_budget, execute_compare_budget
from mcp_server.tools.calculator import execute_calculate_total
from mcp_server.tools.analytics import execute_get_spending_by_category

mcp = MCPServer("Smart Finance Server")

@mcp.tool()
def get_expenses(
    category: Optional[str] = None,
    month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> dict:
    """
    Retrieve expense records from SQLite database.
    Filter by category, month (YYYY-MM), or date range (start_date, end_date in YYYY-MM-DD).
    Returns list of expenses, total spent, and expense count.
    """
    return execute_get_expenses(
        category=category,
        month=month,
        start_date=start_date,
        end_date=end_date
    )

@mcp.tool()
def get_budget(category: str, month: str) -> dict:
    """
    Retrieve the configured budget amount for a given category and month (YYYY-MM).
    Returns category, month, and budget amount.
    """
    return execute_get_budget(category=category, month=month)

@mcp.tool()
def calculate_total(amounts: List[float]) -> dict:
    """
    Calculate the total sum from a list of numerical amounts.
    Returns input amounts, count, and calculated total.
    """
    return execute_calculate_total(amounts=amounts)

@mcp.tool()
def compare_budget(spent: float, budget: float) -> dict:
    """
    Compare actual total spending against a budget amount.
    Returns spent, budget, difference, status ('OVER_BUDGET' or 'WITHIN_BUDGET'), and percentage_used.
    """
    return execute_compare_budget(spent=spent, budget=budget)

@mcp.tool()
def get_spending_by_category(month: Optional[str] = None) -> dict:
    """
    Retrieve total spending grouped by category for a specific month (YYYY-MM) or overall.
    Returns categories with spent totals, highest spending category, and grand total.
    """
    return execute_get_spending_by_category(month=month)

if __name__ == "__main__":
    mcp.run(transport="stdio")
