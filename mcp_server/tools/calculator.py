from typing import List, Dict, Any
from mcp_server.tools.validators import CalculateTotalInput, validation_error

def execute_calculate_total(amounts: List[float]) -> Dict[str, Any]:
    """Calculate the exact sum of a list of numeric amounts."""
    try:
        validated = CalculateTotalInput(amounts=amounts)
    except Exception as e:
        msg = str(e)
        if "Value error, " in msg:
            msg = msg.split("Value error, ")[-1]
        return validation_error(msg)

    total_sum = round(sum(validated.amounts), 2)
    return {
        "success": True,
        "amounts": validated.amounts,
        "count": len(validated.amounts),
        "total": total_sum
    }
