import pytest
from datetime import date
from agent.timeframe_parser import (
    extract_category,
    extract_timeframe,
    is_ambiguous_budget_question,
    SUPPORTED_CATEGORIES
)
from agent.llm_policy import LLMPolicy
from agent.observations import ObservationTracker
from agent.agent_loop import GoalBasedFinanceAgent

def test_extract_category_all_types():
    assert extract_category("How much did I spend on food?") == "Food"
    assert extract_category("Show my transport costs") == "Transport"
    assert extract_category("Any shopping receipts?") == "Shopping"
    assert extract_category("What are my utility bills?") == "Bills"
    assert extract_category("Entertainment spending in September") == "Entertainment"
    assert extract_category("Medical checkup in healthcare") == "Healthcare"
    assert extract_category("Summer vacation travel expenses") == "Travel"
    assert extract_category("How much did I spend overall?") is None

def test_extract_timeframe_explicit_month():
    tf = extract_timeframe("How much was spent in August 2026?")
    assert tf["month"] == "2026-08"

    tf_iso = extract_timeframe("Check expenses for 2026-09")
    assert tf_iso["month"] == "2026-09"

    tf_oct = extract_timeframe("Expenses in October 2026")
    assert tf_oct["month"] == "2026-10"

def test_extract_timeframe_relative_months():
    ref = date(2026, 9, 15)
    tf_this = extract_timeframe("How much did I spend this month?", reference_date=ref)
    assert tf_this["month"] == "2026-09"

    tf_last = extract_timeframe("Show my spending from last month", reference_date=ref)
    assert tf_last["month"] == "2026-08"

def test_extract_timeframe_custom_date_range():
    tf = extract_timeframe("Show expenses from 2026-09-01 to 2026-09-15")
    assert tf["start_date"] == "2026-09-01"
    assert tf["end_date"] == "2026-09-15"
    assert tf["month"] is None

def test_extract_timeframe_year_only():
    tf = extract_timeframe("How much did I spend in 2025?")
    assert tf["start_date"] == "2025-01-01"
    assert tf["end_date"] == "2025-12-31"

def test_ambiguous_budget_question_detected():
    # When user asks if they exceeded budget without naming category
    assert is_ambiguous_budget_question("Did I exceed my budget?") is True
    assert is_ambiguous_budget_question("Am I over budget this month?") is True

    # When category is explicitly stated
    assert is_ambiguous_budget_question("Did I exceed my food budget?") is False
    assert is_ambiguous_budget_question("Did I exceed my transport budget?") is False

@pytest.mark.asyncio
async def test_agent_clarification_on_ambiguous_budget():
    """Verify agent asks for clarification rather than assuming Food."""
    policy = LLMPolicy()
    tracker = ObservationTracker()
    action = policy.run_fallback_policy(
        question="Did I exceed my budget?",
        observation_tracker=tracker,
        iteration=1
    )

    assert action.action == "final_answer"
    assert "specify which budget category" in action.answer.lower() or "clarif" in action.answer.lower() or "available categories" in action.answer.lower()
    # Ensure it did NOT silently assume Food
    assert "food" not in action.answer.lower() or "food, transport" in action.answer.lower()
