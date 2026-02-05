# Clinical Operations Intelligence System

## Overview
LLM-first agentic intelligence platform for clinical trial operations. Provides autonomous agent-driven analysis of data quality, enrollment funnels, and operational metrics across clinical trial sites.

## Architecture
- **Backend**: FastAPI with Python 3.12
- **Database**: PostgreSQL (via EXTERNAL_DATABASE_URL)
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
- `EXTERNAL_DATABASE_URL` - PostgreSQL connection string for the external Neon database
- `AI_INTEGRATIONS_GEMINI_API_KEY` - Replit AI Integrations Gemini key (auto-configured)
- `AI_INTEGRATIONS_GEMINI_BASE_URL` - Replit AI Integrations base URL (auto-configured)

## LLM Integration
The application uses Replit AI Integrations for Gemini access, which provides:
- No personal API key required
- Charges billed to Replit credits
- Supported models: gemini-3-pro-preview (primary), gemini-2.5-flash

## Data Transparency & Provenance
All calculated metrics include formula breakdowns and source information:
- **DQ Score**: Formula shown in site detail (e.g., "100 - (5 × 5) = 75")
- **Financial Figures**: Include over_plan_amount, variance_formula, delay_cost_formula
- **Data Sources**: All metrics show source table (e.g., "site_financial_metrics table")

## Fraud Detection / Data Integrity
The Data Integrity Agent (phantom_compliance) detects sophisticated fraud signals:
- **Variance suppression**: Near-zero stddev in entry lag, completeness, query aging
- **Weekday entry patterns**: Batch catchup (e.g., all entries on Mondays)
- **Entry date clustering**: >30% entries on <5% of calendar days = backfill
- **CRA oversight gaps**: Periods without monitoring coverage
- **CRA rubber-stamping**: CRAs who never find issues across multiple sites
- **Correction provenance**: Unprompted corrections (pre-emptive cleanup)
- **Narrative duplication**: Copy-paste screen failure reasons
- **Cross-domain inconsistency**: Perfect metrics in one domain but gaps in another

## Site Journey Timeline
The Site Dossier includes a unified timeline aggregating events from multiple data sources:
- **CRA Transitions**: Staff assignment changes with coverage gaps highlighted
- **Monitoring Visits**: On-site/remote visits with findings and critical issues
- **Screening Events**: Monthly aggregates with fail rates
- **Randomization Events**: Monthly enrollment success counts
- **Alerts**: AI-generated alerts with severity and agent attribution
- **Query Events**: Monthly query volume with resolution rates

API endpoint: `GET /api/dashboard/site/{site_id}/journey?limit=N`

## Design System
Apple-inspired aesthetic with greyscale-forward design, using color sparingly only for status indicators.

### Color Palette
- **Greyscale**: 50-900 scale (50 = #fafafa, 900 = #171717)
- **Status Colors**: Success (emerald), Warning (amber), Critical (red) - used only for borders and indicators
- **Backgrounds**: Light grey (#f5f5f4 bg, #ffffff surface)

### Typography
- Font: Inter/SF Pro-like stack with -apple-system fallbacks
- Scales: hero (3xl), title (2xl), section (lg), body (base), caption (sm), data (xs mono)

### Components
- **card**: Clean surface with subtle border and soft shadow
- **card-elevated**: Enhanced shadow for floating elements
- **metric-card**: Greyscale with colored left border for status
- **button-primary**: Dark grey fill, white text
- **button-ghost**: Minimal styling for secondary actions
- **input-primary**: Clean input with subtle focus states

## Agentic Reasoning Visibility
Progressive disclosure pattern for AI transparency - reasoning is hidden by default, revealed on click:

### Key Risk Cards (Intelligence Brief)
- Click to expand reasoning section showing:
  - **Agent Attribution**: Which agent detected this risk (only shown when data exists)
  - **Investigation Steps**: Sequence of tools/queries used (only when recorded)
  - **Data Sources**: Tables/databases queried (only when provided)
  - **Confidence Score**: Visual bar indicator (only when confidence value exists)

### Active Signals
- Click to expand reasoning for each alert:
  - Agent that generated the alert
  - Reasoning explanation
  - Data source reference

### Investigation Trail (Intelligence Brief Header)
- "View Investigation Trail" button reveals:
  - Contributing Agents with their roles
  - Investigation timeline with step-by-step flow

**Design Principle**: All reasoning sections only display data when it actually exists in the database - no synthetic/fabricated fallbacks. Shows explicit "not available" messages when data is missing.

## Recent Changes
- 2026-02-05: Enhanced brief generator to capture contributing_agents and investigation_steps from findings
- 2026-02-05: Added agent, contributing_agents, investigation_steps fields to SiteIntelligenceBrief model and schema
- 2026-02-05: Added expandable agentic reasoning to Key Risks, Active Signals, and Intelligence Brief
- 2026-02-05: Progressive disclosure for AI transparency - collapsed by default, expand on click
- 2026-02-05: Removed all synthetic fallbacks - only displays data from actual database records
- 2026-02-04: Added unified Site Journey Timeline with events from 6+ data sources
- 2026-02-04: Complete UX overhaul - replaced fragmented tab navigation with unified CommandCenter
- 2026-02-04: New conversational-first interface with AI investigation as primary interaction
- 2026-02-04: Added KPI summary cards (Enrolled, Sites at Risk, DQ Score, Screen Fail Rate)
- 2026-02-04: Added Attention Panel auto-surfacing top priority sites
- 2026-02-04: Added "Explore more" section for vendor, financial, data quality queries
- 2026-02-04: Simplified routing - removed 8 separate tabs, now just CommandCenter + SiteDossier + InvestigationTheater
- 2026-02-03: Added 7 fraud detection tools (weekday_entry_pattern, cra_oversight_gap, cra_portfolio_analysis, correction_provenance, entry_date_clustering, screening_narrative_duplication, cross_domain_consistency)
- 2026-02-03: Enhanced Data Integrity Agent to detect CRA oversight gaps and rubber-stamp patterns
- 2026-02-03: All agent details collapsed by default for cleaner UX
- 2026-02-03: Redesigned Causal Hypothesis page UX with ExecutiveBrief component for clean, consumable insights
- 2026-02-03: Added progressive disclosure - summary first, full analysis on demand
- 2026-02-03: Added DQ score formula breakdown to site detail metrics
- 2026-02-03: Added source provenance to all financial tool outputs (over_plan_amount, variance_formula, delay_cost_formula, data_source)
- 2026-01-31: Imported to Replit, configured for Replit environment
- 2026-01-31: Set up Replit-managed PostgreSQL database
- 2026-01-31: Configured Gemini via Replit AI Integrations
