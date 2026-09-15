# 💰 Smart Finance Agent

> **Goal-Based Tool-Calling Financial Assistant with Model Context Protocol (MCP)**

A professional, production-ready AI-powered personal finance assistant built with **Python 3.11+**, **FastMCP**, **FastAPI**, **SQLite**, **Pydantic**, **Ollama**, and a modern Web UI.

The system processes natural language questions about expenses, budgets, and category spending. The agent understands user goals, dynamically selects and calls tools over standard MCP (stdio JSON-RPC protocol), records real database observations, generates grounded responses, and verifies all numerical claims through an independent **Reflection & Grounding Audit Layer**.

---

## 🚀 Key Features

- **Goal-Based Agent Loop**: Dynamic iteration loop bounded by `MAX_ITERATIONS = 5` to solve multi-step financial inquiries.
- **Model Context Protocol (MCP)**: Strict client-server stdio transport layer exposing 5 specialized financial tools.
- **Real Execution**: All queries execute against actual SQLite database records—zero fake data or hardcoded responses.
- **Dual Policy Engine**: Connects to **Ollama** (`qwen2.5:7b` / `llama3.2`) for local LLM inference with automated fallback to a deterministic policy engine when offline.
- **Reflection & Grounding Layer**: Audits draft answers against recorded tool observations to prevent hallucinations or unverified financial claims.
- **Interactive Web Interface**: Clean web dashboard built with HTML5, CSS3, and JavaScript to ask questions and inspect live tool trace execution logs.

---

## 🏗️ System Architecture

```text
User Question (Web UI / REST API)
       │
       ▼
 FastAPI Backend (/api/ask)
       │
       ▼
 Agent Loop (MAX_ITERATIONS = 5)
       │
       ▼
 LLM Policy Layer (Ollama / Local LLM / Deterministic Fallback)
       │ (Selects: tool_call or final_answer)
       ▼
 MCP Client (FinanceMCPClient)
       │ (Stdio Transport & JSON-RPC Handshake)
       ▼
 MCP Server (MCPServer / FastMCP)
       │
       ├─► get_expenses
       ├─► get_budget
       ├─► compare_budget
       ├─► calculate_total
       └─► get_spending_by_category
       │
       ▼
 SQLite Database (expenses & budgets tables)
       │
       ▼
 Recorded Tool Observations
       │
       ▼
 Reflection & Grounding Layer (ReflectionEvaluator)
       │
       ▼
 Verified Answer → Web UI / API Response
```

---

## 📊 Requirement Mapping Matrix

| Requirement | Description & Implementation | Target File |
| :--- | :--- | :--- |
| **Practical Problem** | Natural language analysis of personal expenses, budgets, and spending trends | [`frontend/index.html`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/frontend/index.html) |
| **LLM Policy** | Ollama chat integration with Pydantic JSON validation & rule fallback | [`agent/llm_policy.py`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/agent/llm_policy.py) |
| **MCP Tools** | 5 finance tools: `get_expenses`, `get_budget`, `calculate_total`, `compare_budget`, `get_spending_by_category` | [`mcp_server/tools/`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/mcp_server/tools/) |
| **MCP Protocol** | Real stdio client-server protocol connection & JSON-RPC handshake | [`mcp_client/client.py`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/mcp_client/client.py) |
| **Dynamic Agent Loop** | Bounded step-by-step iteration loop (`MAX_ITERATIONS = 5`) | [`agent/agent_loop.py`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/agent/agent_loop.py) |
| **Real Database Execution** | Real SQLite queries for expense records and configured budgets | [`database/database.py`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/database/database.py) |
| **Grounded Answers** | Answers generated strictly from accumulated observation state | [`agent/agent_loop.py`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/agent/agent_loop.py) |
| **Reflection Audit** | Independent verification checking numerical figures against recorded observations | [`reflection/evaluator.py`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/reflection/evaluator.py) |
| **Reliability & Edge Cases**| Exception handling for missing data, unknown tools, and malformed JSON | [`tests/test_failures.py`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/tests/test_failures.py) |
| **Automated Tests** | 22 Pytest unit and integration test cases | [`tests/`](file:///c:/Users/GopiChandGarikapati/Desktop/L2%20smart%20finace/tests/) |

---

## 📁 Repository Structure

```text
Smart-Finance/
├── README.md               # Project documentation
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore configuration
├── backend/
│   ├── main.py             # FastAPI entrypoint & static file server
│   └── config.py           # Backend settings & paths
├── agent/
│   ├── agent_loop.py       # Main goal-based loop controller
│   ├── llm_policy.py       # Ollama API client & fallback policy engine
│   ├── schemas.py          # Pydantic models for actions and responses
│   └── observations.py    # Observation state tracker
├── mcp_client/
│   ├── client.py           # Stdio MCP client wrapper
│   └── tool_discovery.py   # MCP tool discovery & prompt formatter
├── mcp_server/
│   ├── server.py           # MCP server implementation
│   └── tools/             # MCP tool implementations
│       ├── expenses.py     # Expense search tool
│       ├── budgets.py      # Budget retrieval tool
│       ├── calculator.py   # Total calculation tool
│       └── analytics.py   # Category comparison tool
├── database/
│   ├── database.py         # SQLite connection manager & queries
│   ├── init_db.py          # Schema creation script
│   └── seed_data.py        # Database seed script
├── reflection/
│   ├── evaluator.py        # Reflection grounding & verification auditor
│   └── schemas.py          # Reflection result models
├── frontend/
│   ├── index.html          # Web dashboard interface
│   ├── style.css           # Styling rules
│   └── script.js           # Frontend interactive API logic
└── tests/                  # Pytest test suite (22 tests)
    ├── test_agent.py
    ├── test_failures.py
    ├── test_mcp.py
    ├── test_reflection.py
    └── test_failures.py
```

---

## ⚡ Quickstart Guide

### 1. Prerequisites
- **Python 3.11+** installed.
- (Optional) [Ollama](https://ollama.com/) running locally (`ollama run qwen2.5:7b` or `llama3.2`).

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize & Seed Database
```bash
python -m database.seed_data
```

### 4. Run Automated Test Suite
```bash
python -m pytest tests/ -v
```

### 5. Start the Web Server
```bash
python -m backend.main
```
Open your browser and navigate to: **`http://localhost:8000`**

---

## 🔍 Example Execution Flow

### Question: *"Did I exceed my food budget?"*

#### Terminal Execution Log:
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

## 🛡️ Self-Correction & Grounding Examples

- **Scenario A (Missing Data)**: Asking *"How much did I spend in October 2026?"* queries SQLite, receives `0.0`, and outputs: *"No expense records were found for that category in 2026-10."*
- **Scenario B (Reflection Audit)**: If a draft answer mentions an unverified number (e.g., *"₹8,000 on food"* when tool recorded `₹6,000`), the reflection audit flags `UNSUPPORTED_CLAIMS` and replaces the draft with grounded observation facts.

---

## 📄 License
Built for **Smart Finance Agent** demonstration using Python 3.11, FastMCP, FastAPI, SQLite, and Pydantic.