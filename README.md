# 💼 Smart Finance Agent — Enterprise AI Assistant

> **Goal-Based Tool-Calling Assistant with Model Context Protocol (MCP), Hybrid RAG Document Intelligence, and Reflection Grounding Audit**

Built with **Python 3.11 / 3.12**, **FastAPI**, **FastMCP / MCP SDK**, **Pydantic v2**, **SQLite**, **Ollama**, and **HTML5/CSS3/JS**.

---

## 🎯 Overview & Architecture

The **Smart Finance Agent** is an enterprise AI financial assistant engineered to resolve multi-step natural language questions about personal expenses, budgets, category analytics, and financial document terms (taxes, credit card rules, warranties).

Unlike conventional chat agents that hallucinate financial figures or follow rigid predetermined script sequences, this system utilizes:
1. **Model Context Protocol (MCP)**: Decoupled stdio JSON-RPC transport protocol connecting the agent to database query tools.
2. **Hybrid Dual-Engine**: Structured SQL queries against an ACID SQLite database combined with an unstructured RAG vector store for policy documentation.
3. **Model-Mediated Dynamic Policy**: LLM-driven decision loop (bounded at `MAX_ITERATIONS = 5`) powered by local Ollama (`qwen2.5:7b`), supporting observation-dependent replanning and bounded repair.
4. **Independent Reflection & Grounding Layer (`reflection/`)**: Audits draft answers against real tool observations, catching numerical discrepancies, category contradictions, timeframe mismatches, or unsupported qualitative claims, and regenerating verified responses strictly from evidence.
5. **Degraded Offline Mode**: Transparent, clearly labelled fallback for offline testing and environments without an active Ollama instance.

```text
                       ┌──────────────────────────────────────────────┐
                       │           User Interface (Web UI)            │
                       └──────────────────────┬───────────────────────┘
                                              │ REST API /api/ask
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │             FastAPI Backend Server           │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │     Agent Loop (MAX_ITERATIONS = 5)          │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │ LLM Policy Layer (Ollama / Local LLM)        │
                       └──────────────────────┬───────────────────────┘
                                              │ Selects tool_call over stdio JSON-RPC
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │           MCP Client & Discovery             │
                       └──────────────────────┬───────────────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
     ┌───────────────────────────────┐                 ┌───────────────────────────────┐
     │        Structured Tools       │                 │       Unstructured RAG        │
     │      (FastMCP Server)         │                 │         Vector Store          │
     ├───────────────────────────────┤                 ├───────────────────────────────┤
     │ • get_expenses                │                 │ • search_documents            │
     │ • get_budget                  │                 │   - Tax Policy 2026           │
     │ • compare_budget              │                 │   - Credit Card Terms         │
     │ • calculate_total             │                 │   - Receipts & Invoices       │
     │ • get_spending_by_category    │                 │   - Expense Policies          │
     └───────────────┬───────────────┘                 └───────────────┬───────────────┘
                     │                                                 │
                     ▼                                                 ▼
             SQLite Database                                   RAG Vector Store
       (expenses & budgets tables)                             (rag_store.json)
                     │                                                 │
                     └────────────────────────┬────────────────────────┘
                                              │ Real Tool Observations
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │ Reflection & Grounding Audit Layer           │
                       │ (Audits figures & prevents hallucinations)   │
                       └──────────────────────┬───────────────────────┘
                                              │ Verified Response
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │        Verified Answer & Live Trace          │
                       └──────────────────────────────────────────────┘
```

---

## 🛠️ MCP Tools & Input/Output Contracts

All tools use reusable **Pydantic v2 validation models** (`mcp_server/tools/validators.py`) and parameterized SQL statements before database execution:

| Tool Name | Parameters | Contract & Behavior | Return Format |
| :--- | :--- | :--- | :--- |
| `get_expenses` | `category` (opt), `month` (opt `YYYY-MM`), `start_date` (opt `YYYY-MM-DD`), `end_date` (opt `YYYY-MM-DD`) | Queries SQLite `expenses` table. Parameterized SQL with date & month validation. | `{"success": true, "category": ..., "month": ..., "expenses": [...], "count": N, "total": float}` |
| `get_budget` | `category` (req str), `month` (req str `YYYY-MM`) | Queries configured budget in SQLite `budgets` table. | `{"success": true, "category": ..., "month": ..., "budget": float}` |
| `compare_budget` | `spent` (req float), `budget` (req float) | Calculates `difference = spent - budget`, `percentage_used`, and `status`: `OVER_BUDGET` or `WITHIN_BUDGET`. | `{"success": true, "spent": float, "budget": float, "difference": float, "status": str, "percentage_used": float}` |
| `get_spending_by_category`| `month` (opt str `YYYY-MM`) | Aggregates spending grouped by category with grand total and highest spending category. | `{"success": true, "month": ..., "categories": [...], "grand_total": float, "highest_category": str, "highest_amount": float}` |
| `calculate_total` | `amounts` (req list of float) | Computes the arithmetic sum of arbitrary numeric values. | `{"success": true, "amounts": [...], "count": N, "total": float}` |
| `search_documents` | `query` (req str), `top_k` (opt int = 3) | Vector similarity search (TF-IDF cosine similarity) on financial policies and receipts. | `{"success": true, "query": ..., "matches_found": N, "results": [...]}` |

---

## 🧠 Decision Policy & Reflection Layer

### 1. Model-Mediated Decision Policy (`agent/llm_policy.py`)
- **Ollama Integration**: Passes question, tool schemas, and observation history to local LLM with structured output (`format="json"`).
- **Structured Pydantic Actions**: Validates model output using `LLMAction(action="tool_call" | "final_answer", tool_name=..., arguments=..., thought=...)`.
- **Bounded Error Recovery**: If the model produces malformed JSON, a 1-retry repair prompt is sent to Ollama with the specific schema error.
- **Dynamic Replanning**: The model receives actual observations in subsequent iterations and can select another tool (e.g. `get_expenses` -> `get_budget` -> `compare_budget` -> `final_answer`).
- **Clarification Trigger**: Ambiguous requests (e.g., *"Did I exceed my budget?"* with no category specified) trigger an immediate clarification question instead of silently guessing "Food".
- **Degraded Offline Fallback**: If Ollama is offline, a deterministic policy executes with dynamic date parsing and observation-driven error repair.

### 2. Reflection & Grounding Layer (`reflection/evaluator.py`)
- **Fact Auditing**: Extracts all numbers, categories, dates, and budget statuses from draft answers and cross-references them against actual observation records.
- **Contradiction Detection**: Detects when a draft claims "within budget" when observation says `OVER_BUDGET`, or mentions "Shopping" when observation was "Food".
- **Unsupported Claim Detection**: Flags ungrounded monetary figures (e.g., claiming ₹8,000 when observation was ₹6,000).
- **Safe Answer Repair**: Automatically regenerates answers strictly from available observation evidence without inventing new financial facts.
- **Grounding Statuses**: `VERIFIED`, `UNSUPPORTED_CLAIMS`, `CONTRADICTION`, `MISSING_EVIDENCE`, `MALFORMED_OBSERVATION`.

---

## 🚀 Installation & Quickstart

### 1. Prerequisites
- **Python 3.11** or **Python 3.12**
- (Optional) [Ollama](https://ollama.com/) with `qwen2.5:7b` for local model inference

### 2. Install Dependencies
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Initialize & Seed Database
```bash
python -m database.seed_data
python -m rag.seed_docs
```

### 4. Run Automated Test Suite
```bash
# Compilation check
python -m compileall -q agent backend database mcp_client mcp_server rag reflection tests

# Run all 56 tests with pytest
pytest tests/ -v
# or
python -m pytest tests/ -q
```

### 5. Start the Application
```bash
# Start FastAPI backend & Web UI
python -m backend.main
```
Open **`http://localhost:8000`** in your browser.

---

## 🧪 Automated Test Suite & Coverage

The repository includes **56 automated unit and integration tests** across 9 test modules with **100% pass rate**:

```text
tests/
├── test_agent.py                 # Multi-step loop flows & expense lookups (3 tests)
├── test_backend_api.py           # FastAPI REST endpoints & document upload (4 tests)
├── test_date_category_parsing.py # Timeframe/category extraction & clarification (7 tests)
├── test_failures.py              # Unknown tools, invalid arguments, 5-iter limit (5 tests)
├── test_mcp.py                   # MCP handshake & tool invocation (3 tests)
├── test_model_behavior.py        # Model decisions, observation replanning, stubs (7 tests)
├── test_rag.py                   # Vector store chunking & document search (4 tests)
├── test_reflection.py            # Reflection grounding, numbers, status, repair (9 tests)
└── test_tools.py                 # Tool validations, edge cases & date ranges (14 tests)
```

### Test Execution Summary
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1
56 passed in 55.48s (100% pass rate)
```

---

## 📋 Verified Execution Scenarios

### Scenario A: Quantitative Budget Comparison (Multi-Step MCP Trace)
* **Question**: *"Did I exceed my food budget in September 2026?"*
* **Trace**:
  1. `get_expenses(category='Food', month='2026-09')` ➔ Total spent: **₹6,000.00**
  2. `get_budget(category='Food', month='2026-09')` ➔ Budget: **₹5,000.00**
  3. `compare_budget(spent=6000.0, budget=5000.0)` ➔ Status: **OVER_BUDGET** by **₹1,000.00**
* **Reflection**: Verified against tool outputs.
* **Verified Answer**: *"Yes, you exceeded your Food budget by ₹1,000.00."*

### Scenario B: Ambiguous Parameter Clarification
* **Question**: *"Did I exceed my budget?"*
* **Decision**: Target category is unspecified; agent detects ambiguous budget inquiry.
* **Verified Answer**: *"Could you please specify which budget category you would like to check? Available categories include: Food, Transport, Shopping, Bills, Entertainment, Healthcare, Travel."*

### Scenario C: Reflection Catching Ungrounded Numbers
* **Tool Observation**: `get_expenses(total=6000.0, category='Food')`
* **Draft Answer**: *"You spent ₹8,000 on food this month."*
* **Reflection Status**: `UNSUPPORTED_CLAIMS` (Number 8,000 does not match observed 6,000).
* **Corrected Answer**: *"Based on verified records, you spent a total of ₹6,000.00 on Food in 2026-09."*

### Scenario D: Document Policy Retrieval (Hybrid RAG)
* **Question**: *"What is the tax deduction policy for home office internet in 2026?"*
* **Tool Call**: `search_documents(query="tax deduction home office internet", top_k=3)`
* **Verified Answer**: *"Based on financial document '2026 Personal Income Tax & Deduction Policy': Under the 2026 Income Tax rules, individuals can claim tax deductions for work-from-home expenses, up to $1,500 per year for high-speed internet..."*

---

## 🔒 Security & Best Practices

- **Parameterized SQL**: All database operations use `?` parameter substitution; zero string interpolation or SQL injection risk.
- **Pydantic Validation**: All tool arguments, action schemas, and API requests validated via Pydantic v2 schemas before execution.
- **Bound Safety**: Iteration limit strictly enforced at `MAX_ITERATIONS = 5` to prevent infinite loops.
- **Safe Error Responses**: API returns sanitized JSON error messages without leaking internal tracebacks to clients.
- **CORS Configuration**: Restricts access to configured origins defined in `backend/config.py`.

---

## 📝 Known Limitations

1. **Local LLM Performance**: When running with Ollama on hardware without GPU acceleration, model response latency depends on host CPU capacity.
2. **Offline Mode Scope**: The degraded fallback policy covers personal expense and budget queries present in the project domain. Complex conversational chit-chat is deferred to the LLM.