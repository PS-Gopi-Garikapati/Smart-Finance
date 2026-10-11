import pytest
import httpx
from typing import Optional
from agent.schemas import LLMAction, AgentResponse
from agent.llm_policy import LLMPolicy
from agent.agent_loop import GoalBasedFinanceAgent
from agent.observations import ObservationTracker
from database.seed_data import seed_database

@pytest.fixture(autouse=True)
def setup_db():
    seed_database()

class MockedLLMPolicy(LLMPolicy):
    """Custom stub LLM policy returning pre-scripted responses per iteration or observation state."""
    def __init__(self, action_sequence=None):
        super().__init__()
        self.action_sequence = action_sequence or []
        self.call_count = 0

    async def decide_next_action(
        self,
        question: str,
        tools_formatted: str,
        observation_tracker: ObservationTracker,
        iteration: int
    ) -> LLMAction:
        if self.call_count < len(self.action_sequence):
            action = self.action_sequence[self.call_count]
            self.call_count += 1
            return action
        return LLMAction(action="final_answer", answer="Default mock answer.")

@pytest.mark.asyncio
async def test_different_model_responses_select_different_tools():
    """Prove different model responses select different tools."""
    policy1 = MockedLLMPolicy([
        LLMAction(action="tool_call", tool_name="get_expenses", arguments={"category": "Food", "month": "2026-09"}),
        LLMAction(action="final_answer", answer="Spent 6000 on food.")
    ])
    agent1 = GoalBasedFinanceAgent(llm_policy=policy1)
    resp1 = await agent1.run("Food spending query")
    assert resp1.tools_used == ["get_expenses"]

    policy2 = MockedLLMPolicy([
        LLMAction(action="tool_call", tool_name="get_spending_by_category", arguments={"month": "2026-09"}),
        LLMAction(action="final_answer", answer="Highest spending category is Food.")
    ])
    agent2 = GoalBasedFinanceAgent(llm_policy=policy2)
    resp2 = await agent2.run("Category spending query")
    assert resp2.tools_used == ["get_spending_by_category"]

@pytest.mark.asyncio
async def test_agent_selects_tool_based_on_observations():
    """Prove the agent can select next tool dynamically based on observations."""
    class DynamicObservationPolicy(LLMPolicy):
        async def decide_next_action(
            self, question: str, tools_formatted: str, observation_tracker: ObservationTracker, iteration: int
        ) -> LLMAction:
            obs = observation_tracker.observations
            if not obs:
                # Step 1: Call get_expenses
                return LLMAction(action="tool_call", tool_name="get_expenses", arguments={"category": "Food", "month": "2026-09"})
            
            # Step 2: Check observation result to dynamically choose next tool
            exp_obs = next((o for o in obs if o.tool_name == "get_expenses"), None)
            if exp_obs and exp_obs.result.get("total") == 6000.0:
                # Based on spending observation of 6000, retrieve budget to compare
                return LLMAction(action="tool_call", tool_name="get_budget", arguments={"category": "Food", "month": "2026-09"})

            return LLMAction(action="final_answer", answer="Completed based on observations.")

    agent = GoalBasedFinanceAgent(llm_policy=DynamicObservationPolicy())
    resp = await agent.run("Dynamic observation decision test")

    assert "get_expenses" in resp.tools_used
    assert "get_budget" in resp.tools_used

@pytest.mark.asyncio
async def test_agent_finishes_without_unnecessary_tools():
    """Prove the agent can finish without unnecessary tool calls once sufficient evidence is gathered."""
    policy = MockedLLMPolicy([
        LLMAction(action="tool_call", tool_name="get_expenses", arguments={"category": "Food", "month": "2026-09"}),
        LLMAction(action="final_answer", answer="Total spent on Food in 2026-09 is ₹6,000.00.")
    ])
    agent = GoalBasedFinanceAgent(llm_policy=policy)
    resp = await agent.run("What did I spend on food?")

    assert resp.iterations == 2
    assert resp.tools_used == ["get_expenses"]
    assert "compare_budget" not in resp.tools_used
    assert resp.grounding_status == "VERIFIED"

@pytest.mark.asyncio
async def test_invalid_unknown_tool_selection_repaired():
    """Prove an invalid/unknown tool selection can be repaired."""
    policy = MockedLLMPolicy([
        # Iteration 1: Attempt invalid non-existent tool
        LLMAction(action="tool_call", tool_name="invalid_finance_tool_xyz", arguments={}),
        # Iteration 2: After receiving UNKNOWN_TOOL observation error, retry with valid tool
        LLMAction(action="tool_call", tool_name="get_expenses", arguments={"category": "Food", "month": "2026-09"}),
        # Iteration 3: Final answer
        LLMAction(action="final_answer", answer="Successfully recovered and fetched food expenses of 6000.")
    ])

    agent = GoalBasedFinanceAgent(llm_policy=policy)
    resp = await agent.run("Repair invalid tool test")

    assert "invalid_finance_tool_xyz" in resp.tools_used
    assert "get_expenses" in resp.tools_used
    assert resp.grounding_status == "VERIFIED"

@pytest.mark.asyncio
async def test_agent_replans_after_receiving_tool_observation():
    """Prove the agent can re-plan after receiving a tool observation."""
    class ReplanningPolicy(LLMPolicy):
        async def decide_next_action(
            self, question: str, tools_formatted: str, observation_tracker: ObservationTracker, iteration: int
        ) -> LLMAction:
            obs = observation_tracker.observations
            if iteration == 1:
                return LLMAction(action="tool_call", tool_name="get_expenses", arguments={"category": "Food", "month": "2026-09"})
            elif iteration == 2:
                # Re-plan: Instead of stopping, decide to query overall category analytics
                return LLMAction(action="tool_call", tool_name="get_spending_by_category", arguments={"month": "2026-09"})
            else:
                return LLMAction(action="final_answer", answer="Re-planned analysis complete.")

    agent = GoalBasedFinanceAgent(llm_policy=ReplanningPolicy())
    resp = await agent.run("Re-planning test question")

    assert resp.tools_used == ["get_expenses", "get_spending_by_category"]

def test_deterministic_fallback_tested_separately_as_degraded_mode():
    """Test the deterministic fallback policy separately and verify degraded mode."""
    policy = LLMPolicy()
    tracker = ObservationTracker()

    fallback_action = policy.run_fallback_policy(
        question="Did I exceed my food budget?",
        observation_tracker=tracker,
        iteration=1
    )

    assert fallback_action.action == "tool_call"
    assert fallback_action.tool_name == "get_expenses"
    assert fallback_action.arguments.get("category") == "Food"

@pytest.mark.asyncio
async def test_real_ollama_integration_if_service_active():
    """Real Ollama integration test executed only when local Ollama service is active."""
    policy = LLMPolicy()
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{policy.ollama_host}/api/tags")
            if resp.status_code != 200:
                pytest.skip("Local Ollama service returned non-200 status.")
    except Exception:
        pytest.skip("Local Ollama instance not running or unreachable at " + policy.ollama_host)

    # If Ollama is running, execute real prompt
    tracker = ObservationTracker()
    action = await policy.decide_next_action(
        question="How much did I spend on food in 2026-09?",
        tools_formatted="Tool: `get_expenses`\nParameters: (category: str, month: str)",
        observation_tracker=tracker,
        iteration=1
    )
    assert action.action in ["tool_call", "final_answer"]
    if action.action == "tool_call":
        assert action.tool_name == "get_expenses"
