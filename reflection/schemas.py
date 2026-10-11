from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, model_validator

GroundingStatus = Literal[
    "VERIFIED",
    "UNSUPPORTED_CLAIMS",
    "CONTRADICTION",
    "MISSING_EVIDENCE",
    "MALFORMED_OBSERVATION"
]

class ClaimAudit(BaseModel):
    """Detailed audit of a single claim checked against observation evidence."""
    claim_type: str = Field(description="Type of claim (amount, category, date, budget_status, policy)")
    claimed_value: Any = Field(description="Value claimed in the draft answer")
    verified_value: Optional[Any] = Field(default=None, description="Ground truth value from observations")
    is_supported: bool = Field(default=True, description="Whether the claim is strictly supported by evidence")
    is_verified: bool = Field(default=True, description="Alias for frontend compatibility")
    note: str = Field(default="", description="Audit commentary")
    details: str = Field(default="", description="Verification details")

    @model_validator(mode="before")
    @classmethod
    def sync_aliases(cls, data: Any):
        if isinstance(data, dict):
            # Sync is_supported and is_verified
            if "is_supported" in data and "is_verified" not in data:
                data["is_verified"] = data["is_supported"]
            elif "is_verified" in data and "is_supported" not in data:
                data["is_supported"] = data["is_verified"]
            # Sync note and details
            if "note" in data and "details" not in data:
                data["details"] = data["note"]
            elif "details" in data and "note" not in data:
                data["note"] = data["details"]
        return data

class ReflectionResult(BaseModel):
    """Result of reflection and grounding evaluation on a draft answer."""
    grounding_status: GroundingStatus
    verified_answer: str
    summary: str
    claims_checked: List[ClaimAudit] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    raw_draft: str = ""
