# Site Rescue Agent — Design Document

**Agent ID:** `site_rescue` | **Finding Type:** `site_rescue_analysis` | **Version:** 1.0

---

## 1. Purpose & Differentiating Intelligence

The Site Rescue Agent produces a **rescue / close / watch recommendation** for underperforming sites based on root cause classification. The critical distinction other analyses miss: whether the root cause is _temporary_ (fixable with intervention) or _structural_ (unfixable regardless of investment). This classification determines whether resources spent on rescue will yield returns or be wasted.

**Signature capabilities:**

1. **Temporary vs Structural Root Cause Classification** — The agent classifies every identified root cause as temporary (amenable to intervention) or structural (inherent to site circumstances). CRA transition disruption is temporary; patient population mismatch is structural. Supply chain stockouts are temporary; geographic competitor saturation is structural. The classification drives fundamentally different recommendations.

2. **Rescue/Close/Watch Decision Framework** — A multi-factor scoring framework that synthesizes enrollment trajectory, screen failure root causes, CRA staffing stability, supply constraint history, and competitive landscape into a single recommendation. RESCUE when majority of causes are temporary AND historical velocity demonstrates capability. CLOSE when majority are structural AND resources yield better returns elsewhere. WATCH when evidence is mixed or insufficient.

3. **Projected Time-to-Complete** — Using enrollment velocity trends and gap-to-target analysis, the agent projects how long it would take each site to reach enrollment targets at current and improved rates. A site that needs 52 weeks at current pace but only 16 weeks if a temporary cause is resolved has a clear rescue case. A site that needs 52 weeks regardless has a clear close case.

---

## 2. Investigation Methodology

### 2.1 Reasoning Philosophy

The agent applies **root cause classification with decision tree reasoning**. Every observation is tagged as supporting rescue, close, or being inconclusive. The decision is not based on a single signal but on the _preponderance_ of classified evidence across five independent factors.

**Severity scale:** `critical` / `high` / `medium` / `low`. Each hypothesis includes a `root_cause_type` (temporary/structural/mixed) and `preliminary_recommendation` (rescue/close/watch).

**Root cause classification framework:**

| Temporary (Fixable) — Support RESCUE | Structural (Unfixable) — Support CLOSURE |
|---------------------------------------|------------------------------------------|
| CRA transition (learning curve disruption) | Patient population mismatch (demographics, prevalence) |
| Supply constraint (kit stockouts, depot delays) | Geographic competition (permanent patient pool cannibalization) |
| Seasonal volume dip | Regulatory/institutional barriers |
| PI engagement lapse | PI capability limitations |
| Referral pipeline disruption | Insufficient disease prevalence in catchment area |

### 2.2 Perception Strategy

Iteration 1 gathers the five decision factors:

| Tool | Decision Factor |
|------|----------------|
| `enrollment_trajectory` | Velocity, slope, gap to target, projected weeks to complete |
| `screening_funnel` | Funnel decomposition — where is the bottleneck? |
| `cra_assignment_history` | CRA stability — recent transitions indicate temporary cause |
| `kit_inventory` | Supply constraints — stockouts are temporary and fixable |
| `site_summary` | Site metadata, experience level, activation date |

### 2.3 Multi-Iteration Deepening

**Iteration 1:** Gather five decision factors for all underperforming sites. Generate initial root cause hypotheses with temporary/structural classification.

**Iteration 2:** Test classifications with targeted evidence:
- `screen_failure_root_cause` — failure code distribution reveals fixable (PI interpretation) vs structural (population) causes
- `supply_constraint_impact` — temporal cross-reference of stockouts, delays, and withdrawals
- `regional_comparison` — same region, different outcomes = site-specific issue; same region, same outcomes = regional cause

**Iteration 3:** If classification remains ambiguous, seek external evidence via `competing_trial_search` (structural competition) or deeper enrollment velocity analysis for recovery signals. Produce final recommendation with confidence level.

---

## 3. Key Signals & Detection Logic

| Signal | Detection Method | Why It Matters | Naive Misinterpretation |
|--------|-----------------|----------------|------------------------|
| Velocity slope recovering | `enrollment_trajectory` slope positive last 2 weeks | Temporary cause may be resolving — support WATCH/RESCUE | "Still behind target" — trajectory matters more than current gap |
| Screen failure codes: fixable dominant | `screen_failure_root_cause` SF_ECOG, SF_SMOKING > 50% of failures | PI interpretation issue — fixable with education | "High failure rate = bad site" — may be fixable PI calibration |
| Screen failure codes: structural dominant | `screen_failure_root_cause` SF_CONSENT, SF_GEOGRAPHIC > 50% | Population mismatch — not fixable | "Need more screening volume" — more screening won't help if population doesn't fit |
| CRA transition within 60 days | `cra_assignment_history` recent transition | Temporary disruption — will resolve with onboarding | "Site is declining" — CRA learning curve is temporary |
| Kit stockout episodes | `kit_inventory` below-reorder flags + `supply_constraint_impact` | Fixable supply chain issue — depot reallocation | "Low randomization" — operational fix available |
| Projected weeks > 52 at current velocity | `enrollment_trajectory` projected_weeks | Time-to-complete exceeds reasonable horizon | "Give it more time" — the math doesn't support waiting |
| Regional peers outperforming | `regional_comparison` same country, site underperforming peers | Site-specific issue, not regional | "Regional slow enrollment" — this site specifically underperforming |

---

## 4. Tools

| Tool | Purpose | Key Arguments |
|------|---------|---------------|
| `enrollment_trajectory` | 4-week velocity, slope, gap to target, projected weeks | `site_id` |
| `screen_failure_root_cause` | Failure code breakdown with fixable vs structural classification | `site_id` |
| `supply_constraint_impact` | Stockout episodes, randomization delays, consent withdrawals | `site_id` |
| `screening_funnel` | Funnel decomposition: screened/passed/failed/withdrawn | `site_id`, `period_start`, `period_end` |
| `enrollment_velocity` | Detailed weekly velocity trends | `site_id`, `last_n_weeks` |
| `cra_assignment_history` | CRA transitions and tenure | `site_id` |
| `kit_inventory` | Kit inventory and reorder status | `site_id` |
| `regional_comparison` | Cross-site performance within same country | `country`, `site_ids`, `period_start`, `period_end` |
| `site_summary` | Site metadata, target enrollment | `site_id`, `country` |
| `competing_trial_search` | External competition check (if internal causes insufficient) | `condition`, `lat`, `lon`, `distance` |
| `trend_projection` | Linear regression projection for velocity and gap-to-target forecasting | _(varies)_ |
| `context_search` | Semantic search of prior agent findings for cross-investigation context | _(query text)_ |

All registered tools (39+) are available to the LLM during Plan/Act phases. The table above lists the most commonly selected tools for this agent's domain.

---

## 5. Cross-Domain Interactions

Every agent output includes metadata consumed by the Conductor: `investigation_complete` (bool), `remaining_gaps` (list), and `confidence` (0-1). The Conductor caps cross-domain confidence at 0.7 for any finding that relies primarily on an agent whose `investigation_complete` is `false`.

### 5.1 Signals Produced (for other agents)

- **Rescue/close/watch recommendation** → consumed by the Conductor for the `site_decision` verdict object (REQUIRED when this agent is invoked)
- **Root cause classification** (temporary/structural) → consumed by [financial_intelligence.md](financial_intelligence.md) for budget reallocation modeling
- **Projected time-to-complete** → consumed by [financial_intelligence.md](financial_intelligence.md) for cost projection

### 5.2 Signals Consumed (from other agents)

- **Funnel stage binding constraint** from [enrollment_funnel.md](enrollment_funnel.md) — which stage is the bottleneck
- **Competing trial evidence** from [clinical_trials_gov.md](clinical_trials_gov.md) — structural competition supports closure
- **CRA transition impact** from [data_quality.md](data_quality.md) — data quality degradation due to CRA change is temporary
- **Vendor attribution** from [vendor_performance.md](vendor_performance.md) — vendor-caused issues may be resolvable through vendor management

### 5.3 Conductor Synthesis Patterns

- **Enrollment Funnel + Site Decision:** The Conductor combines enrollment trajectory analysis with the rescue/close recommendation. When site_rescue is invoked, the Conductor MUST produce a `site_decision` verdict object with fields:
  - `verdict`: `rescue` | `close` | `watch`
  - `site_id`, `site_name`: the assessed site
  - `rescue_indicators`: list of temporary/fixable root causes supporting rescue
  - `close_indicators`: list of structural/unfixable root causes supporting closure
  - `rationale`: evidence summary supporting the verdict
  - `recommended_actions`: specific interventions with owners
- **Site Decision + Competitive Intelligence:** Geographic competition from [clinical_trials_gov.md](clinical_trials_gov.md) is a structural close indicator. The Conductor weighs this against temporary rescue indicators.

---

## 6. Failure Modes & Anti-Patterns

**MUST NOT rules:**
- MUST NOT recommend closure based on a single factor — require evidence across multiple decision dimensions
- MUST NOT recommend rescue without a specific, actionable plan (what intervention, who owns it, expected timeline)
- MUST NOT ignore velocity _slope_ in favor of absolute velocity — a site at 50% target but accelerating may be rescuable; a site at 70% target but decelerating may not
- MUST NOT classify a root cause as temporary without evidence of a specific, reversible mechanism

**Known failure modes:**
- **Sunk cost fallacy:** Recommending rescue for a site with significant historical investment when structural causes clearly dominate — past spend does not justify future spend
- **Optimism bias:** Classifying ambiguous causes as temporary because rescue is the preferred outcome — must maintain objectivity
- **Single-factor override:** A single dramatic signal (e.g., zero enrollment last month) triggering closure without examining whether the cause is temporary (supply chain outage)
- **Ignoring opportunity cost:** Recommending WATCH indefinitely when the resources monitoring a struggling site could be redeployed to accelerate a high-performing site

---

## 7. Investigation Scenarios

### Scenario A — Clear Rescue Case (1-2 iterations)

**Query:** "Should we close Site 1035?"

_Context: The enrollment funnel agent previously identified supply-masked consent withdrawals at this site (withdrawal rate 27% vs study average 8%, clustered around kit stockout episodes). This investigation determines whether the site is rescuable._

**Iteration 1:**
- **Perceive:** Site 1035: velocity dropped from 3.5/week to 1.2/week over 4 weeks. Gap to target: 35 subjects. 45 screened, 30 passed, 8 withdrawn (27% withdrawal rate — flagged by enrollment funnel agent as supply-masked). CRA changed 5 weeks ago. Kit inventory: 2 stockout episodes. Screening funnel: failure rate normal (28% vs study 30%).
- **Reason:** H1: CRA transition + supply chain = dual temporary causes. Historical velocity (3.5/week) demonstrates capability. Projected weeks at current: 29. Projected at historical: 10.
- **Plan:** `screen_failure_root_cause(site_id=1035)`, `supply_constraint_impact(site_id=1035)`, `regional_comparison(country=<site_country>)`
- **Act:** Failure codes: 70% fixable (PI interpretation). Supply: 6 withdrawals during stockout windows. Regional peers performing at historical rate — confirms this is site-specific and temporary.
- **Reflect:** **RESCUE.** Rescue indicators: CRA transition (temporary, 4-8 week disruption), supply chain (fixable with depot reallocation), historical velocity demonstrates capability. Close indicators: none. Recommended actions: expedite CRA onboarding, resolve supply chain with depot, PI calibration call.

### Scenario B — Complex Close/Rescue Deliberation (2-3 iterations)

**Query:** "Evaluate sites below 40% of enrollment target for rescue or closure"

**Iteration 1:**
- **Perceive:** Sites 1008, 1022, 1041 all below 40% of target. Site 1008: velocity declining, no CRA transition, no supply issues. Site 1022: recent CRA change, velocity recovering. Site 1041: velocity near zero for 6 weeks.
- **Reason:** Site 1008: H1 structural (population?) H2 external competition. Site 1022: H1 temporary (CRA transition). Site 1041: H1 structural (zero velocity = fundamental issue).
- **Plan:** `screen_failure_root_cause` for all three, `enrollment_velocity` for recovery signals.
- **Act:** (Executed in iteration 2 below with results.)

**Iteration 2:**
- **Reason (with prior results):** Classify root causes from failure codes and velocity data.
- **Act:** Site 1008: 65% structural failure codes (population mismatch). Site 1022: velocity slope positive last 2 weeks. Site 1041: failure codes mixed, but zero screening volume — not failing screens, not getting referrals.

**Iteration 3:**
- **Reason (with prior results):** Site 1008: structural confirmed, check regional context. Site 1041: zero volume unexplained — external competition likely, need ClinicalTrials.gov search.
- **Plan:** `competing_trial_search` for Site 1041 location. `regional_comparison` for Site 1008.
- **Act:** Site 1041: competing trial at same facility, strong evidence. Site 1008: regional peers also underperforming but less severely.
- **Reflect:**
  - Site 1008: **CLOSE.** Structural population mismatch confirmed by failure codes + regional underperformance.
  - Site 1022: **RESCUE.** CRA transition (temporary) with demonstrated recovery.
  - Site 1041: **CLOSE.** Structural competition (same facility) with zero referral volume.

---

## 8. Proactive Scan Directives

Proactive scans execute after each data ingestion cycle via the Directive Catalog (`/prompt/directives/`). Each focus area below maps to a parameterized directive `.txt` file registered in `catalog.json`. Reactive user queries take priority over proactive scans; scans are interruptible and resumable.

**Default directive focus areas:**
- Sites below 50% of enrollment target
- Sites with velocity slope negative for 4+ consecutive weeks
- Sites with projected time-to-complete > 40 weeks
- Sites with recent CRA transitions (may need temporary support rather than closure)
- Sites with screen failure rate diverging > 2 standard deviations from study mean

**Scan triggers:**
- Any site reaches 0 enrollments for 3 consecutive weeks
- CRA transition at a site already below 60% of target
- Kit stockout at a site with declining velocity
- Competing trial detected near a site (from [clinical_trials_gov.md](clinical_trials_gov.md))
