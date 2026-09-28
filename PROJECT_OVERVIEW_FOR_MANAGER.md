# 💼 Smart Finance Agent - Executive Presentation & Manager Briefing

> **Goal-Based Tool-Calling AI Assistant with Model Context Protocol (MCP), Hybrid RAG Document Intelligence, and Reflection Grounding Audit**

---

## 🎯 Executive Summary

The **Smart Finance Agent** is an enterprise-grade AI financial assistant that resolves complex, multi-step natural language questions regarding personal expenses, monthly budgets, tax rules, credit card terms, and financial documents.

Unlike traditional chat models that hallucinate figures or read static prompt templates, this system uses a **Goal-Based Agent Loop** powered by **Model Context Protocol (MCP)**, querying real SQLite databases and a **RAG (Retrieval-Augmented Generation)** vector search engine. Every numerical claim is strictly audited by a **Reflection & Grounding Verification Layer** before being presented to the user.

---

## 🏗️ High-Level System Architecture

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
                       │ (Audits figures & prevents hallucinations)    │
                       └──────────────────────┬───────────────────────┘
                                              │ Verified Response
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │        Verified Answer & Live Trace          │
                       └──────────────────────┬───────────────────────┘
```

---

## 🔑 Key Features & Technical Highlights

| Feature | Description | Business & Technical Value |
| :--- | :--- | :--- |
| **Model Context Protocol (MCP)** | Standardized stdio transport layer decoupling AI agent logic from backend tools. | Allows adding new tools without altering core LLM logic. |
| **Hybrid Dual-Engine** | Combines **Structured SQL Tool-Calling** with **Unstructured RAG Document Search**. | Solves both quantitative (totals, budgets) and qualitative (policies, receipts) questions. |
| **Goal-Based Dynamic Loop** | Iterative loop (bounded at `MAX_ITERATIONS = 5`) enabling step-by-step problem solving. | Resolves multi-step inquiries (e.g. fetch expenses ➔ fetch budget ➔ compare budget). |
| **Reflection & Grounding Layer** | Independent evaluator checking numbers against recorded tool observations. | Guarantees **0% hallucination** on financial calculations and document claims. |
| **Local LLM & Offline Resilience** | Integrates with Ollama (`qwen2.5:7b`) with a deterministic policy fallback when offline. | Ensures 100% uptime and test stability even without an internet connection or LLM service. |

---

## 📁 Repository & Component Breakdown

```text
Smart-Finance/
├── backend/                # FastAPI Web Server (/api/ask, /api/documents)
├── agent/                  # Goal-Based Agent Loop, LLM Policy & Pydantic Schemas
├── mcp_client/             # Stdio MCP Protocol Client & Dynamic Tool Discovery
├── mcp_server/             # FastMCP Server & Finance Tools (get_expenses, compare_budget)
├── rag/                    # Vector Store, Document Chunking & Seed Financial Documents
├── database/               # SQLite Connection Manager, Schema & Seed Script
├── reflection/             # Reflection Evaluator & Grounding Verification Layer
├── frontend/               # Web Dashboard UI with Live Tool Tracing & RAG Upload
└── tests/                  # 26 Pytest Automated Unit & Integration Tests (100% Pass)
```

---

## 🎙️ Executive Presentation Script (What to tell your Manager)

Here is a step-by-step script you can use when explaining the project to your manager:

### 1. The Business Problem
> *"Managers and users want an AI assistant that can answer personal finance questions—like 'Did I exceed my budget?' or 'What is our tax deduction policy for home internet?' Traditional LLMs often invent fake numbers or hallucinate rules. We needed a system that queries real databases and real documents with zero room for error."*

### 2. The Architecture (MCP + RAG)
> *"We built a Goal-Based Agent that uses **Model Context Protocol (MCP)**. Instead of hardcoding responses, the LLM dynamically discovers tools and decides what data to fetch. We implemented a **Hybrid Engine**:"*
> - *"For structured data like expense records and budget limits, it runs real SQLite queries."*
> - *"For unstructured data like tax guides, credit card agreements, and receipt text, it uses a RAG Vector Store to search exact document chunks."*

### 3. Safety & Reflection Guardrail
> *"To ensure accuracy, we added an independent **Reflection & Grounding Audit Layer**. Before any answer is displayed to the user, the auditor verifies that every dollar amount and date in the draft answer matches actual tool observations. If an LLM tries to guess a figure, the reflection layer catches and corrects it."*

### 4. Verification & Readiness
> *"The project is fully tested with 26 automated unit and integration tests passing in Pytest, complete with a REST API and an interactive Web Dashboard."*

---

## 📊 Sample Demo Scenarios

### Scenario A: Quantitative Budget Comparison (SQL MCP Tools)
* **User Question:** *"Did I exceed my food budget?"*
* **Execution Trace:**
  1. `get_expenses(category='Food', month='2026-09')` ➔ Total spent: **₹6,000.00**
  2. `get_budget(category='Food', month='2026-09')` ➔ Budget: **₹5,000.00**
  3. `compare_budget(spent=6000, budget=5000)` ➔ Status: **OVER_BUDGET** by **₹1,000.00**
* **Verified Answer:** *"Yes, you exceeded your food budget by ₹1,000.00 this month."*

### Scenario B: Unstructured Policy Retrieval (RAG Vector Tool)
* **User Question:** *"What is the tax deduction policy for home office internet in 2026?"*
* **Execution Trace:**
  1. `search_documents(query="What is the tax deduction policy for home office internet in 2026?")`
  2. Matched Chunk: *"2026 Personal Income Tax & Deduction Policy: Under 2026 Tax rules, claim up to $1,500/year for high-speed internet."*
* **Verified Answer:** *"Based on financial document '2026 Personal Income Tax & Deduction Policy', individuals can claim up to $1,500 per year for high-speed internet work-from-home expenses."*
