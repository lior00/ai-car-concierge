# System Architecture

## Overview

```
User → Streamlit UI (frontend/app.py)
          ↓  HTTP POST /chat
     FastAPI Backend (backend/main.py)
          ↓
     Agent Orchestrator (backend/agent/orchestrator.py)
          ↓ tool calls
     ┌────────────────────────────────────────────────┐
     │  Tool: query_inventory  → sql_tool.py          │
     │  Tool: search_knowledge → rag_tool.py          │
     │  Tool: send_email       → email_tool.py        │
     │  Tool: reserve_vehicle  → reservation_tool.py  │
     └────────────────────────────────────────────────┘
          ↓ always runs after query_inventory returns
     Policy Guard (backend/agent/tools/policy_guard.py)
          ↓
     SQLite DB  /  ChromaDB  /  Resend API
```

## Component Responsibilities

| Component | Owns | Does NOT own |
|---|---|---|
| `orchestrator.py` | Tool routing, chat history, response synthesis | Business rules |
| `sql_tool.py` | Natural language → SQL → rows | Policy, writes |
| `rag_tool.py` | Query → vector search → chunks | SQL, business logic |
| `policy_guard.py` | Year eligibility check | DB access, LLM calls |
| `email_tool.py` | HTTP call to email API | Routing, policy |
| `reservation_tool.py` | DB UPDATE stock_count | Policy check (delegated to orchestrator) |

## Key Design Decisions

1. **Policy as code, not prompt:** `policy_guard.py` is a pure Python function. The LLM cannot override it regardless of user input.

2. **Hybrid RAG:** SQL handles structured queries (price, specs, availability). ChromaDB handles unstructured policy/FAQ queries. The orchestrator chooses which tool to call based on query type.

3. **No LangChain required:** Uses Anthropic tool-use API directly for maximum control and minimal dependencies.

4. **SQLite + ChromaDB in-process:** Zero external infrastructure. Both databases are file-backed. Deploy as a single container.

5. **Automation safety:** `email_tool` and `reservation_tool` are only called after the orchestrator has confirmed policy compliance. The system prompt explicitly forbids calling them for pre-2022 vehicles.
