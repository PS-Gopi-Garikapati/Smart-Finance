import os
import json
import logging
import re
import httpx
from typing import List, Dict, Any, Optional
from agent.schemas import LLMAction
from agent.observations import ObservationTracker

logger = logging.getLogger("LLMPolicy")

SYSTEM_PROMPT = """You are a Goal-Based Smart Finance AI Agent.
Your goal is to answer the user's personal finance questions accurately based ONLY on real tool observations.

You have access to the following tools:
{tools_formatted}

RULES FOR TOOL SELECTION:
1. Break down the user's goal step-by-step.
2. Select ONE tool at a time to gather necessary expense or budget information.
3. If you need spending for a category/month/date range, call `get_expenses`.
4. If you need budget amounts, call `get_budget`.
5. If you need to calculate totals from multiple numbers, call `calculate_total`.
6. If you have both spent amount and budget amount, call `compare_budget`.
7. If asked for category comparisons or highest spending, call `get_spending_by_category`.
8. Once you have sufficient real tool results to answer the question, output `final_answer`.

CRITICAL SAFETY RULE:
- NEVER invent financial figures, spending totals, or budgets.
- Only state facts supported by the tool observations.

You MUST respond strictly in valid JSON using one of these two schemas:

Schema 1 (Tool Call):
{{
  "action": "tool_call",
  "tool_name": "<name>",
  "arguments": {{ ... }}
}}

Schema 2 (Final Answer):
{{
  "action": "final_answer",
  "answer": "<your grounded answer here>"
}}
"""

class LLMPolicy:
    """Decision-making policy layer interacting with Ollama and Pydantic validation."""

    def __init__(
        self,
        ollama_host: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.ollama_host = (ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    async def decide_next_action(
        self,
        question: str,
        tools_formatted: str,
        observation_tracker: ObservationTracker,
        iteration: int
    ) -> LLMAction:
        """Query LLM to dynamically decide the next tool call or final answer."""
        obs_text = observation_tracker.format_for_llm()
        
        prompt = (
            f"User Goal/Question: \"{question}\"\n\n"
            f"Previous Observations:\n{obs_text}\n\n"
            f"Current Iteration: {iteration}\n"
            f"What is your next action? Respond ONLY in valid JSON matching one of the required schemas."
        )

        sys_inst = SYSTEM_PROMPT.format(tools_formatted=tools_formatted)

        # Attempt call to local Ollama instance
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.ollama_host}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": [
                            {"role": "system", "content": sys_inst},
                            {"role": "user", "content": prompt}
                        ],
                        "stream": False,
                        "format": "json"
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("message", {}).get("content", "")
                    action = self._parse_and_validate_json(content)
                    if action:
                        return action
        except Exception as e:
            logger.warning(f"Ollama call failed or offline ({str(e)}). Engaging deterministic policy fallback.")

        # Fallback deterministic dynamic policy for offline environments/test suite
        return self._rule_based_fallback(question, observation_tracker, iteration)

    def _parse_and_validate_json(self, content: str) -> Optional[LLMAction]:
        """Validate raw JSON output using Pydantic."""
        try:
            clean_content = content.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            clean_content = clean_content.strip()

            parsed = json.loads(clean_content)
            return LLMAction.model_validate(parsed)
        except Exception as e:
            logger.error(f"Malformed LLM JSON output: {str(e)} -> '{content}'")
            return None

    def _rule_based_fallback(
        self,
        question: str,
        observation_tracker: ObservationTracker,
        iteration: int
    ) -> LLMAction:
        """Deterministic policy layer ensuring intelligent goal progress when Ollama is unavailable."""
        q_lower = question.lower()
        observations = observation_tracker.observations

        # Extract year if mentioned (e.g. 2025, 2024, 2026)
        year_match = re.search(r'\b(20\d{2})\b', question)
        year_str = year_match.group(1) if year_match else None

        start_date = None
        end_date = None
        month = None

        if "august" in q_lower:
            month = f"{year_str or '2026'}-08"
        elif "october" in q_lower:
            month = f"{year_str or '2026'}-10"
        elif "september" in q_lower:
            month = f"{year_str or '2026'}-09"
        elif year_str and year_str != "2026":
            start_date = f"{year_str}-01-01"
            end_date = f"{year_str}-12-31"
        else:
            month = "2026-09"

        # Identify target category if mentioned
        category = None
        for cat in ["food", "transport", "shopping", "bills", "entertainment"]:
            if cat in q_lower:
                category = cat.capitalize()
                break

        # Check existing tools executed
        executed_tools = [o.tool_name for o in observations]

        # Case A: Budget comparison question ("Did I exceed my food budget?")
        if "budget" in q_lower or "exceed" in q_lower or "over" in q_lower:
            if "get_expenses" not in executed_tools:
                return LLMAction(
                    action="tool_call",
                    tool_name="get_expenses",
                    arguments={"category": category or "Food", "month": month or "2026-09", "start_date": start_date, "end_date": end_date},
                    thought="Step 1: Retrieve actual expenses for the specified category and timeframe."
                )
            elif "get_budget" not in executed_tools:
                return LLMAction(
                    action="tool_call",
                    tool_name="get_budget",
                    arguments={"category": category or "Food", "month": month or "2026-09"},
                    thought="Step 2: Retrieve the budget amount for comparison."
                )
            elif "compare_budget" not in executed_tools:
                spent = 0.0
                budget = 0.0
                for obs in observations:
                    if obs.tool_name == "get_expenses" and obs.result.get("success"):
                        spent = obs.result.get("total", 0.0)
                    if obs.tool_name == "get_budget" and obs.result.get("success"):
                        budget = obs.result.get("budget", 0.0)

                return LLMAction(
                    action="tool_call",
                    tool_name="compare_budget",
                    arguments={"spent": spent, "budget": budget},
                    thought="Step 3: Compare actual spending against budget."
                )
            else:
                comp_obs = next(o for o in observations if o.tool_name == "compare_budget")
                res = comp_obs.result
                if res.get("status") == "OVER_BUDGET":
                    diff = res.get("difference", 0.0)
                    ans = f"Yes, you exceeded your {category or 'food'} budget by ₹{diff:,.2f}."
                else:
                    ans = f"No, your {category or 'food'} spending is within budget."

                return LLMAction(action="final_answer", answer=ans)

        # Case B: Highest spending category ("Which category has the highest spending?")
        if "highest" in q_lower or "most" in q_lower or "by category" in q_lower:
            if "get_spending_by_category" not in executed_tools:
                return LLMAction(
                    action="tool_call",
                    tool_name="get_spending_by_category",
                    arguments={"month": month},
                    thought="Retrieve category breakdown to find highest spending category."
                )
            else:
                obs = next(o for o in observations if o.tool_name == "get_spending_by_category")
                res = obs.result
                cat_highest = res.get("highest_category")
                amt_highest = res.get("highest_amount", 0.0)
                if cat_highest:
                    ans = f"The category with the highest spending is {cat_highest} with a total of ₹{amt_highest:,.2f}."
                else:
                    ans = f"No expense data is available for {month or 'that period'}."
                return LLMAction(action="final_answer", answer=ans)

        # Case C: Expense lookup ("add the total amount of food bill in 2025")
        if "get_expenses" not in executed_tools:
            return LLMAction(
                action="tool_call",
                tool_name="get_expenses",
                arguments={"category": category, "month": month, "start_date": start_date, "end_date": end_date},
                thought="Fetch expense entries from database for specified category/timeframe."
            )
        else:
            exp_obs = next(o for o in observations if o.tool_name == "get_expenses")
            res = exp_obs.result
            if not res.get("success"):
                return LLMAction(action="final_answer", answer=f"Error retrieving expenses: {res.get('message')}")
            
            expenses = res.get("expenses", [])
            total = res.get("total", 0.0)
            timeframe_label = f"in {year_str}" if (year_str and not month) else (f"in {month}" if month else "this period")

            if not expenses or res.get("count", 0) == 0:
                ans = f"No expense records were found for {category or 'that category'} {timeframe_label}."
            elif category:
                ans = f"You spent a total of ₹{total:,.2f} on {category} {timeframe_label}."
            else:
                ans = f"Your total spending {timeframe_label} across all categories was ₹{total:,.2f}."

            return LLMAction(action="final_answer", answer=ans)
