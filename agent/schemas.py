from typing import Dict, Any, Optional, Literal, List
from pydantic import BaseModel, Field, model_validator

class LLMAction(BaseModel):
    """Pydantic model validating structured decision from LLM policy."""
    action: Literal["tool_call", "final_answer"]
    tool_name: Optional[str] = Field(default=None, description="Name of tool to call if action is tool_call")
    arguments: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Arguments dictionary for tool call")
    answer: Optional[str] = Field(default=None, description="Final answer text if action is final_answer")
    thought: Optional[str] = Field(default=None, description="Brief step reasoning")

    @model_validator(mode="after")
    def validate_action_fields(self):
        if self.action == "tool_call":
            if not self.tool_name:
                raise ValueError("tool_name is required when action is 'tool_call'")
        elif self.action == "final_answer":
            if not self.answer:
                raise ValueError("answer is required when action is 'final_answer'")
        return self

class AgentResponse(BaseModel):
    """Final output object returned by the agent loop."""
    question: str
    answer: str
    tools_used: List[str]
    observations: List[Dict[str, Any]]
    iterations: int
    grounding_status: str
    reflection: Dict[str, Any]
