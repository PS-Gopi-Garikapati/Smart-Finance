import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator

def validate_month_format(month_str: str) -> bool:
    """Validate that month is in YYYY-MM format with valid month integer 01-12."""
    if not isinstance(month_str, str):
        return False
    return bool(re.match(r"^\d{4}-(0[1-9]|1[0-2])$", month_str.strip()))

def validate_date_format(date_str: str) -> bool:
    """Validate that date is a valid ISO date YYYY-MM-DD."""
    if not isinstance(date_str, str):
        return False
    clean = date_str.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", clean):
        return False
    try:
        datetime.strptime(clean, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def validation_error(message: str) -> Dict[str, Any]:
    """Uniform structured validation error."""
    return {
        "success": False,
        "error": "INVALID_ARGUMENT",
        "message": message
    }

def database_error(message: str) -> Dict[str, Any]:
    """Uniform structured database error."""
    return {
        "success": False,
        "error": "DATABASE_ERROR",
        "message": f"Database failure: {message}"
    }

class GetExpensesInput(BaseModel):
    category: Optional[str] = None
    month: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    @field_validator("category")
    @classmethod
    def check_category(cls, v):
        if v is not None and not isinstance(v, str):
            raise ValueError("Category must be a string.")
        return v.strip() if v else None

    @field_validator("month")
    @classmethod
    def check_month(cls, v):
        if v is not None and not validate_month_format(v):
            raise ValueError(f"Invalid month format '{v}'. Must be YYYY-MM with month between 01 and 12 (e.g., '2026-09').")
        return v.strip() if v else None

    @field_validator("start_date")
    @classmethod
    def check_start_date(cls, v):
        if v is not None and not validate_date_format(v):
            raise ValueError(f"Invalid start_date format '{v}'. Must be a valid YYYY-MM-DD date.")
        return v.strip() if v else None

    @field_validator("end_date")
    @classmethod
    def check_end_date(cls, v):
        if v is not None and not validate_date_format(v):
            raise ValueError(f"Invalid end_date format '{v}'. Must be a valid YYYY-MM-DD date.")
        return v.strip() if v else None

    @model_validator(mode="after")
    def check_date_range(self):
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError(f"Invalid date range: start_date '{self.start_date}' cannot be after end_date '{self.end_date}'.")
        return self

class GetBudgetInput(BaseModel):
    category: str
    month: str

    @field_validator("category")
    @classmethod
    def check_category(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("Category must be a non-empty string.")
        return v.strip()

    @field_validator("month")
    @classmethod
    def check_month(cls, v):
        if not v or not validate_month_format(v):
            raise ValueError(f"Invalid month format '{v}'. Must be a valid YYYY-MM format (e.g. '2026-09').")
        return v.strip()

class CompareBudgetInput(BaseModel):
    spent: float
    budget: float

    @model_validator(mode="before")
    @classmethod
    def check_numbers(cls, data):
        if not isinstance(data, dict):
            raise ValueError("Input must be a dictionary.")
        for k in ["spent", "budget"]:
            val = data.get(k)
            try:
                float(val)
            except (ValueError, TypeError):
                raise ValueError("Both 'spent' and 'budget' must be valid numeric values.")
        return data

class GetSpendingByCategoryInput(BaseModel):
    month: Optional[str] = None

    @field_validator("month")
    @classmethod
    def check_month(cls, v):
        if v is not None and not validate_month_format(v):
            raise ValueError(f"Invalid month format '{v}'. Must be YYYY-MM with month between 01 and 12 (e.g., '2026-09').")
        return v.strip() if v else None

class CalculateTotalInput(BaseModel):
    amounts: List[float]

    @field_validator("amounts")
    @classmethod
    def check_amounts(cls, v):
        if not isinstance(v, list):
            raise ValueError("Input 'amounts' must be a list of numbers.")
        valid = []
        for item in v:
            try:
                valid.append(float(item))
            except (ValueError, TypeError):
                raise ValueError(f"Invalid numeric item in amounts list: {item}")
        return valid

class SearchDocumentsInput(BaseModel):
    query: str
    top_k: int = 3

    @field_validator("query")
    @classmethod
    def check_query(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("Query must be a non-empty string.")
        return v.strip()

    @field_validator("top_k")
    @classmethod
    def check_top_k(cls, v):
        if not isinstance(v, int) or v <= 0:
            return 3
        return v
