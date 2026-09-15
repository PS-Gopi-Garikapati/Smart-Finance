import pytest
from mcp_client.client import FinanceMCPClient
from mcp_client.tool_discovery import ToolDiscoverer
from database.seed_data import seed_database

@pytest.fixture(autouse=True)
def setup_test_db():
    seed_database()

@pytest.mark.asyncio
async def test_mcp_handshake_and_discovery():
    client = FinanceMCPClient()
    discoverer = ToolDiscoverer(client)
    tools = await discoverer.discover_tools()
    
    tool_names = [t["name"] for t in tools]
    assert "get_expenses" in tool_names
    assert "get_budget" in tool_names
    assert "calculate_total" in tool_names
    assert "compare_budget" in tool_names
    assert "get_spending_by_category" in tool_names

@pytest.mark.asyncio
async def test_mcp_tool_invocation_get_expenses():
    client = FinanceMCPClient()
    res = await client.invoke_tool("get_expenses", {"category": "Food", "month": "2026-09"})
    
    assert res["success"] is True
    assert res["total"] == 6000.0
    assert len(res["expenses"]) == 3

@pytest.mark.asyncio
async def test_mcp_tool_invocation_compare_budget():
    client = FinanceMCPClient()
    res = await client.invoke_tool("compare_budget", {"spent": 6000.0, "budget": 5000.0})
    
    assert res["success"] is True
    assert res["difference"] == 1000.0
    assert res["status"] == "OVER_BUDGET"
    assert res["percentage_used"] == 120.0
