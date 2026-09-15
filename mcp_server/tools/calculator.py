from typing import List, Dict, Any

def execute_calculate_total(amounts: List[float]) -> Dict[str, Any]:
    """Calculate the exact sum of a list of numeric amounts."""
    if not isinstance(amounts, list):
        return {
            "success": False,
            "error": "INVALID_ARGUMENT",
            "message": "Input 'amounts' must be a list of numbers."
        }

    valid_numbers = []
    for item in amounts:
        try:
            valid_numbers.append(float(item))
        except (ValueError, TypeError):
            return {
                "success": False,
                "error": "INVALID_ARGUMENT",
                "message": f"Invalid numeric item in amounts list: {item}"
            }

    total_sum = round(sum(valid_numbers), 2)
    return {
        "success": True,
        "amounts": valid_numbers,
        "count": len(valid_numbers),
        "total": total_sum
    }
