from typing import List, Dict, Any, Literal
from pydantic import BaseModel

class ClaimVerification(BaseModel):
    """Result of verifying an individual statement or numerical claim."""
    claim_type: str  # e.g., 'amount', 'category', 'budget_status'
    claimed_value: Any
    observed_value: Any
    is_verified: bool
    details: str

class ReflectionResult(BaseModel):
    """Output from the Reflection and Grounding Verification layer."""
    grounding_status: Literal["VERIFIED", "UNSUPPORTED_CLAIMS"]
    draft_answer: str
    verified_answer: str
    claims_checked: List[ClaimVerification]
    summary: str
