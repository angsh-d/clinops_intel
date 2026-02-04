# Phantom Compliance Agent — Design Document

**Agent ID:** `phantom_compliance` | **Finding Type:** `phantom_compliance_analysis` | **Version:** 1.0

---

## 1. Purpose & Differentiating Intelligence

The Phantom Compliance Agent detects **manufactured perfection** — sites that appear to have excellent operational metrics but where the data has been fabricated, batch-entered, or artificially normalized. This is the system's fraud detection capability. Every other agent treats data at face value; this agent questions whether the data itself is trustworthy.

**Signature capabilities:**

1. **Multi-Domain Variance Correlation** — Real clinical data has natural variance. A site with near-zero standard deviation in entry lag, completeness, AND correction rate simultaneously is statistically improbable. The agent correlates variance suppression across independent data domains — when multiple domains show simultaneously flat metrics, the probability of manufacturing rises exponentially. One domain with low variance could be genuine excellence; four domains simultaneously is a red flag.

2. **Manufactured Perfection Detection** — The agent distinguishes genuine operational excellence from phantom compliance using a specific criterion: genuine excellence shows natural variance around a strong central tendency (tight distribution, not zero variance); phantom compliance shows _suppressed_ variance (near-zero standard deviation, artificial uniformity). The difference is subtle but statistically detectable.

3. **CRA Rubber-Stamping Detection** — A CRA who never finds issues at any site is not doing thorough reviews. The agent uses `cra_portfolio_analysis` to examine findings-per-visit across all sites a CRA covers. A CRA with consistently zero findings across 5+ sites is rubber-stamping — either through insufficient review, collusion, or time pressure. This is a _cross-site_ signal that no single-site dashboard can detect.

4. **Narrative Duplication Detection** — Identical or near-identical screening failure narratives across multiple subjects suggest templated responses rather than genuine clinical assessment. The agent detects copy-paste patterns that indicate inadequate documentation or fabricated screening records.

---

## 2. Investigation Methodology

### 2.1 Reasoning Philosophy

The agent applies **statistical impossibility reasoning** — if observed data patterns are statistically improbable given the volume and complexity of clinical operations at a site, the data may not be genuine. The agent calculates how many standard deviations a site's variance is _below_ the study median and flags sites in the extreme lower tail.

**Severity scale:** `critical` / `high` / `medium` / `low`. Each hypothesis includes an `integrity_risk_level` and `domains_affected` (entry_lag, completeness, query_lifecycle, monitoring, randomization).

Six canonical reasoning principles:

- Near-zero variance is the primary signal — real data has natural noise
- Cross-domain consistency of perfection is exponentially improbable — one domain perfect = possible; four domains simultaneously perfect = suspicious
- Monitoring findings should NOT be zero — real SDV visits find issues at every site
- Query lifecycle uniformity (near-identical age_days, near-zero stddev) = artificially managed query queue
- Randomization timing CV < 0.1 = unnaturally regular inter-subject intervals
- Always compare against the population — the signal is not the absolute value but the deviation from study-wide distribution

### 2.2 Perception Strategy

Iteration 1 casts a wide statistical net:

| Tool | Purpose |
|------|---------|
| `data_variance_analysis` | Core variance signals: stddev of entry_lag, completeness, correction_rate |
| `site_summary` | Site metadata for context |
| `query_burden` | Query profile for lifecycle uniformity detection |
| `monitoring_visit_history` | Monitoring findings for zero-finding pattern |
| `cra_oversight_gap` | CRA coverage gaps and monitoring gaps |
| `cra_portfolio_analysis` | Cross-site CRA rubber-stamping detection |
| `cross_domain_consistency` | Validates cross-domain consistency (100% completeness + 0 queries + 0 corrections + 0 findings = too perfect) |

### 2.3 Multi-Iteration Deepening

**Iteration 1:** Statistical screening across all sites. Identify sites with variance suppression in 2+ domains. Flag CRAs with zero-finding portfolios. Calculate study-wide variance baselines for comparison.

**Iteration 2:** Deep-dive into flagged sites with specialized tools:
- `timestamp_clustering` — CV analysis of entry lag and inter-randomization intervals
- `weekday_entry_pattern` — batch entry detection (>40% on single weekday)
- `entry_date_clustering` — batch backfill detection (>30% entries on <5% calendar days)
- `screening_narrative_duplication` — copy-paste narrative detection
- Compare suspect sites against 2-3 "normal" sites as statistical controls

**Iteration 3:** Cross-reference CRA signals. If a suspect site's CRA shows rubber-stamping patterns at _other_ sites, the CRA-level pattern strengthens the site-level finding. Produce final integrity risk assessment.

---

## 3. Key Signals & Detection Logic

| Signal | Detection Method | Why It Matters | Naive Misinterpretation |
|--------|-----------------|----------------|------------------------|
| Near-zero entry lag stddev | `data_variance_analysis` stddev < study_median × 0.2 | Artificially uniform data entry timing | "Consistent site" — real sites have natural day-to-day variation |
| Cross-domain simultaneous perfection | `cross_domain_consistency` all domains green + near-zero variance | Statistically improbable across independent dimensions | "Best performing site" — manufactured perfection |
| Zero monitoring findings (consistent) | `monitoring_findings_variance` zero_finding_pct > 80% | CRA not conducting thorough SDV | "No issues found = excellent site" — no one is actually looking |
| Query lifecycle uniformity | `query_lifecycle_anomaly` age stddev near zero | Queries managed to artificial timeline | "Efficient query resolution" — artificial management |
| Randomization timing CV < 0.1 | `timestamp_clustering` inter-randomization CV | Unnaturally regular enrollment intervals | "Steady enrollment" — real enrollment has natural variation |
| >40% entries on single weekday | `weekday_entry_pattern` max_day_pct > 0.4 | Batch catchup entry, not real-time | "Busy day at site" — batch data entry pattern |
| >30% entries on <5% calendar days | `entry_date_clustering` concentration ratio | Batch backfill of accumulated data | "Efficient data entry sprint" — backfilling neglected entries |
| >50% identical screening narratives | `screening_narrative_duplication` duplication_pct > 0.5 | Templated rather than genuine clinical assessment | "Standardized documentation" — copy-paste fabrication |
| CRA zero findings across 5+ sites | `cra_portfolio_analysis` zero_finding_pct > 80% across portfolio | Rubber-stamping oversight | "Thorough CRA with clean sites" — not actually reviewing |
| High unprompted correction rate | `correction_provenance` unprompted_rate > 40% | Pre-monitoring cleanup of fabricated data | "Proactive quality" — suspicious pre-emptive corrections |

---

## 4. Tools

| Tool | Purpose | Key Arguments |
|------|---------|---------------|
| `data_variance_analysis` | Per-site stddev of entry lag, completeness, correction rate | `site_id` |
| `timestamp_clustering` | CV of entry lag and inter-randomization intervals | `site_id` |
| `query_lifecycle_anomaly` | Query age mean/stddev, monitoring-triggered % | `site_id` |
| `monitoring_findings_variance` | Findings mean/stddev, zero-finding %, overdue variance | `site_id` |
| `weekday_entry_pattern` | Weekday distribution of data entries | `site_id` |
| `cra_oversight_gap` | CRA coverage gaps, monitoring gaps | `site_id` |
| `cra_portfolio_analysis` | Cross-site CRA findings per visit | `cra_id` |
| `correction_provenance` | Query-triggered vs unprompted correction sources | `site_id` |
| `entry_date_clustering` | Batch backfill detection via calendar concentration | `site_id` |
| `screening_narrative_duplication` | Copy-paste narrative detection | `site_id` |
| `cross_domain_consistency` | Multi-domain consistency validation | `site_id` |
| `context_search` | Semantic search of prior agent findings for cross-investigation context | _(query text)_ |

All registered tools (39+) are available to the LLM during Plan/Act phases. The table above lists the most commonly selected tools for this agent's domain.

---

## 5. Cross-Domain Interactions

Every agent output includes metadata consumed by the Conductor: `investigation_complete` (bool), `remaining_gaps` (list), and `confidence` (0-1). The Conductor caps cross-domain confidence at 0.7 for any finding that relies primarily on an agent whose `investigation_complete` is `false`.

### 5.1 Signals Produced (for other agents)

- **Integrity risk level** (genuine/suspicious/critical_risk) → consumed by the Conductor to qualify all other agents' findings for flagged sites
- **CRA rubber-stamping evidence** → consumed by [vendor_performance.md](vendor_performance.md) to attribute oversight failures to specific CROs
- **Data trustworthiness verdict** → consumed by [data_quality.md](data_quality.md) to distinguish real quality from manufactured quality
- **Batch backfill detection** → consumed by [data_quality.md](data_quality.md) as context for entry lag patterns

### 5.2 Signals Consumed (from other agents)

- **Entry lag patterns** from [data_quality.md](data_quality.md) — provides baseline for distinguishing genuine quality from suppressed variance
- **Monitoring visit history** from [data_quality.md](data_quality.md) — monitoring gaps provide context for whether zero findings are due to infrequent visits vs rubber-stamping
- **CRA assignment history** from [data_quality.md](data_quality.md) — CRA tenure and transition context

### 5.3 Conductor Synthesis Patterns

- **Data Quality + Data Integrity:** The most critical synthesis. The Conductor MUST determine whether a site's excellent data quality metrics are genuine or manufactured. When phantom_compliance is invoked, the Conductor MUST produce an `integrity_assessment` verdict object with fields:
  - `verdict`: `genuine` | `suspicious` | `critical_risk`
  - `site_id`, `site_name`: the assessed site
  - `domains_with_suppressed_variance`: list of affected domains (entry_lag, completeness, query_lifecycle, monitoring, randomization)
  - `rationale`: evidence summary supporting the verdict
  - `recommended_actions`: triggered SDV, for-cause audit, CRA reassignment, etc.
- **Data Integrity + Vendor Performance:** If CRA rubber-stamping is detected, the Conductor attributes oversight failure to the responsible CRO.

---

## 6. Failure Modes & Anti-Patterns

**MUST NOT rules:**
- MUST NOT conclude fraud from a single domain's low variance — require 2+ independent domains
- MUST NOT flag small-volume sites (< 10 subjects) for variance suppression — insufficient data for statistical conclusions
- MUST NOT treat zero monitoring findings as automatically suspicious without checking visit frequency and SDV scope
- MUST NOT conflate batch entry (weekday pattern) with fabrication — batch entry may indicate resource constraints, not dishonesty
- MUST NOT present integrity risk findings without explicit evidence quality and alternative explanations

**Known failure modes:**
- **False positive on small sites:** Sites with few subjects naturally have less variance — the agent must normalize for subject volume
- **CRA portfolio misattribution:** A CRA covering high-performing sites may genuinely find fewer issues — must compare CRA's findings rate against other CRAs at the _same_ sites if overlap exists
- **Cultural batch entry:** Some regions have legitimate batch entry patterns (weekly data entry sessions rather than real-time) — must distinguish cultural practice from backfill fraud
- **Legitimate uniformity:** Highly protocolized sites (e.g., phase I units) may have genuinely low variance due to standardized procedures — context matters

---

## 7. Investigation Scenarios

### Scenario A — Multi-Domain Variance Suppression (2 iterations)

**Query:** "Proactive scan — identify data integrity risks"

**Iteration 1:**
- **Perceive:** All-site variance analysis. Site 1027 flagged: entry_lag stddev = 0.3 (study median 2.8), completeness stddev = 0.01 (study median 0.05), correction_rate = 0.01. Zero open queries. Monitoring: 4 visits, 0 findings each. Cross-domain consistency: all domains "perfect."
- **Reason:** H1: Manufactured perfection — 4 independent domains with simultaneously suppressed variance is statistically improbable for a site with 28 subjects. Calculate: probability of this pattern occurring naturally < 0.1%.
- **Plan:** `timestamp_clustering(site_id=1027)`, `weekday_entry_pattern(site_id=1027)`, `entry_date_clustering(site_id=1027)`, `cra_portfolio_analysis(cra_id=<site_1027_cra>)`, plus 2 "normal" sites for comparison
- **Act:** CV of inter-randomization intervals = 0.08 (below 0.1 threshold). 62% of entries on Tuesdays. CRA has zero findings across 3 other sites as well.

**Iteration 2:**
- **Reason:** All signals converge — variance suppression, batch Tuesday entry, unnaturally regular randomization, CRA rubber-stamping across portfolio. Multiple independent lines of evidence.
- **Plan:** `screening_narrative_duplication(site_id=1027)`, `correction_provenance(site_id=1027)`
- **Act:** 65% identical screening narratives. Correction provenance: 80% unprompted (pre-monitoring cleanup pattern).
- **Reflect:** Integrity risk = CRITICAL. Domains with suppressed variance: entry_lag, completeness, query_lifecycle, monitoring, randomization (5 of 5). CRA rubber-stamping confirmed across portfolio. Recommended: triggered SDV, for-cause audit referral.

### Scenario B — CRA Rubber-Stamping Discovery (2 iterations)

**Query:** "Investigate monitoring effectiveness across the study"

**Iteration 1:**
- **Perceive:** CRA portfolio analysis reveals CRA-007 has 0 findings across 4 sites over 12 visits. Study average is 2.3 findings per visit. All other CRAs find issues.
- **Reason:** H1: CRA-007 rubber-stamping — zero findings across multiple sites with adequate subject volume is not credible. H2: CRA-007 covers genuinely excellent sites (unlikely across 4 independent sites).
- **Plan:** `monitoring_findings_variance` for each of CRA-007's sites. `data_variance_analysis` for those same sites. Compare against sites covered by other CRAs in same region.
- **Act:** CRA-007's sites show lower data quality variance than sites covered by other CRAs. Two of CRA-007's sites have entry_date_clustering patterns.

**Iteration 2:**
- **Reason:** CRA rubber-stamping confirmed. Sites under CRA-007's oversight may have undetected quality issues. The lack of findings IS the finding.
- **Plan:** Deep-dive variance analysis on CRA-007's two suspect sites
- **Act:** Both sites show multi-domain variance suppression consistent with batch entry and minimal oversight
- **Reflect:** CRA-007 rubber-stamping confirmed. Recommend: CRA reassignment, triggered SDV at all 4 sites, for-cause audit for 2 suspect sites. Flag to [vendor_performance.md](vendor_performance.md) for CRO attribution.

---

## 8. Proactive Scan Directives

Proactive scans execute after each data ingestion cycle via the Directive Catalog (`/prompt/directives/`). Each focus area below maps to a parameterized directive `.txt` file registered in `catalog.json`. Reactive user queries take priority over proactive scans; scans are interruptible and resumable.

**Default directive focus areas:**
- Sites with entry_lag stddev in lowest 10th percentile of study distribution
- Sites with zero monitoring findings across 3+ consecutive visits
- CRAs with zero-finding visit rate > 80% across their portfolio
- Sites with cross-domain consistency score indicating "too perfect" across 3+ domains
- Sites with weekday entry concentration > 40% on single day

**Scan triggers:**
- New monitoring visit with zero findings at a site already flagged for low variance
- CRA assignment change where the departing CRA had zero-finding history
- Any site achieving 100% completeness with 0 corrections and 0 open queries
- Entry date clustering detected (batch backfill pattern)
