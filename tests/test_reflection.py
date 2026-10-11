import pytest
from reflection.evaluator import ReflectionEvaluator
from reflection.schemas import ReflectionResult

def test_reflection_verified():
    evaluator = ReflectionEvaluator()
    obs = [
        {
            "iteration": 1,
            "tool_name": "get_expenses",
            "result": {"success": True, "category": "Food", "month": "2026-09", "total": 6000.0}
        },
        {
            "iteration": 2,
            "tool_name": "get_budget",
            "result": {"success": True, "category": "Food", "month": "2026-09", "budget": 5000.0}
        },
        {
            "iteration": 3,
            "tool_name": "compare_budget",
            "result": {"success": True, "spent": 6000.0, "budget": 5000.0, "difference": 1000.0, "status": "OVER_BUDGET"}
        }
    ]

    draft = "You spent ₹6,000 on food, exceeding your ₹5,000 budget by ₹1,000."
    res = evaluator.evaluate(draft, obs)

    assert res.grounding_status == "VERIFIED"
    assert res.verified_answer == draft
    assert isinstance(res.model_dump(), dict)

def test_reflection_detect_unsupported_claims():
    evaluator = ReflectionEvaluator()
    obs = [
        {
            "iteration": 1,
            "tool_name": "get_expenses",
            "result": {"success": True, "category": "Food", "month": "2026-09", "total": 6000.0}
        }
    ]

    # Draft answer invents an ungrounded figure of 8000
    draft = "You spent ₹8,000 on food this month."
    res = evaluator.evaluate(draft, obs)

    assert res.grounding_status == "UNSUPPORTED_CLAIMS"
    assert res.verified_answer != draft
    assert "6,000" in res.verified_answer or "6000" in res.verified_answer

def test_reflection_incorrect_amount():
    """Verify reflection catches fabricated amount and repairs it."""
    evaluator = ReflectionEvaluator()
    obs = [
        {
            "iteration": 1,
            "tool_name": "get_expenses",
            "result": {"success": True, "category": "Transport", "month": "2026-09", "total": 2000.0, "count": 2}
        }
    ]
    draft = "You spent ₹4,500 on transport in 2026-09."
    res = evaluator.evaluate(draft_answer=draft, observations=obs)

    assert res.grounding_status == "UNSUPPORTED_CLAIMS"
    assert "2,000" in res.verified_answer or "2000" in res.verified_answer
    assert "Transport" in res.verified_answer

def test_reflection_wrong_category():
    """Verify reflection detects category contradiction."""
    evaluator = ReflectionEvaluator()
    obs = [
        {
            "iteration": 1,
            "tool_name": "get_expenses",
            "result": {"success": True, "category": "Food", "month": "2026-09", "total": 6000.0}
        }
    ]
    # Observation is Food, but draft claims Shopping
    draft = "You spent ₹6,000 on shopping in 2026-09."
    res = evaluator.evaluate(draft, obs)

    assert res.grounding_status == "CONTRADICTION"
    assert "Food" in res.verified_answer
    assert any("contradiction" in c.lower() for c in res.contradictions)

def test_reflection_incorrect_budget_status():
    """Verify reflection catches contradicting budget status."""
    evaluator = ReflectionEvaluator()
    obs = [
        {
            "iteration": 1,
            "tool_name": "compare_budget",
            "result": {"success": True, "spent": 6000.0, "budget": 5000.0, "difference": 1000.0, "status": "OVER_BUDGET"}
        }
    ]
    # Observation says OVER_BUDGET, but draft falsely claims within budget
    draft = "You spent ₹6,000 on food, which is within budget."
    res = evaluator.evaluate(draft, obs)

    assert res.grounding_status == "CONTRADICTION"
    assert "exceeding" in res.verified_answer or "OVER_BUDGET" in str(res.claims_checked)

def test_reflection_incorrect_date():
    """Verify reflection detects timeframe mismatch."""
    evaluator = ReflectionEvaluator()
    obs = [
        {
            "iteration": 1,
            "tool_name": "get_expenses",
            "result": {"success": True, "category": "Food", "month": "2026-09", "total": 6000.0}
        }
    ]
    draft = "You spent ₹6,000 on food in 2026-10."
    res = evaluator.evaluate(draft, obs)

    assert res.grounding_status == "CONTRADICTION"
    assert "2026-09" in res.verified_answer

def test_reflection_missing_evidence():
    """Verify reflection handles empty observations when draft asserts financial numbers."""
    evaluator = ReflectionEvaluator()
    obs = []
    draft = "You spent ₹5,000 on groceries."
    res = evaluator.evaluate(draft, obs)

    assert res.grounding_status == "MISSING_EVIDENCE"
    assert "No tool observations" in res.verified_answer or "not retrieved" in res.verified_answer

def test_reflection_malformed_observation():
    """Verify reflection safely handles malformed observation items."""
    evaluator = ReflectionEvaluator()
    obs = [
        {"iteration": 1, "tool_name": "get_expenses", "result": None},
        "not_a_valid_dict"
    ]
    draft = "You spent ₹6,000."
    res = evaluator.evaluate(draft, obs)

    assert res.grounding_status == "MALFORMED_OBSERVATION"
    assert isinstance(res.verified_answer, str)

def test_reflection_safe_error_handling():
    """Verify evaluator never crashes on empty, null, or malformed inputs."""
    evaluator = ReflectionEvaluator()
    res1 = evaluator.evaluate(draft_answer="", observations=None)
    assert res1.grounding_status == "MISSING_EVIDENCE"

    res2 = evaluator.evaluate(draft_answer="Reached maximum iterations (5) without completing all tool steps.")
    assert res2.grounding_status == "VERIFIED"
