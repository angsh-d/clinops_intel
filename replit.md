# Clinical Operations Intelligence System

## Overview
LLM-first agentic intelligence platform for clinical trial operations. Provides autonomous agent-driven analysis of data quality, enrollment funnels, and operational metrics across clinical trial sites.

## Architecture
- **Backend**: FastAPI with Python 3.12
- **Database**: PostgreSQL (Replit-managed via DATABASE_URL)
- **LLM Integration**: Google Gemini and Azure OpenAI support
- **Vector Store**: ChromaDB for embeddings

## Project Structure
```
backend/
  ├── main.py          # FastAPI app entry point
  ├── config.py        # Settings and database configuration
  ├── agents/          # AI agents for analysis
  ├── conductor/       # Query routing
  ├── llm/             # LLM client abstractions
  ├── models/          # SQLAlchemy models
  ├── prompts/         # Prompt templates
  ├── routers/         # API endpoints
  ├── schemas/         # Pydantic schemas
  ├── services/        # Business logic
  └── tests/           # Test suite
data_generators/       # Data generation utilities
prompt/                # Additional prompts
protocol/              # Protocol definitions
design/                # Design documents
```

## API Endpoints
- `GET /` - Service info
- `/api/query` - Natural language query processing
- `/api/agents` - Direct agent invocation
- `/api/alerts` - Alert management
- `/api/dashboard` - Dashboard aggregations
- `/api/feeds` - Data freshness checks
- `/ws` - WebSocket for real-time streaming

## Running the Application
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 5000 --reload
```

## Environment Variables
- `DATABASE_URL` - PostgreSQL connection string (auto-configured by Replit)
- `GEMINI_API_KEY` - Google Gemini API key (optional)
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key (optional)

## Recent Changes
- 2026-01-31: Imported to Replit, configured for Replit environment
