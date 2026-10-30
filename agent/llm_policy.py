#Decides the next action using Ollama or fallback rules.
#Reads environment variables, such as the Ollama model name.
#Reads the AI's JSON response.
#Records decisions and errors.
import os
import json
import logging
import re
from typing import List, Dict, Any, Optional
#Sends HTTP requests to the Ollama service.
import httpx
from agent.schemas import LLMAction
from agent.observations import ObservationTracker
from agent.timeframe_parser import (
    extract_category,
    extract_timeframe,
    is_ambiguous_budget_question,
    SUPPORTED_CATEGORIES
)

__all__ = [
    "LLMPolicy",
    "extract_category",
    "extract_timeframe",
    "is_ambiguous_budget_question",
    "SUPPORTED_CATEGORIES"
]

logger = logging.getLogger("LLMPolicy")
#The System Prompt is a set of instructions 
#given to the LLM that tells it how to 
#behave in your Smart Finance project.
#It guides the LLM on which MCP tools to use, 
#how to make decisions,
#and how to return accurate answers
#in the required JSON format.
SYSTEM_PROMPT = """You are an intelligent Goal-Based Financial AI Assistant.
Your goal is to answer the user's financial inquiries accurately using the available tools via Model Context Protocol (MCP).

AVAILABLE TOOLS:
{tools_formatted}

DECISION-MAKING GUIDELINES:
1. Break down the user's question into logical steps.
2. If asking about expense amounts, call `get_expenses`.
3. If asking about budget limits or comparison, retrieve expenses and budget first, then call `compare_budget`.
4. If asking which category has highest spending or overall category breakdown, call `get_spending_by_category`.
5. If calculating custom numerical sums, call `calculate_total`.
6. If asking about policies, receipts, taxes, or credit card terms, call `search_documents`.
7. Inspect the observations returned in previous iterations to decide your next action (dynamic replanning).
8. If the user request is ambiguous (e.g. asking if budget was exceeded without naming a category), output `final_answer` asking for clarification.
9. When you have gathered sufficient factual tool observations, output `final_answer`.

CRITICAL GROUNDING RULES:
- NEVER invent financial figures or unobserved facts.
- Answer must be strictly supported by the tool observations.

You MUST respond strictly in valid JSON matching one of the two formats:

Format 1 (Tool Call):
{{
  "action": "tool_call",
  "tool_name": "<exact_tool_name>",
  "arguments": {{ ... }},
  "thought": "<brief step reasoning>"
}}

Format 2 (Final Answer):
{{
  "action": "final_answer",
  "answer": "<grounded response to user>",
  "thought": "<conclusion reasoning>"
}}
"""

VALID_TOOLS = [
    "get_expenses",#retrieves expense records.
    "get_budget",#retrieves budget information.
    "calculate_total",
    "compare_budget",#compares spending with a budget.
    "get_spending_by_category",
    "search_documents"#searches financial documents.
]

class LLMPolicy:
    """Model-mediated decision policy with Ollama integration and bounded degraded fallback."""

    def __init__(
        self,
        ollama_host: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        timeout: float = 15.0
    ):
        self.ollama_host = (ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        #The temperature setting controls how variable the model's responses
        self.temperature = float(os.getenv("OLLAMA_TEMPERATURE", str(temperature)))
        #while the timeout specifies how long the request can wait before timing out.
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT", str(timeout)))

    #This is the main decision-making function.
    #It prepares the user question, available tools,
    #and previous observations, then sends them to Ollama.
    async def decide_next_action(
        self,
        question: str,
        tools_formatted: str,
        observation_tracker: ObservationTracker,
        iteration: int
    ) -> LLMAction:
        """
        Query LLM to dynamically decide the next action based on current observations.
        Executes bounded retry/repair if model JSON is malformed.
        Falls back to degraded rule-based policy if Ollama is unavailable.
        """
        obs_text = observation_tracker.format_for_llm()
        sys_inst = SYSTEM_PROMPT.format(tools_formatted=tools_formatted)
#user prompt
#The User Prompt provides the LLM with the user's actual question
#the observation history from previous tool calls, and the instruction to select the next action.
#it helps the LLM decide which MCP tool to call next or whether to provide the final answer.
        user_content = (
            f"User Goal/Question: \"{question}\"\n\n"
            f"Observation History (Iteration {iteration} of 5):\n{obs_text}\n\n"
            f"Select your next action. Respond ONLY in valid JSON matching Schema 1 or Schema 2."
        )

        messages = [
            {"role": "system", "content": sys_inst},
            {"role": "user", "content": user_content}
        ]

        # 1. Attempt model-backed decision via Ollama
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.ollama_host}/api/chat",
            #This sends the instructions and question to the local Ollama API.
            #Let the AI decide dynamically which action to take next.
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": self.temperature
                        }
                    }
                )

                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("message", {}).get("content", "")
                    action = self._parse_and_validate_json(content)
                    if action:
                        logger.info(f"Ollama selected action: {action.action} (tool: {action.tool_name})")
                        return action

                    # Bounded repair: retry once if model output was malformed
                    logger.warning("Ollama returned malformed JSON or invalid schema. Attempting bounded repair prompt.")
                    repaired_action = await self._repair_model_output(client, messages, content)
                    if repaired_action:
                        return repaired_action

        except Exception as e:
            logger.warning(
                f"Ollama/LLM service unavailable ({str(e)}). "
                f"Switching to DEGRADED OFFLINE FALLBACK MODE."
            )

        # 2. Degraded offline fallback mode
        return self._rule_based_fallback(question, observation_tracker, iteration)

    async def _repair_model_output(
        self,
        client: httpx.AsyncClient,
        original_messages: List[Dict[str, str]],
        bad_content: str
    ) -> Optional[LLMAction]:
        """Bounded repair attempt sending error feedback back to Ollama."""
        repair_messages = list(original_messages)
        repair_messages.append({"role": "assistant", "content": bad_content})
        repair_messages.append({
            "role": "user",
            "content": (
                "Your previous response was not valid JSON matching the schema. "
                "Output strictly a JSON object with 'action' ('tool_call' or 'final_answer') "
                "and required fields ('tool_name' and 'arguments' for tool_call, or 'answer' for final_answer)."
            )
        })

        try:
            resp = await client.post(
                f"{self.ollama_host}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": repair_messages,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.0}
                }
            )
            if resp.status_code == 200:
                repaired_content = resp.json().get("message", {}).get("content", "")
                return self._parse_and_validate_json(repaired_content)
        except Exception as e:
            logger.error(f"Bounded repair request failed: {e}")

        return None

    def _parse_and_validate_json(self, content: str) -> Optional[LLMAction]:
        """Validate raw JSON string into Pydantic LLMAction model."""
        if not content or not content.strip():
            return None

        clean_content = content.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content[7:]
        elif clean_content.startswith("```"):
            clean_content = clean_content[3:]
        if clean_content.endswith("```"):
            clean_content = clean_content[:-3]
        clean_content = clean_content.strip()

        try:
            parsed = json.loads(clean_content)
            action = LLMAction.model_validate(parsed)
            # Validate tool_name if action is tool_call
            if action.action == "tool_call" and action.tool_name not in VALID_TOOLS:
                logger.warning(f"Model proposed unknown tool '{action.tool_name}'.")
            return action
        except Exception as e:
            logger.debug(f"JSON validation failed: {e} for content '{clean_content}'")
            return None

    def run_fallback_policy(
        self,
        question: str,
        observation_tracker: ObservationTracker,
        iteration: int
    ) -> LLMAction:
        """Public entrypoint for executing and testing the degraded offline fallback policy."""
        return self._rule_based_fallback(question, observation_tracker, iteration)

    def _rule_based_fallback(
        self,
        question: str,
        observation_tracker: ObservationTracker,
        iteration: int
    ) -> LLMAction:
        """
        DEGRADED OFFLINE FALLBACK POLICY:
        Dynamic policy utilized when Ollama service is unavailable.
        Uses observation state tracking, dynamic timeframe/category parsing,
        clarification checks for ambiguous prompts, and observation-driven error recovery.
        """
        logger.info(f"[DEGRADED OFFLINE FALLBACK] Iteration {iteration} for question: '{question}'")
        q_lower = question.lower()
        observations = observation_tracker.observations

        # Dynamic Category & Timeframe Extraction (completely data-driven, no hardcoded dates)
        category = extract_category(question)
        tf = extract_timeframe(question)
        month = tf.get("month")
        start_date = tf.get("start_date")
        end_date = tf.get("end_date")
        tf_label = tf.get("timeframe_label", "the requested timeframe")

        # Handle invalid date inputs safely
        if tf.get("error") == "INVALID_DATE" or tf.get("invalid_date"):
            inv = tf.get("invalid_date", "provided")
            return LLMAction(
                action="final_answer",
                answer=f"The date '{inv}' is not a valid calendar date. Please check the date and try again.",
                thought="Clarification requested: user provided an invalid calendar date."
            )

        budget_intent = any(k in q_lower for k in ("budget", "exceed", "over"))
        analytics_intent = any(k in q_lower for k in ("highest", "most", "by category"))
        if start_date or end_date:
            if budget_intent:
                return LLMAction(
                    action="final_answer",
                    answer=(
                        "Budget comparisons are available by calendar month. "
                        "Please specify a month instead of a date range or specific date."
                    ),
                    thought="Clarification requested because the budget tool requires a calendar month."
                )
            if analytics_intent:
                return LLMAction(
                    action="final_answer",
                    answer=(
                        "Category breakdowns are available by calendar month. "
                        "Please specify a month instead of a date range or specific date."
                    ),
                    thought="Clarification requested because the analytics tool requires a calendar month."
                )

        # 1. Observation-Driven Error Repair: Check if previous tool call encountered an error
        if observations:
            last_obs = observations[-1]
            last_res = last_obs.result
            if isinstance(last_res, dict) and not last_res.get("success"):
                err = last_res.get("error")
                if err == "BUDGET_NOT_FOUND" and last_obs.tool_name == "get_budget":
                    missing_category = last_obs.arguments.get("category") or category or "requested"
                    missing_month = last_obs.arguments.get("month") or month
                    period = f" for {missing_month}" if missing_month else f" {tf_label}"
                    return LLMAction(
                        action="final_answer",
                        answer=(
                            f"I can't determine whether you exceeded your {missing_category} budget{period} "
                            f"because no {missing_category} budget is configured for that period."
                        ),
                        thought="Budget comparison stopped because the requested budget was not configured."
                    )
                if err == "UNKNOWN_TOOL":
                    logger.info(f"Observation error detected: '{last_obs.tool_name}' is UNKNOWN_TOOL. Repairing tool selection.")
                    if "budget" in q_lower or "exceed" in q_lower:
                        return LLMAction(
                            action="tool_call",
                            tool_name="get_expenses",
                            arguments={
                                "category": category or "Food",
                                "month": month,
                                "start_date": start_date,
                                "end_date": end_date
                            },
                            thought=f"Tool repair: 'get_expenses' selected after invalid tool error for {tf_label}."
                        )
                    elif "highest" in q_lower or "category" in q_lower:
                        return LLMAction(
                            action="tool_call",
                            tool_name="get_spending_by_category",
                            arguments={"month": month},
                            thought=f"Tool repair: 'get_spending_by_category' selected after invalid tool error for {tf_label}."
                        )
                    else:
                        return LLMAction(
                            action="tool_call",
                            tool_name="get_expenses",
                            arguments={
                                "category": category,
                                "month": month,
                                "start_date": start_date,
                                "end_date": end_date
                            },
                            thought=f"Tool repair: default to 'get_expenses' following invalid tool observation for {tf_label}."
                        )

        # 2. Ambiguity Check: Do not assume Food or a random category without evidence
        if is_ambiguous_budget_question(question):
            return LLMAction(
                action="final_answer",
                answer=(
                    "Could you please specify which budget category you would like to check? "
                    f"Available categories include: {', '.join(SUPPORTED_CATEGORIES)}."
                ),
                thought="Clarification request: budget inquiry omitted target category."
            )

        # Track executed successful tools
        executed_tools = [
            o.tool_name for o in observations
            if isinstance(o.result, dict) and o.result.get("success")
        ]

        # 3. RAG / Unstructured Document Inquiry
        doc_keywords = [
            "policy", "document", "receipt", "tax", "fee", "deduction",
            "warranty", "rule", "reimbursement", "credit card", "apple", "terms"
        ]
        if any(k in q_lower for k in doc_keywords) and not any(k in q_lower for k in ["spent", "budget", "exceed", "highest"]):
            if "search_documents" not in executed_tools:
                return LLMAction(
                    action="tool_call",
                    tool_name="search_documents",
                    arguments={"query": question, "top_k": 3},
                    thought="Execute RAG vector similarity search for document intelligence."
                )
            else:
                doc_obs = next(o for o in observations if o.tool_name == "search_documents")
                res = doc_obs.result
                results = res.get("results", [])
                if results:
                    top_match = results[0]
                    ans = f"Based on financial document '{top_match.get('title')}': {top_match.get('content')}"
                else:
                    ans = "No relevant financial documents found matching your search query."
                return LLMAction(action="final_answer", answer=ans, thought="Document answer synthesized.")

        # 4. Quantitative Budget Comparison ("Did I exceed my food budget?")
        if budget_intent:
            target_cat = category or "Food"

            if "get_expenses" not in executed_tools:
                return LLMAction(
                    action="tool_call",
                    tool_name="get_expenses",
                    arguments={
                        "category": target_cat,
                        "month": month,
                        "start_date": start_date,
                        "end_date": end_date
                    },
                    thought=f"Step 1: Retrieve actual spending for {target_cat} {tf_label}."
                )
            elif "get_budget" not in executed_tools:
                return LLMAction(
                    action="tool_call",
                    tool_name="get_budget",
                    arguments={"category": target_cat, "month": month},
                    thought=f"Step 2: Retrieve configured budget for {target_cat} {tf_label}."
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
                    ans = f"Yes, you exceeded your {target_cat} budget by ₹{diff:,.2f}."
                else:
                    ans = f"No, your {target_cat} spending is within budget."
                return LLMAction(action="final_answer", answer=ans, thought="Budget comparison completed.")

        # 5. Analytics: Highest spending category
        if analytics_intent:
            if "get_spending_by_category" not in executed_tools:
                return LLMAction(
                    action="tool_call",
                    tool_name="get_spending_by_category",
                    arguments={"month": month},
                    thought=f"Retrieve category breakdown to identify highest spending {tf_label}."
                )
            else:
                obs = next(o for o in observations if o.tool_name == "get_spending_by_category")
                res = obs.result
                cat_highest = res.get("highest_category")
                amt_highest = res.get("highest_amount", 0.0)
                if cat_highest:
                    ans = f"The category with the highest spending is {cat_highest} with a total of ₹{amt_highest:,.2f}."
                else:
                    ans = f"No expense data is available for {tf_label}."
                return LLMAction(action="final_answer", answer=ans, thought="Highest spending category identified.")

        # 6. General Expense Lookup
        if "get_expenses" not in executed_tools:
            return LLMAction(
                action="tool_call",
                tool_name="get_expenses",
                arguments={
                    "category": category,
                    "month": month,
                    "start_date": start_date,
                    "end_date": end_date
                },
                thought=f"Fetch expense entries for {category or 'all categories'} {tf_label}."
            )
        else:
            exp_obs = next(o for o in observations if o.tool_name == "get_expenses")
            res = exp_obs.result
            if not res.get("success"):
                return LLMAction(
                    action="final_answer",
                    answer=f"Error retrieving expenses: {res.get('message')}",
                    thought="Handled database error."
                )

            expenses = res.get("expenses", [])
            total = res.get("total", 0.0)
            is_single_date = bool(start_date and end_date and start_date == end_date)
            date_display = tf.get("raw_date") or start_date

            if not expenses or res.get("count", 0) == 0:
                if is_single_date:
                    if category:
                        ans = f"No {category} expenses found for {date_display}."
                    else:
                        ans = f"No expense records found for {date_display}."
                elif category:
                    ans = f"No expense records were found for {category} {tf_label}."
                else:
                    ans = f"No expense records were found {tf_label}."
            elif is_single_date:
                if category:
                    ans = f"You spent a total of ₹{total:,.2f} on {category} on {date_display}."
                else:
                    ans = f"Your total spending on {date_display} across all categories was ₹{total:,.2f}."
            elif category:
                ans = f"You spent a total of ₹{total:,.2f} on {category} {tf_label}."
            else:
                ans = f"Your total spending {tf_label} across all categories was ₹{total:,.2f}."

            return LLMAction(action="final_answer", answer=ans, thought="Expense lookup summarized.")
