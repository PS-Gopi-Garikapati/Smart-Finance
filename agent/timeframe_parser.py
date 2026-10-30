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
    from user query with specific date support, relative month awareness, and date ranges.
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
        return {"month": None, "start_date": start_date, "end_date": end_date, "timeframe_label": label, "raw_date": f"{start_date} to {end_date}"}

    # 1b. Custom DD-MM-YYYY or DD/MM/YYYY date range (e.g., from 01-09-2026 to 15-09-2026)
    dmy_range_match = re.search(r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\s+(?:to|until|through|-)\s+(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b', question)
    if dmy_range_match:
        r_start_raw = dmy_range_match.group(1)
        r_end_raw = dmy_range_match.group(2)
        try:
            sep1 = "-" if "-" in r_start_raw else "/"
            d1, m1, y1 = [int(p) for p in r_start_raw.split(sep1)]
            dt1 = datetime(y1, m1, d1).date().strftime("%Y-%m-%d")
            sep2 = "-" if "-" in r_end_raw else "/"
            d2, m2, y2 = [int(p) for p in r_end_raw.split(sep2)]
            dt2 = datetime(y2, m2, d2).date().strftime("%Y-%m-%d")
            label = f"from {r_start_raw} to {r_end_raw}"
            return {"month": None, "start_date": dt1, "end_date": dt2, "timeframe_label": label, "raw_date": f"{r_start_raw} to {r_end_raw}"}
        except (ValueError, OverflowError):
            return {"month": None, "start_date": None, "end_date": None, "timeframe_label": "invalid date range", "invalid_date": f"{r_start_raw} to {r_end_raw}", "error": "INVALID_DATE"}

    # 2. Specific Single Dates in various formats:
    # 2a. DD-Month-YYYY or DD Month YYYY (e.g., 02-September-2026, 02 September 2026, 2nd September 2026, 02-Sep-2026)
    d_month_y = re.search(r'\b(0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?[- \t]+([a-zA-Z]+)[- \t]+(\d{4})\b', question)
    if d_month_y:
        raw_m = d_month_y.group(2).lower()
        if raw_m in MONTH_NAME_TO_NUM:
            day_val = int(d_month_y.group(1))
            mon_val = int(MONTH_NAME_TO_NUM[raw_m])
            yr_val = int(d_month_y.group(3))
            raw_match = d_month_y.group(0)
            try:
                valid_dt = datetime(yr_val, mon_val, day_val).date().strftime("%Y-%m-%d")
                return {"month": None, "start_date": valid_dt, "end_date": valid_dt, "timeframe_label": f"on {raw_match}", "raw_date": raw_match}
            except (ValueError, OverflowError):
                return {"month": None, "start_date": None, "end_date": None, "timeframe_label": f"on {raw_match}", "invalid_date": raw_match, "error": "INVALID_DATE"}

    # 2b. Month DD, YYYY or Month DD YYYY (e.g., September 02, 2026, September 2 2026)
    month_d_y = re.search(r'\b([a-zA-Z]+)[- \t]+(0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?[- \t,]+(\d{4})\b', question)
    if month_d_y:
        raw_m = month_d_y.group(1).lower()
        if raw_m in MONTH_NAME_TO_NUM:
            mon_val = int(MONTH_NAME_TO_NUM[raw_m])
            day_val = int(month_d_y.group(2))
            yr_val = int(month_d_y.group(3))
            raw_match = month_d_y.group(0)
            try:
                valid_dt = datetime(yr_val, mon_val, day_val).date().strftime("%Y-%m-%d")
                return {"month": None, "start_date": valid_dt, "end_date": valid_dt, "timeframe_label": f"on {raw_match}", "raw_date": raw_match}
            except (ValueError, OverflowError):
                return {"month": None, "start_date": None, "end_date": None, "timeframe_label": f"on {raw_match}", "invalid_date": raw_match, "error": "INVALID_DATE"}

#\d{4} — matches a 4-digit year, such as 2026.
#(0?[1-9]|1[0-2]) — matches a month from 1 to 12, such as 09.
#(0?[1-9]|[12]\d|3[01]) — matches a day from 1 to 31, such as 02.
#\b — helps match the date at word boundaries.


    # 2c. DD-MM-YYYY or DD/MM/YYYY (e.g., 02-09-2026, 02/09/2026, 2-9-2026, 31-02-2026)
    dmy_match = re.search(r'\b(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])[-/](\d{4})\b', question)
    if dmy_match:
        day_val = int(dmy_match.group(1))
        mon_val = int(dmy_match.group(2))
        yr_val = int(dmy_match.group(3))
        raw_match = dmy_match.group(0)
        try:
            valid_dt = datetime(yr_val, mon_val, day_val).date().strftime("%Y-%m-%d")
            return {"month": None, "start_date": valid_dt, "end_date": valid_dt, "timeframe_label": f"on {raw_match}", "raw_date": raw_match}
        except (ValueError, OverflowError):
            return {"month": None, "start_date": None, "end_date": None, "timeframe_label": f"on {raw_match}", "invalid_date": raw_match, "error": "INVALID_DATE"}



    # 2d. ISO format YYYY-MM-DD (e.g., 2026-09-02, 2026-9-2)  #searches for a matching date.
    iso_date_match = re.search(r'\b(\d{4})-(0?[1-9]|1[0-2])-(0?[1-9]|[12]\d|3[01])\b', question)
    if iso_date_match:
        yr_val = int(iso_date_match.group(1))
        mon_val = int(iso_date_match.group(2))
        day_val = int(iso_date_match.group(3))
        raw_match = iso_date_match.group(0)
        try:
            valid_dt = datetime(yr_val, mon_val, day_val).date().strftime("%Y-%m-%d")
            return {"month": None, "start_date": valid_dt, "end_date": valid_dt, "timeframe_label": f"on {valid_dt}", "raw_date": raw_match}
        except (ValueError, OverflowError):
            return {"month": None, "start_date": None, "end_date": None, "timeframe_label": f"on {raw_match}", "invalid_date": raw_match, "error": "INVALID_DATE"}

    # 3. ISO Month format YYYY-MM (e.g. 2026-09, 2025-01) - negative lookahead prevents matching full dates
    iso_month_match = re.search(r'\b(20\d{2})-(0[1-9]|1[0-2])(?!\s*-\s*\d{1,2})\b', question)
    if iso_month_match:
        month = iso_month_match.group(1) + "-" + iso_month_match.group(2)
        label = f"in {month}"
        return {"month": month, "start_date": None, "end_date": None, "timeframe_label": label, "raw_date": month}

    # 4. Explicit Year (e.g., in 2025, 2024, 2026)
    year_match = re.search(r'\b(20\d{2})\b', question)
    explicit_year = year_match.group(1) if year_match else None

    # 5. Check for month names (e.g. September 2026, in August, October 2026)
    for m_name, m_num in MONTH_NAME_TO_NUM.items():
        pattern = r'\b' + m_name + r'\b'
        if re.search(pattern, q_lower):
            target_year = explicit_year or str(ref_d.year)
            month = f"{target_year}-{m_num}"
            label = f"in {m_name.capitalize()} {target_year}"
            return {"month": month, "start_date": None, "end_date": None, "timeframe_label": label, "raw_date": f"{m_name.capitalize()} {target_year}"}

    # 6. Relative timeframe: "this month" / "current month"
    if "this month" in q_lower or "current month" in q_lower:
        month = f"{ref_d.year:04d}-{ref_d.month:02d}"
        label = f"in {month}"
        return {"month": month, "start_date": None, "end_date": None, "timeframe_label": label, "raw_date": "this month"}

    # 7. Relative timeframe: "last month" / "previous month"
    if "last month" in q_lower or "previous month" in q_lower:
        if ref_d.month == 1:
            prev_year = ref_d.year - 1
            prev_month = 12
        else:
            prev_year = ref_d.year
            prev_month = ref_d.month - 1
        month = f"{prev_year:04d}-{prev_month:02d}"
        label = f"in {month}"
        return {"month": month, "start_date": None, "end_date": None, "timeframe_label": label, "raw_date": "last month"}

    # 8. Year-only question (e.g. "food bill in 2025")
    if explicit_year:
        start_date = f"{explicit_year}-01-01"
        end_date = f"{explicit_year}-12-31"
        label = f"in {explicit_year}"
        return {"month": None, "start_date": start_date, "end_date": end_date, "timeframe_label": label, "raw_date": explicit_year}

    # 9. No explicit date specified
    # Default to current month when asking about spending or budget without date
    month = f"{ref_d.year:04d}-{ref_d.month:02d}"
    label = f"in {month}"
    return {"month": month, "start_date": None, "end_date": None, "timeframe_label": label, "raw_date": None}

def is_ambiguous_budget_question(question: str) -> bool:
    """Return True if question asks about exceeding budget but omits the category."""
    q_lower = question.lower()
    has_budget_intent = any(k in q_lower for k in ["budget", "exceed", "over budget"])
    has_category = extract_category(question) is not None
    # If asking general questions like "Which category exceeded budget?", that's an analytics question
    if "which" in q_lower or "highest" in q_lower:
        return False
    return has_budget_intent and not has_category
