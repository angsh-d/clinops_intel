# Data Quality Agent — Design Document

**Agent ID:** `data_quality` | **Finding Type:** `data_quality_analysis` | **Version:** 1.0

---

## 1. Purpose & Differentiating Intelligence

The Data Quality Agent detects **non-obvious causal patterns** behind data quality degradation that dashboards and KRI thresholds miss entirely. A KRI dashboard shows _that_ entry lag is red; this agent explains _why_ — and the answer is often not what an operations team assumes.

**Signature capabilities:**

1. **CRA Transition Impact Detection** — When a CRA changes at a site, there is a 4-8 week learning-curve disruption to data quality. The agent correlates CRA assignment history with entry lag spikes and query burden increases, identifying the _transition itself_ as the root cause rather than blaming site staff.

2. **Monitoring Gap Hidden Debt** — A site with low open queries and good entry lag looks healthy on a dashboard. But if the last monitoring visit was 90+ days ago, the absence of queries means absence of _oversight_, not good quality. The agent detects this inverse signal: apparent quality during monitoring gaps is hidden debt that will surface as a query avalanche after the next visit.

3. **Strict PI Paradox** — A site with excellent data quality metrics (low corrections, fast entry) combined with high screen failure rates reveals an overly strict Principal Investigator. The PI's rigorous screening filters patients aggressively, producing clean data on fewer subjects. This cross-domain pattern (quality + enrollment) cannot be detected by either domain alone.

---

## 2. Investigation Methodology

### 2.1 Reasoning Philosophy

The agent applies **causal chain reasoning** — every finding must trace from root cause through intermediate mechanisms to the observable surface signal.

**Entity focus rule:** When the query names a specific site, the first hypothesis (H1) MUST be about that entity. The agent uses the site directory for name-to-ID resolution.

**Severity scale:** `critical` / `high` / `medium` / `low`

Six canonical reasoning chains guide hypothesis generation:

- Entry lag spike → check CRA assignment dates → transition detected → root cause is onboarding disruption
- Low query count during monitoring gap → absence of oversight → hidden quality debt accumulating
- High correction rate NOT triggered by queries → systematic entry errors OR proactive self-correction
- Excellent quality + high screen failure → overly strict PI filtering
- Regional cluster of simultaneous degradation → shared external cause (holiday, regulatory change, system outage)
- High unprompted correction rate → suspicious pre-emptive cleanup before monitoring

### 2.2 Perception Strategy

Iteration 1 casts a wide net across all data quality dimensions simultaneously:

| Tool | Purpose |
|------|---------|
| `entry_lag_analysis` | Baseline entry lag distribution (mean/median/p90) |
| `query_burden` | Open/aging queries, type distribution |
| `data_correction_analysis` | Correction rates, query-triggered vs unprompted |
| `cra_assignment_history` | CRA transitions and tenure |
| `monitoring_visit_history` | Visit dates, findings, critical findings |
| `site_summary` | Site metadata for context |

The broad sweep prevents premature narrowing — a site's worst signal may not be the one initially asked about.

### 2.3 Multi-Iteration Deepening

**Iteration 1:** Broad perception across all sites and dimensions. Reason phase generates hypotheses with causal chains. Plan selects tools to test specific hypotheses.

**Iteration 2:** Receives prior results and reflection gaps. Targets _specific sites_ identified in iteration 1. Avoids repeating tools that returned empty results. Drills into CRA-specific analysis (`cra_portfolio_analysis`) or regional patterns (`regional_comparison`) based on hypotheses.

**Iteration 3:** Resolves remaining contradictions. If a site shows conflicting signals (good entry lag but bad query aging), iteration 3 examines monitoring visit timing to reconcile. Cross-domain signals are flagged for the Conductor.

---

## 3. Key Signals & Detection Logic

| Signal | Detection Method | Why It Matters | Naive Misinterpretation |
|--------|-----------------|----------------|------------------------|
| Entry lag spike at site | `entry_lag_analysis` p90 > study median × 2 | Data not entering EDC promptly | "Site staff are slow" — may actually be CRA transition disruption |
| Low queries during monitoring gap | `query_burden` open_queries near 0 + `monitoring_visit_history` last visit >60 days | Hidden quality debt accumulating | "Site has excellent quality" — actually no one is looking |
| High unprompted corrections | `data_correction_analysis` unprompted_rate > 40% | Systematic entry process issues OR pre-monitoring cleanup | "Site is proactively fixing errors" — may be covering tracks |
| CRA transition within 60 days of spike | `cra_assignment_history` dates vs `entry_lag_analysis` trend | Transition is the root cause | "Site degraded" — actually CRA onboarding curve |
| Zero monitoring findings | `monitoring_visit_history` findings_count = 0 consistently | CRA not conducting thorough review | "Excellent site" — may be inadequate oversight |
| Regional simultaneous degradation | `regional_comparison` entry lag trends across sites in same country | Shared external cause (holidays, regulatory) | "Multiple sites underperforming" — single shared cause |

---

## 4. Tools

| Tool | Purpose | Key Arguments |
|------|---------|---------------|
| `entry_lag_analysis` | eCRF entry lag by site/page (mean, median, p90, max) | `site_id`, `period_start`, `period_end` |
| `query_burden` | Query counts, aging, types, status by site | `site_id`, `period_start`, `period_end` |
| `data_correction_analysis` | Correction rates, query-triggered vs unprompted | `site_id` |
| `cra_assignment_history` | CRA IDs, assignment dates, transitions | `site_id` |
| `monitoring_visit_history` | Visit dates, findings, critical findings, overdue days | `site_id` |
| `site_summary` | Site metadata (country, type, experience, activation) | `site_id`, `country` |
| `regional_comparison` | Cross-site metrics within same country/region | `country`, `site_ids`, `period_start`, `period_end` |
| `cra_portfolio_analysis` | Cross-site CRA analysis for rubber-stamping | `cra_id` |
| `kri_snapshot` | KRI values and thresholds | `site_id`, `kri_name` |
| `context_search` | Semantic search of prior agent findings for cross-investigation context | _(query text)_ |

All registered tools (39+) are available to the LLM during Plan/Act phases. The table above lists the most commonly selected tools for this agent's domain.

---

## 5. Cross-Domain Interactions

Every agent output includes metadata consumed by the Conductor: `investigation_complete` (bool), `remaining_gaps` (list), and `confidence` (0-1). The Conductor caps cross-domain confidence at 0.7 for any finding that relies primarily on an agent whose `investigation_complete` is `false`.

### 5.1 Signals Produced (for other agents)

- **CRA transition timeline** → consumed by [vendor_performance.md](vendor_performance.md) to attribute staffing instability to specific CROs
- **Monitoring gap duration** → consumed by [phantom_compliance.md](phantom_compliance.md) (context for zero-finding visits) and [financial_intelligence.md](financial_intelligence.md) (deferred SDV cost accumulation)
- **Entry lag spikes** → consumed by [financial_intelligence.md](financial_intelligence.md) to calculate operational delay costs
- **Strict PI signal** → consumed by [enrollment_funnel.md](enrollment_funnel.md) as explanation for high screen failure rates

### 5.2 Signals Consumed (from other agents)

- **Enrollment velocity decline** from [enrollment_funnel.md](enrollment_funnel.md) — coincident enrollment and quality degradation suggests shared root cause
- **Vendor KPI breaches** from [vendor_performance.md](vendor_performance.md) — vendor-attributable quality degradation
- **Variance suppression flags** from [phantom_compliance.md](phantom_compliance.md) — distinguishes genuine quality from manufactured perfection

### 5.3 Conductor Synthesis Patterns

- **Data Quality + Enrollment Funnel:** Shared operational root causes (CRA transitions affect both domains simultaneously)
- **Data Quality + Data Integrity:** Genuine quality vs manufactured perfection — the Conductor must determine if excellent metrics are real or fabricated
- **Vendor Performance + Data Quality:** Vendor-attributable root causes for quality degradation (CRA turnover linked to specific CRO)

---

## 6. Failure Modes & Anti-Patterns

**MUST NOT rules:**
- MUST NOT treat low query counts as inherently positive without checking monitoring visit recency
- MUST NOT blame site staff for entry lag spikes without checking CRA transition history
- MUST NOT treat aggregate site averages as representative — use p90 and distributions
- MUST NOT ignore absence of data (no monitoring visits, no corrections) as "no issues"

**Known failure modes:**
- **Threshold anchoring:** Fixating on whether a metric crosses a threshold rather than analyzing the _trend_ and _cause_
- **Single-site tunnel vision:** Investigating one site in isolation when regional comparison would reveal a shared cause
- **Conflating correlation with causation:** CRA transition coinciding with entry lag spike needs directional evidence (did lag start _after_ transition date?)
- **Ignoring denominator effects:** A site with 3 subjects and 0 queries is not "good quality" — it is insufficient data

---

## 7. Investigation Scenarios

### Scenario A — CRA Transition Impact (1-2 iterations)

**Query:** "Why has data quality degraded at Site 1042?"

**Iteration 1:**
- **Perceive:** Broad sweep of Site 1042 — entry lag p90 jumped from 5 to 18 days over last 4 weeks. Open queries doubled. Monitoring visits on schedule.
- **Reason:** H1: CRA transition disruption (check assignment history). H2: EDC system issue (check if regional pattern).
- **Plan:** `cra_assignment_history(site_id=1042)`, `regional_comparison(country="US")`
- **Act:** CRA changed 6 weeks ago. No regional pattern — other US sites stable.
- **Reflect:** Strong evidence for CRA transition. Goal satisfied — root cause identified with temporal correlation. No iteration 2 needed.

### Scenario B — Hidden Debt Discovery (2-3 iterations)

**Query:** "Proactive scan — identify sites at risk for data quality issues"

**Iteration 1:**
- **Perceive:** All sites scanned. Sites 1015 and 1023 flagged — both show low queries AND low corrections. Looks excellent on the surface.
- **Reason:** H1: Genuinely excellent sites. H2: Hidden debt — monitoring gaps masking issues. H3: Phantom compliance (manufactured perfection).
- **Plan:** `monitoring_visit_history(site_id=1015)`, `monitoring_visit_history(site_id=1023)`, `cra_oversight_gap(site_id=1015)`, `cra_oversight_gap(site_id=1023)`
- **Act:** Site 1015 last monitored 95 days ago. Site 1023 last monitored 72 days ago. Both have CRA coverage gaps.

**Iteration 2:**
- **Reason (with prior results):** H2 confirmed for both sites. Monitoring gaps explain "good" metrics. Estimate hidden debt by calculating expected queries per monitoring visit × gap duration.
- **Plan:** `entry_lag_analysis(site_id=1015, period_start=<gap_start>)` — check if entry lag is degrading during the unmonitored period
- **Act:** Entry lag has been gradually increasing during the monitoring gap — confirming quality debt accumulation.
- **Reflect:** Hidden debt confirmed. Cross-domain followup: flag to [vendor_performance.md](vendor_performance.md) for CRA staffing investigation. Goal satisfied.

---

## 8. Proactive Scan Directives

Proactive scans execute after each data ingestion cycle via the Directive Catalog (`/prompt/directives/`). Each focus area below maps to a parameterized directive `.txt` file registered in `catalog.json`. Reactive user queries take priority over proactive scans; scans are interruptible and resumable.

**Default directive focus areas:**
- Sites with monitoring gaps > 45 days
- Sites where CRA transition occurred in last 60 days
- Sites with entry lag trend worsening over 4+ weeks
- Sites with suspiciously low query counts relative to subject volume
- Regional clusters showing simultaneous degradation

**Scan triggers:**
- New CRA assignment detected for any site
- Monitoring visit overdue by > 30 days
- Entry lag p90 crosses 2× study median
- Query aging > 14 days for > 20% of open queries
