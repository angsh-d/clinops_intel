# Clinical Operations Intelligence Platform — Solution Outline

**Audience:** Technical stakeholders (CTOs, architects, engineering leads)
**Scope:** Agentic backend architecture, dual-mode intelligence, and data model

---

## 1. Executive Summary

Clinical trial operations generate large volumes of structured data across dozens of systems — but the data does not come from a single unified source. In a typical Phase III trial, the sponsor contracts a **Global CRO** for monitoring and data management across most regions, one or more **Regional CROs** for specific countries (e.g., Japan, China), a **Central Lab** vendor, an **IRT/IWRS** vendor for randomization and supply, an **EDC** platform vendor, an **imaging** vendor, and specialists for safety/PV and patient recruitment. Each vendor operates its own systems, delivers data on its own schedule, and is accountable to its own contractual KPIs.

Operational oversight of this multi-vendor ecosystem remains manual, reactive, and dashboard-driven. Traditional approaches rely on static KRI thresholds and rule-based alerting, which miss non-obvious cross-domain patterns — especially those that span vendor boundaries (e.g., a CRO's CRA transition causing a downstream data quality collapse that masks an enrollment stall attributable to the IRT vendor's supply chain delay).

This platform replaces threshold-based monitoring with **LLM-first autonomous agents** that investigate clinical operations data the way an experienced CODM lead would: forming hypotheses from signals, selecting investigative tools, evaluating evidence, and iterating until the investigation is complete. The system is designed for the **multi-CRO reality** — where a Global CRO manages most geographies while Regional CROs handle specific countries, and operational problems frequently originate at vendor handoff boundaries.

**The platform operates in two complementary modes:**

1. **Proactive Mode (Primary)** — When operational data lands in the Common Operational Data Model (CODM), the system autonomously launches a site performance scan across all agents. Each agent runs its PRPA cognitive loop against fresh data — without any user query — producing pre-emptive findings, alerts, and per-site intelligence briefs before anyone asks a question.

2. **Reactive Mode** — An Orchestrator Agent routes natural-language queries to the appropriate agents, which investigate using the same PRPA loop and tool infrastructure. This enables ad-hoc deep dives complementing proactive surveillance.

**Core differentiation:** Agents do not answer questions — they investigate them. Whether triggered by data ingestion or a user query, a multi-iteration cognitive loop perceives signals, reasons about root causes, plans which tools to invoke, acts on those plans, and reflects on whether the investigation is complete. Every metric includes its formula, data source, and causal chain.

---

## 2. Architecture Overview

The platform has two entry points into a shared agent/tool/CODM infrastructure:

```
  ┌──────────────────────────┐                  ┌──────────────────────────┐
  │   PROACTIVE MODE         │                  │   REACTIVE MODE          │
  │                          │                  │                          │
  │   Source Systems          │                  │   Natural Language       │
  │   (EDC, IRT, CTMS,      │                  │   Query                  │
  │    Vendors, Finance,     │                  │                          │
  │    Digital Protocol)     │                  │                          │
  └────────────┬─────────────┘                  └────────────┬─────────────┘
               │                                             │
  ┌────────────▼─────────────┐                  ┌────────────▼─────────────┐
  │   Data Ingestion Layer   │                  │   Orchestrator Agent     │
  │   Normalize → CODM       │                  │   (LLM semantic routing) │
  └────────────┬─────────────┘                  └───┬────────┬─────────┬──┘
               │                                    │        │         │
  ┌────────────▼─────────────┐                      │        │         │
  │  Proactive Scan Engine   │                      │        │         │
  │                          │                      │        │         │
  │  ┌────────────────────┐  │                      │        │         │
  │  │ 1. Select from     │  │                      │        │         │
  │  │    Directive       │  │                      │        │         │
  │  │    Catalog         │  │                      │        │         │
  │  │    (user-curated,  │  │                      │        │         │
  │  │     per agent)     │  │                      │        │         │
  │  └────────┬───────────┘  │                      │        │         │
  │           │              │                      │        │         │
  │  ┌────────▼───────────┐  │          ┌───────────▼┐ ┌────▼─────┐ ┌─▼──────────────┐
  │  │ 2. Execute Agent   │──┼─────────►│  Agent A   │ │ Agent B  │ │  Agent C       │
  │  │    PRPA Loops      │  │          │ (PRPA loop)│ │ (PRPA)   │ │ (PRPA loop)    │
  │  │    (all agents,    │  │          │ isolated DB│ │ isolated │ │ isolated DB    │
  │  │     isolated DB)   │  │          └──────┬─────┘ └────┬─────┘ └──┬─────────────┘
  │  └────────┬───────────┘  │                 │            │           │
  │           │              │                 │            │           │
  │  ┌────────▼───────────┐  │       ┌─────────▼────────────▼───────────▼──────┐
  │  │ 3. Persist         │  │       │          ToolRegistry                   │
  │  │    Findings →      │◄─┼───────│   (self-describing, LLM-selected)      │
  │  │    agent_findings  │  │       └────┬────────────────────────────────┬───┘
  │  │    Raise Alerts →  │  │            │                                │
  │  │    alert_log       │  │    ┌───────▼────────┐            ┌──────────▼──────┐
  │  └────────┬───────────┘  │    │  SQL Tools     │            │  External APIs   │
  │           │              │    │  (30+ tools)   │            │ (ClinicalTrials  │
  │  ┌────────▼───────────┐  │    │                │            │  .gov)           │
  │  │ 4. Assemble Site   │  │    └───────┬────────┘            └─────────────────┘
  │  │    Intelligence    │  │            │
  │  │    Briefs          │  │    ┌───────▼────────┐
  │  │    (LLM cross-     │  │    │  CODM Database │
  │  │     agent synth.)  │  │    │  (PostgreSQL)  │
  │  └────────┬───────────┘  │    │  38 tables     │
  │           │              │    └───────┬────────┘
  └───────────┼──────────────┘            │
              │                  ┌────────▼───────────────────┐
              │                  │  Cross-Domain Synthesis    │
              │                  │  (LLM merges findings)     │
              │                  └────────┬───────────────────┘
              │                           │
              ▼                           ▼
  ┌──────────────────────────┐  ┌────────────────────────────┐
  │  Site Intelligence       │  │  Structured Response       │
  │  Briefs                  │  │  + Reasoning Trace         │
  │  • Risk Summary          │  │                            │
  │  • Cross-Domain          │  │                            │
  │    Correlations          │  │                            │
  │  • Recommended Actions   │  │                            │
  │  • Trend Indicators      │  │                            │
  └──────────────────────────┘  └────────────────────────────┘
       (Proactive output)            (Reactive output)
```

**Left path (Proactive):** Data ingestion triggers an autonomous scan — agents run PRPA loops against fresh data using internally generated investigation directives. Findings are persisted, alerts raised, and site intelligence briefs assembled.

**Right path (Reactive):** A user submits a natural-language query. The Orchestrator Agent routes it to relevant agents, which run the same PRPA loops and tools. Results are synthesized into a structured response with full reasoning traces.

WebSocket streaming runs parallel to the reactive pipeline. The client POSTs a query and receives a `query_id`, then connects to `/ws/query/{query_id}`. The server emits `{phase, agent_id, data}` events at each PRPA phase boundary, giving the frontend real-time visibility into investigation progress.

---

## 3. Data Ingestion & CODM

### Data Ingestion Layer

Operational data flows into CODM from clinical trial vendor systems. Ingestion is the trigger for proactive analysis — when fresh data lands, the system has new signals to investigate.

**The multi-vendor data reality:** Sponsors do not receive data from abstract "source systems." They receive structured extracts from specific contracted vendors, each delivering on its own schedule, format, and completeness level. The ingestion layer must normalize across these vendor-specific feeds.

**Vendor-mediated data sources:**

| Vendor Type | Example Vendor | Data Delivered | Typical Frequency | CODM Target Tables |
|-------------|---------------|----------------|-------------------|-------------------|
| **EDC Vendor** | Medidata Rave | eCRF entries, queries, data corrections, subject visit records | Daily extract | `ecrf_entries`, `queries`, `data_corrections`, `subject_visits` |
| **IRT/IWRS Vendor** | Almac | Randomization events, kit inventory, depot definitions, depot shipments, drug kit type reference, screening logs, enrollment velocity metrics | Daily extract | `randomization_log`, `randomization_events`, `kit_inventory`, `depots`, `depot_shipments`, `drug_kit_types`, `screening_log`, `enrollment_velocity` |
| **Global CRO** | IQVIA | Monitoring visits, CRA assignments, overdue actions, site activation status, KRI snapshots | Weekly transfer | `monitoring_visits`, `cra_assignments`, `overdue_actions`, `sites` (partial), `kri_snapshots` |
| **Regional CRO(s)** | EPS (Japan) | Same as Global CRO, for assigned countries | Weekly transfer | Same tables, country-scoped |
| **Central Lab** | Covance | Lab results, sample tracking | Weekly transfer | Referenced via `subject_visits`, lab-related `queries` |
| **Imaging Vendor** | Bioclinica | Image review status, adjudication outcomes | Biweekly transfer | Referenced via `subject_visits`, imaging-related `queries` |
| **Safety/PV Vendor** | PharSafer | SAE reports, safety narratives | As reported | Referenced via safety-related `queries` and `kri_snapshots` |
| **Patient Recruitment Vendor** | StudyKIK | Referral volumes, pre-screening funnels | Weekly report | Feeds into `screening_log` referral attribution |
| **Sponsor Finance / ERP** | Internal | Budgets, budget categories, invoices, change orders, payment milestones, site-level financial metrics | Monthly close | `study_budget`, `budget_categories`, `budget_line_items`, `financial_snapshots`, `invoices`, `change_orders`, `payment_milestones`, `site_financial_metrics` |
| **Sponsor Vendor Management** | Internal | Vendor contracts, scope of work, site assignments, KPI targets, milestones, issue tracking | As contracted / quarterly | `vendors`, `vendor_scope`, `vendor_site_assignments`, `vendor_kpis`, `vendor_milestones`, `vendor_issues` |
| **Digital Protocol (Sponsor)** | Internal | Study config, visit schedule, eligibility criteria, arms, stratification, screen failure reason codes | As amended | `study_config`, `study_arms`, `visit_schedule`, `visit_activities`, `eligibility_criteria`, `stratification_factors`, `screen_failure_reason_codes` |

**Multi-CRO ingestion pattern:** In a multi-CRO model, monitoring data arrives from multiple CROs covering different geographies. The Global CRO (e.g., IQVIA) provides monitoring visit data, CRA assignments, and site oversight for most countries, while Regional CROs (e.g., EPS for Japan) provide the same data types for their assigned countries. The ingestion layer normalizes both feeds into the same CODM tables, with `vendor_site_assignments` tracking which vendor is responsible for which site. This enables apples-to-apples comparison of CRO performance across regions.

**Ingestion flow:** Vendor extracts are received on defined schedules (daily, weekly, biweekly, or monthly depending on data type), normalized to the CODM schema, and loaded into PostgreSQL. The platform does not own the source-of-truth — it ingests and normalizes vendor data for investigative purposes. Each ingestion cycle triggers a proactive scan for the affected data domains.

### Common Operational Data Model (CODM)

In a multi-CRO trial, the Global CRO's CTMS, the Regional CRO's CTMS, the EDC vendor's database, the IRT vendor's supply system, and the central lab's LIMS each have proprietary schemas and deliver data in different formats. CODM normalizes all vendor feeds into a single PostgreSQL schema that agents can query uniformly — enabling cross-vendor analysis that no single vendor's system can provide.

### Table Inventory (46 tables)

The CODM schema contains 38 operational tables and 8 governance tables, organized into the following domains:

| Domain | Tables | Key Tables | Primary Agents |
|--------|--------|------------|----------------|
| Study Configuration | 7 | `study_config`, `visit_schedule`, `eligibility_criteria` | All (study context) |
| Site & Staffing | 3 | `sites`, `cra_assignments` | data_quality, site_rescue |
| Supply Chain | 3 | `kit_inventory`, `depot_shipments` | enrollment_funnel, site_rescue |
| Enrollment & Screening | 4 | `screening_log`, `enrollment_velocity`, `randomization_log` | enrollment_funnel, site_rescue |
| Clinical Data | 3 | `ecrf_entries`, `queries`, `subject_visits` | data_quality, phantom_compliance |
| Data Quality | 3 | `data_corrections`, `monitoring_visits`, `kri_snapshots` | data_quality, phantom_compliance |
| Operations | 1 | `overdue_actions` | data_quality |
| Vendor Management | 6 | `vendors`, `vendor_site_assignments`, `vendor_kpis` | vendor_performance |
| Financial | 8 | `budget_line_items`, `financial_snapshots`, `invoices`, `change_orders` | financial_intelligence |
| Governance | 8 | `agent_findings`, `alert_log`, `audit_trail` | Platform internals |

**Architectural notes:**
- `sites` is the atomic unit of operational analysis — every agent investigates at site granularity.
- `vendor_site_assignments` is the multi-vendor-per-site junction table (indexed on both `vendor_id` and `site_id`), enabling attribution of operational issues to specific vendors.
- `cra_assignments` tracks CRA transitions — a leading indicator of operational disruption that agents cross-reference with data quality and enrollment signals.
- Governance tables (`backend/models/governance.py`) record platform operations: findings, alerts, audit trail, and runtime configuration.

**→ See [`data_dictionary.md`](data_dictionary.md) for complete column definitions, data types, indexes, production source systems, refresh cadences, and cross-table relationships for all 46 tables.**

---

## 4. Proactive Intelligence Engine

The proactive engine is the platform's primary operating mode. Rather than waiting for users to ask questions, the system autonomously investigates operational health after each data ingestion cycle.

### Site Performance Scan

When fresh data lands in CODM, the proactive engine launches a **Site Performance Scan** — a systematic sweep across all agents and all sites:

1. **Select Investigation Directives** — For each agent, the engine selects active directives from a **user-curated Directive Catalog**. Each directive is a prompt template stored as a `.txt` file in `/prompt/directives/` (e.g., `data_quality_directive_01.txt`), loaded via `PromptManager` with `{variable}` substitution for study-specific context. Operations leads can add, modify, or disable directives without code changes. The selected directives replace user queries as the input to the PRPA loop.

2. **Execute Agent PRPA Loops** — Each agent runs its standard PRPA loop (up to 3 iterations) against the directive. The same tools, LLM calls, and convergence logic used in reactive mode apply here — agents perceive signals, reason about root causes, plan tool invocations, act, and reflect on completeness.

3. **Persist Findings** — Agent outputs are written to `agent_findings` with full reasoning traces. Findings above severity thresholds generate entries in `alert_log` (status: `open`).

4. **Assemble Site Intelligence Briefs** — A synthesis LLM call cross-references findings from all agents for each site, producing a **Site Intelligence Brief** — a per-site summary that integrates data quality, enrollment, compliance, vendor, and financial signals into a unified risk picture.

### Directive Catalog

Investigation directives are the proactive counterpart to user queries. They live in a **Directive Catalog** — a set of user-curated prompt templates that define what the proactive engine investigates.

**Storage & management:**

- Each directive is a `.txt` file in `/prompt/directives/`, following the naming convention `{agent_id}_directive_{nn}.txt` (e.g., `data_quality_directive_01.txt`)
- Directives are prompt templates with `{variable}` placeholders (e.g., `{study_id}`, `{data_window_days}`) substituted at runtime by `PromptManager` — consistent with the platform's existing prompt externalization pattern
- A directive metadata file (`/prompt/directives/catalog.json`) tracks each directive's `agent_id`, `enabled` flag, `priority`, and `description`, allowing operations leads to enable/disable directives or adjust scan priority without editing prompt text
- Directives can be added or modified by study teams, CODM leads, or operations managers — no code deployment required

**Default directives (shipped with the platform):**

| Agent | Directive File | Focus |
|-------|---------------|-------|
| `data_quality` | `data_quality_directive_01.txt` | Deteriorating eCRF entry lags, rising query burden, monitoring gaps |
| `enrollment_funnel` | `enrollment_funnel_directive_01.txt` | Screening volume trends, randomization velocity, consent withdrawal rates |
| `phantom_compliance` | `phantom_compliance_directive_01.txt` | Variance suppression, timestamp clustering, CRA rubber-stamping |
| `site_rescue` | `site_rescue_directive_01.txt` | Enrollment trajectory risk, rescue feasibility assessment |
| `vendor_performance` | `vendor_performance_directive_01.txt` | Cross-CRO performance comparison, vendor KPI adherence, vendor-attributable site-level issues, CRA staffing stability per CRO |
| `financial_intelligence` | `financial_intelligence_directive_01.txt` | Budget variance, burn rate acceleration, change order accumulation |

Study teams can extend the catalog with study-specific directives (e.g., a directive focused on a particular country's regulatory compliance pattern, or a directive targeting sites in a rescue cohort).

### Finding Persistence & Alert Generation

Proactive findings flow into the governance tables:

- **`agent_findings`** — Every finding is stored with its `agent_id`, `finding_type`, `severity`, `summary`, `detail`, `data_signals`, `reasoning_trace`, and `confidence`. Findings are idempotent — re-scanning the same data does not create duplicate findings.
- **`alert_log`** — Findings that exceed configured thresholds in `alert_thresholds` generate alerts. Alerts follow a lifecycle: `open` → `acknowledged` → `resolved`. Suppression rules in `suppression_rules` prevent alert fatigue for known issues.

### Site Intelligence Brief

The brief is the primary proactive output — a per-site document that answers: *"What does the platform know about this site right now?"*

A brief synthesizes findings across all agents into:
- **Risk Summary** — overall site health with contributing factors
- **Vendor Accountability** — which vendors are responsible for each risk area at this site (via `vendor_site_assignments`), enabling the sponsor to direct escalation to the correct CRO or vendor
- **Cross-Domain Correlations** — patterns that span agent and vendor domains (e.g., CRO's CRA transition → data quality collapse → enrollment stall → IRT supply misalignment)
- **Recommended Actions** — prioritized interventions with expected impact, attributed to the responsible vendor where applicable
- **Trend Indicators** — whether each signal is improving, stable, or deteriorating

---

## 5. Orchestrator Agent & Ad-Hoc Q&A

The Orchestrator Agent (implemented as `ConductorRouter` in `backend/conductor/router.py`) provides the reactive complement to proactive scanning. When a user asks a natural-language question, the Orchestrator routes it to the appropriate agents for investigation.

### LLM-Driven Semantic Routing

The Orchestrator uses the LLM to understand query intent and select agents. There is zero keyword matching — the routing decision is made by rendering the `conductor_route` prompt template with the query and session context, then parsing the LLM's structured JSON response:

```json
{
  "selected_agents": ["data_quality", "enrollment_funnel"],
  "routing_rationale": "...",
  "signal_summary": "...",
  "requires_synthesis": true
}
```

### Parallel Agent Execution

When multiple agents are selected, the Orchestrator runs them concurrently via `asyncio.gather`. Each agent receives an **isolated SQLAlchemy session** (`SessionLocal()`) to prevent concurrent access issues. Sessions are closed in a `finally` block regardless of outcome. Exceptions from individual agents are caught and logged without aborting others.

### Cross-Domain Synthesis with Ground Truth Anchoring

The Orchestrator always invokes a synthesis LLM call (`conductor_synthesize` prompt), even for single-agent results. Synthesis receives three inputs:

1. **Agent outputs** — findings from all routed agents
2. **Operational snapshot** — an authoritative ground-truth payload pulled from the shared service layer (`backend/services/dashboard_data.py`), containing the same attention-sites list and site overview data displayed on the dashboard. This ensures synthesis responses never contradict dashboard KPIs.
3. **Query type classification** — the synthesis prompt detects whether the user query is a **data retrieval** ("show me", "list"), **analytical** ("why", "root cause"), or **comparison** ("compare", "rank") request, and adapts the response format accordingly.

Synthesis outputs:

- Cross-domain findings with causal chains
- Priority actions ranked by impact
- An executive summary grounded in both agent findings and the operational snapshot
- A **display format** directive (`narrative`, `narrative_table`, `table`, or `narrative_chart`) with optional structured `table_data` and `chart_data` — consumed by the frontend to render the response in the optimal visual format

### Anti-Hallucination Guardrails

The synthesis prompt enforces strict factual accuracy rules: every numerical claim must be directly traceable to agent data, cross-metric inference is prohibited (e.g., "zero enrollment" must not imply "zero monitoring visits"), and all claims are cross-checked against the operational snapshot before output.

---

## 6. PRPA Cognitive Loop

The PRPA (Perceive–Reason–Plan–Act–Reflect) loop is the core execution model shared by both proactive and reactive modes. Each agent runs up to **3 iterations** of this loop, converging when the Reflect phase determines the investigation goal is satisfied.

```
    ┌─────────────────────────────────────────────┐
    │               PRPA Iteration                │
    │                                             │
    │  ┌──────────┐    ┌──────────┐               │
    │  │ PERCEIVE │───►│  REASON  │               │
    │  │ (SQL     │    │ (LLM     │               │
    │  │  tools)  │    │ hypotheses)              │
    │  └──────────┘    └────┬─────┘               │
    │                       │                     │
    │                  ┌────▼─────┐               │
    │                  │   PLAN   │               │
    │                  │ (LLM     │               │
    │                  │ selects  │               │
    │                  │  tools)  │               │
    │                  └────┬─────┘               │
    │                       │                     │
    │                  ┌────▼─────┐               │
    │                  │   ACT    │               │
    │                  │ (execute │               │
    │                  │  tools)  │               │
    │                  └────┬─────┘               │
    │                       │                     │
    │                  ┌────▼─────┐    ┌────────┐ │
    │                  │ REFLECT  │───►│ Goal   │ │
    │                  │ (LLM     │    │ met?   │ │
    │                  │ evaluates│    └───┬──┬─┘ │
    │                  └──────────┘        │  │   │
    │                              yes ◄───┘  └──►│ no → next iteration
    │                               │             │
    └───────────────────────────────┼─────────────┘
                                    │
                              AgentOutput
```

**Phase details:**

| Phase | Input | LLM Role | Output |
|-------|-------|----------|--------|
| **Perceive** | Query or investigation directive + prior iteration context | None (data gathering) | Raw data signals from SQL tools |
| **Reason** | Perceptions | Generates hypotheses with causal chains, site IDs, confidence scores | Hypothesis list |
| **Plan** | Hypotheses + available tools | Selects tools and maps them to hypotheses | Ordered tool invocation plan |
| **Act** | Plan steps | None (execution) | Tool results with row counts |
| **Reflect** | All accumulated evidence | Evaluates completeness, identifies gaps | Goal satisfaction flag + remaining gaps |

**Why this matters vs. simple LLM Q&A or RAG:** A single-pass LLM call or RAG retrieval answers what is in the data. PRPA investigates what the data means — it can discover that a site's clean data quality metrics are explained by a CRA who never reports findings, which is only discoverable by cross-referencing monitoring visit patterns with query lifecycle data across multiple tool invocations.

In **proactive mode**, the "query" input to the PRPA loop is an investigation directive generated by the proactive engine. In **reactive mode**, it is the user's natural-language question. The loop logic is identical in both cases.

---

## 7. Agent Framework

### BaseAgent Abstraction

`BaseAgent` (`backend/agents/base.py`) defines the PRPA loop as a template method. Subclasses implement six abstract methods:

- `perceive(ctx)` — gather domain-specific signals
- `reason(ctx)` — LLM hypothesis generation
- `plan(ctx)` — LLM tool selection
- `act(ctx)` — tool execution
- `reflect(ctx)` — LLM completeness evaluation
- `_build_output(ctx)` — structure final findings

Agents are agnostic to their invocation mode — the same agent class handles both proactive scans (with investigation directives) and reactive queries (with user questions).

### AgentContext State Machine

`AgentContext` is a mutable dataclass that flows through every phase:

| Field | Type | Purpose |
|-------|------|---------|
| `query` | str | Original natural-language question or investigation directive |
| `perceptions` | dict | Raw data signals gathered in Perceive |
| `hypotheses` | list | LLM-generated hypotheses from Reason |
| `plan_steps` | list | Tool invocation plan from Plan |
| `action_results` | list | Accumulated results across all iterations |
| `reflection` | dict | Latest Reflect output |
| `is_goal_satisfied` | bool | Convergence flag |
| `iteration` / `max_iterations` | int | Loop control (max 3) |
| `reasoning_trace` | list | Append-only audit trail of every phase |

### AgentOutput

Structured output returned to the Orchestrator (reactive mode) or persisted to `agent_findings` (proactive mode):

| Field | Type |
|-------|------|
| `agent_id` | str |
| `finding_type` | str |
| `severity` | str |
| `summary` | str |
| `detail` | dict |
| `data_signals` | dict |
| `reasoning_trace` | list |
| `confidence` | float |
| `findings` | list |
| `investigation_complete` | bool |
| `remaining_gaps` | list |

### The 7 Specialized Agents

| Agent ID | Name | Investigation Domain |
|----------|------|---------------------|
| `data_quality` | Data Quality Agent | eCRF entry lags, query burden, data corrections, CRA assignments, monitoring gaps. Detects CRA transition impacts (attributable to the monitoring CRO via `vendor_site_assignments`), monitoring gap hidden debt, strict PI paradoxes. |
| `enrollment_funnel` | Enrollment Funnel Agent | Screening volume, screen failure rates, randomization velocity, consent withdrawals, regional patterns. Detects competing trials, supply-chain-masked withdrawals, funnel stage decomposition. |
| `clinical_trials_gov` | Competitive Intelligence Agent | BioMCP-powered ClinicalTrials.gov searches with geo-distance filtering, condition synonym expansion, and structured detail retrieval (protocol, locations, outcomes, references). Identifies competing trials near sites with unexplained enrollment decline — provides external evidence for cannibalization hypotheses. |
| `phantom_compliance` | Data Integrity Agent | Variance suppression, CRA rubber-stamping, weekday entry clustering, correction provenance anomalies, narrative duplication, cross-domain inconsistencies. Flags sites where multiple fraud signals co-occur. |
| `site_rescue` | Site Decision Agent | Enrollment trajectory, screen failure root causes (fixable vs structural), CRA staffing stability, supply constraints, competitive landscape. Produces rescue/close decision frameworks. |
| `vendor_performance` | Vendor Performance Agent | Multi-CRO and vendor KPI adherence, site activation timelines, query resolution speed, monitoring completion. Compares Global CRO vs. Regional CRO performance across overlapping metrics. Cross-references vendor KPIs with site-level operational data via `vendor_site_assignments` to attribute site problems to specific vendors. Detects CRO staffing instability (CRA transitions), vendor milestone slippage, and issue accumulation patterns. |
| `financial_intelligence` | Financial Intelligence Agent | Budget variance, cost per patient, vendor spending patterns, burn rate projections, change order impact, financial consequences of operational delays. |

### Agent Registration

`AgentRegistry` (`backend/agents/registry.py`) is a dict-based lookup. `build_agent_registry()` imports all 7 agent classes and registers them. Both the Orchestrator Agent and the Proactive Scan Engine resolve agent IDs to classes at runtime via the same registry.

---

## 8. LLM Client Stack

### Abstract Interface

`LLMClient` (`backend/llm/client.py`) defines two abstract methods:

- `generate(prompt, system, temperature)` → `LLMResponse`
- `generate_structured(prompt, system, temperature)` → `LLMResponse`

`LLMResponse` carries `text`, `model`, `usage` (token counts), `raw` provider response, and an `is_fallback` flag.

### Gemini Primary Client

`GeminiClient` (`backend/llm/gemini.py`) uses the `google-genai` SDK:

- Configurable model name, temperature (default 0.0 for deterministic output), top_p, max output tokens
- Timeout with exponential backoff retry (configurable retries)
- Detects empty/blocked responses and raises to trigger failover
- Supports both direct API key and Replit AI Integrations base URL

### Azure OpenAI Fallback

`AzureOpenAIClient` (`backend/llm/azure_openai.py`) provides the same interface over Azure OpenAI deployments.

### Failover Strategy

`FailoverLLMClient` (`backend/llm/failover.py`) wraps both clients:

1. Every call attempts Gemini first
2. On any exception, logs the failure and retries with Azure OpenAI
3. Sets `is_fallback = True` on fallback responses — no silent degradation

### Prompt Externalization

All prompts are `.txt` files in the `/prompt/` directory. `PromptManager` (`backend/prompts/manager.py`) loads templates by name and applies `{variable}` substitution at runtime. Prompt naming convention: `{agent_id}_{phase}.txt` (e.g., `data_quality_perceive.txt`, `conductor_route.txt`). Templates are cached in memory after first load.

---

## 9. Tool Framework & Dynamic Selection

### Self-Describing Tools

Every tool extends `BaseTool` (`backend/tools/base.py`) and exposes:

- `name` — unique identifier (e.g., `entry_lag_analysis`)
- `description` — natural-language description of what the tool does and its arguments
- `describe()` — returns `{name, description}` dict for LLM prompt injection
- `execute(db_session, **kwargs)` → `ToolResult`

`ToolResult` carries `tool_name`, `success`, `data`, `error`, and `row_count`.

### ToolRegistry & LLM-Driven Selection

`ToolRegistry` maintains a dict of registered tools and provides:

- `list_tools_text()` — formatted tool descriptions injected into the Plan phase prompt
- `invoke(name, db_session, **kwargs)` — executes a tool by name with result caching

During the **Plan phase**, the LLM receives the full list of available tool descriptions and selects which to invoke based on the hypotheses it generated in the Reason phase. There is no hardcoded tool-to-agent mapping — any agent can invoke any tool if the LLM determines it is relevant. This applies in both proactive and reactive modes.

### Result Caching

`ToolRegistry.invoke()` checks an in-memory LRU cache (`sql_tool_cache`) keyed by tool name + kwargs. Cache hits skip SQL execution entirely. Only successful results are cached.

### Tool Categories (35+ tools)

| Domain | Tools |
|--------|-------|
| **Data Quality** | `entry_lag_analysis`, `query_burden`, `data_correction_analysis`, `cra_assignment_history`, `monitoring_visit_history`, `monitoring_visit_report`, `site_summary` |
| **Enrollment Funnel** | `screening_funnel`, `enrollment_velocity`, `screen_failure_pattern`, `regional_comparison`, `kit_inventory`, `kri_snapshot` |
| **Data Integrity** | `data_variance_analysis`, `timestamp_clustering`, `query_lifecycle_anomaly`, `monitoring_findings_variance`, `weekday_entry_pattern`, `cra_oversight_gap`, `cra_portfolio_analysis`, `correction_provenance`, `entry_date_clustering`, `screening_narrative_duplication`, `cross_domain_consistency` |
| **Site Rescue** | `enrollment_trajectory`, `screen_failure_root_cause`, `supply_constraint_impact` |
| **Vendor Performance** | `vendor_kpi_analysis` (KPI trends across all vendors), `vendor_site_comparison` (operational metrics per vendor via site assignments — enables Global CRO vs. Regional CRO comparison), `vendor_milestone_tracker`, `vendor_issue_log` |
| **Financial** | `budget_variance_analysis`, `cost_per_patient_analysis`, `burn_rate_projection`, `change_order_impact`, `financial_impact_of_delays` |
| **Study Operations** | `study_operational_snapshot` (authoritative study-wide snapshot: attention sites + site overview — shared data source with dashboard) |
| **Cross-Domain** | `context_search` (vector similarity), `trend_projection` (forecasting) |
| **External** | `competing_trial_search` (BioMCP — geo-distance, synonym expansion, pagination), `trial_detail` (BioMCP — protocol, locations, references, outcomes by NCT ID) |

**Notable tool additions:**

- **`study_operational_snapshot`** — Calls the shared service layer (`dashboard_data.py`) to return the same attention-sites list and site overview data shown on the dashboard. Agents use this as the authoritative source for "which sites need attention" queries, ensuring consistency between agent responses and dashboard displays.
- **`monitoring_visit_report`** — Returns detailed monitoring visit reports for a specific site, including visit metadata, findings counts, and linked follow-up action items from the `overdue_actions` table. Pre-formats a `findings_summary` field for LLM consumption.

---

## 10. Key Design Decisions

### No Hardcoded Thresholds

All anomaly detection is LLM-driven. The system does not use static rules like "flag if entry lag > 7 days." Instead, the LLM evaluates signals in context — a 5-day lag at a high-volume academic site is different from a 5-day lag at a community site with one patient. This eliminates false positives from one-size-fits-all thresholds and detects novel patterns that rules cannot anticipate.

### Multi-CRO as a First-Class Concept

The platform assumes a multi-vendor operating model where a Global CRO manages most geographies while Regional CROs handle specific countries, and specialized vendors (central lab, IRT, imaging, ePRO, safety, recruitment) each own their data domain. The `vendor_site_assignments` junction table is the architectural keystone — it maps every site to its responsible vendors by role, enabling the platform to:

- **Attribute site-level problems to specific vendors** — when data quality deteriorates at a site, the platform can identify which CRO's monitoring team is responsible
- **Compare CRO performance across regions** — Global CRO's sites vs. Regional CRO's sites on the same operational metrics (entry lag, query burden, monitoring findings)
- **Detect vendor handoff failures** — operational problems that emerge at the boundary between two vendors' responsibilities (e.g., CRO monitoring delays causing IRT supply chain misalignment)
- **Track CRA-to-CRO affiliation** — CRA transitions are analyzed in the context of which CRO employs that CRA, connecting staffing instability to vendor performance

### Proactive-First Architecture

The platform is designed around data-triggered investigation, not user-triggered queries. Proactive scanning ensures that operational risks are surfaced before anyone asks — the system operates as a continuous surveillance engine, not a Q&A chatbot. Ad-hoc queries complement this by enabling targeted deep dives into specific concerns.

### Idempotent Finding Generation

Proactive scans must be safe to re-run. Findings are deduplicated by agent, site, finding type, and data window — re-scanning the same data produces the same findings without duplication. New findings are only created when underlying data signals change.

### Scan vs. Query Priority

When a proactive scan and a reactive query compete for resources, reactive queries take priority (lower latency expectation). Proactive scans are designed to be interruptible and resumable — a scan can yield to a reactive query and resume afterward without losing progress.

### DB Session Isolation Per Agent

Each agent run receives its own `SessionLocal()` instance, closed in a `finally` block. This prevents SQLAlchemy session state corruption when multiple agents execute concurrently via `asyncio.gather`. The pattern is enforced in both the Orchestrator's `_run_one()` method and the proactive scan engine.

### Data Transparency

Every calculated metric includes:
- **Formula breakdown** (e.g., `"$150,000 actual - $120,000 planned = $30,000 over plan"`)
- **Data source attribution** (e.g., `"site_financial_metrics table"`)

This ensures findings are auditable and stakeholders can trace any number back to its source table and calculation.

### Safe WebSocket Callbacks

The `on_step` callback is wrapped in `_make_safe_callback()` which swallows exceptions. If the WebSocket disconnects mid-investigation, the agent continues executing — the investigation is never aborted due to a frontend disconnect. The server also emits periodic `keepalive` messages during long LLM calls to prevent connection timeouts.

### Structured JSON Responses

All LLM calls use `generate_structured()` with a system instruction requiring valid JSON output. Temperature is set to 0.0 for deterministic outputs. Responses are parsed through `parse_llm_json()` which handles markdown fences and extraction from mixed content. Parse failures fall back to safe defaults rather than crashing the pipeline.

### Two-Layer Persistent Cache

The platform uses a two-layer cache (L1: in-memory LRU, L2: PostgreSQL-backed) for dashboard results, SQL tool results, and LLM responses. L1 provides fast access within a running process; L2 survives server restarts. No TTL — entries persist until explicitly invalidated (e.g., after an investigation completes). This avoids redundant SQL/LLM calls across requests and agent iterations.

### Dashboard–Agent Data Consistency

A shared service layer (`backend/services/dashboard_data.py`) contains the SQL logic for attention-sites and site-overview computations. Both the dashboard API endpoints and the `study_operational_snapshot` agent tool call the same service functions, guaranteeing that dashboard KPIs, map pulsating dots, and agent investigation responses all reflect the same underlying data.

### Operational Signal Fallback

Proactive scans may not cover every site in every cycle. Sites without AlertLog entries, agent findings, or intelligence briefs still receive operational signals derived from their live metrics (anomaly flags, open query counts, enrollment %, entry lag). The `site_detail` endpoint generates these fallback signals from already-computed data, ensuring no site appears silent when real issues exist.

---

## 11. Frontend Architecture

React 18 + Vite + Tailwind CSS + Zustand (state management). Apple-inspired greyscale design system (`bg-apple-surface`, `border-apple-border`, `text-apple-text/secondary/tertiary`). Framer Motion for all transitions and modal animations.

### Command Center (`frontend/src/components/CommandCenter.jsx`)

The Command Center is the study-level intelligence hub — it combines operational KPIs, geographic site visualization, AI-powered investigation, and pre-aggregated domain summaries in a single view.

**Layout (top to bottom when no conversation is active):**

1. **Sticky header** — Study ID, phase, enrollment progress bar, site count, "New chat" button
2. **KPI cards** — 4-column grid: Enrolled (with target), Sites at Risk, DQ Score, Screen Fail Rate. Each card includes a RAG status dot and a hover tooltip showing formula, data source, and sample size (sourced from `/api/dashboard/kpi-metrics`)
3. **World Map** — D3-geo projection showing all sites with pulsating blue dots for sites needing attention. Clickable for site drill-down
4. **AI Investigation search** — Natural-language input with quick action chips (pre-built queries) and "Explore more" section
5. **Attention list** — Top 5 sites needing attention, sorted by risk level

**Assistant Panel (`AssistantPanel.jsx`):** When a query is submitted, a right-side slide-in panel opens (420px, Framer Motion animated) while the dashboard remains fully visible. The panel renders investigation results using an LLM-chosen display format:

- **Narrative** — executive summary, top hypothesis with causal chain, recommended action
- **Narrative + Table** — narrative section plus a sortable data table (headers/rows from `display_format.table_data`)
- **Table** — full-width sortable table with minimal narrative
- **Narrative + Chart** — narrative section plus an inline SVG bar/line chart

Investigation progress streams via WebSocket with phase labels (Analyzing → Gathering → Analyzing patterns → Planning → Running → Evaluating → Preparing → Complete). The panel includes a follow-up input for iterative investigation. For cached results, the backend simulates phase progression (~7s) to provide a consistent real-time feel.

### Explore More Modals

The "Explore more" section exposes 4 domain summaries as lightweight modals that display pre-aggregated dashboard data — no agent investigation required. Each modal fetches from cached dashboard API endpoints on open and renders in a consistent Apple greyscale design.

**Shared modal chrome (`ExploreModal` component):**
- Framer Motion spring animation (`damping: 30, stiffness: 400`)
- Backdrop blur overlay with click-to-close
- `max-w-4xl`, scrollable body, X close button
- Consistent header with title + subtitle

**Modal 1: Vendor Performance Summary**
- **API**: `GET /api/dashboard/vendor-scorecards` → `getVendorScorecards()`
- **Header**: RAG breakdown (on track / watch / action needed vendor counts) in greyscale tones
- **Body**: 2-column grid of vendor cards — each shows vendor name, type, country HQ, greyscale RAG dot, contract value ($M), active sites, KPI summary (value/target with bold emphasis for off-target), top issues with severity labels, and milestone status pills

**Modal 2: Financial Health Overview**
- **APIs**: `GET /api/dashboard/financial-summary` → `getFinancialSummary()` + `GET /api/dashboard/cost-per-patient` → `getCostPerPatient()`
- **Header**: 4-metric row — Total Budget, Spent to Date, Remaining, Forecast (formatted as $M/$K)
- **Indicators**: Variance % badge (color-coded), burn rate per month, spend trend
- **Body**: Top 8 sites by cost variance as a compact table (site name, cost per randomized patient, variance %)

**Modal 3: Data Quality Trends**
- **API**: `GET /api/dashboard/data-quality` → `getDataQualityDashboard()`
- **Header**: Study-wide averages — mean entry lag (days), total queries
- **Body**: Top 12 sites sorted by worst data quality (highest mean entry lag) in a compact table with visual bar indicators for entry lag and open query counts, plus correction counts

**Modal 4: Enrollment Velocity**
- **API**: `GET /api/dashboard/enrollment-funnel` → `getEnrollmentDashboard()`
- **Header**: 4-metric row — Screened, Randomized, Target, % of Target
- **Funnel**: Horizontal bar visualization showing screened → passed screening → randomized with counts
- **Body**: Top 12 sites sorted by lowest enrollment % in a compact table with color-coded progress bars

**Design rationale:** These modals provide instant operational visibility without waiting for agent investigations. The data is pre-aggregated on the backend (pure SQL, no LLM calls), served from cached endpoints (120s TTL with in-flight dedup), and renders in under 200ms. This complements the AI investigation workflow — users get a quick overview from modals, then ask targeted questions via the search bar for deeper analysis.

### API Client (`frontend/src/lib/api.js`)

All API calls route through a client-side caching layer:

- **`cachedFetch(endpoint, ttlMs)`** — TTL-based cache (default 120s) with in-flight request deduplication. Prevents redundant network calls when multiple components request the same data simultaneously
- **`invalidateApiCache()`** — Clears all cached data; called after investigation completes (new findings may change dashboard data)
- **WebSocket streaming** — `connectInvestigationStream()` manages the `/ws/query/{queryId}` connection with phase, completion, error, and keepalive message handling. For cached investigation results, the backend simulates real-time phase progression (~7s) before delivering the final response

### Other Key Views

| Component | File | Purpose |
|-----------|------|---------|
| `Home` | `Home.jsx` | Landing page with study selection, AI agents modal, platform architecture modal |
| `AssistantPanel` | `AssistantPanel.jsx` | Right-side slide-in panel for investigation results with smart display format rendering |
| `Pulse` | `Pulse.jsx` | Real-time data pulse visualization |
| `Constellation` | `Constellation.jsx` | Site network graph |
| `WorldMap` | `WorldMap.jsx` | D3-geo geographic site map (reused in Command Center) |
| `CommandPalette` | `CommandPalette.jsx` | Cmd+K command interface for natural-language queries |
| `InvestigationTheater` | `InvestigationTheater.jsx` | Full-screen agent investigation result display |
