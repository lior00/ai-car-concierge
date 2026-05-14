# AI Car Concierge

A web-based AI chatbot for a premium car dealership. Built in 24 hours for the AI Engineering Home Task assessment.

**Live URL:** https://ai-car-concierge.onrender.com

---

## What It Does

- **Hybrid RAG:** Routes questions between a SQL inventory database and a ChromaDB vector store backed by 5 policy/FAQ documents.
- **Policy Enforcement:** Vehicles from 2021 or earlier are "Pending De-listing." The bot acknowledges their existence but refuses to sell them — enforced at the code layer, not just via prompt.
- **Email Automation:** Detects purchase intent + customer email → sends a real confirmation email via Mailtrap SMTP sandbox.
- **Reservation Automation:** "Reserve this car" → decrements `stock_count` in SQLite with a single atomic UPDATE.

---

## AI Tools Used & How They Helped

| Tool | How it helped |
|---|---|
| **Claude Code (claude-sonnet-4-6)** | Scaffolded the entire project: folder structure, all source files, tests, and documentation. Estimated time saved: ~18 of 24 hours. |
| **Anthropic API (tool-use)** | Powers the agent orchestrator. Claude decides which tool to call (SQL, RAG, email, reservation) based on user intent. |
| **Anthropic API (text generation)** | Converts natural language to SQL inside `sql_tool.py`. |
| **ChromaDB** | In-process vector store for policy/FAQ document retrieval. No external service required. |
| **sentence-transformers** | Local embedding model — no OpenAI quota needed for RAG ingestion. |

**Architectural insight from AI assistance:** The key design decision suggested by Claude was to make `policy_guard.py` a pure Python function at the code layer — not an LLM instruction. This makes the 2022+ rule deterministic and immune to prompt injection, which is the correct production-grade approach.

---

## Local Setup

### Prerequisites

- **Python 3.12.10** — tested and confirmed working. Python 3.13+ has dependency conflicts with `sentence-transformers` and `chromadb`; use 3.12.x.
- A [Mailtrap](https://mailtrap.io) account (free) for email testing.
- An [Anthropic](https://console.anthropic.com) API key.

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/lior00/ai-car-concierge.git
cd ai-car-concierge

# 2. Create a virtual environment pinned to Python 3.12
py -3.12 -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
copy .env.example .env    # Windows
# cp .env.example .env   # macOS / Linux
# Then edit .env and fill in ANTHROPIC_API_KEY, MAILTRAP_USERNAME, MAILTRAP_PASSWORD

# 5. Start the backend
# First run: automatically migrates the SQLite DB and ingests the knowledge base
uvicorn backend.main:app --reload --port 8000

# 6. Start the frontend (separate terminal, same venv)
streamlit run frontend/app.py
```

Open http://localhost:8501 in your browser.

### Getting Mailtrap Credentials

1. Sign up at https://mailtrap.io (free).
2. Go to **Email Testing → Inboxes → your inbox → SMTP Settings**.
3. Select **Python** from the integrations dropdown.
4. Copy the `username` and `password` values into `.env`.

Sent emails appear in your Mailtrap inbox — no real delivery, no domain verification needed.

### Embedding Provider

By default `.env.example` uses `EMBEDDING_PROVIDER=sentence-transformers` which downloads a small model locally on first run (~90MB, one-time). No OpenAI key required. If you prefer OpenAI embeddings, set `EMBEDDING_PROVIDER=openai` and add your `OPENAI_API_KEY`.

> **Note:** If you switch embedding providers after the knowledge base has already been ingested, delete `data/chroma_db/` to force re-ingestion with the new model.

### Run Tests

```bash
pytest
```

---

## Architecture

```
User → Streamlit UI (port 8501)
          ↓ POST /chat
     FastAPI Backend (port 8000)
          ↓
     Agent Orchestrator (Anthropic tool-use API)
          ├── query_inventory  → SQLite (data/inventory.db)
          ├── search_knowledge → ChromaDB (data/chroma_db/)
          ├── send_email       → Mailtrap SMTP sandbox
          └── reserve_vehicle  → SQLite UPDATE stock_count
          ↓ always runs after query_inventory
     policy_guard.py  (pure function: year >= 2022 = SELLABLE)
```

See [docs/architecture.md](docs/architecture.md) for full detail.

---

## Key Files

| File | Purpose |
|---|---|
| `backend/agent/tools/policy_guard.py` | **Critical.** 2022+ rule as deterministic code. |
| `backend/agent/orchestrator.py` | Agent loop using Anthropic tool-use API. |
| `backend/agent/prompts/system_prompt.txt` | Agent persona and tool-routing instructions. |
| `data/knowledge_base/policy.md` | Source of truth for 2022+ sales policy. |
| `data/inventory.sql` | 100 vehicles (2019–2025 spread for policy testing). |

---

## Environment Variables

See [.env.example](.env.example) for all variables with descriptions.

**Required:**
- `ANTHROPIC_API_KEY`
- `MAILTRAP_USERNAME` + `MAILTRAP_PASSWORD` — for email automation

**Optional:**
- `OPENAI_API_KEY` — only if `EMBEDDING_PROVIDER=openai`
- `EMBEDDING_PROVIDER` — defaults to `sentence-transformers`

---

## Deployment (Railway)

1. Push to GitHub.
2. Connect repo to Railway.
3. Set environment variables in Railway dashboard (same keys as `.env`).
4. Railway auto-deploys using `railway.toml` and `Dockerfile`.
5. For Streamlit frontend: deploy as a second Railway service with start command:
   ```
   streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0
   ```
   Set `BACKEND_URL` env var to the FastAPI service URL.
