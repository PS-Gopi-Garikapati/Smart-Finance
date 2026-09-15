import pytest
from database.seed_data import seed_database
from mcp_client.client import FinanceMCPClient
from agent.agent_loop import GoalBasedFinanceAgent
from agent.llm_policy import LLMPolicy
from agent.schemas import LLMAction, AgentResponse

@pytest.fixture(autouse=True)
def setup_db():
    seed_database()

@pytest.mark.asyncio
async def test_unknown_tool_handling():
    """Requirement 16: Return UNKNOWN_TOOL error when non-existent tool is called."""
    client = FinanceMCPClient()
    res = await client.invoke_tool("non_existent_tool_xyz", {})
    
    assert res["success"] is False
    assert res["error"] == "UNKNOWN_TOOL"
    assert "does not exist" in res["message"]

@pytest.mark.asyncio
async def test_invalid_argument_handling():
    """Requirement 16: Validate tool arguments before execution."""
    client = FinanceMCPClient()
    res = await client.invoke_tool("calculate_total", {"amounts": ["invalid_numeric_value"]})
    
    assert res["success"] is False
    assert res["error"] == "INVALID_ARGUMENT"

@pytest.mark.asyncio
async def test_missing_partial_data_scenario():
    """Requirement 20: Demonstrate missing/partial-data handling without inventing facts."""
    agent = GoalBasedFinanceAgent()
    resp = await agent.run("How much did I spend in October 2026?")
    
    assert resp.grounding_status == "VERIFIED"
    assert "No expense records" in resp.answer or "not found" in resp.answer or "0" in resp.answer

@pytest.mark.asyncio
async def test_malformed_llm_json_recovery():
    """Requirement 16 & 20: Safe handling of malformed LLM JSON string."""
    policy = LLMPolicy()
    action = policy._parse_and_validate_json("INVALID NON-JSON OUTPUT")
    assert action is None

    from agent.observations import ObservationTracker
    fallback_action = policy._rule_based_fallback(
        question="How much did I spend on food?",
        observation_tracker=ObservationTracker(),
        iteration=1
    )
    assert fallback_action.action == "tool_call"
    assert fallback_action.tool_name == "get_expenses"

@pytest.mark.asyncio
async def test_max_iteration_limit():
    """Requirement 11 & 20: Ensure loop stops safely at MAX_ITERATIONS limit."""
    class EndlessPolicy(LLMPolicy):
        async def decide_next_action(self, question, tools_formatted, observation_tracker, iteration):
            return LLMAction(
                action="tool_call",
                tool_name="get_expenses",
                arguments={"category": "Food", "month": "2026-09"},
                thought="Looping test..."
            )

    agent = GoalBasedFinanceAgent(llm_policy=EndlessPolicy())
    resp = await agent.run("Indefinite loop test question")

    assert resp.iterations == 5
    assert "maximum iterations" in resp.answer.lower() or resp.grounding_status in ["VERIFIED", "UNSUPPORTED_CLAIMS"]
