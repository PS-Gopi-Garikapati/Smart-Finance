#This file acts as the Quality Checker / Blueprint.
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
    #The original user question
    question: str
    #The final answer
    answer: str
    #Names of tools used
    tools_used: List[str]
    #Results collected from tool calls
    observations: List[Dict[str, Any]]
    #Number of agent decision cycles
    iterations: int
    #Status reported for grounding checks
    grounding_status: str
    #Details from the agent's reflection or evaluation
    reflection: Dict[str, Any]
