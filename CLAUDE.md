# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLM-first agentic intelligence platform for clinical trial operations (CODM - Clinical Operations Data Management). FastAPI backend with React frontend. Agents autonomously investigate data quality, enrollment funnels, and operational metrics across clinical trial sites using a PRPA (Perceive-Reason-Plan-Act-Reflect) loop.

## Commands

### Backend
```bash
# Activate virtual environment (ALWAYS do this first)
source .venv/bin/activate

# Run backend server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Run all tests
pytest backend/tests/ -v

# Run a single test file
pytest backend/tests/test_agents.py -v

# Run a specific test
pytest backend/tests/test_agents.py::test_function_name -v

# Generate synthetic data
python -m data_generators.run_all
```

### Frontend
```bash
cd frontend
npm install
npm run dev    # Vite dev server on port 5000
```

## Architecture

### PRPA Agent Loop (Core Pattern)
Each agent (`backend/agents/`) runs an autonomous investigation loop (max 3 iterations):
1. **Perceive** — gather raw signals via SQL tools
2. **Reason** — LLM generates hypotheses from perceptions
3. **Plan** — LLM decides which tools to invoke next (dynamic tool selection)
4. **Act** — execute planned tools
5. **Reflect** — LLM evaluates if the investigation goal is satisfied

`BaseAgent` in `backend/agents/base.py` defines this loop. `AgentContext` carries mutable state across iterations. Agents stream progress to clients via WebSocket `on_step` callbacks.

### Conductor Routing
`backend/conductor/router.py` — `ConductorRouter` uses LLM semantic routing (not keyword matching) to decide which agents to invoke for a natural-language query. It can run multiple agents in parallel with isolated DB sessions, then synthesize findings across agents.

### LLM Client Stack
`backend/llm/` — Abstract `LLMClient` base with two implementations:
- `GeminiClient` (primary) — uses google-genai SDK via Replit AI Integrations
- `AzureOpenAIClient` (fallback)
- `FailoverLLMClient` wraps both: tries Gemini first, falls back to Azure OpenAI

All LLM calls use structured JSON responses. Temperature is 0.0 for deterministic outputs.

### Prompt Management
All prompts live as `.txt` files in `/prompt/` directory. `backend/prompts/manager.py` loads them at runtime with `{variable_name}` placeholder substitution. Never hardcode prompts in Python code.

Prompt naming convention: `{agent_id}_{phase}.txt` (e.g., `agent1_perceive.txt`, `conductor_route.txt`).

### Database
- PostgreSQL with SQLAlchemy ORM
- CODM tables (24 operational tables) defined in `data_generators/models.py`
- Governance tables (findings, audit, alerts, conversations) in `backend/models/governance.py`
- Tables auto-created on startup via `Base.metadata.create_all(checkfirst=True)`

### SQL Tools
`backend/tools/sql_tools.py` — agents query the 24 CODM tables (eCRF entries, queries, data corrections, CRA assignments, monitoring visits, screening logs, randomization, enrollment velocity, kit inventory, KRI snapshots). Tools are registered via `ToolRegistry` and selected dynamically by the LLM during the Plan phase.

### Frontend
React 18 + Vite + Tailwind CSS + Zustand (state management). Key views:
- `Pulse.jsx` — real-time data pulse visualization
- `Constellation.jsx` — site network graph
- `WorldMap.jsx` — geographic site map (D3-geo)
- `CommandPalette.jsx` — Cmd+K command interface for natural-language queries
- `InvestigationTheater.jsx` — displays agent investigation results

### Active Agents
Registered in `backend/agents/registry.py`:
- **data_quality** — eCRF entry lags, query burden, data corrections, CRA assignments, monitoring
- **enrollment_funnel** — screening volume, screen failures, randomization, consent withdrawals, kit inventory
- **clinical_trials_gov** — competitive intelligence from ClinicalTrials.gov API
- **phantom_compliance** — data integrity & fraud detection (variance suppression, weekday patterns, CRA rubber-stamping)
- **site_rescue** — enrollment trajectory, screen failure root cause, supply constraints
- **vendor_performance** — vendor KPI analysis, milestone tracking, issue logs
- **financial_intelligence** — budget variance, cost per patient, burn rate projection, change orders

### WebSocket Streaming
Agents stream progress to the frontend via WebSocket during investigations:
1. Client POSTs to `/api/agents/investigate` → receives `query_id`
2. Client connects to `/ws/query/{query_id}`
3. Server streams `{phase, agent_id, data}` at each PRPA phase
4. `on_step` callbacks are wrapped in try/except to survive WebSocket disconnects
5. Server sends `{phase: "keepalive"}` messages to prevent timeout during long LLM calls

### API Routers
`backend/routers/` — query processing, direct agent invocation, alerts, dashboard (pure SQL aggregations, no LLM), data freshness feeds, WebSocket streaming.

## Environment Variables

Settings loaded from `.env` via Pydantic Settings (`backend/config.py`):
- `EXTERNAL_DATABASE_URL` — PostgreSQL connection string (Neon)
- `AI_INTEGRATIONS_GEMINI_API_KEY`, `AI_INTEGRATIONS_GEMINI_BASE_URL` — Gemini via Replit
- `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`
- `PRIMARY_LLM` — model name (default: `gemini-3-pro-preview`), `EMBEDDING_MODEL` — `text-embedding-004`
- 20+ operational thresholds (query aging, DQ scores, attention sites) also in `.env`

## Key Conventions

- **No hardcoded thresholds** — all anomaly detection is LLM-driven, not rule-based
- **No fallback/mock data** — always use real integrations and fix root causes
- **Logging** — all logs go to `./tmp/` directory, never project root; use `from pipeline.logging_config import setup_logging`
- **Archiving** — superseded files go to `.archive/<timestamp>/` immediately; never keep multiple versions in workspace
- **Prompts** — every prompt is a separate `.txt` file in `/prompt/`; load via `PromptManager`
- **Max output tokens** — always set `max_output_tokens` to the model's maximum on all LLM API calls
- **DB session isolation** — each agent run gets its own SQLAlchemy session to prevent concurrent access issues
- **Data transparency** — all calculated metrics must include formula breakdowns and data source attribution
- **Tool self-description** — tools expose `describe()` for LLM-driven dynamic selection during the Plan phase
- **Vite proxy** — frontend proxies `/api` → `localhost:8000` and `/ws` → WebSocket; no separate CORS config needed in dev