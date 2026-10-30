import pytest
import sqlite3
from datetime import date
from agent.timeframe_parser import extract_timeframe, extract_category
from agent.llm_policy import LLMPolicy
from agent.observations import ObservationTracker
from agent.agent_loop import GoalBasedFinanceAgent
from mcp_server.tools.expenses import execute_get_expenses
from database.database import execute_query, DEFAULT_DB_PATH
from database.seed_data import seed_database

# 1. Test specific dates in all supported formats
@pytest.mark.parametrize("query,expected_iso", [
    ("How much did I spend on Food on 02-09-2026?", "2026-09-02"),
    ("Show me Food expenses on 02/09/2026", "2026-09-02"),
    ("Food spending on 02-September-2026", "2026-09-02"),
    ("Expenses for Food on 02 September 2026", "2026-09-02"),
    ("What was my spending on Food on 2026-09-02", "2026-09-02"),
    ("How much did I spend on Food on 2 September 2026", "2026-09-02"),
    ("Food costs on 2nd September 2026", "2026-09-02"),
    ("What was my spending on Food on 02-Sep-2026", "2026-09-02"),
])
def test_extract_timeframe_all_specific_date_formats(query, expected_iso):
    tf = extract_timeframe(query)
    assert tf["month"] is None
    assert tf["start_date"] == expected_iso
    assert tf["end_date"] == expected_iso
    assert tf["error"] is None if "error" in tf else True

# 2. Test fallback engine passes correct arguments to get_expenses
def test_fallback_engine_passes_correct_date_args_to_get_expenses():
    policy = LLMPolicy()
    tracker = ObservationTracker()
    action = policy.run_fallback_policy(
        question="How much did I spend on Food on 02-09-2026?",
        observation_tracker=tracker,
        iteration=1
    )

    assert action.action == "tool_call"
    assert action.tool_name == "get_expenses"
    assert action.arguments == {
        "category": "Food",
        "month": None,
        "start_date": "2026-09-02",
        "end_date": "2026-09-02"
    }

# 3. Test database query: retrieves ONLY records for specific date, not entire month
def test_database_query_filters_only_specific_date():
    seed_database(DEFAULT_DB_PATH)
    res = execute_get_expenses(
        category="Food",
        month=None,
        start_date="2026-09-02",
        end_date="2026-09-02"
    )

    assert res["success"] is True
    assert res["count"] == 1
    assert res["total"] == 2500.0
    assert len(res["expenses"]) == 1
    assert res["expenses"][0]["date"] == "2026-09-02"
    assert res["expenses"][0]["amount"] == 2500.0
    # Must NOT include other September records (total for month is 6000)
    assert res["total"] != 6000.0

# 4. Test multiple expenses on the same date
def test_database_multiple_expenses_on_same_date(tmp_path):
    test_db = str(tmp_path / "test_finance.db")
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT
        )
    """)
    cursor.execute("INSERT INTO expenses (date, category, amount, description) VALUES ('2026-09-02', 'Food', 500.0, 'Morning Coffee')")
    cursor.execute("INSERT INTO expenses (date, category, amount, description) VALUES ('2026-09-02', 'Food', 1200.0, 'Lunch')")
    cursor.execute("INSERT INTO expenses (date, category, amount, description) VALUES ('2026-09-05', 'Food', 800.0, 'Other day')")
    conn.commit()
    conn.close()

    res = execute_get_expenses(
        category="Food",
        start_date="2026-09-02",
        end_date="2026-09-02",
        db_path=test_db
    )

    assert res["success"] is True
    assert res["count"] == 2
    assert res["total"] == 1700.0
    assert len(res["expenses"]) == 2
    assert all(e["date"] == "2026-09-02" for e in res["expenses"])

# 5. Test date with no matching records
def test_database_no_matching_records():
    seed_database(DEFAULT_DB_PATH)
    res = execute_get_expenses(
        category="Food",
        month=None,
        start_date="2026-09-15",
        end_date="2026-09-15"
    )

    assert res["success"] is True
    assert res["count"] == 0
    assert res["total"] == 0.0
    assert res["expenses"] == []

# 6. Test fallback engine response when no records found
def test_fallback_engine_message_when_no_records_found():
    policy = LLMPolicy()
    tracker = ObservationTracker()
    tracker.add(
        iteration=1,
        tool_name="get_expenses",
        arguments={"category": "Food", "month": None, "start_date": "2026-09-15", "end_date": "2026-09-15"},
        result={"success": True, "category": "Food", "month": None, "start_date": "2026-09-15", "end_date": "2026-09-15", "expenses": [], "count": 0, "total": 0.0}
    )

    action = policy.run_fallback_policy(
        question="How much did I spend on Food on 15-09-2026?",
        observation_tracker=tracker,
        iteration=2
    )

    assert action.action == "final_answer"
    assert "No Food expenses found" in action.answer or "No expense records found" in action.answer
    assert "15-09-2026" in action.answer or "2026-09-15" in action.answer

# 7. Test invalid dates without crashing
def test_extract_timeframe_invalid_dates_without_crashing():
    # 31 February 2026 is invalid
    tf1 = extract_timeframe("How much did I spend on Food on 31-02-2026?")
    assert tf1["start_date"] is None
    assert tf1["end_date"] is None
    assert tf1.get("error") == "INVALID_DATE"

    policy = LLMPolicy()
    tracker = ObservationTracker()
    action = policy.run_fallback_policy(
        question="How much did I spend on Food on 31-02-2026?",
        observation_tracker=tracker,
        iteration=1
    )
    assert action.action == "final_answer"
    assert "not a valid calendar date" in action.answer.lower() or "invalid" in action.answer.lower()

# 8. Test month-only questions preserve existing behavior
def test_month_only_questions_preserved():
    tf_aug = extract_timeframe("How much was spent in August 2026?")
    assert tf_aug["month"] == "2026-08"
    assert tf_aug["start_date"] is None
    assert tf_aug["end_date"] is None

    tf_iso = extract_timeframe("Food spending for 2026-09")
    assert tf_iso["month"] == "2026-09"
    assert tf_iso["start_date"] is None
    assert tf_iso["end_date"] is None

# 9. Test date ranges and year-only queries preserved
def test_date_ranges_and_year_only_preserved():
    tf_range = extract_timeframe("Show expenses from 2026-09-01 to 2026-09-15")
    assert tf_range["start_date"] == "2026-09-01"
    assert tf_range["end_date"] == "2026-09-15"
    assert tf_range["month"] is None

    tf_year = extract_timeframe("How much did I spend in 2025?")
    assert tf_year["start_date"] == "2025-01-01"
    assert tf_year["end_date"] == "2025-12-31"

# 10. End-to-end agent loop with single-date expense inquiry
@pytest.mark.asyncio
async def test_end_to_end_agent_specific_date():
    seed_database(DEFAULT_DB_PATH)
    class OfflineFallbackPolicy(LLMPolicy):
        async def decide_next_action(self, question, tools_formatted, observation_tracker, iteration):
            return self.run_fallback_policy(question, observation_tracker, iteration)

    agent = GoalBasedFinanceAgent(llm_policy=OfflineFallbackPolicy())
    response = await agent.run("How much did I spend on Food on 02-09-2026?")

    assert "2,500.00" in response.answer
    assert "Food" in response.answer
    assert response.grounding_status == "VERIFIED"
    assert "get_expenses" in response.tools_used

