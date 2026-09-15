# Smart Finance Agent – Goal-Based Tool-Calling Agent with MCP

A professional, production-ready AI-powered personal finance assistant built with **Python 3.11+**, **FastMCP (Model Context Protocol)**, **FastAPI**, **SQLite**, **Pydantic**, **Ollama**, and a modern web interface.

The system allows users to ask natural-language questions about their expenses, budgets, and spending. The agent understands the user's goal, dynamically selects and calls tools over standard MCP client-server protocol, records real observations, generates grounded responses, and verifies claims through a reflection/verification layer.

---

## Architecture

```
User (Web UI / API)
       ↓
 Fast API Backend (/api/ask)
       ↓
  Agent Loop (MAX_ITERATIONS = 5)
       ↓
   LLM Policy Layer (Ollama / Local LLM)
       ↓ (Dynamic Decision: tool_call / final_answer)
   MCP Client (FinanceMCPClient)
       ↓ (Stdio Transport Handshake & JSON-RPC Protocol)
   MCP Server (MCPServer / FastMCP)
       ↓
 Finance Tools (get_expenses, get_budget, compare_budget, calculate_total, get_spending_by_category)
       ↓
 SQLite Database (expenses & budgets tables)
       ↓
 Real Tool Results & Observations
       ↓
 Reflection & Grounding Layer (ReflectionEvaluator)
       ↓
 Verified Response → User Interface
```

---

## Requirement Mapping Matrix

| Requirement | Implementation Details | Target File |
| :--- | :--- | :--- |
| **Practical Problem** | Natural language analysis of personal expenses and budgets | [`frontend/index.html`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/frontend/index.html) |
| **LLM Policy** | Ollama integration with Pydantic JSON validation & fallback | [`agent/llm_policy.py`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/agent/llm_policy.py) |
| **MCP Tools** | 5 finance tools: `get_expenses`, `get_budget`, `calculate_total`, `compare_budget`, `get_spending_by_category` | [`mcp_server/tools/`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/mcp_server/tools/) |
| **MCP Boundary** | Real stdio client-server protocol connection & handshake | [`mcp_client/client.py`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/mcp_client/client.py) & [`mcp_server/server.py`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/mcp_server/server.py) |
| **Dynamic Agent Loop** | Iterative loop bounded by `MAX_ITERATIONS = 5` | [`agent/agent_loop.py`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/agent/agent_loop.py) |
| **Real Execution** | Actual SQLite queries & numeric calculations (No hardcoded/fake data) | [`database/database.py`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/database/database.py) |
| **Grounded Answer** | Answers derived exclusively from recorded tool observations | [`agent/agent_loop.py`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/agent/agent_loop.py) |
| **Reflection Layer** | Independent audit checking numerical claims & budget statuses | [`reflection/evaluator.py`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/reflection/evaluator.py) |
| **Reliability** | Exception handling for missing data, unknown tools, malformed JSON | [`tests/test_failures.py`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/tests/test_failures.py) |
| **Automated Tests** | 22 Pytest unit and integration tests covering all paths | [`tests/`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/tests/) |

---

## Directory Structure

```
smart-finance-mcp-agent/
├── README.md
├── requirements.txt
├── .env.example
├── .env
├── .gitignore
├── backend/
│   ├── main.py
│   └── config.py
├── agent/
│   ├── agent_loop.py
│   ├── llm_policy.py
│   ├── schemas.py
│   └── observations.py
├── mcp_client/
│   ├── client.py
│   └── tool_discovery.py
├── mcp_server/
│   ├── server.py
│   └── tools/
│       ├── expenses.py
│       ├── budgets.py
│       ├── calculator.py
│       └── analytics.py
├── database/
│   ├── database.py
│   ├── init_db.py
│   └── seed_data.py
├── reflection/
│   ├── evaluator.py
│   └── schemas.py
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
└── tests/
    ├── test_mcp.py
    ├── test_tools.py
    ├── test_agent.py
    ├── test_reflection.py
    └── test_failures.py
```

---

## Installation & Quickstart

### 1. Prerequisites
- Python 3.11+ installed.
- (Optional) [Ollama](https://ollama.com/) running locally for local LLM inference (`qwen2.5:7b` or `llama3.2`).

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize & Seed Database
```bash
python -m database.seed_data
```

### 4. Run Automated Tests
```bash
python -m pytest tests/ -v
```

### 5. Launch Application Server
```bash
python -m backend.main
```
Open your browser and navigate to: **`http://localhost:8000`**

---

## Example Questions & Execution Flow

### Query 1: Budget Exceeded Inquiry
> **Question**: *"Did I exceed my food budget?"*

#### Terminal Execution Trace Log:
```text
============================================================
SMART FINANCE AGENT - GOAL-BASED AGENT LOOP
============================================================
USER QUESTION:
"Did I exceed my food budget?"

MCP SERVER & HANDSHAKE:
✓ Connected to MCP Server via stdio protocol
✓ MCP Handshake successful
TOOLS DISCOVERED (5):
  • get_expenses
  • get_budget
  • calculate_total
  • compare_budget
  • get_spending_by_category
------------------------------------------------------------

[ITERATION 1/5]
  Selected Tool: `get_expenses`
  Arguments: {'category': 'Food', 'month': '2026-09'}
  Reasoning: Step 1: Retrieve actual expenses for Food in September 2026.
  OBSERVATION: {'success': True, 'category': 'Food', 'month': '2026-09', 'expenses': [...], 'count': 3, 'total': 6000.0}

[ITERATION 2/5]
  Selected Tool: `get_budget`
  Arguments: {'category': 'Food', 'month': '2026-09'}
  Reasoning: Step 2: Retrieve the configured budget amount for Food.
  OBSERVATION: {'success': True, 'category': 'Food', 'month': '2026-09', 'budget': 5000.0}

[ITERATION 3/5]
  Selected Tool: `compare_budget`
  Arguments: {'spent': 6000.0, 'budget': 5000.0}
  Reasoning: Step 3: Compare actual spending against budget.
  OBSERVATION: {'success': True, 'spent': 6000.0, 'budget': 5000.0, 'difference': 1000.0, 'status': 'OVER_BUDGET', 'percentage_used': 120.0}

[ITERATION 4/5]
  FINAL DRAFT ANSWER:
  Yes, you exceeded your food budget by ₹1,000.00 this month.

------------------------------------------------------------
REFLECTION & GROUNDING VERIFICATION:
  GROUNDING STATUS: VERIFIED
  SUMMARY: All numerical figures and statuses were successfully grounded in MCP observations.
============================================================
```

---

## Failure & Partial-Data Scenarios

### Scenario A: Missing / Partial Data (October 2026)
> **Question**: *"How much did I spend in October 2026?"*
- **Behavior**: The agent queries `get_expenses(month="2026-10")`, receives `{"success": True, "count": 0, "total": 0.0}` from SQLite.
- **Output**: *"No expense records were found for that category in 2026-10."*
- **Grounding Guarantee**: The system refuses to fabricate October spending.

### Scenario B: Unsupported Claim Detection & Self-Correction
- **Draft Answer**: *"You spent ₹8,000 on food."*
- **Observation**: `total = 6000.0`
- **Reflection Audit**: Detects `8000.0` is unverified, changes status to `UNSUPPORTED_CLAIMS`, rejects draft, and outputs verified observation text: `[VERIFIED OBSERVATIONS]: Total spent on Food (2026-09): ₹6,000.00.`

---

## License & Author
Built for **Smart Finance Agent** demonstration using Python, MCP SDK, FastAPI, SQLite, and Pydantic.
#   S m a r t - F i n a n c e  
 