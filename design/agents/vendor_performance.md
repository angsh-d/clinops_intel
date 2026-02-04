# Vendor Performance Agent — Design Document

**Agent ID:** `vendor_performance` | **Finding Type:** `vendor_performance_analysis` | **Version:** 1.0

---

## 1. Purpose & Differentiating Intelligence

The Vendor Performance Agent attributes operational problems to specific **vendors (CROs)** using junction-table relationships between vendors, sites, CRAs, and milestones. While other agents detect _what_ is happening at sites, this agent answers _who is responsible_ — which vendor's performance is driving the issue.

**Signature capabilities:**

1. **Vendor Attribution via Junction Table** — The CODM schema links vendors to sites through assignment tables. When the [data_quality.md](data_quality.md) agent finds CRA turnover at multiple sites, this agent determines whether those CRAs all belong to the same CRO — turning a collection of site-level observations into a vendor-level finding. This attribution is the bridge between operational signals and contractual accountability.

2. **Cross-CRO Benchmarking** — In multi-vendor trials (e.g., Global CRO handling North America + Europe, Regional CRO handling Asia-Pacific), the agent compares operational metrics (entry lag, query resolution speed, monitoring completion) across vendors covering comparable site portfolios. One CRO consistently 2× slower than another on the same metrics is a vendor performance issue, not a site issue.

3. **Milestone Cascade Risk Detection** — Vendor milestone delays rarely exist in isolation. A delayed site activation milestone at one vendor cascades to delayed enrollment milestones, which cascade to delayed database lock timelines. The agent detects these cascade patterns — a 2-week activation delay at a CRO managing 40 sites compounds into study-level timeline risk.

4. **Issue Pattern Analysis** — Individual vendor issues may seem minor. The agent analyzes issue log patterns: recurring issue types, escalation frequency, resolution time trends, severity distribution shifts. A vendor with increasing issue severity and lengthening resolution times signals systemic degradation, not isolated incidents.

---

## 2. Investigation Methodology

### 2.1 Reasoning Philosophy

The agent applies **vendor accountability reasoning** — every operational metric has a responsible party. When sites under one vendor consistently underperform sites under another vendor with comparable complexity, the vendor is the differentiating variable. The agent separates vendor-attributable causes from site-attributable causes by using cross-vendor comparison as a natural control group.

**Severity scale:** `critical` / `warning` / `info` (distinct from site-level agents which use critical/high/medium/low — vendor findings use an operational urgency scale). Each finding includes `vendor_id`, `operational_impact`, and `recommendation`.

Five canonical reasoning chains:

- KPI trend declining 3+ periods → check if site-level metrics degraded at vendor's sites → vendor-attributable systemic issue (not one-off)
- CRA turnover concentrated at one vendor → check data quality/enrollment at affected sites → vendor staffing problem causing operational degradation
- Milestone delay at one vendor → check downstream milestone dependencies → cascade risk compounding across vendor's entire portfolio
- Cross-CRO metric divergence on same dimensions → normalize for portfolio complexity → vendor capability gap (not regional difficulty)
- Issue severity distribution shifting toward critical → check resolution time trends → vendor losing operational capacity

### 2.2 Perception Strategy

Iteration 1 captures the full vendor performance landscape:

| Tool | Purpose |
|------|---------|
| `vendor_kpi_analysis` | KPI trends and threshold breaches per vendor |
| `vendor_site_comparison` | Operational metrics (entry lag, queries, randomized) per vendor |
| `vendor_milestone_tracker` | Planned vs actual milestone dates and delays |
| `vendor_issue_log` | Issue patterns, severity, resolution rates |
| `site_summary` | Site metadata for vendor-to-site mapping context |

### 2.3 Multi-Iteration Deepening

**Iteration 1:** Broad vendor landscape — KPIs, milestones, issues across all vendors. Identify vendors with threshold breaches or negative KPI trends.

**Iteration 2:** Drill into underperforming vendors. Cross-reference vendor KPI degradation with site-level data quality and enrollment metrics. Use `cra_assignment_history` to identify CRA turnover patterns specific to a vendor. Use `vendor_site_comparison` to compare vendor's sites against study averages.

**Iteration 3:** Quantify impact. Link vendor delays to study-level timeline risk. Identify specific contractual KPI breaches for governance discussions. Generate cross-domain followups for [financial_intelligence.md](financial_intelligence.md) to calculate dollar impact.

---

## 3. Key Signals & Detection Logic

| Signal | Detection Method | Why It Matters | Naive Misinterpretation |
|--------|-----------------|----------------|------------------------|
| Vendor KPI trend declining 3+ periods | `vendor_kpi_analysis` trend direction | Systemic degradation, not isolated incident | "One bad month" — trend matters more than point-in-time |
| Cross-CRO metric divergence | `vendor_site_comparison` Vendor A vs Vendor B | Vendor-attributable performance gap | "Different regions have different challenges" — same-complexity sites with different vendors perform differently |
| Milestone delays accumulating | `vendor_milestone_tracker` planned - actual > threshold | Cascade risk to downstream milestones | "Minor delay" — 2-week delay × 40 sites = study-level impact |
| Issue severity escalating | `vendor_issue_log` severity distribution shifting toward critical | Vendor operational capacity degrading | "More issues being reported" — severity shift is the signal |
| CRA turnover concentrated at one vendor | `cra_assignment_history` + vendor attribution | Vendor staffing problem, not site-level turnover | "CRA turnover is normal" — concentrated at one vendor is not |
| Resolution time increasing | `vendor_issue_log` resolution_days trend | Vendor losing capacity to address issues | "Complex issues take longer" — systemic slowdown across all issue types |

---

## 4. Tools

| Tool | Purpose | Key Arguments |
|------|---------|---------------|
| `vendor_kpi_analysis` | KPI trends, threshold breaches, target comparisons | `vendor_id` |
| `vendor_site_comparison` | Operational metrics per vendor across sites | `vendor_id` |
| `vendor_milestone_tracker` | Planned vs actual milestone dates and delays | `vendor_id` |
| `vendor_issue_log` | Issue patterns, severity, resolution rates | `vendor_id`, `status` |
| `site_summary` | Site metadata for vendor-site context | `site_id`, `country` |
| `cra_assignment_history` | CRA transitions for vendor staffing analysis | `site_id` |
| `entry_lag_analysis` | Entry lag at vendor's sites vs study average | `site_id` |
| `query_burden` | Query aging at vendor's sites | `site_id` |
| `monitoring_visit_history` | Monitoring visit completion at vendor's sites | `site_id` |
| `context_search` | Semantic search of prior agent findings for cross-investigation context | _(query text)_ |

All registered tools (39+) are available to the LLM during Plan/Act phases. The table above lists the most commonly selected tools for this agent's domain.

---

## 5. Cross-Domain Interactions

Every agent output includes metadata consumed by the Conductor: `investigation_complete` (bool), `remaining_gaps` (list), and `confidence` (0-1). The Conductor caps cross-domain confidence at 0.7 for any finding that relies primarily on an agent whose `investigation_complete` is `false`.

### 5.1 Signals Produced (for other agents)

- **Vendor-attributable root causes** → consumed by [data_quality.md](data_quality.md) to explain CRA turnover and monitoring gaps
- **Milestone delay cascade timeline** → consumed by [financial_intelligence.md](financial_intelligence.md) to calculate delay cost impact
- **CRO staffing instability evidence** → consumed by [site_rescue.md](site_rescue.md) as a temporary (fixable) root cause if vendor can be managed
- **Vendor issue patterns** → consumed by [financial_intelligence.md](financial_intelligence.md) for change order and budget impact analysis

### 5.2 Signals Consumed (from other agents)

- **CRA transition detection** from [data_quality.md](data_quality.md) — site-level CRA changes attributed to vendor staffing
- **Site enrollment decline** from [enrollment_funnel.md](enrollment_funnel.md) — vendor's sites disproportionately affected
- **Supply-masked withdrawal evidence** from [enrollment_funnel.md](enrollment_funnel.md) — supply chain failures attributed to vendor's logistics/depot management
- **CRA rubber-stamping** from [phantom_compliance.md](phantom_compliance.md) — oversight failure attributed to vendor's CRA training/management
- **Budget variance by vendor** from [financial_intelligence.md](financial_intelligence.md) — financial context for vendor performance discussions

### 5.3 Conductor Synthesis Patterns

- **Vendor Performance + Data Quality:** The Conductor determines whether data quality issues are vendor-attributable (CRA staffing, monitoring completion) or site-attributable (PI capability, local staff)
- **Vendor Performance + Financial Intelligence:** Cost impact of vendor underperformance — milestone delays converted to dollar cost, change order patterns linked to KPI breaches
- **Vendor Performance + Site Rescue:** Whether vendor management (temporary fix) or vendor replacement is needed as part of site rescue strategy

---

## 6. Failure Modes & Anti-Patterns

**MUST NOT rules:**
- MUST NOT blame vendors for site-level issues without establishing the vendor-attribution link (sites may underperform for non-vendor reasons)
- MUST NOT compare vendors without normalizing for portfolio complexity (a vendor managing difficult sites in developing countries should not be compared raw against one managing established US sites)
- MUST NOT treat KPI threshold breaches in isolation — trend direction matters more than single-period breach
- MUST NOT ignore vendor issue resolution patterns — a vendor that resolves issues quickly demonstrates operational capacity even if issue volume is high

**Known failure modes:**
- **Complexity-blind comparison:** Comparing Global CRO (60 sites, 15 countries) against Regional CRO (20 sites, 3 countries) without normalizing for complexity
- **Volume conflation:** High issue volume may indicate thorough self-monitoring, not poor performance — check severity distribution
- **Correlation without attribution:** Sites under Vendor A underperforming may be caused by regional factors (e.g., regulatory delays), not vendor capability
- **Recency bias:** One recent milestone miss overshadowing a track record of on-time delivery

---

## 7. Investigation Scenarios

### Scenario A — CRA Turnover Attribution (1-2 iterations)

**Query:** "Multiple sites reporting CRA transitions in the last 60 days — is this a vendor issue?"

**Iteration 1:**
- **Perceive:** 8 sites had CRA transitions in last 60 days. Vendor KPI analysis: Global CRO (6 of 8 transitions), Regional CRO (2 of 8). Global CRO's staffing KPI trending down 3 consecutive months.
- **Reason:** H1: Global CRO has systemic staffing problem — 6/8 transitions concentrated at one vendor with declining staffing KPI. H2: Normal turnover spread across vendors.
- **Plan:** `vendor_site_comparison` for Global CRO — check if entry lag and query metrics degraded at affected sites
- **Act:** Global CRO sites with recent transitions show entry lag spike (p90: 5→14 days). Regional CRO sites stable.
- **Reflect:** Vendor-attributable CRA turnover confirmed at Global CRO. Systemic staffing problem evidenced by KPI trend + concentrated transitions + measurable site impact. Recommend: contractual KPI discussion, staffing plan review, escalation pathway.

### Scenario B — Milestone Cascade Analysis (2-3 iterations)

**Query:** "Global CRO milestone delays — what is the downstream impact?"

**Iteration 1:**
- **Perceive:** Global CRO milestones: site activation delayed average 18 days (8 of 25 sites). Site initiation visits delayed 12 days average. Enrollment milestones not yet assessable.
- **Reason:** H1: Activation delays will cascade to enrollment start delays, compounding gap to enrollment targets. H2: Sites may be absorbing delays through accelerated enrollment after activation.

**Iteration 2:**
- **Reason (with prior results):** If activation delays are cascading, the 8 delayed sites should show enrollment gaps proportional to the delay. Need to confirm cascade vs absorption.
- **Plan:** `enrollment_velocity` for the 8 delayed-activation sites. `vendor_milestone_tracker` for downstream milestones.
- **Act:** 6 of 8 delayed sites are behind enrollment target by the amount predicted by the activation delay. Only 2 sites recovered through accelerated enrollment. Downstream: database lock milestone projected 6 weeks late.
- **Reflect:** Cascade confirmed. 18-day activation delay × 25 sites = study-level impact. Database lock delay has financial implications. Cross-domain followup to [financial_intelligence.md](financial_intelligence.md) for delay-to-dollar calculation. Recommend: vendor performance improvement plan, activation process audit, contingency enrollment strategy.

---

## 8. Proactive Scan Directives

Proactive scans execute after each data ingestion cycle via the Directive Catalog (`/prompt/directives/`). Each focus area below maps to a parameterized directive `.txt` file registered in `catalog.json`. Reactive user queries take priority over proactive scans; scans are interruptible and resumable.

**Default directive focus areas:**
- Vendor KPIs with negative trends for 2+ consecutive measurement periods
- Milestone delays > 10 days for activation or enrollment milestones
- CRA turnover concentrated at a single vendor (>50% of all transitions)
- Issue log severity distribution shifting toward critical/high
- Cross-CRO metric divergence > 50% on same operational dimensions

**Scan triggers:**
- Vendor KPI crosses threshold in any dimension
- 3+ milestone delays at same vendor within one month
- Issue log shows unresolved critical issue for > 14 days
- CRA assignment change at vendor already flagged for staffing concerns
