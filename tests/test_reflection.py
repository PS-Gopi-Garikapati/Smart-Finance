import pytest
from reflection.evaluator import ReflectionEvaluator

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
