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
- **data_quality** (`DataQualityAgent`) — eCRF entry lags, query burden, data corrections, CRA assignments, monitoring
- **enrollment_funnel** (`EnrollmentFunnelAgent`) — screening volume, screen failures, randomization, consent withdrawals, kit inventory

## Environment Variables

Settings loaded from `.env` via Pydantic Settings (`backend/config.py`):
- `DATABASE_URL` — PostgreSQL connection string
- `AI_INTEGRATIONS_GEMINI_API_KEY`, `AI_INTEGRATIONS_GEMINI_BASE_URL` — Gemini via Replit
- `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`
- Primary model: `gemini-3-pro-preview`, Embedding: `text-embedding-004`

## Key Conventions

- **No hardcoded thresholds** — all anomaly detection is LLM-driven, not rule-based
- **No fallback/mock data** — always use real integrations and fix root causes
- **Logging** — all logs go to `./tmp/` directory, never project root
- **Archiving** — superseded files go to `.archive/<timestamp>/` immediately; never keep multiple versions in workspace
- **Prompts** — every prompt is a separate `.txt` file in `/prompt/`; load via `PromptManager`
- **Max output tokens** — always set `max_output_tokens` to the model's maximum on all LLM API calls
- **DB session isolation** — each agent run gets its own SQLAlchemy session to prevent concurrent access issues