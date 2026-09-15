import pytest
from database.seed_data import seed_database
from agent.agent_loop import GoalBasedFinanceAgent

@pytest.fixture(autouse=True)
def setup_db():
    seed_database()

@pytest.mark.asyncio
async def test_agent_budget_exceeded_flow():
    agent = GoalBasedFinanceAgent()
    resp = await agent.run("Did I exceed my food budget?")
    
    assert resp.grounding_status == "VERIFIED"
    assert "get_expenses" in resp.tools_used
    assert "get_budget" in resp.tools_used
    assert "compare_budget" in resp.tools_used
    assert "exceeded" in resp.answer.lower() or "over" in resp.answer.lower() or "1,000" in resp.answer

@pytest.mark.asyncio
async def test_agent_highest_spending_category():
    agent = GoalBasedFinanceAgent()
    resp = await agent.run("Which category has the highest spending?")
    
    assert resp.grounding_status == "VERIFIED"
    assert "get_spending_by_category" in resp.tools_used
    assert "Food" in resp.answer

@pytest.mark.asyncio
async def test_agent_food_expenses_lookup():
    agent = GoalBasedFinanceAgent()
    resp = await agent.run("How much did I spend on food this month?")
    
    assert resp.grounding_status == "VERIFIED"
    assert "get_expenses" in resp.tools_used
    assert "6,000" in resp.answer or "6000" in resp.answer
