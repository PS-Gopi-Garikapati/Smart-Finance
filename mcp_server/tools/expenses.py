from typing import Dict, Any, Optional
from database.database import execute_query
from mcp_server.tools.validators import (
    GetExpensesInput, #validates the input fields.
    validation_error, #creates an error response for invalid input.
    database_error, #creates an error response for database failures.
    validate_month_format, 
    validate_date_format
    #are imported but are not directly called in the code shown.
)
#Step 1: Accept the user's filters
def execute_get_expenses(
    category: Optional[str] = None,
    month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve expense records from SQLite based on category, month, or date range."""
   #Step 2: Validate the input
    try:
        validated = GetExpensesInput(
            category=category,
            month=month,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        msg = str(e)
        if "Value error, " in msg:
            msg = msg.split("Value error, ")[-1]
        return validation_error(msg)
    #Step 3: Create the basic SQL query
    query = "SELECT id, date, category, amount, description FROM expenses WHERE 1=1" #WHERE 1=1 is a convenient starting condition so additional AND filters can be appended.
    params = []
#params = [] creates an empty list to store the values for those filters.
    #Filter by category
    if validated.category:
        query += " AND LOWER(category) = LOWER(?)"
        params.append(validated.category)

    # For a specific date, retrieve only records matching that exact date
    if validated.start_date and validated.end_date and validated.start_date == validated.end_date:
        query += " AND date = ?"
        params.append(validated.start_date)
    else:
        if validated.month:
            query += " AND strftime('%Y-%m', date) = ?"
            params.append(validated.month)

        if validated.start_date:
            query += " AND date >= ?"
            params.append(validated.start_date)

        if validated.end_date:
            query += " AND date <= ?"
            params.append(validated.end_date)

    query += " ORDER BY date ASC"
#Step 8: Execute the query and calculate the total
    try:
        #execute_query() sends the SQL query and parameters to SQLite.
        rows = execute_query(query, tuple(params), db_path=db_path)
        #sum(r["amount"] for r in rows) adds the amount from each matching expense record.
        total = round(sum(r["amount"] for r in rows), 2)
        return {
            "success": True, #indicates the query succeeded.
            "category": validated.category, #the requested category filter.
            "month": validated.month, #the requested month filter.
            "start_date": validated.start_date,
            "end_date": validated.end_date,
            "expenses": rows, #the matching expense records.
            "count": len(rows), #number of matching records.
            "total": total #sum of the matching expense amounts.
        }
    except Exception as e:
        return database_error(str(e))
