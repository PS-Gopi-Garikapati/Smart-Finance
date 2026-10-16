import re
import os
from datetime import datetime, date
from typing import Optional, Dict, Any, List

SUPPORTED_CATEGORIES: List[str] = [
    "Food", "Transport", "Shopping", "Bills", "Entertainment", "Healthcare", "Travel"
]

MONTH_NAME_TO_NUM: Dict[str, str] = {
    "january": "01", "jan": "01",
    "february": "02", "feb": "02",
    "march": "03", "mar": "03",
    "april": "04", "apr": "04",
    "may": "05",
    "june": "06", "jun": "06",
    "july": "07", "jul": "07",
    "august": "08", "aug": "08",
    "september": "09", "sep": "09", "sept": "09",
    "october": "10", "oct": "10",
    "november": "11", "nov": "11",
    "december": "12", "dec": "12"
}

def get_reference_date(reference_date: Optional[Any] = None) -> date:
    """Return the configured reference date, defaulting to today's date."""
    if reference_date is not None:
        if isinstance(reference_date, datetime):
            return reference_date.date()
        if isinstance(reference_date, date):
            return reference_date
        if isinstance(reference_date, str):
            try:
                return datetime.strptime(reference_date.strip(), "%Y-%m-%d").date()
            except ValueError:
                pass

    env_date = os.getenv("CURRENT_DATE")
    if not env_date:
        return date.today()
    try:
        return datetime.strptime(env_date.strip(), "%Y-%m-%d").date()
    except ValueError:
        return date.today()

def extract_category(question: str) -> Optional[str]:
    """Extract recognized financial category from text, or None if unspecified."""
    q_lower = question.lower()
    for cat in SUPPORTED_CATEGORIES:
        if re.search(r'\b' + cat.lower() + r'\b', q_lower):
            return cat
    return None

def extract_timeframe(question: str, reference_date: Optional[Any] = None) -> Dict[str, Optional[str]]:
    """
    Extract timeframe parameters (month, start_date, end_date, timeframe_label)
    from user query with relative month awareness.
    """
    ref_d = get_reference_date(reference_date)
    q_lower = question.lower()

    month: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    label: str = "this period"

    # 1. Custom ISO date range (e.g., from 2026-09-01 to 2026-09-15)
    range_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\s+(?:to|until|through|-)\s+(\d{4}-\d{2}-\d{2})\b', question)
    if range_match:
        start_date = range_match.group(1)
        end_date = range_match.group(2)
        label = f"from {start_date} to {end_date}"
        return {"month": None, "start_date": start_date, "end_date": end_date, "timeframe_label": label}

    # 2. ISO Month format YYYY-MM (e.g. 2026-09, 2025-01)
    iso_month_match = re.search(r'\b(20\d{2})-(0[1-9]|1[0-2])\b', question)
    if iso_month_match:
        month = iso_month_match.group(0)
        label = f"in {month}"
        return {"month": month, "start_date": None, "end_date": None, "timeframe_label": label}

    # 3. Explicit Year (e.g., in 2025, 2024, 2026)
    year_match = re.search(r'\b(20\d{2})\b', question)
    explicit_year = year_match.group(1) if year_match else None

    # 4. Check for month names (e.g. September 2026, in August, October 2026)
    for m_name, m_num in MONTH_NAME_TO_NUM.items():
        pattern = r'\b' + m_name + r'\b'
        if re.search(pattern, q_lower):
            target_year = explicit_year or str(ref_d.year)
            month = f"{target_year}-{m_num}"
            label = f"in {m_name.capitalize()} {target_year}"
            return {"month": month, "start_date": None, "end_date": None, "timeframe_label": label}

    # 5. Relative timeframe: "this month" / "current month"
    if "this month" in q_lower or "current month" in q_lower:
        month = f"{ref_d.year:04d}-{ref_d.month:02d}"
        label = f"in {month}"
        return {"month": month, "start_date": None, "end_date": None, "timeframe_label": label}

    # 6. Relative timeframe: "last month" / "previous month"
    if "last month" in q_lower or "previous month" in q_lower:
        if ref_d.month == 1:
            prev_year = ref_d.year - 1
            prev_month = 12
        else:
            prev_year = ref_d.year
            prev_month = ref_d.month - 1
        month = f"{prev_year:04d}-{prev_month:02d}"
        label = f"in {month}"
        return {"month": month, "start_date": None, "end_date": None, "timeframe_label": label}

    # 7. Year-only question (e.g. "food bill in 2025")
    if explicit_year:
        start_date = f"{explicit_year}-01-01"
        end_date = f"{explicit_year}-12-31"
        label = f"in {explicit_year}"
        return {"month": None, "start_date": start_date, "end_date": end_date, "timeframe_label": label}

    # 8. No explicit date specified
    # Default to current month when asking about spending or budget without date
    month = f"{ref_d.year:04d}-{ref_d.month:02d}"
    label = f"in {month}"
    return {"month": month, "start_date": None, "end_date": None, "timeframe_label": label}

def is_ambiguous_budget_question(question: str) -> bool:
    """Return True if question asks about exceeding budget but omits the category."""
    q_lower = question.lower()
    has_budget_intent = any(k in q_lower for k in ["budget", "exceed", "over budget"])
    has_category = extract_category(question) is not None
    # If asking general questions like "Which category exceeded budget?", that's an analytics question
    if "which" in q_lower or "highest" in q_lower:
        return False
    return has_budget_intent and not has_category
