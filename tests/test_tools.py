import pytest
from database.seed_data import seed_database
from mcp_server.tools.expenses import execute_get_expenses
from mcp_server.tools.budgets import execute_get_budget, execute_compare_budget
from mcp_server.tools.calculator import execute_calculate_total
from mcp_server.tools.analytics import execute_get_spending_by_category

@pytest.fixture(autouse=True)
def setup_db():
    seed_database()

def test_get_expenses_september_food():
    res = execute_get_expenses(category="Food", month="2026-09")
    assert res["success"] is True
    assert res["total"] == 6000.0
    assert len(res["expenses"]) == 3

def test_get_expenses_invalid_arg():
    res = execute_get_expenses(category=123) # type: ignore
    assert res["success"] is False
    assert res["error"] == "INVALID_ARGUMENT"

def test_get_budget_valid():
    res = execute_get_budget(category="Food", month="2026-09")
    assert res["success"] is True
    assert res["budget"] == 5000.0

def test_get_budget_missing():
    res = execute_get_budget(category="Food", month="2026-10")
    assert res["success"] is False
    assert res["error"] == "BUDGET_NOT_FOUND"

def test_calculate_total():
    res = execute_calculate_total(amounts=[250.5, 300, 449.5])
    assert res["success"] is True
    assert res["total"] == 1000.0

def test_calculate_total_invalid():
    res = execute_calculate_total(amounts=["invalid", 100]) # type: ignore
    assert res["success"] is False
    assert res["error"] == "INVALID_ARGUMENT"

def test_compare_budget_over():
    res = execute_compare_budget(spent=6000, budget=5000)
    assert res["success"] is True
    assert res["difference"] == 1000.0
    assert res["status"] == "OVER_BUDGET"
    assert res["percentage_used"] == 120.0

def test_compare_budget_within():
    res = execute_compare_budget(spent=2000, budget=3000)
    assert res["success"] is True
    assert res["difference"] == -1000.0
    assert res["status"] == "WITHIN_BUDGET"

def test_get_spending_by_category():
    res = execute_get_spending_by_category(month="2026-09")
    assert res["success"] is True
    assert res["highest_category"] == "Food"
    assert res["highest_amount"] == 6000.0
    assert res["grand_total"] == 20500.0
