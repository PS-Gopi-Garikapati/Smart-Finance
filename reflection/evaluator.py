import re
import logging
from typing import List, Dict, Any, Set
from reflection.schemas import ReflectionResult, ClaimVerification

logger = logging.getLogger("ReflectionEvaluator")

class ReflectionEvaluator:
    """Verifies LLM draft answers strictly against recorded MCP tool observations."""

    def evaluate(self, draft_answer: str, observations: List[Dict[str, Any]]) -> ReflectionResult:
        claims: List[ClaimVerification] = []
        
        # 1. Collect all numerical values present in observations
        observed_numbers: Set[float] = set()
        observed_statuses: Set[str] = set()
        observed_categories: Set[str] = set()

        for obs in observations:
            res = obs.get("result", {})
            if not isinstance(res, dict):
                continue
            
            # Numeric fields
            for key in ["total", "budget", "spent", "difference", "grand_total", "highest_amount"]:
                if key in res and res[key] is not None:
                    try:
                        val = float(res[key])
                        observed_numbers.add(val)
                        observed_numbers.add(round(val, 2))
                        observed_numbers.add(abs(val))
                    except (ValueError, TypeError):
                        pass

            # Expenses list totals
            if "expenses" in res and isinstance(res["expenses"], list):
                for exp in res["expenses"]:
                    if "amount" in exp:
                        val = float(exp["amount"])
                        observed_numbers.add(val)
                        observed_numbers.add(round(val, 2))

            # Statuses
            if "status" in res:
                observed_statuses.add(str(res["status"]).upper())

            # Categories
            if "category" in res and res["category"]:
                observed_categories.add(str(res["category"]).lower())

        # 2. Extract monetary/numerical numbers mentioned in draft answer
        draft_numbers = self._extract_numbers_from_text(draft_answer)

        all_numbers_verified = True
        for num in draft_numbers:
            match_found = any(abs(num - obs_num) < 0.01 for obs_num in observed_numbers)
            
            claims.append(ClaimVerification(
                claim_type="numerical_amount",
                claimed_value=num,
                observed_value=list(observed_numbers),
                is_verified=match_found,
                details=f"Number {num:,.2f} in answer {'matches' if match_found else 'does NOT match'} tool observations."
            ))
            if not match_found:
                all_numbers_verified = False

        # 3. Verify budget status claims if budget comparison occurred
        if "compare_budget" in [obs.get("tool_name") for obs in observations]:
            comp_obs = next(o for o in observations if o.get("tool_name") == "compare_budget")
            comp_res = comp_obs.get("result", {})
            actual_status = comp_res.get("status")
            
            answer_lower = draft_answer.lower()
            over_keywords = ["exceed", "over", "above", "surpass", "higher than"]
            claimed_status = "OVER_BUDGET" if any(k in answer_lower for k in over_keywords) else "WITHIN_BUDGET"
            
            status_match = (claimed_status == actual_status)
            claims.append(ClaimVerification(
                claim_type="budget_status",
                claimed_value=claimed_status,
                observed_value=actual_status,
                is_verified=status_match,
                details=f"Budget status claimed '{claimed_status}' {'matches' if status_match else 'CONFLICTS with'} observed '{actual_status}'."
            ))
            if not status_match:
                all_numbers_verified = False

        # 4. Determine overall Grounding Status
        grounding_status = "VERIFIED" if all_numbers_verified else "UNSUPPORTED_CLAIMS"
        
        verified_answer = draft_answer
        if grounding_status == "UNSUPPORTED_CLAIMS":
            logger.warning(f"Reflection rejected draft answer: '{draft_answer}'. Generating corrected answer.")
            verified_answer = self._generate_corrected_answer(observations)

        summary_text = (
            "All numerical figures and statuses were successfully grounded in MCP observations."
            if grounding_status == "VERIFIED"
            else "Draft answer contained unsupported figures. Answer was corrected using verified observations."
        )

        return ReflectionResult(
            grounding_status=grounding_status,
            draft_answer=draft_answer,
            verified_answer=verified_answer,
            claims_checked=claims,
            summary=summary_text
        )

    def _extract_numbers_from_text(self, text: str) -> List[float]:
        """Extract monetary & numerical values from text, ignoring ISO date tags."""
        text_no_dates = re.sub(r'\b\d{4}-\d{2}(-\d{2})?\b', '', text)
        cleaned = text_no_dates.replace("₹", "").replace(",", "")
        pattern = r"\b\d+(?:\.\d+)?\b"
        matches = re.findall(pattern, cleaned)
        numbers = []
        for m in matches:
            try:
                val = float(m)
                numbers.append(val)
            except ValueError:
                pass
        return numbers

    def _generate_corrected_answer(self, observations: List[Dict[str, Any]]) -> str:
        """Construct a guaranteed accurate answer from observations when draft is rejected."""
        facts = []
        for obs in observations:
            tname = obs.get("tool_name")
            res = obs.get("result", {})
            if tname == "get_expenses" and res.get("success"):
                cat = res.get("category") or "All categories"
                month = res.get("month")
                total = res.get("total", 0.0)
                period_str = f" ({month})" if month else ""
                facts.append(f"Total spent on {cat}{period_str}: ₹{total:,.2f}.")
            elif tname == "get_budget" and res.get("success"):
                cat = res.get("category")
                b_amt = res.get("budget", 0.0)
                facts.append(f"Configured budget for {cat}: ₹{b_amt:,.2f}.")
            elif tname == "compare_budget" and res.get("success"):
                status = res.get("status")
                diff = res.get("difference", 0.0)
                if status == "OVER_BUDGET":
                    facts.append(f"Spending exceeded budget by ₹{diff:,.2f}.")
                else:
                    facts.append(f"Spending was within budget.")
            elif tname == "get_spending_by_category" and res.get("success"):
                h_cat = res.get("highest_category")
                h_amt = res.get("highest_amount", 0.0)
                facts.append(f"Highest spending category: {h_cat} (₹{h_amt:,.2f}).")

        if facts:
            return " [VERIFIED OBSERVATIONS]: " + " ".join(facts)
        return "Data from observations is insufficient to verify the claim."
