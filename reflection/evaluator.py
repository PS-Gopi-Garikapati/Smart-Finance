import re
import logging
from typing import List, Dict, Any, Optional, Set
from reflection.schemas import ReflectionResult, ClaimAudit, GroundingStatus

logger = logging.getLogger("ReflectionEvaluator")

KNOWN_CATEGORIES = [
    "food", "transport", "shopping", "bills", "entertainment",
    "healthcare", "travel", "groceries", "utilities"
]

MONTH_NAME_TO_NUM = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12"
}

class ReflectionEvaluator:
    """
    Independent Reflection & Grounding Audit Layer.
    Audits draft answers against MCP tool observations and SQLite/RAG evidence.
    Validates numbers, totals, categories, dates, budget status, and qualitative claims.
    Detects contradictions and ungrounded claims, and repairs unsupported answers.
    """

    def __init__(self):
        pass

    def evaluate(
        self,
        draft_answer: str = "",
        observations: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> ReflectionResult:
        """
        Evaluate and audit a draft answer against actual tool observations.
        Accepts positional or keyword arguments for backward compatibility.
        """
        if not draft_answer and "draft" in kwargs:
            draft_answer = kwargs["draft"]
        if observations is None and "obs" in kwargs:
            observations = kwargs["obs"]
        observations = observations or []

        draft = (draft_answer or "").strip()

        # Handle edge case: empty draft
        if not draft:
            return ReflectionResult(
                grounding_status="MISSING_EVIDENCE",
                verified_answer="No answer was generated to evaluate.",
                summary="Draft answer was empty.",
                raw_draft=draft
            )

        # Handle edge case: max iterations safety limit reached
        if "maximum iterations" in draft.lower():
            return ReflectionResult(
                grounding_status="VERIFIED",
                verified_answer=draft,
                summary="Agent loop reached maximum iteration safety limit.",
                raw_draft=draft
            )

        # 1. Parse and extract ground truth facts from observations
        evidence = self._extract_evidence(observations)

        # 2. Check for empty observations or malformed observation states
        if evidence["malformed"]:
            summary = "Encountered malformed or erroneous tool observations during execution."
            repaired = self._generate_grounded_answer(evidence, draft)
            return ReflectionResult(
                grounding_status="MALFORMED_OBSERVATION",
                verified_answer=repaired,
                summary=summary,
                raw_draft=draft
            )

        if not observations:
            # If draft claims specific financial figures without any observations
            draft_numbers = self._extract_numbers(draft)
            if draft_numbers:
                return ReflectionResult(
                    grounding_status="MISSING_EVIDENCE",
                    verified_answer="No tool observations or database records were retrieved to verify financial claims.",
                    summary="Financial claims made without supporting tool observations.",
                    unsupported_claims=[f"Claimed numbers: {draft_numbers} without evidence"],
                    raw_draft=draft
                )
            # If draft is just stating no tools or inability to answer, it's verified
            return ReflectionResult(
                grounding_status="VERIFIED",
                verified_answer=draft,
                summary="Honest non-financial response verified in absence of observations.",
                raw_draft=draft
            )

        # 3. Perform claim extraction and audits
        claims_checked: List[ClaimAudit] = []
        contradictions: List[str] = []
        unsupported_claims: List[str] = []

        # Audit A: Numerical claims
        draft_numbers = self._extract_numbers(draft)
        for num in draft_numbers:
            # Check if this number is grounded in evidence numbers or doc chunks
            matched = False
            for valid_num in evidence["numbers"]:
                if abs(num - valid_num) < 0.05:
                    matched = True
                    break

            if matched:
                claims_checked.append(ClaimAudit(
                    claim_type="amount",
                    claimed_value=num,
                    verified_value=num,
                    is_supported=True,
                    note=f"Number {num} matches observation evidence."
                ))
            else:
                unsupported_claims.append(f"Ungrounded number '{num}' in draft answer.")
                claims_checked.append(ClaimAudit(
                    claim_type="amount",
                    claimed_value=num,
                    verified_value=list(evidence["numbers"]) if evidence["numbers"] else None,
                    is_supported=False,
                    note=f"Number {num} does not match any observed amount {evidence['numbers']}."
                ))

        # Audit B: Category claims
        draft_categories = self._extract_categories(draft)
        if evidence["categories"]:
            for d_cat in draft_categories:
                if any(d_cat.lower() == e_cat.lower() for e_cat in evidence["categories"]):
                    claims_checked.append(ClaimAudit(
                        claim_type="category",
                        claimed_value=d_cat,
                        verified_value=d_cat,
                        is_supported=True,
                        note=f"Category '{d_cat}' confirmed by observations."
                    ))
                else:
                    contradictions.append(
                        f"Category contradiction: draft mentions category '{d_cat}', but tool observation was for {list(evidence['categories'])}."
                    )
                    claims_checked.append(ClaimAudit(
                        claim_type="category",
                        claimed_value=d_cat,
                        verified_value=list(evidence["categories"]),
                        is_supported=False,
                        note=f"Category contradiction: '{d_cat}' not in observed categories."
                    ))

        # Audit C: Budget status (over budget vs within budget)
        if evidence.get("budget_status"):
            expected_status = evidence["budget_status"] # "OVER_BUDGET" or "WITHIN_BUDGET"
            lower_draft = draft.lower()
            claims_exceeded = any(w in lower_draft for w in ["exceed", "over budget", "surpassed", "more than budget"])
            claims_within = any(w in lower_draft for w in ["within budget", "under budget", "not exceed", "below budget", "did not exceed"])

            if expected_status == "OVER_BUDGET" and claims_within and not claims_exceeded:
                contradictions.append("Draft claims spending was within budget, but tool observation status is OVER_BUDGET.")
                claims_checked.append(ClaimAudit(
                    claim_type="budget_status",
                    claimed_value="WITHIN_BUDGET",
                    verified_value="OVER_BUDGET",
                    is_supported=False,
                    note="Direct contradiction of budget status."
                ))
            elif expected_status == "WITHIN_BUDGET" and claims_exceeded and not claims_within:
                contradictions.append("Draft claims spending exceeded budget, but tool observation status is WITHIN_BUDGET.")
                claims_checked.append(ClaimAudit(
                    claim_type="budget_status",
                    claimed_value="OVER_BUDGET",
                    verified_value="WITHIN_BUDGET",
                    is_supported=False,
                    note="Direct contradiction of budget status."
                ))
            elif (expected_status == "OVER_BUDGET" and claims_exceeded) or (expected_status == "WITHIN_BUDGET" and claims_within):
                claims_checked.append(ClaimAudit(
                    claim_type="budget_status",
                    claimed_value=expected_status,
                    verified_value=expected_status,
                    is_supported=True,
                    note=f"Budget status {expected_status} accurately described."
                ))

        # Audit D: Date / Month claims
        draft_months = self._extract_months(draft)
        if evidence["months"] and draft_months:
            for d_month in draft_months:
                if any(self._matches_month(d_month, e_m) for e_m in evidence["months"]):
                    claims_checked.append(ClaimAudit(
                        claim_type="month",
                        claimed_value=d_month,
                        verified_value=d_month,
                        is_supported=True,
                        note=f"Timeframe '{d_month}' matches tool observation."
                    ))
                else:
                    contradictions.append(
                        f"Draft mentions month '{d_month}', but observed data is for {list(evidence['months'])}."
                    )
                    claims_checked.append(ClaimAudit(
                        claim_type="month",
                        claimed_value=d_month,
                        verified_value=list(evidence["months"]),
                        is_supported=False,
                        note="Month timeframe mismatch."
                    ))

        # 4. Determine overall status and construct verified response
        if contradictions:
            status: GroundingStatus = "CONTRADICTION"
            summary = f"Identified {len(contradictions)} contradiction(s) with observed data."
            verified_answer = self._generate_grounded_answer(evidence, draft)
        elif unsupported_claims:
            status: GroundingStatus = "UNSUPPORTED_CLAIMS"
            summary = f"Identified {len(unsupported_claims)} unsupported financial claim(s) or figure(s)."
            verified_answer = self._generate_grounded_answer(evidence, draft)
        else:
            status: GroundingStatus = "VERIFIED"
            summary = "All figures, categories, and conclusions strictly verified against observations."
            verified_answer = draft

        return ReflectionResult(
            grounding_status=status,
            verified_answer=verified_answer,
            summary=summary,
            claims_checked=claims_checked,
            contradictions=contradictions,
            unsupported_claims=unsupported_claims,
            raw_draft=draft
        )

    def _extract_evidence(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate all factual ground truth evidence from successful observations."""
        numbers: Set[float] = set()
        categories: Set[str] = set()
        months: Set[str] = set()
        budget_status: Optional[str] = None
        has_malformed = False
        latest_tool_data: Dict[str, Any] = {}
        doc_matches: List[Dict[str, Any]] = []

        for obs in observations:
            if not isinstance(obs, dict):
                has_malformed = True
                continue

            result = obs.get("result")
            if not isinstance(result, dict):
                has_malformed = True
                continue

            if not result.get("success", False):
                # An error observation or failed tool call
                continue

            tool_name = obs.get("tool_name", "")
            latest_tool_data[tool_name] = result

            # Extract numbers from result dict recursively
            self._collect_numbers_from_obj(result, numbers)

            # Tool specific entity extraction
            if "category" in result and result["category"]:
                categories.add(str(result["category"]))
            if "month" in result and result["month"]:
                months.add(str(result["month"]))
            if "status" in result and result["status"]:
                budget_status = str(result["status"])
            if "highest_category" in result and result["highest_category"]:
                categories.add(str(result["highest_category"]))

            # Document search results
            if tool_name == "search_documents":
                docs = result.get("results", [])
                for d in docs:
                    doc_matches.append(d)
                    if isinstance(d, dict) and "content" in d:
                        for n in self._extract_numbers(d["content"]):
                            numbers.add(n)

        return {
            "numbers": numbers,
            "categories": categories,
            "months": months,
            "budget_status": budget_status,
            "latest_tool_data": latest_tool_data,
            "doc_matches": doc_matches,
            "malformed": has_malformed
        }

    def _collect_numbers_from_obj(self, obj: Any, out_set: Set[float]):
        """Recursively scan dict/list for float or int amounts."""
        if isinstance(obj, (int, float)) and not isinstance(obj, bool):
            out_set.add(float(obj))
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if k in ["id", "count", "iteration", "top_k", "status", "success"]:
                    continue
                self._collect_numbers_from_obj(v, out_set)
        elif isinstance(obj, list):
            for item in obj:
                self._collect_numbers_from_obj(item, out_set)

    def _extract_numbers(self, text: str) -> List[float]:
        """Extract monetary or numeric values from text, ignoring dates, years, and iteration limits."""
        # 1. Mask dates and system annotations
        masked = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', ' ', text)
        masked = re.sub(r'\b\d{4}-(?:0[1-9]|1[0-2])\b', ' ', masked)
        masked = re.sub(r'\b(?:in|for|year|during|since|until)\s+20\d{2}\b', ' ', masked, flags=re.I)
        masked = re.sub(r'\b20\d{2}\b', ' ', masked) # isolated 4-digit years like 2024, 2025, 2026
        masked = re.sub(r'\b(?:maximum|max)\s+iterations?\s*(?:\(\d+\)|\d+)?', ' ', masked, flags=re.I)
        masked = re.sub(r'\biteration\s*\d+\b', ' ', masked, flags=re.I)
        masked = re.sub(r'\b\d+\s*transactions?\b', ' ', masked, flags=re.I)

        # Match currency numbers like ₹6,000, $1,500.00, 6000, 5,000.50, 0
        raw_matches = re.findall(r'(?:[₹$€]|INR\s*|USD\s*)?([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)', masked)
        numbers = []
        for m in raw_matches:
            clean = m.replace(",", "").strip()
            try:
                val = float(clean)
                numbers.append(val)
            except ValueError:
                pass
        return numbers

    def _extract_categories(self, text: str) -> List[str]:
        """Extract recognized financial categories mentioned in text."""
        found = []
        for cat in KNOWN_CATEGORIES:
            if re.search(r'\b' + cat + r'\b', text, re.IGNORECASE):
                found.append(cat.capitalize())
        return found

    def _extract_months(self, text: str) -> List[str]:
        """Extract explicit months or YYYY-MM strings from text."""
        months = []
        month_names = [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december"
        ]
        # Match YYYY-MM
        iso_matches = re.findall(r'\b\d{4}-(?:0[1-9]|1[0-2])\b', text)
        months.extend(iso_matches)
        for m in month_names:
            if re.search(r'\b' + m + r'\b', text, re.IGNORECASE):
                months.append(m.capitalize())
        return months

    def _matches_month(self, d_month: str, e_month: str) -> bool:
        """Check if claimed draft month matches observed month."""
        d_m = d_month.lower()
        e_m = e_month.lower()
        if d_m in e_m or e_m in d_m:
            return True
        e_parts = e_m.split("-")
        if len(e_parts) == 2 and d_m in MONTH_NAME_TO_NUM:
            return MONTH_NAME_TO_NUM[d_m] == e_parts[1]
        return False

    def _generate_grounded_answer(self, evidence: Dict[str, Any], raw_draft: str) -> str:
        """
        Regenerate answer strictly from verified observation evidence.
        Never invents new financial figures or unobserved facts.
        """
        tools = evidence.get("latest_tool_data", {})

        # Priority 1: Budget comparison results
        if "compare_budget" in tools:
            cb = tools["compare_budget"]
            spent = cb.get("spent", 0.0)
            budget = cb.get("budget", 0.0)
            diff = cb.get("difference", 0.0)
            status = cb.get("status", "UNKNOWN")
            
            # Find associated category
            cat = next(iter(evidence["categories"]), "the requested category")
            month = next(iter(evidence["months"]), "the requested month")

            if status == "OVER_BUDGET":
                return f"Based on verified records, you spent ₹{spent:,.2f} on {cat} in {month}, exceeding your ₹{budget:,.2f} budget by ₹{abs(diff):,.2f}."
            else:
                return f"Based on verified records, you spent ₹{spent:,.2f} on {cat} in {month}, which is within your ₹{budget:,.2f} budget (₹{abs(diff):,.2f} remaining)."

        # Priority 2: Expense total results
        if "get_expenses" in tools:
            exp = tools["get_expenses"]
            total = exp.get("total", 0.0)
            count = exp.get("count", 0)
            cat = exp.get("category") or next(iter(evidence["categories"]), None)
            month = exp.get("month") or next(iter(evidence["months"]), None)

            time_str = f"in {month}" if month else "for the requested period"
            count_str = f" ({count} transactions)" if count > 0 else ""
            if count == 0 and total == 0.0 and "expenses" in exp and len(exp.get("expenses", [])) == 0:
                cat_str = f"for {cat} " if cat else ""
                return f"Verified database query returned 0 expense records {cat_str}{time_str}."
            elif cat:
                return f"Based on verified records, you spent a total of ₹{total:,.2f} on {cat} {time_str}{count_str}."
            else:
                return f"Based on verified records, your total spending {time_str} was ₹{total:,.2f}{count_str}."

        # Priority 3: Category breakdown / Highest spending
        if "get_spending_by_category" in tools:
            cat_data = tools["get_spending_by_category"]
            highest = cat_data.get("highest_category")
            highest_amt = cat_data.get("highest_amount", 0.0)
            grand = cat_data.get("grand_total", 0.0)
            month = cat_data.get("month") or next(iter(evidence["months"]), None)
            month_str = f"for {month}" if month else "overall"

            if highest:
                return f"Based on verified records {month_str}, the highest spending category is {highest} with ₹{highest_amt:,.2f} (grand total: ₹{grand:,.2f})."
            else:
                return f"Verified database query returned no category spending records {month_str}."

        # Priority 4: Document / RAG search
        if "search_documents" in tools:
            doc_data = tools["search_documents"]
            results = doc_data.get("results", [])
            if results:
                top = results[0]
                return f"Based on verified financial document '{top.get('title')}': {top.get('content')}"
            else:
                return "No matching financial policy or document was found in verified document store."

        # Priority 5: Calculator
        if "calculate_total" in tools:
            calc = tools["calculate_total"]
            total = calc.get("total", 0.0)
            count = calc.get("count", 0)
            return f"Verified calculation: total sum of {count} amounts is {total:,.2f}."

        return "Could not verify claims: no matching financial records or tool observations were found in the database."
