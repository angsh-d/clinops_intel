# Data Dictionary — Clinical Operations Intelligence System

**Database:** `clinops_intel` (PostgreSQL)
**Protocol:** NCT02264990 / M14-359 — Veliparib in Non-Squamous NSCLC
**Study Timeline:** 2024-03-01 to 2025-09-30 (18 months, ~82 weeks)
**Total Rows:** ~119,800 across 24 tables

---

## Table of Contents

1. [Schema Overview](#1-schema-overview)
2. [Static / Configuration Tables](#2-static--configuration-tables)
3. [Enrollment Funnel Tables (Category D)](#3-enrollment-funnel-tables-category-d)
4. [EDC Telemetry Tables (Category A)](#4-edc-telemetry-tables-category-a)
5. [Monitoring Oversight Tables (Category B)](#5-monitoring-oversight-tables-category-b)
6. [IRT / Supply Tables (Category E)](#6-irt--supply-tables-category-e)
7. [Cross-Table Relationships](#7-cross-table-relationships)
8. [Embedded Anomaly Sites](#8-embedded-anomaly-sites)
9. [How the Data Supports Transformational Insights](#9-how-the-data-supports-transformational-insights)

---

## 1. Schema Overview

The database implements the **Common Operational Data Model (CODM)** described in the solution architecture. Tables are organized into five groups aligned with the data feed categories.

| Group | Tables | Approx Rows | Data Category | Primary Production Source Systems |
|-------|--------|-------------|---------------|----------------------------------|
| Static / Config | 11 | ~475 | Reference data derived from USDM 4.0 protocol | CTMS, EDC, IRT/IWRS, Protocol Management |
| Enrollment Funnel | 3 | ~10,800 | Category D — MVP | EDC, IRT/IWRS, CTMS |
| EDC Telemetry | 4 | ~65,100 | Category A — MVP | EDC (Rave, InForm, Vault CDMS) |
| Monitoring Oversight | 3 | ~23,000 | Category B — Phase 2 | CTMS, RBQM platforms |
| IRT / Supply | 3 | ~20,400 | Category E — Phase 2 | IRT/IWRS, Supply chain / logistics |

### Production Source System Reference

The following vendor platforms are the most common sources for each data category in industry practice. The CODM source adapters normalize data from any of these platforms into the unified schema.

| System Category | Representative Platforms | Data Delivered |
|----------------|------------------------|----------------|
| **EDC** (Electronic Data Capture) | Medidata Rave, Oracle InForm / Clinical One, Veeva Vault CDMS, Castor EDC | eCRF entries, queries, corrections, visit data, screening CRFs |
| **CTMS** (Clinical Trial Management System) | Veeva Vault CTMS, Oracle Siebel CTMS, Medidata Rave CTMS, Bio-Optronics Clinical Conductor | Site management, CRA assignments, monitoring visits, enrollment tracking, action items |
| **IRT / IWRS** (Interactive Response Technology) | Suvoda, Signant Health (RTSM), Medidata Rave RTSM, Oracle InForm IRT | Randomization, stratification, kit inventory, depot shipments, supply events |
| **RBQM** (Risk-Based Quality Management) | CluePoints, Veeva Vault QualityOne, TransCelerate RBQM tools | KRI computation, centralized statistical monitoring, risk signals |
| **Protocol Management** | Veeva Vault Clinical (PromoMats/eTMF), Study Builder tools, Sponsor protocol authoring systems | Study design, eligibility criteria, visit schedule, activities |
| **Supply Chain / Logistics** | Almac Group, Catalent, Fisher Clinical Services, Marken | Depot operations, shipment tracking, cold-chain compliance |

---

## 2. Static / Configuration Tables

These tables are populated once from the USDM 4.0 protocol JSONs and site configuration. They provide the reference backbone that all transactional tables join against.

### Digital Protocol as Primary Data Source

The static/configuration tables are **driven by the USDM 4.0 Digital Protocol** — three structured JSON files that encode the study design in machine-readable form. This is a deliberate architectural choice: rather than manually configuring study parameters, the system reads them directly from the digital protocol, ensuring consistency between the protocol document and the operational data model.

| Protocol JSON | USDM 4.0 Structures Parsed | Tables Populated | Key Fields Extracted |
|---------------|----------------------------|-----------------|---------------------|
| `NCT02264990_M14-359_usdm_4.0_*.json` | `study`, `studyDesignInfo`, `studyArms`, `studyStratificationFactors`, `studyIdentifiers`, `studyPhase` | `study_config`, `study_arms`, `stratification_factors` | study_id, NCT number, phase, target enrollment (595), planned sites (150), countries (5), cycle length (21d), max cycles (6), screening window (28d), arm definitions, stratification factors |
| `NCT02264990_M14-359_soa_usdm_draft_*.json` | `visits` (10 encounters), `activities` (25), `scheduledActivityInstances` (80) | `visit_schedule`, `visit_activities` | Visit IDs/names/types/timing/windows, activity-to-visit mappings, required/optional flags |
| `NCT02264990_M14-359_eligibility_criteria_*.json` | `criteria` (25 items: 13 inclusion + 12 exclusion) | `eligibility_criteria`, `screen_failure_reason_codes` (mapped) | Criterion IDs, inclusion/exclusion type, full criterion text |

**Protocol-derived parameters that drive transactional data generation:**

- **`target_enrollment = 595`** — caps the enrollment S-curve; determines when screening wind-down begins
- **`cycle_length_days = 21`** — computes every subject visit `planned_date` across all 595 subjects
- **`max_cycles = 6`** — determines treatment duration and early discontinuation modeling
- **`screening_window_days = 28`** — governs screening-to-randomization timing
- **`countries = [USA, JPN, CAN, AUS, NZL]`** — drives site country distribution across 5 activation waves
- **Eligibility criteria IDs** — mapped to screen failure reason codes (e.g., `SF_ECOG` → `INC_6`, `SF_HISTO` → `EXC_1`), ensuring failure reasons trace back to specific protocol criteria

In a production deployment, this same pattern applies: the system would ingest the sponsor's digital protocol (USDM 4.0 export, TransCelerate Digital Protocol, or equivalent structured protocol representation) to automatically configure study parameters, visit schedules, and eligibility criteria — eliminating manual configuration and ensuring the operational intelligence layer always reflects the current protocol version.

### 2.1 `study_config`

Global study parameters. Single row.

> **Production sources:** CTMS study setup module (Veeva Vault CTMS, Oracle Siebel CTMS) for operational parameters; Protocol Management system (Veeva Vault Clinical, Study Builder) for design parameters; ClinicalTrials.gov API for NCT number. Typically configured once at study startup and updated only for protocol amendments.
> **Refresh cadence:** Static — loaded at study setup, updated on protocol amendment.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `study_id` | String(50) | Protocol identifier. Value: `M14-359` |
| `nct_number` | String(20) | ClinicalTrials.gov identifier. Value: `NCT02264990` |
| `phase` | String(20) | Trial phase. Value: `Phase 2` |
| `target_enrollment` | Integer | Protocol enrollment target. Value: `595` |
| `planned_sites` | Integer | Number of planned investigator sites. Value: `150` |
| `cycle_length_days` | Integer | Treatment cycle duration. Value: `21` |
| `max_cycles` | Integer | Maximum treatment cycles per subject. Value: `6` |
| `screening_window_days` | Integer | Allowed screening window. Value: `28` |
| `countries` | JSONB | List of participating countries. Value: `["USA","JPN","CAN","AUS","NZL"]` |
| `study_start_date` | Date | First site activation date. Value: `2024-03-01` |

### 2.2 `study_arms`

Treatment arms with allocation ratios. 2 rows.

> **Production sources:** IRT/IWRS system (Suvoda, Signant RTSM, Medidata RTSM) — the randomization system is the authoritative source for arm definitions, codes, and allocation ratios. Also available from the protocol document or CTMS study design module.
> **Refresh cadence:** Static — loaded at study setup.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `arm_code` | String(20) UNIQUE | Arm identifier: `ARM_A`, `ARM_B` |
| `arm_name` | String(200) | Full name. ARM_A = "Veliparib + Carboplatin + Paclitaxel", ARM_B = "Investigator's Choice Standard Chemotherapy" |
| `arm_type` | String(50) | `Experimental` or `Active Comparator` |
| `allocation_ratio` | Float | Randomization weight. Both `0.5` (1:1 allocation) |

### 2.3 `stratification_factors`

Randomization stratification factors. 2 rows.

> **Production sources:** IRT/IWRS system (Suvoda, Signant RTSM) — the randomization system defines and enforces stratification. Also documented in the Statistical Analysis Plan (SAP) and protocol.
> **Refresh cadence:** Static — loaded at study setup.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `factor_name` | String(100) | Factor name: `Gender`, `ECOG` |
| `factor_levels` | JSONB | Allowed levels. Gender: `["Male","Female"]`, ECOG: `["0","1"]` |

### 2.4 `visit_schedule`

Protocol visit definitions from USDM Schedule of Activities. 10 rows.

> **Production sources:** EDC system study build configuration (Medidata Rave Architect, Oracle InForm Designer, Veeva Vault CDMS) — visit schedules are configured during EDC build from the protocol's Schedule of Activities. Also available from USDM/TransCelerate Digital Protocol exports, or sponsor protocol authoring tools (e.g., Veeva Vault Clinical, Study Builder).
> **Refresh cadence:** Static — loaded at study setup, updated on protocol amendment.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `visit_id` | String(20) UNIQUE | Encounter identifier: `ENC-001` through `ENC-010` |
| `visit_name` | String(100) | Human-readable visit name (e.g., "Screening Visit", "Cycle 1 Day 1") |
| `visit_type` | String(50) | Visit classification (e.g., `Screening`, `Treatment`, `Follow-up`) |
| `timing_value` | Integer | Numeric timing component |
| `timing_unit` | String(20) | Timing unit: `days`, `weeks`, `cycles` |
| `timing_relative_to` | String(50) | Reference event (e.g., `Randomization`, `Prior Cycle`) |
| `window_early_bound` | Integer | Early visit window (days) |
| `window_late_bound` | Integer | Late visit window (days) |
| `recurrence_pattern` | String(50) | Recurrence descriptor (e.g., `Every 21 days`) |

### 2.5 `visit_activities`

Activities performed at each visit, from USDM scheduled instances. ~80 rows.

> **Production sources:** EDC system study build (activity-to-visit mapping configured in EDC forms); USDM/TransCelerate Digital Protocol SOA export; or manually extracted from the protocol Schedule of Activities table.
> **Refresh cadence:** Static — loaded at study setup, updated on protocol amendment.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `visit_id` | String(20) | FK to `visit_schedule.visit_id` |
| `activity_id` | String(20) | Activity identifier from protocol |
| `activity_name` | String(200) | Activity description (e.g., "CBC with Differential", "RECIST Tumor Assessment") |
| `is_required` | Boolean | Whether activity is mandatory at this visit |

### 2.6 `eligibility_criteria`

Inclusion and exclusion criteria from the protocol. 25 rows (13 inclusion + 12 exclusion).

> **Production sources:** Protocol document (Section 3: Eligibility Criteria); USDM/TransCelerate Digital Protocol eligibility export; ClinicalTrials.gov API (`eligibility` field); or sponsor protocol authoring system (Veeva Vault Clinical). In CDISC-aligned studies, maps to Trial Inclusion/Exclusion (TI) domain.
> **Refresh cadence:** Static — loaded at study setup, updated on protocol amendment.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `criterion_id` | String(20) UNIQUE | Identifier: `INC_1`..`INC_13`, `EXC_1`..`EXC_12` |
| `type` | String(20) | `Inclusion` or `Exclusion` |
| `original_text` | Text | Full criterion text from protocol |
| `short_label` | String(200) | Truncated label for display |

### 2.7 `screen_failure_reason_codes`

Lookup table mapping screen failure codes to eligibility criteria. 15 rows.

> **Production sources:** Sponsor-defined codelist, typically configured in the EDC system (Rave Global Libraries, InForm codelist management) and/or the CTMS. The mapping to eligibility criteria is a sponsor data management artifact. In CDISC-aligned studies, aligns with Disposition (DS) domain reason coding.
> **Refresh cadence:** Static — loaded at study setup. May be extended mid-study if new failure reasons are identified.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `reason_code` | String(30) UNIQUE | Code: `SF_ECOG`, `SF_HISTO`, `SF_ORGAN`, `SF_PRIOR_CHEMO`, `SF_SMOKING`, `SF_BRAIN_METS`, `SF_CONSENT`, `SF_NEUROPATHY`, `SF_CARDIAC`, `SF_EGFR_ALK`, `SF_MEASURABLE`, `SF_AGE`, `SF_OTHER`, `SF_HEPATIC`, `SF_RENAL` |
| `description` | String(300) | Human-readable failure description |
| `criterion_id` | String(20) | Mapped eligibility criterion (e.g., `SF_ECOG` → `INC_6`). NULL for non-criterion reasons |
| `category` | String(50) | Grouping category: `Performance Status`, `Histology`, `Lab Values`, `Prior Therapy`, `Smoking Status`, `CNS Disease`, `Consent`, `Neuropathy`, `Cardiac`, `Molecular`, `Measurable Disease`, `Demographics`, `Other` |

### 2.8 `sites`

Investigator sites. 142 rows across 20 countries (real facilities from NCT02264990).

> **Production sources:** CTMS site management module (Veeva Vault CTMS, Oracle Siebel CTMS) — the authoritative source for site identifiers, activation dates, countries, and status. Enriched with: site feasibility data (Citeline TrialScope, WCG SiteIntel) for site type and experience level; IRT/IWRS for per-site enrollment targets. The `anomaly_type` column is a demo-only field not present in production; in production, anomalies are detected by the agents, not pre-labeled.
> **Refresh cadence:** Weekly — new sites activate, site status changes, enrollment targets may be redistributed.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) UNIQUE | Site identifier: `SITE-001` through `SITE-157` (non-contiguous due to anomaly site ID reservations) |
| `country` | String(3) | ISO-3166 alpha-3: `USA` (24), `GBR` (19), `JPN` (12), `RUS` (12), `ESP` (9), `ZAF` (8), `HUN` (7), `TUR` (7), `KOR` (6), `NLD` (5), `ARG` (4), `AUS` (4), `CAN` (4), `CZE` (4), `DEU` (4), `ISR` (4), `TWN` (4), `FIN` (2), `NZL` (2), `DNK` (1) |
| `city` | String(100) | City name (real trial site cities from NCT02264990) |
| `site_type` | String(30) | `Academic` (35%), `Community` (40%), `Hospital` (25%) |
| `experience_level` | String(20) | `High` (30%), `Medium` (50%), `Low` (20%). Anomaly sites have overridden experience levels |
| `activation_date` | Date | Date site was activated for enrollment. Range: 2024-03-01 to 2024-11-30 across 7 waves |
| `target_enrollment` | Integer | Per-site enrollment target (3-6 subjects) |
| `anomaly_type` | String(50) | NULL for normal sites. Values: `high_query_burden`, `enrollment_stall`, `entry_lag_spike`, `supply_constraint`, `monitoring_gap` for the 13 anomaly sites |

**Indexes:** `ix_sites_country` on `country`

**Site activation waves:**

| Wave | Period | Countries | Count |
|------|--------|-----------|-------|
| 1 | Month 0-3 | USA, CAN | 28 |
| 2 | Month 2-4 | GBR, DEU, NLD | 28 |
| 3 | Month 3-5 | JPN, KOR, TWN | 22 |
| 4 | Month 4-6 | ESP, DNK, FIN | 12 |
| 5 | Month 5-7 | AUS, NZL | 6 |
| 6 | Month 5-7 | HUN, CZE, RUS | 23 |
| 7 | Month 6-8 | ARG, TUR, ISR, ZAF | 23 |

### 2.9 `cra_assignments`

Clinical Research Associate assignments to sites. ~180 rows. ~30 sites have CRA transitions (two assignments).

> **Production sources:** CTMS monitoring management module (Veeva Vault CTMS, Oracle Siebel CTMS) — CRA-to-site assignment records with start/end dates. Some CROs track this in dedicated monitoring tools (e.g., Veeva SiteVault, Greenphire). CRA transition events are critical operational signals for downstream agents.
> **Refresh cadence:** Weekly — CRA reassignments happen periodically; change events are operationally significant.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `cra_id` | String(20) | CRA identifier: `CRA-001` through `CRA-300` |
| `site_id` | String(20) | FK to `sites.site_id` |
| `start_date` | Date | Assignment start date |
| `end_date` | Date | Assignment end date (NULL if current) |
| `is_current` | Boolean | Whether this is the active assignment |

**Indexes:** `ix_cra_site` on `site_id`

### 2.10 `drug_kit_types`

Drug kit definitions by treatment arm. 4 rows.

> **Production sources:** IRT/IWRS system (Suvoda, Signant RTSM, Medidata RTSM) — kit type definitions including arm mapping, storage requirements, and shelf life. Also available from the drug supply plan maintained by Clinical Supply Management.
> **Refresh cadence:** Static — loaded at study setup. Updated if new kit types are introduced (e.g., dose modifications).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `kit_type_id` | String(20) UNIQUE | `KIT_VEL` (Veliparib), `KIT_CARBO` (Carboplatin), `KIT_PAC` (Paclitaxel) — all ARM_A; `KIT_STD` (Standard Chemo) — ARM_B |
| `kit_name` | String(200) | Full drug kit name |
| `arm_code` | String(20) | Associated treatment arm |
| `storage_conditions` | String(200) | Storage requirements (e.g., "2-8C", "15-25C") |
| `shelf_life_days` | Integer | Kit shelf life in days |

### 2.11 `depots`

Regional drug supply depots. 8 rows.

> **Production sources:** IRT/IWRS supply management module; Clinical Supply Management systems (Almac Group, Catalent, Fisher Clinical Services); or sponsor logistics/supply chain teams. Depot-to-site mapping and standard shipping times are typically maintained in the IRT system.
> **Refresh cadence:** Static — loaded at study setup. Updated if new depots are added or shipping routes change.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `depot_id` | String(20) UNIQUE | `DEPOT_US`, `DEPOT_AM`, `DEPOT_EU_W`, `DEPOT_EU_E`, `DEPOT_JP`, `DEPOT_AP`, `DEPOT_IL`, `DEPOT_ZA` |
| `depot_name` | String(100) | Full depot name |
| `country` | String(3) | Country served |
| `city` | String(100) | Depot location |
| `standard_shipping_days` | Integer | Standard shipping time to sites (2-5 days) |

---

## 3. Enrollment Funnel Tables (Category D)

These tables power **Agent 3 (Enrollment Funnel Intelligence)** and represent the screening-to-randomization pipeline. Category D is an **MVP data feed**.

### 3.1 `screening_log`

Individual screening events per subject. ~900 rows.

> **Production sources:** Primary: EDC system screening CRFs (Medidata Rave, Oracle InForm, Veeva Vault CDMS) — the screening visit eCRF captures outcome, failure reason code, and free-text narrative. Secondary: CTMS screening tracker module; IRT/IWRS screening log (for sites using IRT-initiated screening). The `failure_reason_narrative` free-text field comes from site-entered eCRF data and varies in quality by country and site — this variability is intentional and realistic.
> **Refresh cadence:** Daily — screening events are entered within 1-7 days of occurrence depending on site entry lag.
> **Integration notes:** The structured `failure_reason_code` is typically a drop-down selection in the EDC form. The `failure_reason_narrative` is a free-text field on the same form. In some CRO setups, the CTMS maintains a parallel screening tracker that may have different coding. The CODM adapter must reconcile these when both sources are available.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | Screening site. FK to `sites.site_id` |
| `subject_id` | String(30) UNIQUE | Subject identifier: `SUBJ-00001` through `SUBJ-00898` |
| `screening_date` | Date | Date of screening assessment |
| `outcome` | String(20) | `Passed` (enrolled) or `Failed` (screen failure) |
| `failure_reason_code` | String(30) | FK to `screen_failure_reason_codes.reason_code`. NULL for passed subjects |
| `failure_reason_narrative` | Text | Free-text narrative describing the failure. Quality varies by country and site — JPN sites produce more detailed narratives; some sites produce terse 2-3 word entries. NULL for passed subjects |

**Indexes:** `ix_screening_site` on `site_id`, `ix_screening_date` on `screening_date`

**Key data characteristics:**
- Overall screen failure rate: ~26%
- Failure reason distribution: SF_ORGAN (20%), SF_ECOG (18%), SF_HISTO (15%), SF_PRIOR_CHEMO (12%), SF_SMOKING (8%), others <5% each
- Narrative quality varies by country (3 tiers: detailed, moderate, terse)
- Seasonal dip: screening volume drops ~40% during Dec 15-Jan 15 holiday window
- Enrollment follows S-curve trajectory: logistic function with midpoint at ~week 40
- Post-enrollment-cap wind-down: screening continues 8 weeks after 595 target reached, with 12%/week decay

### 3.2 `randomization_log`

Subjects who passed screening and were randomized. 595 rows.

> **Production sources:** IRT/IWRS system (Suvoda, Signant RTSM, Medidata RTSM) — the authoritative source for randomization. The IRT system assigns arm codes via the randomization algorithm (block, stratified, dynamic) and records stratification factor values at the time of randomization. This is the single source of truth for arm assignment and stratification balance.
> **Refresh cadence:** Daily or event-driven — randomization events are captured in real-time by the IRT system. Export frequency depends on the IRT vendor's API or flat-file extract cadence.
> **Integration notes:** The IRT system is the only authoritative source for randomization. EDC may record the randomization date and arm, but the IRT record takes precedence for arm assignment, stratification, and balance calculations.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `subject_id` | String(30) UNIQUE | FK to `screening_log.subject_id` |
| `site_id` | String(20) | FK to `sites.site_id` |
| `randomization_date` | Date | Date of randomization (1-14 days post screening) |
| `arm_code` | String(20) | Treatment arm: `ARM_A` or `ARM_B`. Block-randomized in permuted blocks of 4 per site |
| `stratum_gender` | String(10) | Stratification: `Male` (60%) or `Female` (40%) |
| `stratum_ecog` | String(5) | Stratification: `0` (45%) or `1` (55%) |

**Indexes:** `ix_rand_site` on `site_id`

**Key data characteristics:**
- Arm balance: ~295 ARM_A / ~300 ARM_B (block randomization ensures near-equal allocation)
- 141/142 sites have at least one randomized subject

### 3.3 `enrollment_velocity`

Weekly per-site enrollment aggregates computed from individual screening and randomization records. ~9,300 rows.

> **Production sources:** Derived/computed table — aggregated from `screening_log` and `randomization_log` records. In production, this may also be sourced from: CTMS enrollment dashboard exports (weekly enrollment summaries); IRT/IWRS enrollment reports (cumulative randomization counts); or CRO-provided enrollment status reports (typically weekly Excel/CSV extracts). The `target_cumulative` column comes from the enrollment plan maintained in the CTMS or sponsor project management tools.
> **Refresh cadence:** Weekly — computed after daily screening/randomization feeds are processed. Alternatively, CRO-provided enrollment reports arrive weekly.
> **Integration notes:** In a production deployment, this table can be populated either by computing from individual records (preferred — ensures consistency) or by ingesting pre-aggregated enrollment reports from the CTMS. The CODM should validate consistency between these sources when both are available.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `week_start` | Date | Monday of the reporting week |
| `week_number` | Integer | Week number since study start (0-based) |
| `screened_count` | Integer | Subjects screened this week at this site |
| `screen_failed_count` | Integer | Subjects who failed screening this week |
| `randomized_count` | Integer | Subjects randomized this week |
| `cumulative_screened` | Integer | Running total screened at this site |
| `cumulative_randomized` | Integer | Running total randomized at this site |
| `target_cumulative` | Integer | Expected cumulative enrollment based on linear ramp to target |

**Indexes:** `ix_velocity_site_week` on `(site_id, week_number)`

**Cross-table consistency guarantee:** Weekly counts in this table exactly match the counts derivable from grouping `screening_log` and `randomization_log` by site and week. These are computed from the individual records, not independently generated.

---

## 4. EDC Telemetry Tables (Category A)

These tables power **Agent 1 (Data Quality and Query Burden)** and capture electronic data capture operational signals. Category A is an **MVP data feed**.

### 4.1 `subject_visits`

Individual treatment visits per randomized subject. ~5,300 rows.

> **Production sources:** EDC system (Medidata Rave, Oracle InForm/Clinical One, Veeva Vault CDMS) — visit tracking module that records planned vs actual visit dates and visit status. In CDISC-aligned studies, maps to the Subject Visits (SV) domain. Some CROs also track visit compliance in the CTMS monitoring module.
> **Refresh cadence:** Daily — visit records are updated as sites enter visit data into the EDC, typically within 1-7 days of the clinical visit.
> **Integration notes:** The EDC system is the primary source. `planned_date` is derived from the visit schedule + randomization date. `actual_date` comes from site-entered data on the visit eCRF. `visit_status` is typically derived from EDC form completion status (all required forms completed = Completed, no forms entered past window = Missed).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `subject_id` | String(30) | FK to `randomization_log.subject_id` |
| `visit_id` | String(20) | FK to `visit_schedule.visit_id`. Encounters: ENC-002 through ENC-007 |
| `cycle_number` | Integer | Treatment cycle (1-6). NULL for Final Visit / Follow-up |
| `planned_date` | Date | Protocol-scheduled visit date (based on cycle_length_days) |
| `actual_date` | Date | Actual visit date (planned +/- 2-3 days). NULL if missed |
| `visit_status` | String(20) | `Completed` (~98%) or `Missed` (~2%) |

**Indexes:** `ix_sv_subject` on `subject_id`, `ix_sv_visit` on `visit_id`

**Key data characteristics:**
- 15% early discontinuation after cycle 3, additional 10% after cycle 4
- Average ~8.9 visits per subject (accounting for discontinuation)

### 4.2 `ecrf_entries`

Individual eCRF page entries per subject visit. ~31,200 rows.

> **Production sources:** EDC system operational metadata / audit trail (Medidata Rave, Oracle InForm, Veeva Vault CDMS). This is **not** the clinical data itself — it is the *operational telemetry* about data entry: when forms were opened, saved, and completed. Key fields: `visit_date` comes from the clinical visit date on the eCRF; `entry_date` comes from the EDC audit trail (first save timestamp); `entry_lag_days` is computed as the difference. `completeness_pct` comes from EDC form completion status APIs or operational reports. Medidata Rave exposes this via the Clinical Data API; Oracle InForm via operational reports; Veeva Vault CDMS via the Vault API.
> **Refresh cadence:** Daily — EDC operational metadata updates as sites enter and modify data.
> **Integration notes:** This is the most schema-variable table across EDC platforms. Medidata Rave exposes form-level metadata differently from Oracle InForm. The CODM source adapter must normalize: (1) page/form naming conventions, (2) entry timestamp extraction from audit trails, (3) completeness calculation methodology. This normalization is the **primary technical effort** for MVP integration.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `subject_visit_id` | Integer | FK to `subject_visits.id` |
| `subject_id` | String(30) | FK to `randomization_log.subject_id` |
| `site_id` | String(20) | FK to `sites.site_id` |
| `crf_page_name` | String(50) | CRF page: `Lab Results` (30%), `Tumor Assessment` (20%), `Adverse Events` (15%), `Drug Accountability` (15%), `Vital Signs` (8%), `Physical Exam` (7%), `Concomitant Medications` (5%) |
| `visit_date` | Date | Date the clinical visit occurred |
| `entry_date` | Date | Date the data was entered into EDC |
| `entry_lag_days` | Integer | Calendar days between visit and entry. Key EDC quality metric |
| `completeness_pct` | Float | Percentage of required fields completed (50-100%) |
| `has_missing_critical` | Boolean | TRUE if completeness < 85% |
| `missing_field_count` | Integer | Number of missing fields (0 if complete, 1-4 if incomplete) |

**Indexes:** `ix_ecrf_site` on `site_id`, `ix_ecrf_subject` on `subject_id`

**Key data characteristics — Entry lag by country (median days):**

| Country | Distribution | Median |
|---------|-------------|--------|
| JPN | LogNormal(0.5, 0.5) | ~1.6d |
| USA | LogNormal(1.0, 0.7) | ~2.7d |
| CAN | LogNormal(1.1, 0.7) | ~3.0d |
| NZL | LogNormal(1.2, 0.8) | ~3.3d |
| AUS | LogNormal(1.3, 0.8) | ~3.7d |

Additional lag modifiers: +3 days during Dec 15-Jan 5 holiday window; +5-7 days during CRA transition spikes at anomaly sites.

### 4.3 `queries`

Data queries raised against eCRF entries. ~22,900 rows.

> **Production sources:** EDC system query management module (Medidata Rave Query Management, Oracle InForm Discrepancy Management, Veeva Vault CDMS Query Module). Queries are raised by three mechanisms: (1) **Auto-validation / Edit checks** — programmatic rules built into the EDC (range checks, cross-form consistency, conditional logic); (2) **Manual review** — data managers or medical monitors reviewing listings; (3) **Monitoring visits** — CRAs raising queries during on-site or remote monitoring. The `triggered_by` field maps to these mechanisms. Query lifecycle states (Open → Answered → Closed) are tracked by the EDC query workflow engine.
> **Refresh cadence:** Daily — query activity is near-continuous in active studies. EDC query exports are typically available as daily flat files or via API.
> **Integration notes:** Query lifecycle states vary by EDC platform (e.g., Rave uses "Open/Answered/Closed/Cancelled"; InForm uses "Open/Candidate/Answered/Closed"). The CODM adapter normalizes these to a standard lifecycle. The `triggered_by` field may require mapping from platform-specific query origin codes.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `subject_id` | String(30) | FK to `randomization_log.subject_id` |
| `crf_page_name` | String(50) | CRF page the query relates to |
| `query_type` | String(30) | `Missing Data` (35%), `Discrepancy` (25%), `Out of Range` (20%), `Protocol Deviation` (10%), `Logical Inconsistency` (10%) |
| `open_date` | Date | Date the query was opened |
| `response_date` | Date | Date a response was provided. NULL if still Open |
| `close_date` | Date | Date the query was closed. NULL if Open or Answered |
| `status` | String(20) | `Open` (unresolved), `Answered` (response received, not yet closed), `Closed` (resolved) |
| `age_days` | Integer | Days the query has been open (current age if open, total duration if closed) |
| `priority` | String(10) | `High` (15%), `Medium` (50%), `Low` (35%) |
| `triggered_by` | String(50) | What triggered the query: `Auto-validation` (45%), `Manual Review` (35%), `Edit Check` (20%), or `Monitoring Visit` (only during 14-day post-monitoring windows) |

**Indexes:** `ix_queries_site` on `site_id`, `ix_queries_subject` on `subject_id`, `ix_queries_open` on `open_date`

**Key data characteristics:**
- Study-average query rate: ~0.73 queries per eCRF entry
- Query rate by experience level: High ~0.3 base, Medium ~0.5, Low ~0.8
- Post-monitoring spike: 3x query rate increase for 14 days after a completed monitoring visit
- Monitoring-triggered queries are temporally aligned: `triggered_by='Monitoring Visit'` ONLY appears when `open_date` falls within 14 days of an actual completed monitoring visit at that site. 100% alignment verified.
- During monitoring gaps (no completed visits), no monitoring-triggered queries are generated — the *absence* is the signal

### 4.4 `data_corrections`

Field-level data corrections following query resolution. ~5,700 rows.

> **Production sources:** EDC system audit trail (Medidata Rave Audit Trail, Oracle InForm Audit Report, Veeva Vault CDMS Audit Trail). Every field-level data change in the EDC is captured with the original value, new value, change timestamp, reason for change, and associated query ID. This is a GxP-regulated audit trail required by 21 CFR Part 11 / EU Annex 11. The CODM extracts the subset of audit trail records that represent data corrections triggered by queries (as opposed to initial data entry or spontaneous corrections).
> **Refresh cadence:** Daily — audit trail records accumulate continuously; extracted as part of the daily EDC feed.
> **Integration notes:** EDC audit trails are verbose (every keystroke may be logged). The CODM adapter filters to correction events: records where `old_value` differs from `new_value` and a `triggered_by_query_id` linkage exists. Audit trail export formats vary significantly across platforms — Rave exports XML/CSV audit trails; InForm provides operational reports; Vault exposes audit via API.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `subject_id` | String(30) | FK to `randomization_log.subject_id` |
| `crf_page_name` | String(50) | CRF page corrected |
| `field_name` | String(100) | Specific field corrected (e.g., `hemoglobin`, `target_lesion_1`, `ae_start_date`). Drawn from page-specific field lists |
| `old_value` | String(200) | Previous field value |
| `new_value` | String(200) | Corrected field value |
| `correction_date` | Date | Date correction was made |
| `triggered_by_query_id` | Integer | ID of the query that triggered this correction |

**Indexes:** `ix_corrections_site` on `site_id`

---

## 5. Monitoring Oversight Tables (Category B)

These tables power **Agent 2 (Monitoring Oversight)** and provide monitoring cadence, KRI, and action tracking signals. Category B is a **Phase 2 data feed**.

### 5.1 `monitoring_visits`

CRA monitoring visits to sites. ~1,230 rows.

> **Production sources:** CTMS monitoring module (Veeva Vault CTMS, Oracle Siebel CTMS, Bio-Optronics Clinical Conductor) — CRA monitoring visit records including planned/actual dates, visit type, and findings. Some CROs use dedicated monitoring tools (Veeva SiteVault for site-facing; internal CRO monitoring trackers). Monitoring visit reports (MVRs) are the source documents, typically uploaded to the eTMF (Veeva Vault eTMF, Montrium eTMF Connect) and summarized in the CTMS.
> **Refresh cadence:** Weekly — monitoring visit data is typically updated weekly as CRAs complete visit reports within 5-10 business days of the visit. Some CROs provide faster turnaround for on-site visits.
> **Integration notes:** The `queries_generated` field requires cross-referencing with EDC query data — it is not natively tracked in the CTMS. In production, this linkage must be computed by the CODM by matching monitoring visit dates to query open dates at the same site, just as the generator does. The `findings_count` and `critical_findings` come from the monitoring visit report (MVR) summary.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `cra_id` | String(20) | FK to `cra_assignments.cra_id` |
| `planned_date` | Date | Scheduled visit date (every 6-8 weeks) |
| `actual_date` | Date | Actual visit date. NULL if missed |
| `visit_type` | String(20) | `On-Site` (~67%) or `Remote` (~33%) |
| `findings_count` | Integer | Total findings during the visit. Poisson(3) for completed visits, 0 for missed |
| `critical_findings` | Integer | Subset of findings classified as critical. Poisson(0.3), capped at findings_count |
| `queries_generated` | Integer | Count of queries triggered by this visit. Updated in Phase C to match actual query counts where `triggered_by='Monitoring Visit'` within 14 days of `actual_date` |
| `days_overdue` | Integer | Days between planned and actual date (0 = on time) |
| `status` | String(20) | `Completed` or `Missed` |

**Indexes:** `ix_monvisit_site` on `site_id`

**Cross-table consistency guarantee:** `queries_generated` is not randomly generated — it is updated after query generation to equal the actual count of `queries` rows where `triggered_by = 'Monitoring Visit'` and `open_date` falls within 14 days of the monitoring visit's `actual_date`.

### 5.2 `kri_snapshots`

Monthly Key Risk Indicator snapshots per site, computed from actual EDC and enrollment data using 60-day trailing windows. ~21,500 rows.

> **Production sources:** Two possible sourcing strategies:
> 1. **RBQM platform export** (preferred when available): CluePoints, Veeva Vault QualityOne, or TransCelerate-aligned RBQM tools compute KRIs from source data and export snapshots. These platforms implement ICH E6(R2) / E8(R1) risk-based monitoring principles with statistical models for site-level risk scoring.
> 2. **CODM-computed** (used in this system): KRI values are computed by the system from underlying EDC, enrollment, and monitoring data using 60-day trailing windows. This approach ensures KRIs are always consistent with the raw signals agents query and avoids dependency on an external RBQM platform.
>
> In practice, many sponsors use both — RBQM platform KRIs for formal risk governance, and internally computed KRIs for operational intelligence. Discrepancies between the two can themselves be a useful signal.
> **Refresh cadence:** Monthly — aligned with risk governance review cycles. Some RBQM platforms compute weekly; the CODM can support either cadence.
> **Integration notes:** KRI definitions (names, thresholds, computation methods) vary across RBQM platforms and sponsor risk management plans. The CODM must either adopt the sponsor's KRI framework or maintain a mapping from platform-specific KRIs to the standardized set defined here.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `snapshot_date` | Date | Monthly snapshot date (every 30 days from study start + 90 days) |
| `kri_name` | String(100) | KRI metric name (see table below) |
| `kri_value` | Float | Computed KRI value for this site at this snapshot |
| `amber_threshold` | Float | Warning threshold |
| `red_threshold` | Float | Critical threshold |
| `status` | String(10) | `Green`, `Amber`, or `Red` based on value vs thresholds |

**Indexes:** `ix_kri_site_date` on `(site_id, snapshot_date)`

**KRI definitions and thresholds:**

| KRI Name | Unit | Amber | Red | Direction | Computation |
|----------|------|-------|-----|-----------|-------------|
| Query Rate | queries/eCRF entry | 0.8 | 1.5 | Higher is worse | Queries opened in 60-day window / eCRF entries in window |
| Open Query Age (days) | days | 14 | 28 | Higher is worse | Mean age of open/answered queries at snapshot |
| Entry Lag Median (days) | days | 5 | 12 | Higher is worse | Median `entry_lag_days` of eCRF entries in 60-day window |
| Screen Failure Rate (%) | percent | 38 | 50 | Higher is worse | Failed / total screenings in 60-day window |
| Enrollment vs Target (%) | percent | 60 | 40 | Lower is worse | Cumulative randomized / expected (linear ramp) * 100 |
| Monitoring Visit Compliance (%) | percent | 80 | 60 | Lower is worse | Completed / total monitoring visits in 60-day window |
| Critical Findings Rate | per visit | 0.8 | 1.5 | Higher is worse | Critical findings / completed visits in window |
| Data Completeness (%) | percent | 88 | 75 | Lower is worse | Mean `completeness_pct` of eCRF entries in window |
| Correction Rate (%) | percent | 8 | 15 | Higher is worse | Proxy: (queries * 0.15) / eCRF entries * 100 |
| Protocol Deviation Rate | per visit | 0.5 | 1.2 | Higher is worse | Data-driven from monitoring findings |

**Cross-table consistency guarantee:** KRI values are computed from actual data in `ecrf_entries`, `queries`, `screening_log`, `randomization_log`, and `monitoring_visits` — not generated independently. This means KRI alerts are always consistent with the raw operational signals that agents will query.

### 5.3 `overdue_actions`

Follow-up actions from monitoring visits. ~310 rows.

> **Production sources:** CTMS action tracking module (Veeva Vault CTMS, Oracle Siebel CTMS) — follow-up actions are created during monitoring visits and tracked to completion. Some CROs manage these in dedicated issue/action management tools (CAPA systems, Veeva Vault Quality). Actions may also appear in monitoring visit reports (MVRs) uploaded to the eTMF. In RBQM workflows, actions can be generated by centralized monitoring (CluePoints, Vault QualityOne) rather than on-site visits.
> **Refresh cadence:** Weekly — action status updates as CRAs and sites complete follow-up items. Overdue detection requires comparing `due_date` against current date.
> **Integration notes:** Action tracking systems vary widely across CROs. Some use CTMS-integrated action management; others use spreadsheets or email-based tracking. The CODM adapter must handle structured (CTMS export) and semi-structured (spreadsheet) sources. Categories (`Data Quality`, `Safety Reporting`, etc.) may need mapping from CRO-specific taxonomies.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `monitoring_visit_id` | Integer | FK to `monitoring_visits.id` |
| `action_description` | Text | Description of required action (e.g., "Resolve outstanding queries on Lab Results CRF", "Complete missing AE follow-up documentation") |
| `category` | String(50) | `Data Quality`, `Safety Reporting`, `IP Management`, `Regulatory`, `Documentation` |
| `due_date` | Date | Action due date |
| `completion_date` | Date | Date action was completed. NULL if still open/overdue |
| `status` | String(20) | `Completed` (~95%), `Open` (~4%), `Overdue` (~1%) |

**Indexes:** `ix_overdue_site` on `site_id`

---

## 6. IRT / Supply Tables (Category E)

These tables power the **Phase 2 IRT enrichment of Agent 3 (Enrollment Funnel)** and provide drug supply continuity signals. Category E is a **Phase 2 data feed**.

### 6.1 `kit_inventory`

Biweekly drug kit inventory snapshots per site. ~18,100 rows.

> **Production sources:** IRT/IWRS system inventory module (Suvoda, Signant RTSM, Medidata RTSM, 4G Clinical) — the IRT system tracks kit-level inventory at each site in real time. Kit receipts (from depot shipments), dispensations (at randomization/visit), returns, and destructions are all logged. Inventory snapshots can be extracted at any frequency. Some sponsors also track inventory via Clinical Supply Management systems (Almac, Catalent).
> **Refresh cadence:** Daily or event-driven — IRT systems track inventory in real time. For this system, biweekly snapshots are sufficient for trend detection. Event-driven updates (e.g., stockout alerts) are available from IRT systems that support webhook/API notifications.
> **Integration notes:** IRT systems are the single source of truth for site-level drug inventory. The `quantity_on_hand` reflects the IRT's running balance. The `reorder_level` and replenishment logic are configured in the IRT system's resupply algorithm. IRT data is typically available via API (Suvoda REST API, Signant API) or scheduled flat-file exports (CSV/XML).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `kit_type_id` | String(20) | FK to `drug_kit_types.kit_type_id` |
| `snapshot_date` | Date | Inventory snapshot date (every 14 days from site activation) |
| `quantity_on_hand` | Integer | Current kit quantity. 0 during stockout periods |
| `reorder_level` | Integer | Reorder trigger threshold. Fixed at 3 |
| `is_below_reorder` | Boolean | TRUE if `quantity_on_hand <= reorder_level` |

**Indexes:** `ix_kit_site_date` on `(site_id, snapshot_date)`

**Key data characteristics:**
- Initial stock: 6-10 kits per site per kit type
- Auto-replenishment when below reorder level
- Anomaly site SITE-041: `quantity_on_hand = 0` for ~12 biweekly snapshots during stockout episodes
- Anomaly site SITE-031 (Chain 4): elevated inventory (8-15 kits) reflecting low enrollment → kits accumulate

### 6.2 `randomization_events`

IRT system events for each randomization. 595 rows.

> **Production sources:** IRT/IWRS system event log (Suvoda, Signant RTSM, Medidata RTSM) — every randomization attempt is logged with outcome (success, delay, failure), timestamps, and reason codes. The IRT system captures the full randomization workflow: site initiates randomization → IRT validates eligibility/stratification → IRT checks kit availability → IRT assigns arm → IRT dispenses kit number. Failures at any step are logged with specific reason codes.
> **Refresh cadence:** Daily or event-driven — randomization events are captured in real time by the IRT system. These are among the most operationally urgent signals (a randomization failure means a patient is waiting).
> **Integration notes:** IRT event logs are highly structured but vendor-specific. Suvoda exposes events via REST API with webhook support; Signant provides scheduled exports. The `delay_reason` taxonomy must be mapped from vendor-specific codes (e.g., Suvoda's "INSUFFICIENT_INVENTORY" → `Kit Stockout`). The `delay_duration_hours` may need to be computed from event timestamps if not directly provided.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `subject_id` | String(30) | FK to `randomization_log.subject_id` |
| `site_id` | String(20) | FK to `sites.site_id` |
| `event_date` | Date | Date of randomization attempt |
| `event_type` | String(20) | `Success` (~94%), `Delay` (~5%), `Failure` (~1%) |
| `delay_reason` | String(100) | NULL for Success. For Delay: `Kit Stockout` (40%), `System Issue` (30%), `Stratification Error` (20%), `Kit Labeling Error` (10%). For sites during stockout windows: always `Kit Stockout` |
| `delay_duration_hours` | Integer | Duration of delay. 0 for Success. 4-72 hours for normal delays; 48-192 hours for stockout delays |

**Indexes:** `ix_randevt_site` on `site_id`

**Cross-table consistency guarantee:** When `kit_inventory.quantity_on_hand = 0` at a site during a stockout window, any `randomization_events` at that site during the same period have `event_type = 'Delay'` with `delay_reason = 'Kit Stockout'`.

### 6.3 `depot_shipments`

Drug shipments from depots to sites. ~1,700 rows.

> **Production sources:** IRT/IWRS supply management module (Suvoda, Signant RTSM) for shipment initiation and tracking; Clinical Supply chain / logistics providers (Almac Group, Catalent, Fisher Clinical Services, Marken) for shipment execution, carrier tracking, and actual delivery confirmation. Some sponsors use dedicated supply chain platforms (SAP, TraceLink) for end-to-end visibility. Customs/import documentation systems may provide delay reason data for international shipments.
> **Refresh cadence:** Daily — shipment status updates as carriers provide tracking information. Delivery confirmation may lag 1-2 days after actual receipt at site.
> **Integration notes:** Shipment data spans two systems: the IRT (which initiates and tracks the request) and the logistics provider (which executes the physical shipment). The `shipment_date` and `kit_count` come from the IRT; `actual_arrival` and `delay_reason` typically come from the logistics provider or site confirmation in the IRT. Reconciling these two sources is a common integration challenge — shipments may show "delivered" in the carrier system but not yet "received" in the IRT until the site confirms receipt.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `depot_id` | String(20) | FK to `depots.depot_id` |
| `site_id` | String(20) | FK to `sites.site_id` |
| `kit_type_id` | String(20) | FK to `drug_kit_types.kit_type_id` |
| `shipment_date` | Date | Date shipment left depot |
| `expected_arrival` | Date | Expected delivery date (shipment_date + standard_shipping_days) |
| `actual_arrival` | Date | Actual delivery date. NULL if In-Transit |
| `kit_count` | Integer | Number of kits shipped (4-10) |
| `status` | String(20) | `Delivered` (~93%), `In-Transit` (~5%), `Delayed` (~2%) |
| `delay_reason` | String(200) | NULL for on-time deliveries. Values: `Customs clearance delay`, `Weather disruption`, `Carrier logistics issue`, `Documentation error`, or anomaly-specific reasons (e.g., `Customs hold at Auckland depot`) |

**Indexes:** `ix_shipment_site` on `site_id`

---

## 7. Cross-Table Relationships

The following entity relationships ensure data integrity and enable cross-domain queries:

```
study_config
    ├── study_arms (arm_code)
    └── stratification_factors

visit_schedule
    └── visit_activities (visit_id → activity_id)

eligibility_criteria
    └── screen_failure_reason_codes (criterion_id)

sites (site_id) ─────────────────────────────────────┐
    ├── cra_assignments (site_id)                     │
    ├── screening_log (site_id)                       │
    │       └── randomization_log (subject_id)        │
    │               ├── subject_visits (subject_id)   │
    │               │       └── ecrf_entries           │
    │               │              (subject_visit_id)  │
    │               └── randomization_events           │
    │                      (subject_id)                │
    ├── queries (site_id, subject_id)                  │
    ├── data_corrections (site_id, subject_id)         │
    ├── monitoring_visits (site_id)                     │
    │       └── overdue_actions (monitoring_visit_id)   │
    ├── kri_snapshots (site_id)                        │
    ├── kit_inventory (site_id)                        │
    ├── enrollment_velocity (site_id)                  │
    └── depot_shipments (site_id)                      │
                                                       │
depots (depot_id)                                      │
    └── depot_shipments (depot_id) ────────────────────┘

drug_kit_types (kit_type_id)
    ├── kit_inventory (kit_type_id)
    └── depot_shipments (kit_type_id)
```

**Subject journey traceability:** A single subject can be traced from `screening_log` → `randomization_log` → `subject_visits` → `ecrf_entries` → `queries` → `data_corrections` → `randomization_events`, maintaining consistent `site_id`, dates, and arm assignment throughout.

---

## 8. Embedded Anomaly Sites

13 sites have embedded anomaly patterns that the AI agents must detect and diagnose. These anomalies range from obvious single-domain signals to hidden multi-domain causal chains.

| Site | Country | Anomaly Type | Key Signal |
|------|---------|--------------|------------|
| SITE-012 | USA | High query burden | 2.5x query rate, 12% correction rate, low completeness |
| SITE-045 | USA | High query burden | 2x rate concentrated on Lab Results + Drug Accountability |
| SITE-078 | CAN | High query burden | 2.2x rate, staff turnover pattern |
| SITE-031 | JPN | Enrollment stall | 48% screen failure rate, SF_ECOG and SF_SMOKING overrepresented 3x |
| SITE-055 | USA | Enrollment stall | Volume drops 60% after week 20 (competing trial) |
| SITE-089 | AUS | Enrollment stall | 45% failure rate, 50% screening rate reduction |
| SITE-022 | USA | Entry lag spike | CRA transition Sep 2024, +7 days for 6 weeks |
| SITE-067 | CAN | Entry lag spike | Coordinator leave Nov 2024, +5 days for 4 weeks |
| SITE-103 | JPN | Entry lag spike | IT migration Jan 2025, +6 days for 5 weeks |
| SITE-041 | NZL | Supply constraint | 2 stockout episodes: customs hold (20d) + depot delay (14d) |
| SITE-115 | AUS | Supply constraint | 1 stockout episode (weather delay, 8d) |
| SITE-033 | USA | Monitoring gap | 4 missed visits Oct-Mar, CRA reassignment |
| SITE-098 | JPN | Monitoring gap | 2 missed visits, travel restrictions |

Additionally, 3 sites are affected by the regional cluster effect (Chain 5):
- SITE-108, SITE-112, SITE-119 (all JPN): +2-3 days entry lag during Jan-Feb 2025

---

## 9. How the Data Supports Transformational Insights

The data is designed to enable the six cross-domain causal chains described below. Each chain requires reasoning across multiple tables, multiple agents, and multiple time dimensions to diagnose correctly. These chains are what differentiate the system from siloed dashboards — no single-domain view would surface these insights.

### 9.1 Agent 1 (Data Quality) — Autonomous Investigation of Query Burden Root Causes

**Solution capability:** Agent 1 detects query spikes and autonomously traces them to root causes rather than simply reporting "query count exceeds threshold."

**Supporting data:**

| Table | Signal | What the agent finds |
|-------|--------|---------------------|
| `queries` | Per-site query rate (queries / eCRF entries) | SITE-012 (1.85), SITE-045 (1.88), SITE-078 (1.75) vs study avg 0.73 — 2.4-2.6x anomaly |
| `queries` | `crf_page_name` distribution | SITE-045 queries concentrate on Lab Results and Drug Accountability (1.5x additional multiplier on those pages) |
| `queries` | `triggered_by` field | Distinguishes monitoring-triggered queries from auto-validation and manual review — needed for Chain 3 diagnosis |
| `cra_assignments` | CRA transition dates | ~30 sites show CRA changes; Agent 1 correlates query spikes with recent CRA transitions (e.g., SITE-022) |
| `ecrf_entries` | `entry_lag_days` | Entry lag spike at SITE-022 during transition = 16.2d vs 3.4d baseline — CRA handover quality signal |
| `ecrf_entries` | `completeness_pct` | SITE-012 has `completeness_offset` of -15 points — lower completeness drives more missing-data queries |
| `data_corrections` | `correction_rate` per site | SITE-012 at 12% correction rate (vs ~25% baseline) — paradoxically lower corrections despite more queries |
| `kri_snapshots` | Monthly time-series per KRI per site | Temporal dynamics show spikes, drifts, and seasonal effects. Agent 1 can detect when a site *transitions* from Green to Red |

**Transformational insight enabled:** When Agent 1 detects a query spike at SITE-022, it doesn't just flag "high query rate." It traces the spike to CRF pages affected, discovers the CRA transition in `cra_assignments`, sees the simultaneous entry lag spike in `ecrf_entries`, and formulates: "Query spike driven by CRA transition — data entry training gap, not data quality deterioration. Recommend targeted CRA training, not broad remediation."

### 9.2 Agent 2 (Monitoring Gaps) — Detection of Hidden Data Quality Debt

**Solution capability:** Agent 2 identifies monitoring gaps and correlates them with downstream data quality signals to prioritize sites where the gap is actively compounding risk.

**Supporting data — Chain 3 (SITE-033):**

| Table | Signal | What the agent finds |
|-------|--------|---------------------|
| `monitoring_visits` | `status = 'Missed'` | SITE-033: 4 missed visits during Oct 2024 - Mar 2025 |
| `monitoring_visits` | `queries_generated` field | Missed visits show `queries_generated = 0` — no monitoring-triggered queries during gap |
| `queries` | `triggered_by = 'Monitoring Visit'` during gap | **0 monitoring-triggered queries** during Oct 2024 - Mar 2025 (vs 11 before the gap) |
| `queries` | `age_days` during gap period | Average query age 38.6 days during gap vs 10.8 days before — queries aging without resolution |
| `enrollment_velocity` | Enrollment continues normally | SITE-033 shows stable enrollment throughout — the site *looks healthy* on enrollment metrics |
| `kri_snapshots` | `Open Query Age` KRI trending upward | The slow drift in query age (not a spike) is the signal — a gradual accumulation of unresolved debt |

**Transformational insight enabled:** SITE-033 appears healthy on enrollment dashboards. Agent 2 detects the monitoring gap and alerts. Agent 1 notices the *absence* of monitoring-triggered queries (normally a positive signal) is actually masking the gap. When cross-referenced, the compound insight emerges: "SITE-033 is accumulating hidden data quality debt. The site looks fine on enrollment metrics, but 4 missed monitoring visits have allowed query age to drift to 38.6 days. When monitoring resumes, a query avalanche is imminent. Recommend expedited monitoring visit."

### 9.3 Agent 3 (Enrollment Funnel) — Multi-Factor Enrollment Diagnosis

**Solution capability:** Agent 3 decomposes enrollment shortfalls by stage (screening volume → screen failure → randomization) to identify the binding constraint per site, rather than generic "site is behind" alerts.

**Supporting data — Chain 4 (SITE-031, Strict PI):**

| Table | Signal | What the agent finds |
|-------|--------|---------------------|
| `screening_log` | Screen failure rate | SITE-031: 44.4% failure rate (vs ~26% study average) |
| `screening_log` | `failure_reason_code` distribution | SF_ECOG and SF_SMOKING overrepresented by ~3x — the PI is interpreting ECOG borderline cases and smoking history documentation more strictly than protocol requires |
| `screening_log` | `failure_reason_narrative` | Free-text narratives provide clinical context: "ECOG PS 2, assessed during screening visit..." — enables NLP categorization to cluster failure patterns |
| `enrollment_velocity` | Cumulative vs target | SITE-031 consistently below target — enrollment is stalled, not merely slow |
| `ecrf_entries` | Data quality metrics | Paradoxically *excellent* data quality — low query rate, fast entry lag, high completeness. The PI's strictness produces clean data |
| `kit_inventory` | Elevated kit counts | Kits accumulate (8-15 on hand) because few subjects are randomized — approaching shelf-life expiry |
| `kri_snapshots` | `Screen Failure Rate` KRI = Red | Confirms the enrollment stall through KRI lens |

**Transformational insight enabled:** A naive analysis sees SITE-031's excellent data quality and concludes it's a top-performing site. Agent 3 decomposes the enrollment funnel and discovers the binding constraint is the PI's overly strict eligibility interpretation (SF_ECOG and SF_SMOKING 3x overrepresented). Agent 3's IRT enrichment (Phase 2) adds: "Kit inventory is accumulating with 4 kits approaching expiry — direct supply waste." The recommendation is PI re-education on eligibility interpretation, not data quality remediation.

**Supporting data — Chain 6 (SITE-055, Competing Trial):**

| Table | Signal | What the agent finds |
|-------|--------|---------------------|
| `screening_log` | Monthly volume pattern | Pre-competition: ~2 screenings/month. Post week 20: drops to ~0.5/month |
| `screening_log` | Screen failure rate trend | Failure rate *decreases* after competition starts (only well-qualified patients referred) |
| `enrollment_velocity` | Velocity drops but non-zero | Screening doesn't stop entirely — a trickle continues |

**Transformational insight enabled:** Declining volume + improving failure rate = competitive landscape shift. The site is losing its referral pipeline to a competitor, not underperforming on screening execution. The intervention is site engagement about the competitive landscape, not performance remediation.

### 9.4 Agent 3 + IRT (Phase 2) — Supply-Aware Enrollment Diagnosis

**Solution capability:** With IRT enrichment, Agent 3 distinguishes screening shortfalls from supply-driven interruptions — eliminating the blind spot where supply-driven delays are misattributed to site performance.

**Supporting data — Chain 2 (SITE-041, Stockout → Consent Withdrawals):**

| Table | Signal | What the agent finds |
|-------|--------|---------------------|
| `kit_inventory` | `quantity_on_hand = 0` | 12 biweekly snapshots with zero stock during two stockout episodes |
| `randomization_events` | `event_type = 'Delay'`, `delay_reason = 'Kit Stockout'` | Randomization delays during stockout windows |
| `screening_log` | `failure_reason_code = 'SF_CONSENT'` | Consent withdrawals during/after stockout period |
| `screening_log` | `failure_reason_narrative` | Narratives say "patient declined participation" — no mention of supply issue |
| `depot_shipments` | `delay_reason` | Stockout-related shipment delays with reasons: "Customs hold at Auckland depot", "Depot shipping delay" |
| `depot_shipments` | `status = 'Delayed'` | Shipments to SITE-041 show delays correlated with stockout periods |

**Transformational insight enabled:** The consent withdrawals at SITE-041 *look like* poor patient engagement (screening_log shows "SF_CONSENT" with narrative "patient declined"). Without IRT data, the team would blame site performance. With IRT enrichment, Agent 3 traces: zero kit inventory → randomization delay → patients who passed screening couldn't be randomized → 2 of 3 withdrew consent. The root cause is a customs hold at the Auckland depot, not site engagement failure. The intervention is supply chain escalation, not site remediation.

### 9.5 Agent 4 (Site Risk Synthesis) — Cross-Domain Compound Risk Detection

**Solution capability:** Agent 4 fuses signals from all domain agents to surface compound risks that no single-domain report would catch.

**Supporting data — Chain 1 (SITE-022, CRA Transition Cascade):**

| Domain | Agent | Table(s) | Signal |
|--------|-------|----------|--------|
| EDC | Agent 1 | `ecrf_entries` | Entry lag spikes 4.8x during Sep-Oct 2024 |
| EDC | Agent 1 | `queries` | Query rate doubles during CRA transition window |
| Monitoring | Agent 2 | `monitoring_visits` | Monitoring visit delayed 3 weeks during CRA handover |
| Enrollment | Agent 3 | `screening_log` | Screening rate drops 40% starting 3 weeks after CRA transition |
| Config | — | `cra_assignments` | CRA transition on Sep 15, 2024 (root cause) |

**Transformational insight enabled:** Agent 4 receives: from Agent 1 — entry lag spike + query burden increase at SITE-022; from Agent 2 — monitoring visit delayed; from Agent 3 — enrollment deceleration at the same site in the same timeframe. No single agent flags this as Critical. Agent 4 synthesizes: "SITE-022 compound risk — the enrollment slowdown looks like a referral pipeline problem, but is actually caused by operational burden from the CRA transition's query backlog. The binding constraint is data quality workload, not patient availability. Recommend CRA handover support and temporary data entry assistance."

**Supporting data — Chain 5 (Regional Cluster, 4 JPN Sites):**

| Table | Signal | What the agent finds |
|-------|--------|---------------------|
| `ecrf_entries` | Entry lag at SITE-103 | 5.3 days during Jan-Feb 2025 (vs 2.2 baseline) — flagged as anomaly |
| `ecrf_entries` | Entry lag at SITE-108/112/119 | 3.9d, 3.5d, 2.9d — each *below* individual alert thresholds |
| `sites` | Geographic proximity | All 4 sites are in Japan |
| `kri_snapshots` | `Entry Lag Median` KRI | SITE-103 hits Amber/Red; neighbors remain Green individually |

**Transformational insight enabled:** SITE-103's entry lag spike is flagged individually. But the mild degradation at 3 neighboring sites falls *below* individual alert thresholds. Agent 4 detects the regional cluster pattern — 4 JPN sites with simultaneous entry lag increases — and identifies the systemic root cause: a regional CRO IT migration, not 4 independent site problems. The intervention is CRO regional infrastructure escalation, not site-level remediation.

### 9.6 Conversational Intelligence — Data-Grounded Investigative Dialogue

**Solution capability:** Study teams ask questions in natural language and receive data-grounded narrative answers with follow-up capability.

**How every table contributes:**

The conversational interface enables queries that span any combination of tables. Examples and the tables they draw from:

| User Question | Tables Queried | Response Pattern |
|---------------|---------------|------------------|
| "Which sites are behind on enrollment?" | `enrollment_velocity`, `sites`, `screening_log` | Ranked list with binding constraint per site |
| "What's driving the query backlog at SITE-012?" | `queries`, `ecrf_entries`, `cra_assignments`, `data_corrections` | CRF page breakdown, temporal pattern, CRA history |
| "Show me sites with monitoring gaps" | `monitoring_visits`, `kri_snapshots`, `queries` | Gap sites with compounding risk from data quality |
| "Why did SITE-041 have consent withdrawals?" | `screening_log`, `kit_inventory`, `randomization_events`, `depot_shipments` | Supply chain root cause trace |
| "Compare screen failure patterns across Japanese sites" | `screening_log`, `screen_failure_reason_codes`, `sites` | SF code distribution by site with eligibility criteria mapping |
| "Is there a regional pattern in entry lag?" | `ecrf_entries`, `sites`, `kri_snapshots` | Country and site-cluster analysis with temporal overlay |
| "What's the overall study health?" | `kri_snapshots`, `enrollment_velocity`, `monitoring_visits`, `queries` | Multi-domain dashboard synthesis |

### 9.7 Summary — Data to Insight Mapping

| Solution Insight | Required Data Domains | Key Tables | Agent(s) |
|-----------------|----------------------|------------|----------|
| Query spike root cause (CRA transition, training gap, page-specific burden) | EDC + Config | `queries`, `ecrf_entries`, `cra_assignments`, `data_corrections` | Agent 1 |
| Hidden data quality debt during monitoring gaps | Monitoring + EDC | `monitoring_visits`, `queries` (absence of monitoring-triggered queries + age drift) | Agent 2 + Agent 1 |
| Enrollment binding constraint diagnosis (PI strictness, competing trial, referral pipeline) | Enrollment | `screening_log`, `screen_failure_reason_codes`, `enrollment_velocity` | Agent 3 |
| Supply-driven enrollment misattribution (stockout → consent withdrawal) | Enrollment + IRT | `screening_log`, `kit_inventory`, `randomization_events`, `depot_shipments` | Agent 3 (Phase 2 IRT) |
| Compound risk detection (CRA transition cascade, regional cluster) | All domains | All transactional tables + `sites`, `cra_assignments` | Agent 4 |
| Conversational Q&A with drill-down | All domains | All tables accessible via SQL tools | Conductor + all agents |

---

*Generated from `data_generators/models.py` and validated against the `clinops_intel` database. Data produced by `data_generators/run_all.py` with seed=42 for reproducibility.*
