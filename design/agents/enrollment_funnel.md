# Enrollment Funnel Agent — Design Document

**Agent ID:** `enrollment_funnel` | **Finding Type:** `enrollment_funnel_analysis` | **Version:** 1.0

---

## 1. Purpose & Differentiating Intelligence

The Enrollment Funnel Agent decomposes enrollment problems into their **precise funnel stage** — volume, conversion, retention, or randomization — because the correct intervention depends entirely on which stage is broken. A dashboard shows enrollment is behind target; this agent explains _which part_ of the funnel is failing and _why_.

**Signature capabilities:**

1. **Funnel Stage Decomposition** — Every enrollment problem has a binding constraint at one specific stage. Low enrollment could mean: (a) insufficient referrals (volume), (b) high screen failures (conversion), (c) consent withdrawals (retention), or (d) randomization delays (IRT/supply). Each requires a fundamentally different intervention. The agent classifies each site's binding constraint and prevents misdiagnosis.

2. **Supply-Chain-Masked Withdrawals** — When subjects consent but then withdraw before randomization, the naive interpretation is "patient changed their mind." The agent cross-references withdrawal timing against kit inventory stockouts and IRT delays. Consent withdrawals that cluster during stockout periods reveal an operational failure masquerading as a patient decision.

3. **Competing Trial Cannibalization Signal** — When screening volume declines but screen failure rate _improves_, the standard interpretation is contradictory. The agent recognizes this as a competing trial signal: a new trial in the area is capturing the marginal (borderline-eligible) patients, leaving only clearly-eligible patients who pass screening more easily. Volume drops, conversion rises — external competitive force, not site underperformance.

---

## 2. Investigation Methodology

### 2.1 Reasoning Philosophy

The agent applies **binding constraint analysis** — for each site, identify the single funnel stage that, if improved, would have the largest impact on enrollment. This prevents scattershot interventions across multiple stages when only one is the bottleneck.

**Entity focus rule:** When the query names a specific site, the first hypothesis (H1) MUST be about that entity. The agent uses the site directory for name-to-ID resolution. Each hypothesis includes a `funnel_stage` field (volume/conversion/retention/randomization).

**Severity scale:** `critical` / `high` / `medium` / `low`

Six canonical reasoning chains:

- Declining volume + improving failure rate → competing trial capturing marginal patients
- Consent withdrawal clusters during specific time windows → check kit inventory for stockouts
- High screen failure + excellent data quality → overly strict PI (detected by [data_quality.md](data_quality.md); this agent provides the enrollment-side evidence — high failure rate — that the data quality agent correlates with quality metrics)
- Volume decline should decompose into: referral pipeline vs seasonal vs competitive
- Geographically proximate sites with simultaneous changes → shared regional cause
- Free-text failure narratives contain nuance that coded failure reasons miss

### 2.2 Perception Strategy

Iteration 1 captures the full funnel across all sites:

| Tool | Purpose |
|------|---------|
| `screening_funnel` | Per-site funnel: screened/passed/failed/withdrawn/failure_rate |
| `enrollment_velocity` | Weekly velocity trends and cumulative vs target |
| `screen_failure_pattern` (with narratives) | Failure reason codes and free-text narratives |
| `regional_comparison` | Cross-site metrics within same country |
| `site_summary` | Site metadata and target enrollment |
| `kit_inventory` | Supply constraint signals |

Narratives are always requested (`include_narratives=True`) because coded failure reasons (SF_ECOG, SF_SMOKING) lose the clinical nuance that determines whether a cause is fixable.

### 2.3 Multi-Iteration Deepening

**Iteration 1:** Full funnel decomposition across all sites. Classify each site's binding constraint stage. Generate hypotheses about root causes per stage.

**Iteration 2:** Drill into specific sites. If competing trial suspected, flag for [clinical_trials_gov.md](clinical_trials_gov.md). If supply-masked withdrawals suspected, cross-reference `kit_inventory` temporal data with consent withdrawal dates. If strict PI suspected, examine failure code distribution vs study average.

**Iteration 3:** Resolve ambiguous cases where multiple funnel stages contribute. Quantify the relative contribution of each stage. Generate cross-domain followups for the Conductor.

---

## 3. Key Signals & Detection Logic

| Signal | Detection Method | Why It Matters | Naive Misinterpretation |
|--------|-----------------|----------------|------------------------|
| Volume decline + failure rate improvement | `enrollment_velocity` weekly rate declining + `screening_funnel` failure_rate decreasing | Competing trial capturing marginal patients | "Site improving quality" — actually losing volume to competitor |
| Consent withdrawal cluster | `screening_funnel` withdrawn count + `kit_inventory` stockout dates | Operational failure (supply chain) masquerading as patient decision | "Patients changed their minds" — actually couldn't randomize due to stockout |
| High failure rate with specific codes | `screen_failure_pattern` code distribution vs study average | Fixable (PI interpretation) vs structural (population mismatch) | "Site has strict criteria" — may be fixable with PI education |
| Velocity slope negative 3+ weeks | `enrollment_velocity` weekly trend slope | Structural deceleration vs temporary dip | "Bad month" — may be permanent decline |
| Regional enrollment divergence | `regional_comparison` same country, different performance | Site-specific vs regional cause | "Region is slow" — may be one site dragging averages |
| Identical failure narratives | `screen_failure_pattern` narratives with duplication | Templated narratives = inadequate screening documentation | "Consistent documentation" — actually copy-paste |

---

## 4. Tools

| Tool | Purpose | Key Arguments |
|------|---------|---------------|
| `screening_funnel` | Per-site funnel decomposition | `site_id`, `period_start`, `period_end` |
| `enrollment_velocity` | Weekly velocity trends, cumulative vs target | `site_id`, `last_n_weeks` |
| `screen_failure_pattern` | Failure reason codes and narratives | `site_id`, `include_narratives`, `period_start`, `period_end` |
| `regional_comparison` | Cross-site enrollment/screening metrics | `country`, `site_ids`, `period_start`, `period_end` |
| `kit_inventory` | Kit inventory snapshots and reorder flags | `site_id` |
| `kri_snapshot` | KRI values and threshold status | `site_id`, `kri_name` |
| `site_summary` | Site metadata, target enrollment | `site_id`, `country` |
| `supply_constraint_impact` | Stockout episodes, randomization delays, withdrawals | `site_id` |
| `trend_projection` | Linear regression time-series projection for velocity forecasting | _(varies)_ |
| `context_search` | Semantic search of prior agent findings for cross-investigation context | _(query text)_ |

All registered tools (39+) are available to the LLM during Plan/Act phases. The table above lists the most commonly selected tools for this agent's domain.

---

## 5. Cross-Domain Interactions

Every agent output includes metadata consumed by the Conductor: `investigation_complete` (bool), `remaining_gaps` (list), and `confidence` (0-1). The Conductor caps cross-domain confidence at 0.7 for any finding that relies primarily on an agent whose `investigation_complete` is `false`.

### 5.1 Signals Produced (for other agents)

- **Binding constraint classification** (volume/conversion/retention/randomization) → consumed by [site_rescue.md](site_rescue.md) for rescue/close decision framework
- **Competing trial signal** → triggers [clinical_trials_gov.md](clinical_trials_gov.md) for external validation
- **Supply-masked withdrawal evidence** → consumed by [vendor_performance.md](vendor_performance.md) to attribute supply chain failures to specific vendors
- **Enrollment gap duration** → consumed by [financial_intelligence.md](financial_intelligence.md) to calculate delay-to-dollar cost

### 5.2 Signals Consumed (from other agents)

- **CRA transition timeline** from [data_quality.md](data_quality.md) — CRA changes can simultaneously disrupt data quality and enrollment
- **Competing trial search results** from [clinical_trials_gov.md](clinical_trials_gov.md) — external evidence for the cannibalization hypothesis
- **Vendor milestone delays** from [vendor_performance.md](vendor_performance.md) — vendor-caused delays in site activation or supply chain

### 5.3 Conductor Synthesis Patterns

- **Enrollment Funnel + Competitive Intelligence:** Internal vs external causes of enrollment decline — the Conductor determines whether decline is site-attributable or market-driven
- **Enrollment Funnel + Site Decision:** Enrollment trajectory and binding constraint feed directly into rescue/close recommendation
- **Financial Intelligence + Enrollment Funnel:** Dollar cost of enrollment delays, cost-per-patient efficiency linked to enrollment pace
- **Data Quality + Enrollment Funnel:** Shared root causes (CRA transitions, monitoring gaps affect both)

---

## 6. Failure Modes & Anti-Patterns

**MUST NOT rules:**
- MUST NOT report "enrollment behind target" without identifying the binding constraint stage
- MUST NOT attribute consent withdrawals to patient preference without checking supply chain timing
- MUST NOT treat improving screen failure rate as positive without checking if volume is simultaneously declining
- MUST NOT use aggregate funnel metrics when site-level decomposition is available

**Known failure modes:**
- **Stage misclassification:** Treating a retention problem (consent withdrawals) as a volume problem (insufficient referrals) leads to wrong intervention — referral outreach vs supply chain fix
- **Narrative neglect:** Ignoring free-text failure narratives when coded reasons are available — the nuance in narratives (e.g., "patient borderline on ECOG but PI chose to exclude") reveals fixability
- **Temporal blindness:** Comparing current month to overall average rather than examining the week-by-week trajectory for inflection points
- **Denominator confusion:** A site with 2 screenings and 1 failure has a 50% failure rate — statistically meaningless at low volumes

---

## 7. Investigation Scenarios

### Scenario A — Supply-Masked Withdrawals (1-2 iterations)

**Query:** "Why are consent withdrawal rates high at Site 1035?"

**Iteration 1:**
- **Perceive:** Site 1035 funnel — 45 screened, 30 passed, 8 withdrawn, 22 randomized. Withdrawal rate 27% vs study average 8%. Kit inventory shows 2 stockout episodes in last 3 months.
- **Reason:** H1: Supply-masked withdrawals — withdrawals clustered during stockouts. H2: Site-specific patient population concerns.
- **Plan:** `supply_constraint_impact(site_id=1035)`, `screen_failure_pattern(site_id=1035, include_narratives=True)`
- **Act:** 6 of 8 withdrawals occurred within 2 weeks of stockout episodes. Failure narratives show no unusual patient concerns.
- **Reflect:** Supply-chain-masked withdrawals confirmed. Root cause is kit supply, not patient decisions. Flag to [vendor_performance.md](vendor_performance.md) for vendor attribution. Goal satisfied.

### Scenario B — Competing Trial Detection (2-3 iterations)

**Query:** "Proactive scan — identify enrollment risks across all sites"

**Iteration 1:**
- **Perceive:** Full funnel scan. Sites 1012, 1018, 1024 (all US Midwest) show declining weekly volume over 4 weeks. Screen failure rates at these sites have improved from 35% to 22%.
- **Reason:** H1: Competing trial — volume decline + failure rate improvement = classic cannibalization signal. H2: Seasonal dip. Geographic clustering supports H1.
- **Plan:** `enrollment_velocity(site_id=1012)`, `enrollment_velocity(site_id=1018)`, `enrollment_velocity(site_id=1024)` — check for sharp vs gradual onset
- **Act:** All three sites show sharp volume drop starting week 12. Not gradual — suggests discrete event, not seasonal.

**Iteration 2:**
- **Reason (with prior results):** Sharp onset + geographic clustering + failure rate inversion = strong competing trial signal. Flag for [clinical_trials_gov.md](clinical_trials_gov.md) geo-distance search.
- **Plan:** `regional_comparison(country="US", site_ids="1012,1018,1024")` — confirm divergence from other US sites
- **Act:** Other US sites (East Coast, West Coast) show stable enrollment. Only Midwest cluster affected.
- **Reflect:** Competing trial hypothesis strong. Cross-domain followup to clinical_trials_gov agent for external validation. Remaining gap: identify specific competing trial. Goal partially satisfied — internal evidence complete, external validation needed.

---

## 8. Proactive Scan Directives

Proactive scans execute after each data ingestion cycle via the Directive Catalog (`/prompt/directives/`). Each focus area below maps to a parameterized directive `.txt` file registered in `catalog.json`. Reactive user queries take priority over proactive scans; scans are interruptible and resumable.

**Default directive focus areas:**
- Sites with enrollment velocity slope negative for 3+ consecutive weeks
- Sites with screen failure rate > study average + 1 standard deviation
- Sites with consent withdrawal rate > 15%
- Geographic clusters with simultaneous enrollment changes
- Sites with kit inventory below reorder threshold

**Scan triggers:**
- Weekly enrollment velocity drops below 50% of target rate at any site
- Consent withdrawal cluster (3+ in one week) at any site
- Kit stockout detected at any site
- New screen failure reason code appearing that was not previously observed
