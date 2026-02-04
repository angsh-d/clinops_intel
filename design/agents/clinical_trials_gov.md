# Clinical Trials Gov Agent — Design Document

**Agent ID:** `clinical_trials_gov` | **Finding Type:** `competing_trial_analysis` | **Version:** 1.0

---

## 1. Purpose & Differentiating Intelligence

The Clinical Trials Gov Agent is the system's **external intelligence** capability — the only agent that reaches outside the trial's operational database to query ClinicalTrials.gov via BioMCP. It answers the question dashboards cannot: _is a competing trial stealing our patients?_

**Signature capabilities:**

1. **Geo-Distance Competitor Search** — Uses BioMCP's latitude/longitude-based search to find competing trials within a specified radius of sites showing enrollment decline. This is not keyword matching — it is spatial proximity analysis against the ClinicalTrials.gov registry, finding trials at the same facilities or nearby institutions.

2. **Temporal Alignment Analysis** — Finding a competing trial nearby is necessary but not sufficient. The agent performs temporal alignment: does the competing trial's recruitment start date correlate with the onset of enrollment decline at the affected site? A trial that started recruiting 2 weeks before enrollment dropped is a strong signal; a trial that has been recruiting for 2 years is noise.

3. **Evidence Quality Tiering** — Not all competing trials are equal threats. The agent classifies competitive evidence into tiers:
   - **STRONG:** Same facility + same condition + overlapping recruitment timeline
   - **MODERATE:** Same city + same condition + active recruitment
   - **WEAK:** Same region only, or different condition/phase

---

## 2. Investigation Methodology

### 2.1 Reasoning Philosophy

The agent applies **external attribution reasoning** — when internal operational data cannot explain enrollment decline, the cause may be external market forces. The key insight is that competing trials affect _volume_ (fewer patients arriving) while leaving _conversion_ unchanged or improved (remaining patients are more clearly eligible). This volume-conversion divergence pattern is the primary trigger for competitive intelligence investigation.

**Severity scale:** `critical` / `high` / `medium` / `low`. Reflect phase output includes `competing_trials_found` count and `strongest_competitor` with evidence quality tier.

Four canonical reasoning chains:

- Declining volume + improving failure rate = strong competing trial signal (marginal patients captured by competitor)
- Sudden onset (not gradual) = discrete event like a competing trial opening, not seasonal drift
- Geographic clustering of decline = regional competitive force affecting multiple sites
- Direct competitors (same condition/phase) vs indirect competitors (same patient population, different indication)

### 2.2 Perception Strategy

The perception phase is deliberately narrow — focused on identifying _which sites_ to investigate and gathering the geographic/temporal context needed for external search:

| Tool | Purpose |
|------|---------|
| `site_summary` | Site locations (city, country, coordinates) for geo-distance search |
| `enrollment_velocity` | Weekly enrollment timelines to identify decline onset week |

The agent does NOT perceive data quality, monitoring, or financial signals — those belong to other agents. It focuses exclusively on enrollment trajectory and geography.

### 2.3 Multi-Iteration Deepening

**Iteration 1:** Identify sites with enrollment decline. Extract geographic coordinates and decline onset dates. Execute `competing_trial_search` with geo-distance parameters for each target site.

**Iteration 2:** For promising matches, use `trial_detail` to fetch full protocol information — eligibility criteria overlap, sponsor, enrollment targets, facility lists. Refine evidence quality assessment based on detailed protocol comparison.

**Iteration 3:** If initial searches returned no results, broaden search parameters (larger radius, state-level terms, condition synonyms). If no competing trials found after broadening, that IS a finding — suggests internal operational causes, not external competition.

---

## 3. Key Signals & Detection Logic

| Signal | Detection Method | Why It Matters | Naive Misinterpretation |
|--------|-----------------|----------------|------------------------|
| Competing trial at same facility | `competing_trial_search` with geo-distance, cross-ref facility list | Direct patient competition — same physicians, same patients | "We need more referrals" — competitor is intercepting existing referrals |
| Trial start date aligns with decline onset | `trial_detail` start date vs `enrollment_velocity` decline onset week | Temporal causation evidence | "Coincidence" — within 4 weeks alignment is too specific to be random |
| Multiple competing trials in region | `competing_trial_search` returns several active studies | Market saturation — not a single competitor but competitive density | "One competitor is the problem" — market is saturated |
| No competing trials found | Empty search results after broadened search | Internal operational cause confirmed by exclusion | "No external issues" — this is actually the finding: problem is internal |
| Competing trial in different phase | `trial_detail` phase field | Patient population overlap may still exist despite phase difference | "Different phase, not a competitor" — Phase II and Phase III can share patient pools |
| Indirect competitor (different condition) | `competing_trial_search` with broader condition terms | Same patient population may be eligible for multiple conditions | "Different disease, not relevant" — immunotherapy trials share oncology populations |

---

## 4. Tools

| Tool | Purpose | Key Arguments |
|------|---------|---------------|
| `competing_trial_search` | BioMCP-powered ClinicalTrials.gov search with geo-distance | `condition`, `lat`, `lon`, `distance`, `location_terms`, `phase`, `status`, `intervention`, `page_size` |
| `trial_detail` | Detailed trial information by NCT ID | `nct_id`, `module` (protocol, locations, references, outcomes, all) |
| `site_summary` | Site location data for geo-distance search parameters | `site_id`, `country` |
| `enrollment_velocity` | Weekly enrollment timelines for decline onset identification | `site_id`, `last_n_weeks` |
| `context_search` | Semantic search of prior agent findings for cross-investigation context | _(query text)_ |

All registered tools (39+) are available to the LLM during Plan/Act phases. The table above lists the most commonly selected tools for this agent's domain.

---

## 5. Cross-Domain Interactions

Every agent output includes metadata consumed by the Conductor: `investigation_complete` (bool), `remaining_gaps` (list), and `confidence` (0-1). The Conductor caps cross-domain confidence at 0.7 for any finding that relies primarily on an agent whose `investigation_complete` is `false`.

### 5.1 Signals Produced (for other agents)

- **Competing trial evidence** (with evidence quality tier) → consumed by [enrollment_funnel.md](enrollment_funnel.md) to confirm/refute competing trial hypothesis
- **Competitive landscape assessment** → consumed by [site_rescue.md](site_rescue.md) as input to rescue/close decision (structural competition = close indicator)
- **Market saturation signal** → consumed by [financial_intelligence.md](financial_intelligence.md) to project enrollment timeline adjustments and budget impact

### 5.2 Signals Consumed (from other agents)

- **Enrollment decline onset dates** from [enrollment_funnel.md](enrollment_funnel.md) — the temporal anchor for alignment analysis
- **Volume-conversion divergence** from [enrollment_funnel.md](enrollment_funnel.md) — the trigger signal that justifies external search

### 5.3 Conductor Synthesis Patterns

- **Enrollment Funnel + Competitive Intelligence:** The Conductor determines whether enrollment decline is internally attributable (operational) or externally driven (market competition). If both agents investigated the same sites, the Conductor synthesizes internal evidence with external evidence for a unified causal narrative.
- **Site Decision + Competitive Intelligence:** Geographic competition is a _structural_ (unfixable) root cause that supports closure rather than rescue. The Conductor feeds competitive landscape evidence into the rescue/close decision framework.

---

## 6. Failure Modes & Anti-Patterns

**MUST NOT rules:**
- MUST NOT conclude "no competition" from a single narrow search — must broaden parameters (radius, condition terms) before declaring external factors excluded
- MUST NOT treat any nearby recruiting trial as a competitor without checking condition overlap and temporal alignment
- MUST NOT assume geo-distance alone proves competition — must verify same patient population (condition, eligibility overlap)
- MUST NOT ignore the "no competing trials found" finding — absence of external competition is valuable evidence for internal attribution

**Known failure modes:**
- **Search parameter too narrow:** Using exact condition text (e.g., "Non-Small Cell Lung Cancer Stage IIIB") instead of broader terms ("NSCLC" or "Lung Cancer") misses relevant competitors
- **Distance threshold too small:** 25 km radius in a major metro area may miss competitors across town; 100 km captures the realistic patient travel distance
- **Temporal mismatch:** Comparing competing trial _registration_ date instead of _recruitment start_ date — registration can precede recruitment by months
- **Phase tunnel vision:** Ignoring Phase I/II trials when investigating a Phase III study — early-phase trials at major academic centers can capture the same referral pipelines

---

## 7. Investigation Scenarios

### Scenario A — Single Site Competitor Identified (1-2 iterations)

**Query:** "Site 1018 enrollment has dropped 40% in the last month — is there a competing trial?"

**Iteration 1:**
- **Perceive:** Site 1018 is in Chicago, IL (41.88, -87.63). Enrollment velocity: 4/week → 2.5/week starting week 10. Decline onset: week 10.
- **Reason:** H1: Competing trial opened at or near Northwestern/University of Chicago. Decline is sharp (not gradual), consistent with discrete competitive event.
- **Plan:** `competing_trial_search(condition="NSCLC", lat=41.88, lon=-87.63, distance=50, status="RECRUITING", phase="PHASE3")`
- **Act:** Found NCT05123456 — Phase III NSCLC trial at Northwestern, recruitment started week 8 (2 weeks before decline onset).
- **Reflect:** STRONG evidence — same condition, same city, recruitment start aligns with decline onset within 2 weeks. Goal satisfied.

### Scenario B — Regional Competitive Saturation (2-3 iterations)

**Query:** (Triggered by enrollment_funnel agent) "Sites 1012, 1018, 1024 (US Midwest) all show simultaneous volume decline with improving screen failure rates."

**Iteration 1:**
- **Perceive:** Three sites in Chicago, Milwaukee, Minneapolis. All show sharp decline starting week 10-12. Failure rates improved from ~35% to ~22%.
- **Reason:** H1: Multiple competing trials opened in Midwest region. H2: Single large multi-center trial opened across Midwest.
- **Plan:** Three parallel `competing_trial_search` calls (one per city, 75km radius, NSCLC, Phase II-III, RECRUITING)
- **Act:** Chicago: 2 competing trials. Milwaukee: 1 competing trial. Minneapolis: 0 results.

**Iteration 2:**
- **Reason:** Chicago and Milwaukee competition confirmed. Minneapolis: no results — broaden search.
- **Plan:** `competing_trial_search(condition="Lung Cancer", lat=44.98, lon=-93.27, distance=100, status="RECRUITING")`, `trial_detail(nct_id=NCT05123456, module="locations")` — check if the Chicago trial has a Minneapolis site
- **Act:** The Chicago trial (NCT05123456) has an expansion site in Minneapolis opened week 11. No separate Minneapolis trial, but the same multi-center competitor reached all three cities.
- **Reflect:** Single multi-center competitor (NCT05123456) explains all three declines. Temporal alignment strong. Evidence quality: STRONG for Chicago/Milwaukee (direct geo-match), MODERATE for Minneapolis (100km expansion site). This is structural competition — relevant to [site_rescue.md](site_rescue.md) for closure consideration.

---

## 8. Proactive Scan Directives

Proactive scans execute after each data ingestion cycle via the Directive Catalog (`/prompt/directives/`). Each focus area below maps to a parameterized directive `.txt` file registered in `catalog.json`. Reactive user queries take priority over proactive scans; scans are interruptible and resumable. This agent is typically triggered by other agents' findings rather than raw data ingestion.

**Default directive focus areas:**
- Sites with enrollment velocity decline > 25% over 3+ weeks where internal causes (CRA transition, supply chain, monitoring gaps) have been excluded
- Geographic clusters of decline (3+ sites in same region showing simultaneous volume reduction)
- Sites where volume decline coincides with screen failure rate improvement (the classic cannibalization inversion)
- Sites in major academic medical centers (high likelihood of multiple competing trials at same institution)
- Sites in therapeutic areas with high competitive trial density (oncology, immunology)

**Scan triggers:**
- Enrollment funnel agent flags "competing trial" hypothesis for a site
- Conductor detects unexplained enrollment decline after data_quality and enrollment_funnel investigations complete
- New site activation in a region where competing trials were previously identified
- Quarterly proactive scan of all sites with enrollment below 50% of target rate
