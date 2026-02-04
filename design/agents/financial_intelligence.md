# Financial Intelligence Agent — Design Document

**Agent ID:** `financial_intelligence` | **Finding Type:** `financial_intelligence_analysis` | **Version:** 1.0

---

## 1. Purpose & Differentiating Intelligence

The Financial Intelligence Agent translates operational problems into **dollar impact** and detects financial patterns invisible to standard budget reporting. A finance dashboard shows planned vs actual spend; this agent explains _why_ budget variances exist by linking them to operational root causes across enrollment, data quality, and vendor performance domains.

**Signature capabilities:**

1. **Delay-to-Dollar Linking** — Every operational delay has a financial cost. The agent quantifies: enrollment delays cost $X per week per site in extended operational overhead; monitoring gaps accumulate hidden costs in deferred SDV effort; CRA transitions increase per-patient cost through duplicate training. These translations enable prioritization of operational fixes by financial impact rather than operational severity alone.

2. **Risk-Adjusted Forecasting (Financial Cliff Detection)** — Standard burn rate projections assume constant spend rate. The agent detects "financial cliffs" — points where remaining budget, at current burn rate, will be exhausted before study completion. By incorporating enrollment trajectory projections and delay costs, it identifies scenarios where the study runs out of money before reaching target enrollment.

3. **Change Order Scope Creep Detection** — Individual change orders may appear justified. The agent analyzes the cumulative pattern: increasing frequency, growing amounts, broadening categories. A vendor with 4 change orders in 6 months, each larger than the last, signals systematic scope underestimation — a governance issue, not operational adjustment.

4. **Budget Reallocation Signals** — When site rescue decisions involve closing underperforming sites, the freed budget can be reallocated. The agent identifies reallocation opportunities: which closing sites free which budget categories, and which high-performing sites could absorb additional enrollment with incremental investment.

---

## 2. Investigation Methodology

### 2.1 Reasoning Philosophy

The agent applies **financial root cause analysis** — every budget variance has an operational cause, and every operational problem has a financial impact. The reasoning flows bidirectionally:
- Forward: operational issue → quantify dollar impact
- Backward: budget variance → trace to operational root cause

**Severity scale:** `critical` / `warning` / `info` (distinct from site-level agents which use critical/high/medium/low — financial findings use an urgency scale). Each finding includes `financial_impact` (dollar or percentage), `root_cause`, and `recommendation` (reallocate/negotiate/close).

Five canonical reasoning chains:

- Budget variance in category → identify which vendors/sites drive the variance → trace to operational root cause (enrollment delay, CRA transition, monitoring gap)
- Cost-per-patient outlier → check enrollment pace at site → high fixed overhead spread over few patients (enrollment problem masquerading as cost problem)
- Enrollment delay at site → calculate extended overhead per week → delay cost often dwarfs the direct operational cost being managed
- Change order frequency increasing + amounts escalating → check vendor KPI trend → change orders compensating for vendor underperformance, not genuine scope expansion
- Burn rate × months remaining < enrollment gap → financial cliff detected → study will exhaust budget before reaching enrollment target

### 2.2 Perception Strategy

Iteration 1 captures the full financial landscape:

| Tool | Purpose |
|------|---------|
| `budget_variance_analysis` | Planned vs actual vs forecast by category, country, vendor |
| `cost_per_patient_analysis` | Site-level cost efficiency: cost per screened/randomized |
| `burn_rate_projection` | Monthly snapshots, remaining budget, months of funding |
| `change_order_impact` | Change orders with amounts, timeline impact, cumulative |
| `financial_impact_of_delays` | Dollar cost of enrollment and operational delays |
| `site_summary` | Site metadata for cost normalization |

### 2.3 Multi-Iteration Deepening

**Iteration 1:** Broad financial landscape — budget variance by category, cost-per-patient distribution, burn rate trajectory, change order summary. Identify the largest financial risks.

**Iteration 2:** Drill into specific variances. Cross-reference budget overruns with enrollment delays (is the variance caused by extended timelines?). Examine change order patterns by vendor. Calculate financial cliff scenario.

**Iteration 3:** Link financial findings to operational recommendations. Quantify the dollar value of specific interventions (e.g., "resolving supply chain at Site 1035 would save $45K/month in extended overhead"). Generate reallocation recommendations for site closure scenarios.

---

## 3. Key Signals & Detection Logic

| Signal | Detection Method | Why It Matters | Naive Misinterpretation |
|--------|-----------------|----------------|------------------------|
| Budget variance > 15% in category | `budget_variance_analysis` actual/planned ratio | Systematic overspend in category | "Costs are higher than expected" — need to identify the operational driver |
| Cost-per-patient outlier site | `cost_per_patient_analysis` site vs study median × 2 | Site consuming disproportionate resources | "Expensive site" — may be caused by low enrollment (high fixed cost per patient) |
| Burn rate exceeds replenishment | `burn_rate_projection` months_remaining < months_to_completion | Financial cliff — budget exhaustion before study completion | "Spend is on track" — not when timeline is extending |
| Change order frequency increasing | `change_order_impact` cumulative count and amounts | Scope creep pattern at vendor level | "Normal contract adjustments" — increasing frequency and amount = governance gap |
| Delay cost exceeding direct spend | `financial_impact_of_delays` delay_cost > direct_cost | Indirect costs of delays exceed the operational costs being managed | "Minor operational delay" — $50K delay cost dwarfs the $10K direct cost |
| Vendor budget variance divergence | `budget_variance_analysis` by vendor | One vendor driving disproportionate budget impact | "Study is over budget" — one vendor responsible for 80% of variance |

---

## 4. Tools

| Tool | Purpose | Key Arguments |
|------|---------|---------------|
| `budget_variance_analysis` | Planned vs actual vs forecast by category/country/vendor | `category_code`, `country`, `vendor_id` |
| `cost_per_patient_analysis` | Site-level cost efficiency metrics | `site_id` |
| `burn_rate_projection` | Monthly financial snapshots, remaining budget | _(none)_ |
| `change_order_impact` | Change orders, amounts, timeline impact, cumulative | `vendor_id` |
| `financial_impact_of_delays` | Dollar cost of enrollment and operational delays | `site_id` |
| `site_summary` | Site metadata for cost normalization context | `site_id`, `country` |
| `enrollment_velocity` | Enrollment timeline for cost projection | `site_id`, `last_n_weeks` |
| `enrollment_trajectory` | Gap-to-target for timeline extension cost | `site_id` |
| `trend_projection` | Linear regression projection for burn rate and cost forecasting | _(varies)_ |
| `context_search` | Semantic search of prior agent findings for cross-investigation context | _(query text)_ |

All registered tools (39+) are available to the LLM during Plan/Act phases. The table above lists the most commonly selected tools for this agent's domain.

---

## 5. Cross-Domain Interactions

Every agent output includes metadata consumed by the Conductor: `investigation_complete` (bool), `remaining_gaps` (list), and `confidence` (0-1). The Conductor caps cross-domain confidence at 0.7 for any finding that relies primarily on an agent whose `investigation_complete` is `false`.

### 5.1 Signals Produced (for other agents)

- **Dollar impact of operational delays** → consumed by the Conductor for prioritizing operational interventions across all agents
- **Budget reallocation opportunities** (from site closures) → consumed by [site_rescue.md](site_rescue.md) for rescue/close economic analysis
- **Financial cliff warning** → consumed by the Conductor as a study-level risk escalation
- **Change order governance signal** → consumed by [vendor_performance.md](vendor_performance.md) for vendor accountability discussions
- **Budget variance by vendor** → consumed by [vendor_performance.md](vendor_performance.md) as financial context for vendor performance discussions

### 5.2 Signals Consumed (from other agents)

- **Enrollment delay duration** from [enrollment_funnel.md](enrollment_funnel.md) — translated to delay cost
- **Site rescue/close decisions** from [site_rescue.md](site_rescue.md) — closure frees budget for reallocation
- **Vendor milestone delays** from [vendor_performance.md](vendor_performance.md) — cascade delays translated to dollar impact
- **Monitoring gap duration** from [data_quality.md](data_quality.md) — deferred SDV cost accumulation

### 5.3 Conductor Synthesis Patterns

- **Financial Intelligence + Enrollment Funnel:** Dollar cost of enrollment delays, cost-per-patient efficiency linked to enrollment pace. The Conductor translates enrollment gaps into financial projections.
- **Vendor Performance + Financial Intelligence:** Cost impact of vendor underperformance — milestone delays converted to dollar cost, change order patterns linked to vendor KPI breaches
- **Financial Intelligence + Site Rescue:** Economic analysis of rescue vs close — cost of continued investment vs reallocation benefit

---

## 6. Failure Modes & Anti-Patterns

**MUST NOT rules:**
- MUST NOT report budget variance without tracing to operational root cause — "15% over budget" is a symptom, not a finding
- MUST NOT calculate cost-per-patient without normalizing for enrollment timeline (a site 2 months into enrollment will have high cost-per-patient due to startup costs)
- MUST NOT project burn rate linearly without adjusting for known timeline extensions or enrollment acceleration plans
- MUST NOT present financial findings without specific dollar amounts — percentages alone are insufficient for decision-making

**Known failure modes:**
- **Startup cost distortion:** New sites have high cost-per-patient during ramp-up — flagging them as inefficient ignores the natural cost curve
- **Currency effects:** International trials have currency exchange fluctuations that appear as budget variance but are not operational issues
- **Fixed vs variable cost confusion:** Reporting total budget variance when fixed costs (facilities, equipment) are on track and only variable costs (per-patient) are varying due to enrollment pace
- **Point-in-time snapshot:** Budget looks fine today but burn rate projection shows cliff in 4 months — must always model forward

---

## 7. Investigation Scenarios

### Scenario A — Delay-to-Dollar Translation (1-2 iterations)

**Query:** "What is the financial impact of enrollment delays?"

**Iteration 1:**
- **Perceive:** Budget variance: 12% over plan in "Site Operations" category. Burn rate: $2.1M/month, remaining budget $8.4M, but projected months to enrollment completion: 6 months (vs 4 months remaining budget). Financial impact of delays: 8 sites with enrollment gaps contributing $340K/month in extended overhead.
- **Reason:** H1: Enrollment delays at 8 sites driving budget overrun through extended operational overhead. Budget will be exhausted 2 months before enrollment completion at current pace — financial cliff.
- **Plan:** `financial_impact_of_delays` per site for the top 8 delay contributors. `cost_per_patient_analysis` to identify which sites are most cost-inefficient.
- **Act:** Site 1008: $85K/month delay cost (closed enrollment, high fixed overhead). Site 1041: $62K/month. Top 3 sites account for 65% of total delay cost.
- **Reflect:** Financial cliff confirmed. Closing Sites 1008 and 1041 (recommended by [site_rescue.md](site_rescue.md)) would free $147K/month. Reallocation to high-performing sites could accelerate enrollment by 3 weeks. Specific dollar amounts enable governance decision.

### Scenario B — Change Order Scope Creep (2-3 iterations)

**Query:** "Analyze vendor spending patterns"

**Iteration 1:**
- **Perceive:** Change orders: Global CRO has 5 change orders in 7 months totaling $1.2M. Regional CRO has 1 change order for $80K. Budget variance by vendor: Global CRO 18% over, Regional CRO 3% under.
- **Reason:** H1: Global CRO scope creep — change order frequency and amounts escalating. H2: Initial contract scope underestimation. Each change order larger than the previous.
- **Plan:** `change_order_impact(vendor_id=<global_cro>)` for detailed breakdown. `vendor_kpi_analysis(vendor_id=<global_cro>)` — are KPIs declining as change orders increase?
- **Act:** Change orders: $120K → $180K → $230K → $280K → $390K (escalating). Categories broadening from "additional monitoring visits" to "protocol amendments" to "site management supplements." KPIs: declining monitoring completion rate coincides with change order pattern.
- **Reflect:** Scope creep pattern detected. KPI decline correlates with change order escalation — but need to confirm whether change orders are compensating for vendor underperformance or genuine scope expansion. Remaining gap: milestone delay correlation.

**Iteration 2:**
- **Reason (with prior results):** Change orders correlate with KPI decline. If change orders also align temporally with missed milestones, this confirms the vendor is billing for remediation of its own performance issues.
- **Plan:** `vendor_milestone_tracker(vendor_id=<global_cro>)` — link milestone delays to change order timing
- **Act:** 3 of 5 change orders filed within 2 weeks of missed milestone deadlines.
- **Reflect:** Change order scope creep driven by vendor underperformance, not scope expansion. $1.2M in change orders directly linked to missed milestones and declining KPIs. Recommend: contract governance review, performance improvement plan, change order approval tightening. Cross-domain: flag to [vendor_performance.md](vendor_performance.md) for vendor accountability.

---

## 8. Proactive Scan Directives

Proactive scans execute after each data ingestion cycle via the Directive Catalog (`/prompt/directives/`). Each focus area below maps to a parameterized directive `.txt` file registered in `catalog.json`. Reactive user queries take priority over proactive scans; scans are interruptible and resumable.

**Default directive focus areas:**
- Budget variance > 10% in any category or vendor
- Cost-per-patient outliers (> 1.5× study median) after normalizing for enrollment maturity
- Burn rate trajectory showing budget exhaustion before projected study completion
- Change order cumulative amount exceeding 10% of original contract value
- Financial impact of delays exceeding $100K/month across all sites

**Scan triggers:**
- Monthly financial snapshot shows burn rate acceleration
- New change order submitted (triggers cumulative pattern analysis)
- Site closure recommended by [site_rescue.md](site_rescue.md) (triggers reallocation analysis)
- Enrollment delay > 4 weeks detected at any site (triggers delay-to-dollar calculation)
