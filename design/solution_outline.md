# High-Level Solution Outline

## Agentic Clinical Operations Intelligence System

**Autonomous AI Agents that Investigate Operational Signals, Reason About Risk, and Drive Proactive Trial Optimization**

----------

## 1. Overview and Vision

Clinical trials are increasingly delivered through CRO partners and distributed vendor ecosystems. While CROs manage day-to-day execution across sites, monitoring, enrollment, and vendors, sponsors often require stronger capabilities for continuous oversight, early risk detection, and proactive intervention.

The Agentic Clinical Operations Intelligence System is an autonomous intelligence layer that integrates operational telemetry across the trial ecosystem and deploys goal-directed AI agents to:

-   **Autonomously investigate** emerging site risks by decomposing complex operational signals into root-cause hypotheses and evidence-backed recommendations

-   **Converse with users** through natural language interaction, enabling drill-down questioning, contextual follow-ups, and collaborative investigation of operational issues

-   **Correlate cross-domain signals** — connecting data quality, enrollment, monitoring, and supply signals to surface compound risks that siloed reports miss

-   **Diagnose enrollment constraints** — distinguishing screening shortfalls from supply-driven interruptions, operational delays, and eligibility barriers so teams intervene at the right point

### Agentic Design Philosophy

The system is built on a **Perceive-Reason-Plan-Act-Reflect (PRPA)** cognitive loop that distinguishes it from traditional analytics dashboards. Each agent does not simply compute metrics from inputs — it perceives operational state, reasons about anomalies and their causes, plans multi-step investigations, acts by invoking tools and requesting cross-agent context, and reflects on whether its goal has been satisfied. This cognitive loop enables agents to handle novel situations, chain together evidence from multiple sources, and produce explanations that trace from raw signal to recommendation.

The system supports informed decision-making by clinical operations teams through explainable, conversational intelligence.

> **Scope note:** This document details the architecture for the system's two-phase delivery. Phase 1 (MVP) delivers Data Quality and Enrollment Funnel agents with EDC and enrollment feeds. Phase 2 (Full Scope) adds Monitoring Gaps and Site Risk Synthesis agents with RBQM/CTMS and IRT/Supply feeds. Capabilities beyond this scope — milestone tracking, vendor SLA monitoring, portfolio intelligence, graduated autonomy, what-if simulation — are documented in the Future Expansion section and are deliberately excluded from current delivery due to higher data access barriers and lower feasibility confidence.

----------

## 2. Data Foundation: Sponsor Digital Oversight Feed

The platform is powered by structured operational data feeds sourced from CRO systems and vendor partners through standardized extracts and integration mechanisms.

Rather than requiring sponsors to directly operate CRO platforms, the solution leverages a Sponsor Digital Oversight Feed that includes key trial execution signals refreshed on appropriate cadences (daily or weekly depending on source).

### 2.1 Data Integration Architecture

The Oversight Feed is built on a **Common Operational Data Model (CODM)** that normalizes signals across heterogeneous source systems into a unified schema. This addresses the reality that CROs operate different platforms (e.g., Medidata Rave, Oracle InForm, Veeva Vault CDMS) with varying schemas, APIs, and export formats.

**Integration approach:**

-   **Source adapters** map vendor-specific extracts (flat files, API responses, CDISC-aligned exports) into the CODM

-   **Schema validation layer** detects format drift, missing fields, and structural anomalies at ingestion time

-   **Feed health monitoring** tracks extract freshness, completeness, and schema conformance — surfacing integration failures before they silently degrade agent outputs

**CODM normalization risk:** EDC schemas vary significantly across vendor platforms (Medidata Rave, Oracle InForm, Veeva Vault CDMS). Field naming, data types, visit structures, and query lifecycle states differ across systems. Mapping these into a common model is the **primary technical effort in the data layer** and the most likely source of integration delays. Mitigation: the CODM design is protocol-aware and version-controlled, with explicit mapping documentation per source system. MVP targets a single CRO platform per study to reduce initial mapping complexity, expanding to multi-CRO normalization as mappings mature.

**Refresh cadence tiers:**

-   **Daily or event-driven:** EDC telemetry, query counts, enrollment metrics, IRT supply events — sufficient for trend detection and daily operational review. IRT systems support event-driven data but extraction into an analytics layer may require API-level integration rather than flat-file exports; the phased approach gives time to negotiate access and build connectors.

-   **Weekly:** Monitoring visit logs, RBQM KRI summaries — aligned with typical CRO reporting cadences

The system treats feed reliability as a first-class concern. Stale or missing feeds trigger explicit data currency warnings on all downstream agent outputs rather than allowing silent degradation.

### 2.2 CRO Data Access Strategy

Obtaining granular operational telemetry from CROs requires deliberate contractual and technical preparation. CROs may treat operational data as proprietary, and data-sharing provisions vary across partnerships.

**Recommended approach:**

-   **Contractual provisions:** Embed structured data feed requirements into CRO Master Service Agreements and study-level work orders, specifying data categories, formats, refresh cadences, and SLAs

-   **Standardized feed specifications:** Provide CRO partners with a published feed specification (schema, file format, delivery mechanism) to reduce integration burden and negotiation friction

-   **Graduated access model:** Begin with aggregated KPI-level feeds (lower CRO resistance) and expand to record-level telemetry as trust and demonstrated value increase

-   **Mutual value positioning:** Frame the Oversight Feed as enabling collaborative risk management rather than CRO performance surveillance — shared visibility benefits both parties

### 2.3 Processing Architecture

**MVP processing model:**

-   **Scheduled batch analysis:** Full agent processing cycles (Agent 1, Agent 3) run on configurable schedules (daily, twice-daily) aligned with feed refresh cadences. This is the primary mode for comprehensive risk assessment.

-   **Conversational request-response:** User queries are routed through the lightweight query router to the appropriate agent, which executes its PRPA loop on demand and returns findings. FastAPI WebSocket endpoints provide streaming delivery so users see reasoning as it unfolds.

**Phase 2 processing model (additive):**

-   **Internal event bus** (FastAPI async with Redis Streams): Data arrival events trigger downstream agent processing without waiting for the next scheduled cycle. Agent finding events at Critical severity trigger Conductor evaluation of cross-agent notification. User queries are routed through the full Conductor for multi-agent orchestration.

-   **Event-triggered real-time analysis:** Critical data changes trigger targeted agent processing outside the scheduled cycle, enabling rapid response to emerging situations.

-   **Backpressure and throttling:** Rate limiting during high-volume periods (e.g., multiple feeds arriving simultaneously) to prevent agent overload while preserving processing order for Critical-severity events.

----------

## 3. Key Data Categories

The system ingests four data categories across two phases. Categories A and D are MVP feeds; Categories B and E are added in Phase 2. Additional categories (Milestones, Vendor KPIs, External Benchmarks) are documented in the Future Expansion section.

----------

### A. EDC Operational Telemetry (Data Quality and Query Signals) — MVP

-   Visit-to-eCRF entry lag

-   Open query counts and aging

-   Missing critical datapoints

-   Data correction frequency

These signals provide early indicators of data quality trends and downstream database readiness risk.

----------

### B. Monitoring Oversight Signals (RBQM-Aligned) — Phase 2

-   Monitoring cadence adherence

-   Last monitoring visit date

-   Overdue follow-up actions

-   Centralized monitoring KRIs

These inputs support monitoring oversight and risk-based prioritization.

----------

### D. Enrollment Funnel Telemetry — MVP

-   Screened vs randomized counts

-   Screen failure rates

-   Failure reason codes (structured) with NLP-assisted categorization of free-text narratives where available

-   Enrollment velocity trends

These signals support enrollment forecasting and site-level intervention planning.

**Note on NLP processing:** Free-text screen failure narratives vary in language, clinical specificity, and completeness across global sites. The system applies NLP categorization as an enrichment layer on top of structured reason codes rather than as a primary signal, ensuring reliability even when narrative quality is inconsistent.

----------

### E. Randomization and Supply Continuity (IRT Signals) — Phase 2

-   Randomization delay or failure events

-   Drug kit inventory gaps

-   Resupply shipment lags

-   Stratification balance indicators

These inputs help prevent enrollment disruption due to supply constraints.

----------

----------

## 3.5 Foundation Model Architecture

The system employs a phased model strategy, starting with a single model for MVP and introducing multi-model consensus in Phase 2.

### MVP: Single-Model Reasoning

-   **Primary Reasoning Model:** Chain-of-thought reasoning for agent cognitive loops, investigation planning, and conversational response generation. Selected based on extended context window and structured output capabilities. Model version is locked per study to ensure reproducibility.

### Phase 2: Multi-Model Strategy

-   **Primary Reasoning Model:** Agent PRPA cycles, complex investigation planning, and cross-domain synthesis

-   **Consensus Partner Model:** Independent assessment for multi-model consensus on Critical-severity findings. Also used for natural language generation in narrative report synthesis where fluency is prioritized.

-   **Conservative Judgment Model:** Applied selectively for tasks requiring careful interpretation of ambiguous signals and situations where conservative judgment reduces risk of false positives in safety-adjacent contexts.

> **Implementation note:** Specific model selections (e.g., Gemini, Azure OpenAI, Anthropic Claude) are configured via environment variables and may change as model capabilities evolve. The architecture depends on model *roles*, not specific versions.

### Model Routing (Phase 2)

The Conductor selects the appropriate model for each sub-task based on:

-   **Task type:** Reasoning-heavy investigation vs. consensus validation vs. narrative generation
-   **Context window needs:** Long investigation chains route to models with larger context windows
-   **Latency requirements:** Real-time conversational interactions prefer lower-latency models

### Consensus Mechanism (Phase 2)

-   Critical-severity findings require agreement from at least two models
-   When models disagree, the finding is flagged for human review with both assessments and their reasoning traces presented
-   Consensus is not required for Informational-tier findings or routine scheduled analysis

### Prompt Management

-   All prompts stored as `.txt` files in the `/prompt/` directory with `{variable_name}` placeholders for runtime substitution
-   Prompts organized by agent and function: `agent1_goal.txt`, `agent1_investigation.txt`, `conductor_decomposition.txt`, `conductor_synthesis.txt`, etc.
-   Prompt changes treated as configuration changes with version tracking and approval

### Model Governance

-   Model versions locked per study to ensure reproducibility of assessments during a study's lifecycle
-   Model updates validated through shadow-mode execution (new model runs in parallel, outputs compared before promotion)
-   Performance tracked per agent: accuracy of predictions, false-positive rates, user feedback scores

### Hallucination Guardrails

-   Output validation layer checks agent claims against source data before surfacing to users — quantitative assertions (counts, dates, percentages) are verified against the underlying CODM records
-   Agents are required to cite specific data signals in their reasoning traces; unsupported claims are flagged and suppressed
-   Confidence scoring reflects data completeness and signal agreement, not model self-assessment

----------

## 4. Agent Layer: Specialized Clinical Operations Intelligence Agents

The system consists of four goal-directed AI agents delivered across two phases. MVP deploys Agent 1 (Data Quality) and Agent 3 (Enrollment Funnel). Phase 2 adds Agent 2 (Monitoring Gaps) and Agent 4 (Site Risk Synthesis). Additional agents (Milestone Drift, Supply Continuity, Vendor Compliance, Portfolio Intelligence) are documented in the Future Expansion section.

### 4.0 Agent Cognitive Architecture

Every agent in the system follows the **Perceive-Reason-Plan-Act-Reflect (PRPA)** cognitive loop:

1.  **Perceive:** Ingest operational signals from the CODM and contextual inputs from adjacent agents. Detect anomalies, threshold breaches, and trend shifts relative to the agent's goal state.

2.  **Reason:** Apply LLM chain-of-thought reasoning to formulate hypotheses about observed patterns. Consider multiple explanations, weigh evidence, and identify information gaps that require further investigation.

3.  **Plan:** Decompose the investigation into concrete steps — which tools to invoke, which additional data to query, which cross-agent context to request. The plan is logged for explainability.

4.  **Act:** Execute the investigation plan by invoking tools from the agent's Tool Registry: SQL queries against the CODM, vector similarity searches in ChromaDB, forecasting model invocations, cross-agent context requests via the Conductor.

5.  **Reflect:** Evaluate whether the agent's Goal State has been satisfied. If the investigation is incomplete or the evidence is insufficient, loop back to Reason with updated context. If satisfied, formulate the output with full reasoning provenance.

**Agent components:**

-   **Goal State:** A declarative objective that goes beyond detection — e.g., "Ensure data quality at all active sites remains within acceptable thresholds, and when it doesn't, investigate root causes and recommend specific remediation actions."

-   **Reasoning Engine:** LLM chain-of-thought processing with externalized prompts (loaded from `/prompt/agent{N}_*.txt`) that define the agent's reasoning patterns, domain knowledge, and investigation strategies.

-   **Tool Registry:** Callable functions available to the agent — SQL query execution, vector similarity search, time-series forecasting, statistical analysis, cross-agent context requests, and report generation.

-   **Working Memory:** ChromaDB scratchpad where the agent stores intermediate findings, hypotheses, and evidence during multi-step investigations. Persists within a processing cycle and is available for cross-agent discovery.

-   **Reflection Step:** Goal satisfaction evaluation that determines whether the agent has produced actionable, evidence-backed output or needs to continue investigating.

**Concrete example — Agent 1 autonomous investigation:**
Agent 1 detects a query spike at Site 042. Rather than simply reporting "query count exceeds threshold," the agent: (1) checks which CRF pages are affected, (2) in Phase 2, retrieves monitoring visit recency from Agent 2 context to determine if a recent visit triggered expected query generation, (3) queries historical episodes of similar spikes at this site, (4) examines whether a new CRA was recently assigned (potential training gap), and (5) formulates a root-cause hypothesis: "Query spike at Site 042 driven by CRF pages 4-7 (efficacy endpoints), not correlated with recent monitoring visit — pattern consistent with data entry training gap following CRA transition on 2026-01-15. Recommend targeted CRA training on efficacy CRF completion."

### 4.1 Agent Communication and Cross-Domain Context

**MVP: Independent agent operation**

In Phase 1, Agents 1 and 3 operate independently — they have no data dependency on each other and produce findings from their own domain feeds. Each agent publishes its findings to a shared store (ChromaDB), building the foundation for cross-agent discovery in Phase 2. The lightweight query router directs user questions to the appropriate agent but does not synthesize across agents.

**Phase 2: Cross-domain communication**

Clinical operational signals are deeply correlated — enrollment delays may be driven by supply constraints, monitoring gaps compound data quality issues, and these cross-domain relationships are invisible in siloed reports. Phase 2 introduces multi-layered communication:

-   **Predefined dependency paths:** Each agent has a primary scope and contextual inputs from adjacent agents where causal relationships are established (e.g., IRT supply signals available to Agent 3, data quality trends available to Agent 2). Agent 4 (Site Risk Synthesis) receives full outputs from all domain agents.

-   **Dynamic Conductor-mediated communication:** Any agent can request context from any other agent through the Conductor when its reasoning identifies a need not covered by predefined paths. Dynamic requests are logged as they may indicate new causal relationships.

-   **Shared Operational Context Store:** Agents publish findings as vector embeddings in ChromaDB, enabling semantic discovery — an agent investigating a site issue can search for related findings from other agents without knowing which agent to ask.

-   **Event-driven broadcast:** Critical findings trigger Conductor evaluation of which other agents should be notified immediately. All cross-agent communications are logged with timestamps and provenance.

### 4.2 Alert Management and Prioritization

Across hundreds of sites and multiple agents, unmanaged alert volume will cause user fatigue and system abandonment. The agent layer incorporates:

-   **Severity tiering:** Alerts classified as Critical (requires action within 24-48 hours), Warning (trending toward risk threshold), and Informational (notable pattern, no action needed)

-   **Suppression rules:** Known issues with active mitigation plans are suppressed from repeated alerting until status changes

-   **Consolidation:** When multiple agents flag the same site (Phase 2), signals are merged into a single composite alert through Agent 4 (Site Risk Synthesis) rather than delivered as separate notifications

-   **Adaptive thresholds:** Alert thresholds adjust based on study phase, therapeutic area norms, and site maturity to reduce false positives

### 4.3 Orchestration Layer — The Trial Operations Conductor

The Conductor is an LLM-backed orchestrator that sits above the domain agents and below the user interaction layer. In MVP, it acts as a **lightweight query router** directing questions to Agents 1 and 3. In Phase 2, it becomes a **full multi-agent orchestrator** — coordinating cross-domain investigations, resolving contradictions between agents, and synthesizing unified responses.

**Goal decomposition (Phase 2):**

-   When a user poses a complex question (e.g., "Why is enrollment behind in Japan?"), the Conductor decomposes it into sub-goals: assess enrollment velocity at Japanese sites (Agent 3), check for supply constraints (Agent 3 IRT enrichment), review monitoring coverage (Agent 2)

-   Sub-goals are dispatched to relevant agents with the query context, and the Conductor tracks completion

**Dynamic agent selection:**

-   The Conductor determines which agents to involve based on query semantics, not a fixed routing table

-   For questions spanning multiple domains (Phase 2), the Conductor identifies the minimal set of agents needed and their execution order (parallel where independent, sequential where one agent's output informs another's investigation)

**Result synthesis:**

-   The Conductor collects agent responses, resolves contradictions, and produces a coherent unified response

-   Contradictions are presented transparently: "Agent 3 identifies screening failure rates as the primary driver at 3 of 5 Japanese sites, while IRT supply signals indicate kit constraints at the remaining 2 sites — both factors are contributing to the regional shortfall"

**Execution plan transparency:**

-   For complex investigations, the Conductor presents its plan to the user before execution: "To answer your question, I'll check enrollment velocity, supply status, and site activation timelines for Japanese sites. Proceed?"

-   Users can refine the plan or add constraints before the investigation runs

**Multi-model consensus:**

-   The Conductor routes high-stakes assessments (escalation recommendations, critical-severity findings) through multiple models and synthesizes the consensus

-   Orchestration prompts stored in `/prompt/conductor_*.txt`

----------

## Agent 1: Data Quality and Query Burden Agent — MVP

**Goal State:** "Ensure data quality at all active sites remains within acceptable thresholds. When quality degrades, investigate root causes — not just symptoms — and recommend specific, actionable remediation."

**Inputs:** EDC lag, query volume, missingness
**Contextual inputs (Phase 2):** Monitoring visit recency (Agent 2) — sites with recent monitoring visits may show transient query spikes that are expected rather than alarming. This correlation is available once monitoring feeds are integrated in Phase 2.

**Tool Registry:**

-   SQL queries: CRF-page-level query breakdowns, query aging distributions, site-level trend analysis, CRA assignment history
-   Vector search: Historical query spike episodes at same site, similar patterns at other sites
-   Forecasting: Query backlog trajectory projection, database readiness impact modeling
-   Cross-agent context (Phase 2): Monitoring visit schedule (Agent 2)

**Autonomous Reasoning Pattern:**
Detect anomaly → Identify affected CRF pages → Query historical episodes → Examine CRA assignment changes → Formulate root-cause hypothesis → Generate targeted remediation recommendation with evidence chain. In Phase 2, add: check monitoring visit correlation (Agent 2 context) to distinguish expected post-visit query spikes from genuine degradation.

**Capabilities:**

-   Detect abnormal query growth and investigate underlying causes

-   Predict backlog impact on database readiness

-   Prioritize sites requiring focused remediation with root-cause attribution

**Outputs:**

-   Query backlog alerts with root-cause analysis

-   Data integrity risk indicators with signal provenance

-   Recommended site-level actions with evidence and expected impact

----------

## Agent 2: Monitoring Oversight Agent — Phase 2

**Goal State:** "Ensure monitoring coverage across all sites maintains the cadence required by the study's risk-based monitoring plan. Identify monitoring gaps before they result in undetected site issues."

**Inputs:** Monitoring cadence, KRIs, overdue actions (from RBQM/CTMS feeds, Phase 2)
**Contextual inputs:** Data quality trends (Agent 1) — deteriorating data quality at a site strengthens the case for monitoring prioritization

**Tool Registry:**

-   SQL queries: Visit schedule adherence, overdue action aging, KRI threshold analysis, CRA workload distribution
-   Vector search: Historical monitoring gap patterns and their outcomes
-   Forecasting: Monitoring capacity modeling, overdue action escalation projections
-   Cross-agent context: Data quality trends (Agent 1)

**Autonomous Reasoning Pattern:**
Detect monitoring cadence breach → Assess severity via KRI status → Check CRA workload and assignment changes → Evaluate data quality trajectory at affected sites → Prioritize based on compound risk → Recommend monitoring plan adjustment with rationale

**Capabilities:**

-   Identify monitoring gaps outside expected tolerance and assess compounding risk

-   Highlight sites requiring targeted review with prioritization rationale

-   Support centralized monitoring workflows with evidence-based recommendations

**Outputs:**

-   Monitoring cadence alerts with compounding risk assessment

-   Oversight prioritization recommendations with evidence chain

----------

## Agent 3: Enrollment Funnel Intelligence Agent — MVP (with Phase 2 IRT enrichment)

**Goal State:** "Maintain enrollment trajectory within protocol targets. When shortfalls emerge, diagnose whether the driver is screening volume, screen failure rates, or operational delays — and recommend targeted interventions. In Phase 2, distinguish screening shortfalls from supply-driven interruptions using IRT data."

**Inputs:** Screening trends, randomization rates, failure reason codes and NLP-categorized narratives
**Contextual inputs (Phase 2):** IRT supply signals — enrollment diagnosis is enriched with supply-constraint data, allowing the agent to identify sites where drug supply constraints (kit stockouts, depot shipping delays, randomization system issues) are the binding factor, not screening volume. Supply-driven enrollment delays are among the most common and most misdiagnosed causes of site underperformance.

**Tool Registry:**

-   SQL queries: Site-level enrollment funnel decomposition, screen failure reason code analysis, regional enrollment velocity comparison
-   NLP analysis: Screen failure narrative categorization and clustering
-   Vector search: Historical enrollment rescue strategies and their effectiveness
-   Forecasting: Enrollment trajectory projection, time-to-target modeling
-   Cross-agent context (Phase 2): IRT supply availability, monitoring visit context (Agent 2)

**Autonomous Reasoning Pattern:**
Detect enrollment shortfall → Decompose funnel by stage (screening → eligibility → consent → randomization) → Identify binding constraint per site → In Phase 2, check IRT supply constraints to distinguish screening shortfalls from supply-driven interruptions → Evaluate screen failure drivers → Recommend site-specific interventions with projected impact

**Capabilities:**

-   Predict enrollment trajectory by site with multi-factor attribution

-   Identify drivers of screen failures through structured and NLP analysis

-   Recommend enrollment support and rescue strategies informed by institutional memory

**Outputs:**

-   Enrollment shortfall forecasts with binding constraint identification

-   Exclusion driver insights with NLP-enriched categorization

-   Site-level prioritization for intervention with projected impact

----------

## Agent 4: Site Risk Synthesis Agent — Phase 2

**Goal State:** "Produce a unified, explainable risk assessment for every active site by fusing signals across all active domain agents. Ensure no compound risk goes undetected because it spans multiple domains."

**Inputs:** Outputs from Agents 1-3 (Data Quality, Monitoring Gaps, Enrollment Funnel)
**Feedback outputs:** Cross-domain pattern signals returned to upstream agents

**Tool Registry:**

-   Cross-agent context: Full output retrieval from Agents 1-3
-   Vector search: Context Store for pattern matching
-   Risk modeling: Multi-factor composite scoring with configurable weights, confidence-adjusted aggregation
-   Report generation: Narrative synthesis of compound risk with full signal provenance

**Autonomous Reasoning Pattern:**
Collect domain agent outputs → Identify sites flagged by multiple agents → Investigate causal connections between cross-domain signals (e.g., rising queries + overdue monitoring + slowing enrollment) → Compute composite risk scores with confidence weighting → Generate narrative explanation tracing from raw signals to recommendations → Broadcast critical findings to Conductor for cross-agent notification

**Capabilities:**

-   Fuse multi-domain risk indicators into composite site risk scores

-   Attribute risk drivers with traceable signal provenance — each recommendation links back to the specific data signals, agent assessments, and thresholds that produced it

-   Prioritize sites requiring immediate attention using weighted multi-factor ranking

-   Generate confidence-scored intervention plans where confidence reflects data completeness, signal agreement across agents, and historical pattern reliability

**Explainability approach:**

-   Every site risk assessment includes a **signal provenance chain:** raw data signal → agent-level assessment → synthesis weighting → composite score

-   Recommendations are presented with **contributing factor breakdowns** showing which agents and signals drove the prioritization

-   Confidence scores are categorized as High (strong agreement across multiple agents with fresh data), Medium (partial agreement or some data currency gaps), or Low (limited signal coverage, flagged for manual review)

**Outputs:**

-   Emerging critical risk site list with composite scores

-   Signal-to-driver-to-action summaries with full provenance

-   Integrated oversight recommendations with confidence classifications

----------

## 5. Insight Modules and Sponsor Dashboards

The platform delivers actionable intelligence through role-specific modules, delivered incrementally across phases:

**MVP Dashboards:**

-   **Enrollment Rescue Hub:** screening and recruitment diagnostics (Agent 3)
-   **Data Quality Monitor:** query burden trends and site-level data health (Agent 1)

**Phase 2 Dashboards:**

-   **Site Risk Radar:** emerging high-risk sites with contributing drivers across all domains (Agent 4)
-   **Monitoring Oversight View:** monitoring cadence compliance and gap detection (Agent 2)

**Future Expansion Dashboards:**

-   Milestone Tracker, Supply Continuity Monitor, Vendor Performance Cockpit — deferred until corresponding agents and data feeds are available

All dashboard modules display **data currency indicators** showing the freshness of underlying feeds, so users can distinguish between insights based on current data and those relying on stale inputs.

### 5.1 Conversational Intelligence Interface

A natural language query interface embedded within dashboards enables users to investigate operational issues interactively rather than through static drill-downs.

**Capabilities:**

-   **Natural language queries:** Users ask questions in plain language — "Why is Site 042 showing a query spike?" or "Which sites are at risk of missing the enrollment target?" — and the Conductor decomposes the query into an agent investigation plan

-   **Conversational drill-down:** Any alert, finding, or dashboard element can be explored through follow-up questions — "What caused this?" → "Is this the same pattern we saw last quarter?" → "What intervention worked last time?"

-   **Clarification and disambiguation:** When queries are ambiguous ("Show me the problem sites"), the system asks clarifying questions rather than guessing — "Do you mean sites with Critical-severity alerts, sites at risk of milestone miss, or sites with enrollment shortfalls?"

-   **Session memory:** Conversational context persists within a session, enabling contextual follow-ups — after discussing Site 042, the user can ask "What about their neighbor Site 043?" without restating the full context

-   **Streaming responses:** Delivered via FastAPI WebSocket endpoints so users see the investigation unfold in real time — first the plan, then interim findings, then the synthesized response

-   **Full audit trail:** All conversational interactions are logged with timestamps, user identity, query text, agent investigation plans, and responses — supporting compliance and continuous improvement

-   **Role-aware response depth:** Responses adapt to the user's persona (Section 6) — an Executive Team member receives portfolio-level summaries, while a Study Manager receives site-level operational detail

### 5.2 Dashboard Architecture

Dashboard modules integrate with the Conversational Intelligence Interface, enabling users to transition seamlessly between structured visualizations and investigative conversation.

----------

## 6. Stakeholder Personas Supported

### Consumers

-   **Sponsor Clinical Operations Leaders:** site oversight and intervention prioritization

-   **CRO Oversight Managers:** execution transparency and governance

-   **Study Managers:** operational control and milestone management

-   **Medical Monitors:** early detection of deviation-heavy or unstable sites

-   **Executive Teams:** portfolio-level performance assurance

### Operational Roles (System Sustainment)

-   **Data Integration Analysts:** feed health monitoring, source adapter maintenance, schema drift resolution

-   **Agent Configuration Owners:** alert threshold tuning, suppression rule management, agent parameter calibration per study

-   **Platform Operations:** system monitoring, model performance tracking, incident response

----------

## 7. Feedback Loop and Continuous Improvement

The system incorporates real-time mechanisms to learn from outcomes, adapt agent behavior, and improve recommendations continuously.

-   **Real-time outcome tracking:** When alerts result in interventions, the system tracks whether the intervention resolved the flagged risk immediately — not at quarterly intervals. Outcome data feeds back into agent reasoning within the same study lifecycle.

-   **Inline user feedback:** Through the conversational interface, users provide nuanced annotations on agent findings — not just "actionable/irrelevant" but contextual feedback: "Correct finding but the recommended action isn't feasible because of regulatory hold at this site." This structured feedback informs both suppression rules and agent reasoning.

-   **Continuous rolling model calibration:** Enrollment forecasts and risk scores are compared against actuals on a rolling basis. Systematic bias is detected and model parameters recalibrated continuously rather than at fixed quarterly intervals. In MVP, calibration relies on enrollment trajectory accuracy and data quality prediction hit rates — expanding to cross-domain risk scores in Phase 2.

-   **Agent self-evaluation scorecards:** Each agent maintains performance metrics: prediction accuracy, false-positive rate, and user feedback scores. Scorecards are visible to Agent Configuration Owners and inform tuning decisions.

-   **Prompt evolution:** Prompts are versioned in the `/prompt/` directory. Updated prompts are validated through shadow-mode testing (new prompt runs in parallel with production prompt, outputs compared) before promotion. Prompt changes are logged as configuration changes.

-   **Reinforcement from outcomes:** The system maintains a growing corpus of (situation, action, outcome) triples in ChromaDB. During agent reasoning, relevant historical outcomes are retrieved via similarity search and presented as context — enabling agents to learn from within-study experience without retraining the underlying models. Cross-study institutional memory is a Future Expansion capability.

----------

## 8. Representative Use Cases

### MVP: Autonomous Multi-Step Investigation (Agent 1)
Agent 1 detects a query spike at Site 042. Through its PRPA cognitive loop, it traces the spike to CRF pages 4-7 (efficacy endpoints), discovers a CRA reassignment occurred two weeks prior, and queries historical episodes for similar patterns. The agent formulates a root-cause hypothesis: data entry training gap following CRA transition. It recommends targeted CRA training on efficacy CRF completion with a projected 60% query reduction within 2 weeks based on historical precedent from a similar episode at Site 019 six months ago. In Phase 2, Agent 1 would additionally request monitoring visit context from Agent 2 to confirm no correlation with recent visits.

### MVP: Enrollment Funnel Diagnosis (Agent 3)
Agent 3 identifies that 3 of 5 Japanese sites have screening rates 40% below target. It decomposes the funnel: Site 305 shows persistent low referral volume (2.1/month vs. target 5/month), while Sites 301/303 show normal screening rates but were activated late. The agent recommends a referral pathway assessment at Site 305 and projects screening ramp-up at Sites 301/303 within 4 weeks. In Phase 2, IRT supply signals would be checked to rule out supply-driven interruptions as a contributing factor.

### Phase 2: Conversational Cross-Domain Investigation
A Study Manager asks: "Why are we behind on enrollment in Japan?" The Conductor decomposes this into sub-goals dispatched to Agents 2 and 3. Agent 3 identifies that 3 of 5 Japanese sites have screening rates 40% below target, with IRT data confirming adequate drug supply. Agent 2 reports monitoring cadence drift at 2 of the underperforming sites. Agent 4 synthesizes: "Japanese enrollment shortfall is driven by persistent low referral volume at Site 305 (screening rate 2.1/month vs. target of 5/month), compounded by monitoring gaps at Sites 301/303 that may be masking data quality issues. Recommend referral pathway assessment at Site 305 and priority monitoring visits at Sites 301/303."

### Phase 2: Compound Risk Detection (Agent 4)
Agent 4 identifies Site 042 as a compound risk: Agent 1 reports rising query backlog (CRF pages 4-7), Agent 2 flags an overdue monitoring visit (3 weeks past schedule), and Agent 3 shows declining screen-to-randomization ratio. No single signal is Critical in isolation, but the combination surfaces a site that needs immediate attention. Agent 4 produces a prioritized watch list with Site 042 at the top, with full signal provenance: "Site 042 — compound risk: data quality degradation + monitoring gap + enrollment deceleration. Most likely driver: CRA transition 2 weeks ago without adequate handover."

----------

## 9. Compliance and Data Governance

The system operates within regulated clinical trial environments and must satisfy applicable data governance requirements:

-   **Audit trail:** All agent-generated assessments, alerts, and recommendations are logged with timestamps, input data versions, and model versions to support traceability

-   **Access control:** Role-based access ensures stakeholders see only the data categories and sites within their authorization scope

-   **Data residency:** The platform supports configurable data residency to comply with regional requirements (GDPR, local data protection regulations) based on sponsor and study geography

-   **GxP positioning:** The system is positioned as a **decision-support tool** — it surfaces insights and recommendations but does not automate clinical or regulatory decisions. This classification informs the validation approach and avoids the full burden of GxP-validated system requirements while maintaining appropriate quality controls

-   **Validation approach:** The platform follows a risk-based validation strategy aligned with GAMP 5 principles, with documented requirements, configuration testing, and periodic performance reviews

-   **Action audit trail:** All agent-generated recommendations include full provenance: triggering signal, agent reasoning trace, recommended action, timestamp, and affected entities. When graduated autonomy is enabled (Future Expansion), autonomous actions will be queryable and auditable by compliance teams.

-   **Model governance:** Model versions are locked per study. Model updates undergo shadow-mode validation before promotion. Reasoning traces are logged for all agent cognitive loops, enabling post-hoc review of any agent assessment.

-   **Prompt version control:** Prompt changes are treated as configuration changes requiring documented approval. All prompt versions are retained with effective date ranges, enabling reconstruction of agent behavior at any historical point.

-   **Conversational interaction logging:** All user queries, agent investigation plans, and system responses are logged with user identity, timestamps, and session context. Retention policies align with study documentation requirements.

-   **Multi-model consensus for critical outputs:** Escalation recommendations and Critical-severity findings require agreement from at least two foundation models. Disagreements are routed to human review with full reasoning traces from both models.

----------

## 10. Outcomes Enabled

### MVP Outcomes

-   Earlier identification of site data quality risks through autonomous multi-step investigation (Agent 1)

-   Enrollment shortfall diagnosis with binding-constraint identification per site (Agent 3)

-   Conversational Q&A replacing manual cross-referencing of static reports

### Phase 2 Outcomes

-   Supply-aware enrollment diagnosis eliminating misattribution of supply-driven delays to site performance (Agent 3 + IRT)

-   Monitoring gap detection before undetected site issues compound (Agent 2)

-   Cross-domain site risk prioritization surfacing compound risks invisible in siloed reports (Agent 4)

-   Enhanced oversight consistency across CROs through unified intelligence layer

### Future Expansion Outcomes

-   Improved milestone predictability with causal attribution

-   Reduced operational disruption through proactive autonomous actions (graduated autonomy)

-   Portfolio-level operational intelligence and cross-study knowledge transfer

-   Proactive scenario planning through what-if simulation

----------

## 11. Implementation Approach

The system is designed for two-phase delivery to manage complexity and demonstrate value incrementally. Additional capabilities are documented as Future Expansion.

### Phase 1 — MVP

**Data:** EDC Operational Telemetry (Category A) + Enrollment Funnel Telemetry (Category D)

**Agents:** Agent 1 (Data Quality) + Agent 3 (Enrollment Funnel) — implemented with PRPA cognitive loops and tool use

**Model:** Single primary reasoning model for agent PRPA cycles (model selection configured via environment variables; see Section 3.5)

**Platform:** Lightweight query router · Conversational interface MVP (basic natural language queries with streaming responses) · Dashboard with data currency indicators

**Dashboards:** Data Quality Monitor + Enrollment Rescue Hub

**Rationale:** These two domains have the most readily available data (EDC exports and screening logs are standard CRO deliverables), address the highest-frequency sponsor pain points, and do not require RBQM, IRT, or vendor portal integrations which carry higher access barriers. The MVP establishes the PRPA cognitive loop pattern and conversational interface as architectural foundations.

### Phase 2 — Full Scope

**Adds:** Monitoring Oversight (Category B) + IRT / Supply Signals (Category E)

**Agents:** Agent 2 (Monitoring Gaps) + Agent 4 (Site Risk Synthesis)

**Enrichments:** Agent 3 (Enrollment Funnel) gains IRT supply-context enrichment, enabling supply-aware enrollment diagnosis. Agent 1 (Data Quality) gains monitoring visit correlation context from Agent 2.

**Platform:** Full Conductor multi-agent orchestration · Multi-model consensus for Critical-severity findings · Event-driven processing for real-time response · Cross-domain site risk prioritization

**Dashboards:** Site Risk Radar + Monitoring Oversight View

**Rationale:** RBQM/CTMS monitoring data and IRT supply signals are the next priority. Monitoring feeds enable gap detection — a high-value capability for study leadership. IRT signals eliminate the blind spot where supply-driven enrollment delays are misattributed to site performance. The Conductor enables the cross-agent reasoning that distinguishes this system from siloed analytics. IRT integration may require API-level access rather than flat-file exports — the phased approach gives time to negotiate data access and build connectors.

----------

## 12. Feasibility Assessment and Key Risks

This section addresses why we believe the system is buildable within the two-phase scope, and where the primary risks lie.

### Why This Is Feasible

-   **MVP data feeds are standard CRO deliverables.** EDC query exports and enrollment screening logs are routinely provided to sponsors as flat files or structured extracts. No novel data access negotiation is required for Phase 1.

-   **The agent architecture builds on proven patterns.** LLM-powered reasoning loops with tool use (SQL queries, vector search, forecasting) are well-established patterns in agentic AI frameworks. The PRPA cognitive loop is an orchestration pattern, not a research problem.

-   **Two MVP agents are independently useful.** Agent 1 and Agent 3 deliver value without cross-agent communication. Each solves a real problem (query backlog diagnosis, enrollment constraint identification) with a single data feed. This eliminates the integration-complexity risk from MVP.

-   **The technology stack is mature.** FastAPI, ChromaDB, Redis, and commercial LLM APIs are production-grade components with established deployment patterns. No custom model training is required — agents use prompted reasoning over structured data.

-   **Phased delivery manages integration risk.** Phase 2 capabilities (monitoring feeds, IRT integration, multi-agent orchestration) are additive. The MVP can ship and deliver value while Phase 2 integration challenges are resolved in parallel.

### Key Technical Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **CODM normalization complexity** — EDC schemas vary significantly across CRO platforms | High | MVP targets a single CRO platform per study; mapping documentation is versioned; schema validation catches drift at ingestion |
| **IRT data access** — IRT integration may require API-level access rather than flat files | Medium | Deferred to Phase 2; phased approach gives time to negotiate access and evaluate integration patterns |
| **LLM reasoning reliability** — agent hypotheses may be incorrect or unsupported | Medium | Output validation layer verifies quantitative claims against CODM records; agents must cite specific data signals; hallucination guardrails suppress unsupported claims |
| **Alert fatigue** — too many findings overwhelm users | Medium | Severity tiering, suppression rules, adaptive thresholds, and Phase 2 consolidation through Agent 4 |
| **CRO data access negotiation** — CROs may resist granular data sharing | Medium | Graduated access model (KPI-level first); mutual value positioning; contractual provisions in MSAs |
| **Feed staleness** — delayed or missing feeds silently degrade agent outputs | Low | Feed health monitoring at ingestion; explicit data currency warnings on all downstream outputs |

### What We Are Not Doing (Deliberate Exclusions)

The following are common pitfalls in clinical analytics platforms that we deliberately avoid:

-   **No custom model training.** Agents use prompted reasoning over structured data — no ML training pipelines, no labeled datasets, no model drift monitoring. This dramatically reduces time to value and operational burden.
-   **No real-time streaming from source systems.** Daily batch feeds are sufficient for operational intelligence. Attempting real-time EDC or CTMS streaming adds integration complexity with marginal benefit.
-   **No direct CRO system integration.** The system consumes exported data feeds, not live API connections to CRO platforms. This avoids the security, authentication, and uptime dependencies that derail integration projects.

----------

## Appendix A: Future Expansion (not in current scope)

The following capabilities are architecturally planned but excluded from Phase 1-2 delivery. Each item lists the prerequisite that must be met before it becomes feasible.

### Future Agents

-   **Milestone Drift Agent:** Operational milestone tracking (site activation, cycle times, visit adherence). *Prerequisite:* deeper CTMS integration with record-level milestone data.
-   **Supply Continuity Agent:** Standalone supply agent with autonomous resupply actions, inventory depletion forecasting, and stratification balance monitoring. *Prerequisite:* mature IRT API integration and graduated autonomy framework.
-   **Vendor Compliance Agent:** Vendor SLA monitoring (imaging, labs, ECG turnaround KPIs). *Prerequisite:* vendor portal integrations with established data sharing agreements.
-   **Portfolio Intelligence Agent:** Cross-study benchmarking, institutional memory, resource optimization. *Prerequisite:* platform operational across multiple studies with established feedback loops.

### Future Platform Capabilities

-   **Graduated Autonomy Framework:** Tiered autonomy model (Tier 0 Inform → Tier 1 Recommend → Tier 2 Act and Notify → Tier 3 Act Autonomously). *Prerequisite:* proven agent accuracy, established rollback mechanisms, regulatory alignment.
-   **What-If Simulation Engine:** Scenario evaluation with shadow data injection and impact propagation. *Prerequisite:* mature agent capabilities and multiple data feeds for reliable projections.
-   **External Benchmark Enrichment:** Historical site performance, trial density, portfolio benchmarks. *Prerequisite:* cross-study data infrastructure.

### Future Data Categories

-   **Operational Milestone Events (CTMS Extracts):** Site activation milestones, startup cycle times, visit schedule adherence, issue resolution timelines. *Prerequisite:* CTMS integration depth beyond Phase 1-2 scope.
-   **Vendor Performance KPIs:** Upload timeliness, rejection rates, turnaround times, lab delays. *Prerequisite:* vendor portal integrations.
-   **External Benchmarks:** Historical site performance, trial density, portfolio benchmarks. *Prerequisite:* cross-study data infrastructure.
