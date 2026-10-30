#this file acts as the Memory Notebook.
#Tracks the results collected from tools.
import json #Converts dictionaries into readable JSON text
from typing import Dict, Any, List
from pydantic import BaseModel
#base model =Validates the structure of an observation.
class Observation(BaseModel):
    #Observation = one tool execution record.
    """Record of a single tool execution step."""
    iteration: int
    tool_name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]

class ObservationTracker:
#ObservationTracker = manages all tool execution records.
    """Tracker for storing and formatting observations across agent loop iterations."""

    def __init__(self):
        self.observations: List[Observation] = []
#add() = saves a record.
    def add(self, iteration: int, tool_name: str, arguments: Dict[str, Any], result: Dict[str, Any]) -> None:
        obs = Observation(
            iteration=iteration,
            tool_name=tool_name,
            arguments=arguments,
            result=result
        )
        self.observations.append(obs)
#get_all() = returns records as dictionaries.
    def get_all(self) -> List[Dict[str, Any]]:
        return [obs.model_dump() for obs in self.observations]
#format_for_llm() = prepares the recorded history as text for the LLM.
    def format_for_llm(self) -> str:
        if not self.observations:
            return "No previous observations."

        formatted = []
        for obs in self.observations:
            formatted.append(
                f"Iteration {obs.iteration}:\n"
                f"  Tool Executed: `{obs.tool_name}`\n"
                f"  Arguments: {json.dumps(obs.arguments)}\n"
                f"  Result: {json.dumps(obs.result)}"
            )
        return "\n\n".join(formatted)
