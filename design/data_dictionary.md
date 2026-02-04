# Data Dictionary — Clinical Operations Intelligence Platform

**Database:** `clinops_intel` (PostgreSQL)
**Protocol:** NCT02264990 / M14-359 — Veliparib in Non-Squamous NSCLC
**Study Timeline:** 2024-03-01 to 2025-09-30 (18 months, ~82 weeks)
**Schema:** 38 CODM tables + 8 governance tables = 46 total
**ORM Definitions:** `data_generators/models.py` (CODM), `backend/models/governance.py` (governance)

---

## Table of Contents

1. [Schema Overview](#1-schema-overview)
2. [Study Configuration (7 tables)](#2-study-configuration-7-tables)
3. [Site & Staffing (3 tables)](#3-site--staffing-3-tables)
4. [Supply Chain (3 tables)](#4-supply-chain-3-tables)
5. [Enrollment & Screening (4 tables)](#5-enrollment--screening-4-tables)
6. [Clinical Data (3 tables)](#6-clinical-data-3-tables)
7. [Data Quality (3 tables)](#7-data-quality-3-tables)
8. [Operations (1 table)](#8-operations-1-table)
9. [Vendor Management (6 tables)](#9-vendor-management-6-tables)
10. [Financial (8 tables)](#10-financial-8-tables)
11. [Governance (8 tables)](#11-governance-8-tables)
12. [Cross-Table Relationships](#12-cross-table-relationships)
13. [Embedded Anomaly Sites](#13-embedded-anomaly-sites)

---

## 1. Schema Overview

The database implements the **Common Operational Data Model (CODM)** — a unified PostgreSQL schema that normalizes vendor-specific data feeds from clinical trial operational systems. CODM enables cross-vendor analysis that no single vendor's system can provide.

### Table Groups

| Group | Tables | Primary Production Source Systems | Agent Consumers |
|-------|--------|----------------------------------|-----------------|
| Study Configuration | 7 | Protocol Management, EDC, IRT/IWRS, CTMS | All agents (reference) |
| Site & Staffing | 3 | CTMS, Site Feasibility (Citeline, WCG) | All agents |
| Supply Chain | 3 | IRT/IWRS, Clinical Supply (Almac, Catalent, Marken) | enrollment_funnel, site_rescue |
| Enrollment & Screening | 4 | EDC, IRT/IWRS, CTMS | enrollment_funnel, site_rescue, clinical_trials_gov |
| Clinical Data | 3 | EDC (Rave, InForm, Vault CDMS) | data_quality, phantom_compliance |
| Data Quality | 3 | CTMS, RBQM (CluePoints), EDC | data_quality, phantom_compliance |
| Operations | 1 | CTMS | data_quality |
| Vendor Management | 6 | CTMS, Sponsor Vendor Management | vendor_performance |
| Financial | 8 | Sponsor Finance/ERP, CTMS, Vendor Invoicing | financial_intelligence |
| Governance | 8 | Platform-internal | All agents (output) |

### Production Source System Reference

| System Category | Representative Platforms | Data Delivered |
|----------------|------------------------|----------------|
| **EDC** (Electronic Data Capture) | Medidata Rave, Oracle InForm / Clinical One, Veeva Vault CDMS, Castor EDC | eCRF entries, queries, corrections, visit data, screening CRFs |
| **CTMS** (Clinical Trial Management System) | Veeva Vault CTMS, Oracle Siebel CTMS, Medidata Rave CTMS, Bio-Optronics Clinical Conductor | Site management, CRA assignments, monitoring visits, enrollment tracking, action items |
| **IRT / IWRS** (Interactive Response Technology) | Suvoda, Signant Health (RTSM), Medidata Rave RTSM, Oracle InForm IRT | Randomization, stratification, kit inventory, depot shipments, supply events |
| **RBQM** (Risk-Based Quality Management) | CluePoints, Veeva Vault QualityOne, TransCelerate RBQM tools | KRI computation, centralized statistical monitoring, risk signals |
| **Protocol Management** | Veeva Vault Clinical, Study Builder, USDM 4.0 exports | Study design, eligibility criteria, visit schedule, activities |
| **Supply Chain / Logistics** | Almac Group, Catalent, Fisher Clinical Services, Marken | Depot operations, shipment tracking, cold-chain compliance |
| **Sponsor Finance / ERP** | SAP, Oracle, internal finance systems | Budgets, invoices, change orders, payment milestones |
| **Vendor Management** | Sponsor procurement, CTMS vendor modules | Vendor master data, KPIs, milestones, issues |

---

## 2. Study Configuration (7 tables)

Populated from the USDM 4.0 Digital Protocol. Reference backbone for all transactional tables.

### 2.1 `study_config`

Global study parameters. Single row.

> **Sources:** CTMS study setup; Protocol Management system; ClinicalTrials.gov API.
> **Refresh:** Static — updated on protocol amendment only.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `study_id` | String(50) | Protocol identifier (`M14-359`) |
| `study_title` | String(500) | Full study title |
| `nct_number` | String(20) | ClinicalTrials.gov ID (`NCT02264990`) |
| `phase` | String(20) | Trial phase (`Phase 2`) |
| `target_enrollment` | Integer | Protocol enrollment target (`595`) |
| `planned_sites` | Integer | Number of planned sites (`150`) |
| `cycle_length_days` | Integer | Treatment cycle duration (`21`) |
| `max_cycles` | Integer | Maximum treatment cycles per subject (`6`) |
| `screening_window_days` | Integer | Allowed screening window (`28`) |
| `countries` | JSONB | Participating countries (`["USA","JPN","CAN","AUS","NZL"]`) |
| `study_start_date` | Date | First site activation date |

### 2.2 `study_arms`

Treatment arms with allocation ratios. 2 rows.

> **Sources:** IRT/IWRS randomization configuration.
> **Refresh:** Static.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `arm_code` | String(20) UNIQUE | Arm identifier (`ARM_A`, `ARM_B`) |
| `arm_name` | String(200) | Full arm name |
| `arm_type` | String(50) | `Experimental` or `Active Comparator` |
| `allocation_ratio` | Float | Randomization weight (both `0.5` for 1:1) |

### 2.3 `stratification_factors`

Randomization stratification factors. 2 rows.

> **Sources:** IRT/IWRS system; Statistical Analysis Plan (SAP).
> **Refresh:** Static.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `factor_name` | String(100) | Factor name (`Gender`, `ECOG`) |
| `factor_levels` | JSONB | Allowed levels (e.g., `["Male","Female"]`) |

### 2.4 `visit_schedule`

Protocol visit definitions from USDM Schedule of Activities. 10 rows.

> **Sources:** EDC study build (Rave Architect, InForm Designer); USDM Digital Protocol SOA export.
> **Refresh:** Static — updated on protocol amendment.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `visit_id` | String(20) UNIQUE | Encounter ID (`ENC-001` through `ENC-010`) |
| `visit_name` | String(100) | Human-readable name |
| `visit_type` | String(50) | `Screening`, `Treatment`, `Follow-up` |
| `timing_value` | Integer | Numeric timing component |
| `timing_unit` | String(20) | `days`, `weeks`, `cycles` |
| `timing_relative_to` | String(50) | Reference event (`Randomization`, `Prior Cycle`) |
| `window_early_bound` | Integer | Early visit window (days) |
| `window_late_bound` | Integer | Late visit window (days) |
| `recurrence_pattern` | String(50) | Recurrence descriptor |

### 2.5 `visit_activities`

Activities performed at each visit. ~80 rows.

> **Sources:** EDC study build (activity-to-visit mapping); USDM SOA export.
> **Refresh:** Static.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `visit_id` | String(20) | FK to `visit_schedule.visit_id` |
| `activity_id` | String(20) | Activity identifier |
| `activity_name` | String(200) | Activity description |
| `is_required` | Boolean | Whether mandatory at this visit |

### 2.6 `eligibility_criteria`

Inclusion and exclusion criteria. 25 rows (13 inclusion + 12 exclusion).

> **Sources:** Protocol document; USDM eligibility export; ClinicalTrials.gov API.
> **Refresh:** Static — updated on protocol amendment.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `criterion_id` | String(20) UNIQUE | ID (`INC_1`..`INC_13`, `EXC_1`..`EXC_12`) |
| `type` | String(20) | `Inclusion` or `Exclusion` |
| `original_text` | Text | Full criterion text |
| `short_label` | String(200) | Truncated label |

### 2.7 `screen_failure_reason_codes`

Screen failure code lookup. 15 rows.

> **Sources:** Sponsor-defined EDC codelist; mapped to eligibility criteria.
> **Refresh:** Static — may extend mid-study.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `reason_code` | String(30) UNIQUE | Code (e.g., `SF_ECOG`, `SF_HISTO`) |
| `description` | String(300) | Human-readable failure description |
| `criterion_id` | String(20) | Mapped eligibility criterion (NULL for non-criterion reasons) |
| `category` | String(50) | Grouping (`Performance Status`, `Histology`, `Lab Values`, etc.) |

---

## 3. Site & Staffing (3 tables)

### 3.1 `sites`

Investigator sites. 142 rows across 20 countries.

> **Sources:** CTMS site management; site feasibility data (Citeline TrialScope, WCG SiteIntel); IRT for per-site enrollment targets.
> **Refresh:** Weekly — new activations, status changes, target redistribution.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) UNIQUE | Site identifier (`SITE-001` through `SITE-157`) |
| `name` | String(200) | Facility name |
| `country` | String(3) | ISO-3166 alpha-3 |
| `city` | String(100) | City name |
| `site_type` | String(30) | `Academic` (35%), `Community` (40%), `Hospital` (25%) |
| `experience_level` | String(20) | `High` (30%), `Medium` (50%), `Low` (20%) |
| `activation_date` | Date | Site activation date |
| `target_enrollment` | Integer | Per-site enrollment target (3-6 subjects) |
| `anomaly_type` | String(50) | Demo-only: embedded anomaly label (NULL for normal sites) |

**Indexes:** `ix_sites_country` on `country`

### 3.2 `cra_assignments`

CRA-to-site assignments. ~180 rows (~30 sites have CRA transitions).

> **Sources:** CTMS monitoring module (Veeva Vault CTMS, Oracle Siebel CTMS).
> **Refresh:** Weekly — CRA reassignments are operationally significant signals.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `cra_id` | String(20) | CRA identifier |
| `site_id` | String(20) | FK to `sites.site_id` |
| `start_date` | Date | Assignment start |
| `end_date` | Date | Assignment end (NULL if current) |
| `is_current` | Boolean | Active assignment flag |

**Indexes:** `ix_cra_site` on `site_id`

### 3.3 `drug_kit_types`

Drug kit definitions by treatment arm. 4 rows.

> **Sources:** IRT/IWRS kit type configuration; Clinical Supply Management.
> **Refresh:** Static.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `kit_type_id` | String(20) UNIQUE | Kit identifier (`KIT_VEL`, `KIT_CARBO`, `KIT_PAC`, `KIT_STD`) |
| `kit_name` | String(200) | Full drug kit name |
| `arm_code` | String(20) | Associated treatment arm |
| `storage_conditions` | String(200) | Storage requirements (e.g., "2-8C") |
| `shelf_life_days` | Integer | Kit shelf life in days |

---

## 4. Supply Chain (3 tables)

### 4.1 `depots`

Regional drug supply depots. 8 rows.

> **Sources:** IRT/IWRS supply module; logistics providers (Almac, Catalent, Marken).
> **Refresh:** Static.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `depot_id` | String(20) UNIQUE | Depot identifier |
| `depot_name` | String(100) | Full depot name |
| `country` | String(3) | Country served |
| `city` | String(100) | Depot location |
| `standard_shipping_days` | Integer | Standard shipping time to sites (2-5 days) |

### 4.2 `kit_inventory`

Biweekly drug kit inventory snapshots per site. ~18,100 rows.

> **Sources:** IRT/IWRS inventory module (Suvoda, Signant RTSM) — single source of truth for site-level drug inventory.
> **Refresh:** Daily or event-driven. Biweekly snapshots sufficient for trend detection.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `kit_type_id` | String(20) | FK to `drug_kit_types.kit_type_id` |
| `snapshot_date` | Date | Inventory snapshot date |
| `quantity_on_hand` | Integer | Current kit quantity (0 during stockout) |
| `reorder_level` | Integer | Reorder trigger threshold (fixed at 3) |
| `is_below_reorder` | Boolean | TRUE if `quantity_on_hand <= reorder_level` |

**Indexes:** `ix_kit_site_date` on `(site_id, snapshot_date)`

### 4.3 `depot_shipments`

Drug shipments from depots to sites. ~1,700 rows.

> **Sources:** IRT/IWRS (initiation/tracking); logistics providers (execution, carrier tracking, delivery confirmation).
> **Refresh:** Daily.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `depot_id` | String(20) | FK to `depots.depot_id` |
| `site_id` | String(20) | FK to `sites.site_id` |
| `kit_type_id` | String(20) | FK to `drug_kit_types.kit_type_id` |
| `shipment_date` | Date | Date shipment left depot |
| `expected_arrival` | Date | Expected delivery date |
| `actual_arrival` | Date | Actual delivery date (NULL if In-Transit) |
| `kit_count` | Integer | Number of kits shipped (4-10) |
| `status` | String(20) | `Delivered` (~93%), `In-Transit` (~5%), `Delayed` (~2%) |
| `delay_reason` | String(200) | NULL for on-time deliveries |

**Indexes:** `ix_shipment_site` on `site_id`

---

## 5. Enrollment & Screening (4 tables)

### 5.1 `screening_log`

Individual screening events per subject. ~900 rows.

> **Sources:** EDC screening CRFs (primary); CTMS screening tracker; IRT screening log.
> **Refresh:** Daily — entered within 1-7 days of occurrence.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `subject_id` | String(30) UNIQUE | Subject identifier |
| `screening_date` | Date | Date of screening assessment |
| `outcome` | String(20) | `Passed`, `Failed`, or `Withdrawn` |
| `failure_reason_code` | String(30) | FK to `screen_failure_reason_codes.reason_code` (NULL for passed) |
| `failure_reason_narrative` | Text | Free-text narrative (quality varies by country/site) |

**Indexes:** `ix_screening_site`, `ix_screening_date`

**Key characteristics:** ~26% overall screen failure rate. Enrollment follows S-curve trajectory.

### 5.2 `randomization_log`

Subjects who passed screening and were randomized. 595 rows.

> **Sources:** IRT/IWRS system — authoritative source for arm assignment and stratification.
> **Refresh:** Daily or event-driven.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `subject_id` | String(30) UNIQUE | FK to `screening_log.subject_id` |
| `site_id` | String(20) | FK to `sites.site_id` |
| `randomization_date` | Date | Date of randomization (1-14 days post screening) |
| `arm_code` | String(20) | Treatment arm (`ARM_A` or `ARM_B`) |
| `stratum_gender` | String(10) | Stratification: `Male` (60%) / `Female` (40%) |
| `stratum_ecog` | String(5) | Stratification: `0` (45%) / `1` (55%) |

**Indexes:** `ix_rand_site` on `site_id`

### 5.3 `enrollment_velocity`

Weekly per-site enrollment aggregates. ~9,300 rows.

> **Sources:** Derived from `screening_log` and `randomization_log`. Also available from CTMS enrollment dashboard or CRO enrollment reports.
> **Refresh:** Weekly.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `week_start` | Date | Monday of reporting week |
| `week_number` | Integer | Week number since study start |
| `screened_count` | Integer | Subjects screened this week |
| `screen_failed_count` | Integer | Subjects who failed screening |
| `randomized_count` | Integer | Subjects randomized this week |
| `cumulative_screened` | Integer | Running total screened |
| `cumulative_randomized` | Integer | Running total randomized |
| `target_cumulative` | Integer | Expected cumulative per linear ramp |

**Indexes:** `ix_velocity_site_week` on `(site_id, week_number)`

### 5.4 `randomization_events`

IRT system events for each randomization attempt. 595 rows.

> **Sources:** IRT/IWRS event log (Suvoda, Signant RTSM).
> **Refresh:** Daily or event-driven.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `subject_id` | String(30) | FK to `randomization_log.subject_id` |
| `site_id` | String(20) | FK to `sites.site_id` |
| `event_date` | Date | Date of randomization attempt |
| `event_type` | String(20) | `Success` (~94%), `Delay` (~5%), `Failure` (~1%) |
| `delay_reason` | String(100) | NULL for Success. Values: `Kit Stockout`, `System Issue`, `Stratification Error`, `Kit Labeling Error` |
| `delay_duration_hours` | Integer | Duration of delay (0 for Success) |

**Indexes:** `ix_randevt_site` on `site_id`

---

## 6. Clinical Data (3 tables)

### 6.1 `subject_visits`

Individual treatment visits per randomized subject. ~5,300 rows.

> **Sources:** EDC visit tracking module.
> **Refresh:** Daily.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `subject_id` | String(30) | FK to `randomization_log.subject_id` |
| `visit_id` | String(20) | FK to `visit_schedule.visit_id` |
| `cycle_number` | Integer | Treatment cycle (1-6, NULL for non-treatment visits) |
| `planned_date` | Date | Protocol-scheduled visit date |
| `actual_date` | Date | Actual visit date (NULL if missed) |
| `visit_status` | String(20) | `Completed` (~98%) or `Missed` (~2%) |

**Indexes:** `ix_sv_subject`, `ix_sv_visit`

### 6.2 `ecrf_entries`

eCRF page-level operational telemetry. ~31,200 rows.

> **Sources:** EDC operational metadata / audit trail (Rave, InForm, Vault CDMS). Not clinical data itself — operational telemetry about data entry timing and completeness.
> **Refresh:** Daily.
> **Integration note:** Most schema-variable table across EDC platforms. Normalization of page naming, timestamp extraction, and completeness calculation is the primary integration effort.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `subject_visit_id` | Integer | FK to `subject_visits.id` |
| `subject_id` | String(30) | FK to `randomization_log.subject_id` |
| `site_id` | String(20) | FK to `sites.site_id` |
| `crf_page_name` | String(50) | CRF page name |
| `visit_date` | Date | Date the clinical visit occurred |
| `entry_date` | Date | Date data was entered into EDC |
| `entry_lag_days` | Integer | Calendar days between visit and entry |
| `completeness_pct` | Float | Percentage of required fields completed |
| `has_missing_critical` | Boolean | TRUE if completeness < 85% |
| `missing_field_count` | Integer | Number of missing fields |

**Indexes:** `ix_ecrf_site`, `ix_ecrf_subject`

### 6.3 `queries`

Data queries raised against eCRF entries. ~22,900 rows.

> **Sources:** EDC query management module (Rave Query Management, InForm Discrepancy Management, Vault CDMS Query Module). Raised by auto-validation, manual review, or monitoring visits.
> **Refresh:** Daily.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `subject_id` | String(30) | FK to `randomization_log.subject_id` |
| `crf_page_name` | String(50) | CRF page the query relates to |
| `query_type` | String(30) | `Missing Data`, `Discrepancy`, `Out of Range`, `Protocol Deviation`, `Logical Inconsistency` |
| `open_date` | Date | Date query opened |
| `response_date` | Date | Date response provided (NULL if Open) |
| `close_date` | Date | Date query closed (NULL if Open/Answered) |
| `status` | String(20) | `Open`, `Answered`, `Closed` |
| `age_days` | Integer | Days the query has been open |
| `priority` | String(10) | `High` (15%), `Medium` (50%), `Low` (35%) |
| `triggered_by` | String(50) | `Auto-validation` (45%), `Manual Review` (35%), `Edit Check` (20%), `Monitoring Visit` |

**Indexes:** `ix_queries_site`, `ix_queries_subject`, `ix_queries_open`

---

## 7. Data Quality (3 tables)

### 7.1 `data_corrections`

Field-level data corrections. ~5,700 rows.

> **Sources:** EDC audit trail (GxP-regulated per 21 CFR Part 11 / EU Annex 11).
> **Refresh:** Daily.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `subject_id` | String(30) | FK to `randomization_log.subject_id` |
| `crf_page_name` | String(50) | CRF page corrected |
| `field_name` | String(100) | Specific field corrected |
| `old_value` | String(200) | Previous value |
| `new_value` | String(200) | Corrected value |
| `correction_date` | Date | Date correction was made |
| `triggered_by_query_id` | Integer | ID of triggering query (NULL if unprompted) |

**Indexes:** `ix_corrections_site` on `site_id`

### 7.2 `monitoring_visits`

CRA monitoring visits to sites. ~1,230 rows.

> **Sources:** CTMS monitoring module; monitoring visit reports (MVRs) via eTMF.
> **Refresh:** Weekly — CRAs complete visit reports within 5-10 business days.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `cra_id` | String(20) | FK to `cra_assignments.cra_id` |
| `planned_date` | Date | Scheduled visit date (every 6-8 weeks) |
| `actual_date` | Date | Actual visit date (NULL if missed) |
| `visit_type` | String(20) | `On-Site` (~67%) or `Remote` (~33%) |
| `findings_count` | Integer | Total findings during visit |
| `critical_findings` | Integer | Critical findings subset |
| `queries_generated` | Integer | Queries triggered by this visit |
| `days_overdue` | Integer | Days between planned and actual date |
| `status` | String(20) | `Completed` or `Missed` |

**Indexes:** `ix_monvisit_site` on `site_id`

### 7.3 `kri_snapshots`

Monthly Key Risk Indicator snapshots per site. ~21,500 rows.

> **Sources:** RBQM platform (CluePoints, Vault QualityOne) or CODM-computed from underlying data using 60-day trailing windows.
> **Refresh:** Monthly — aligned with risk governance review cycles.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `snapshot_date` | Date | Monthly snapshot date |
| `kri_name` | String(100) | KRI metric name |
| `kri_value` | Float | Computed KRI value |
| `amber_threshold` | Float | Warning threshold |
| `red_threshold` | Float | Critical threshold |
| `status` | String(10) | `Green`, `Amber`, or `Red` |

**Indexes:** `ix_kri_site_date` on `(site_id, snapshot_date)`

**KRI definitions:**

| KRI Name | Unit | Amber | Red | Direction |
|----------|------|-------|-----|-----------|
| Query Rate | queries/entry | 0.8 | 1.5 | Higher is worse |
| Open Query Age | days | 14 | 28 | Higher is worse |
| Entry Lag Median | days | 5 | 12 | Higher is worse |
| Screen Failure Rate | % | 38 | 50 | Higher is worse |
| Enrollment vs Target | % | 60 | 40 | Lower is worse |
| Monitoring Visit Compliance | % | 80 | 60 | Lower is worse |
| Critical Findings Rate | per visit | 0.8 | 1.5 | Higher is worse |
| Data Completeness | % | 88 | 75 | Lower is worse |
| Correction Rate | % | 8 | 15 | Higher is worse |
| Protocol Deviation Rate | per visit | 0.5 | 1.2 | Higher is worse |

---

## 8. Operations (1 table)

### 8.1 `overdue_actions`

Follow-up actions from monitoring visits. ~310 rows.

> **Sources:** CTMS action tracking module; CAPA systems.
> **Refresh:** Weekly.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `monitoring_visit_id` | Integer | FK to `monitoring_visits.id` |
| `action_description` | Text | Description of required action |
| `category` | String(50) | `Data Quality`, `Safety Reporting`, `IP Management`, `Regulatory`, `Documentation` |
| `due_date` | Date | Action due date |
| `completion_date` | Date | Date completed (NULL if open/overdue) |
| `status` | String(20) | `Completed` (~95%), `Open` (~4%), `Overdue` (~1%) |

**Indexes:** `ix_overdue_site` on `site_id`

---

## 9. Vendor Management (6 tables)

These tables support the multi-CRO operating model where a Global CRO manages most geographies while Regional CROs handle specific countries, and specialized vendors each own their data domain.

### 9.1 `vendors`

Vendor master data. A typical Phase III study has 6-10 vendors.

> **Sources:** Sponsor procurement / vendor management; CTMS vendor modules.
> **Refresh:** As contracts change.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `vendor_id` | String(20) UNIQUE | Vendor identifier |
| `name` | String(200) | Vendor name |
| `vendor_type` | String(50) | `Global CRO`, `Regional CRO`, `Central Lab`, `Imaging`, `ePRO/EDC`, `IRT/IWRS`, `Safety/PV`, `Patient Recruitment` |
| `country_hq` | String(3) | HQ country |
| `contract_value` | Float | Total contract value |
| `status` | String(20) | `Active`, `On Watch`, `Terminated` |

### 9.2 `vendor_scope`

Vendor scope of work — services, countries, deliverables.

> **Sources:** Contract scope documents; CTMS vendor configuration.
> **Refresh:** On contract amendment.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `vendor_id` | String(20) | FK to `vendors.vendor_id` |
| `scope_type` | String(50) | Service type (`Monitoring`, `Data Management`, `Lab`, etc.) |
| `countries` | JSONB | List of country codes covered |
| `deliverables` | JSONB | List of deliverable descriptions |

**Indexes:** `ix_vendor_scope_vendor` on `vendor_id`

### 9.3 `vendor_site_assignments`

**Multi-vendor-per-site junction table.** Architectural keystone for attributing operational issues to specific vendors.

> **Sources:** CTMS vendor-site mapping; CRO assignment records.
> **Refresh:** Weekly — reassignments are operationally significant.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `vendor_id` | String(20) | FK to `vendors.vendor_id` |
| `site_id` | String(20) | FK to `sites.site_id` |
| `role` | String(50) | `Primary Monitor`, `Data Manager`, `Lab Coordinator`, `Imaging Reviewer`, `EDC Support`, `IRT Manager`, `PV Specialist`, `Recruitment Lead` |
| `is_active` | Boolean | Active assignment flag |

**Indexes:** `ix_vsa_vendor`, `ix_vsa_site`

### 9.4 `vendor_kpis`

Monthly vendor KPI snapshots.

> **Sources:** CRO performance reports; vendor governance meetings; CTMS KPI dashboards.
> **Refresh:** Monthly.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `vendor_id` | String(20) | FK to `vendors.vendor_id` |
| `snapshot_date` | Date | KPI measurement date |
| `kpi_name` | String(100) | KPI metric name |
| `value` | Float | Measured value |
| `target` | Float | Target value |
| `status` | String(10) | `Green`, `Amber`, `Red` |

**Indexes:** `ix_vkpi_vendor_date` on `(vendor_id, snapshot_date)`

### 9.5 `vendor_milestones`

Vendor milestone tracking (planned vs actual).

> **Sources:** Contract milestone schedules; CTMS milestone tracking; CRO status reports.
> **Refresh:** Weekly.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `vendor_id` | String(20) | FK to `vendors.vendor_id` |
| `milestone_name` | String(200) | Milestone description |
| `planned_date` | Date | Planned completion date |
| `actual_date` | Date | Actual completion date (NULL if not completed) |
| `status` | String(20) | `Completed`, `On Track`, `At Risk`, `Delayed` |
| `delay_days` | Integer | Days delayed (0 if on time) |

**Indexes:** `ix_vms_vendor` on `vendor_id`

### 9.6 `vendor_issues`

Vendor issue log.

> **Sources:** Vendor governance meetings; CAPA systems; CRO quality reports.
> **Refresh:** Weekly.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `vendor_id` | String(20) | FK to `vendors.vendor_id` |
| `category` | String(50) | `Quality`, `Timeliness`, `Staffing`, `Communication`, `Compliance` |
| `severity` | String(20) | `Critical`, `Major`, `Minor` |
| `description` | Text | Issue description |
| `open_date` | Date | Date issue opened |
| `resolution_date` | Date | Date resolved (NULL if open) |
| `status` | String(20) | `Open`, `In Progress`, `Resolved` |
| `resolution` | Text | Resolution description |

**Indexes:** `ix_vi_vendor` on `vendor_id`

---

## 10. Financial (8 tables)

### 10.1 `study_budget`

Study-level budget.

> **Sources:** Sponsor Finance/ERP; study financial plan.
> **Refresh:** On budget amendment.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `budget_version` | String(20) | Version identifier (`v1.0`, `current`) |
| `total_budget_usd` | Float | Total budget |
| `service_fees` | Float | Service fee component |
| `pass_through` | Float | Pass-through costs |
| `contingency` | Float | Contingency reserve |
| `effective_date` | Date | Budget version effective date |
| `status` | String(20) | `Active` or `Superseded` |

### 10.2 `budget_categories`

Budget category hierarchy.

> **Sources:** Sponsor Finance; TransCelerate budget template.
> **Refresh:** Static.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `category_code` | String(20) UNIQUE | Category identifier |
| `name` | String(200) | Category name |
| `parent_code` | String(20) | Parent category (NULL for top-level) |
| `cost_type` | String(20) | `Service Fee`, `Pass-Through`, `Contingency` |

### 10.3 `budget_line_items`

Budget line items per vendor, country, and category.

> **Sources:** Sponsor Finance/ERP; vendor contract budgets; monthly financial close.
> **Refresh:** Monthly.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `category_code` | String(20) | FK to `budget_categories.category_code` |
| `country` | String(3) | Country scope |
| `vendor_id` | String(20) | FK to `vendors.vendor_id` |
| `unit_type` | String(50) | `Per Site`, `Per Patient`, `Per Visit`, `Lump Sum` |
| `unit_cost` | Float | Cost per unit |
| `planned_units` | Integer | Planned quantity |
| `actual_units` | Integer | Actual quantity to date |
| `planned_amount` | Float | Planned total |
| `actual_amount` | Float | Actual spend to date |
| `forecast_amount` | Float | Forecast at completion |

**Indexes:** `ix_bli_category`, `ix_bli_vendor`

### 10.4 `financial_snapshots`

Monthly financial snapshots.

> **Sources:** Sponsor Finance monthly close; ERP reports.
> **Refresh:** Monthly.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `snapshot_month` | Date | Monthly period |
| `planned_cumulative` | Float | Planned cumulative spend |
| `actual_cumulative` | Float | Actual cumulative spend |
| `forecast_cumulative` | Float | Forecast cumulative |
| `monthly_planned` | Float | Planned for this month |
| `monthly_actual` | Float | Actual for this month |
| `burn_rate` | Float | Monthly burn rate |
| `variance_pct` | Float | Variance percentage |

**Indexes:** `ix_fs_month` on `snapshot_month`

### 10.5 `invoices`

Vendor invoices.

> **Sources:** Sponsor Accounts Payable; vendor invoicing systems.
> **Refresh:** Monthly.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `vendor_id` | String(20) | FK to `vendors.vendor_id` |
| `invoice_number` | String(50) | Invoice reference |
| `amount` | Float | Invoice amount |
| `category_code` | String(20) | Budget category |
| `invoice_date` | Date | Invoice date |
| `due_date` | Date | Payment due date |
| `status` | String(20) | `Submitted`, `Approved`, `Paid`, `Disputed` |

**Indexes:** `ix_inv_vendor` on `vendor_id`

### 10.6 `payment_milestones`

Milestone-based payments.

> **Sources:** Vendor contracts; Sponsor Finance.
> **Refresh:** On milestone trigger.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `vendor_id` | String(20) | FK to `vendors.vendor_id` |
| `milestone_name` | String(200) | Milestone description |
| `trigger_condition` | Text | Trigger condition text |
| `planned_amount` | Float | Planned payment |
| `actual_amount` | Float | Actual payment |
| `status` | String(20) | `Pending`, `Triggered`, `Paid` |

**Indexes:** `ix_pm_vendor` on `vendor_id`

### 10.7 `change_orders`

Contract change orders. Leading indicator of scope creep.

> **Sources:** Vendor contracts; sponsor change control process.
> **Refresh:** As submitted/approved.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `vendor_id` | String(20) | FK to `vendors.vendor_id` |
| `change_order_number` | String(20) | CO reference number |
| `category` | String(50) | `Scope Increase`, `Timeline Extension`, `Rate Change` |
| `amount` | Float | Change order amount |
| `timeline_impact_days` | Integer | Timeline impact in days |
| `description` | Text | Change description |
| `status` | String(20) | `Proposed`, `Approved`, `Rejected` |
| `submitted_date` | Date | Submission date |
| `approved_date` | Date | Approval date (NULL if pending/rejected) |

**Indexes:** `ix_co_vendor` on `vendor_id`

### 10.8 `site_financial_metrics`

Per-site cost metrics.

> **Sources:** Derived from budget line items, enrollment data, and invoices.
> **Refresh:** Monthly.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `site_id` | String(20) | FK to `sites.site_id` |
| `snapshot_date` | Date | Metrics as-of date |
| `cost_to_date` | Float | Total site cost to date |
| `cost_per_patient_screened` | Float | Cost efficiency per screened patient |
| `cost_per_patient_randomized` | Float | Cost efficiency per randomized patient |
| `planned_cost_to_date` | Float | Planned cost to date |
| `variance_pct` | Float | Variance from plan (%) |

**Indexes:** `ix_sfm_site` on `site_id`

---

## 11. Governance (8 tables)

Defined in `backend/models/governance.py`. These tables record platform operations, agent outputs, and alert management.

### 11.1 `audit_trail`

Timestamped action log for all system events.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `timestamp` | DateTime | Event timestamp (UTC) |
| `user_id` | String(100) | User or system actor |
| `action` | String(100) | Action performed |
| `entity_type` | String(50) | Affected entity type |
| `entity_id` | String(100) | Affected entity ID |
| `detail` | JSONB | Action details |

### 11.2 `agent_findings`

Persisted agent findings with full reasoning traces.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `agent_id` | String(30) | Agent that produced the finding |
| `finding_type` | String(50) | Finding classification |
| `severity` | String(20) | Finding severity |
| `site_id` | String(20) | Affected site (if site-specific) |
| `summary` | Text | Finding summary |
| `detail` | JSONB | Structured finding detail |
| `data_signals` | JSONB | Raw data signals supporting finding |
| `reasoning_trace` | JSONB | Full PRPA reasoning trace |
| `confidence` | Float | Agent confidence score |
| `created_at` | DateTime | Finding creation timestamp |

**Indexes:** `ix_findings_agent`, `ix_findings_site`

### 11.3 `alert_log`

Alerts generated from findings. Lifecycle: `open` → `acknowledged` → `resolved`.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `finding_id` | Integer | FK to `agent_findings.id` |
| `agent_id` | String(30) | Source agent |
| `severity` | String(20) | Alert severity |
| `site_id` | String(20) | Affected site |
| `title` | String(300) | Alert title |
| `description` | Text | Alert description |
| `status` | String(20) | `open`, `acknowledged`, `suppressed`, `resolved` |
| `suppressed` | Boolean | Whether suppressed by rule |
| `suppression_rule_id` | Integer | FK to `suppression_rules.id` |
| `acknowledged_by` | String(100) | User who acknowledged |
| `acknowledged_at` | DateTime | Acknowledgment timestamp |
| `created_at` | DateTime | Alert creation timestamp |

**Indexes:** `ix_alert_status`, `ix_alert_site`

### 11.4 `conversational_interactions`

Query history with routing, agent responses, and synthesis results.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `query_id` | String(50) UNIQUE | Query identifier |
| `session_id` | String(50) | Session identifier |
| `parent_query_id` | String(50) | Parent query for follow-ups |
| `user_query` | Text | Original user query |
| `routed_agents` | JSONB | Agents selected by conductor |
| `agent_responses` | JSONB | Per-agent response data |
| `synthesized_response` | Text | Cross-agent synthesized response |
| `synthesis_data` | JSONB | Full synthesis structure |
| `status` | String(20) | `pending`, `processing`, `completed`, `failed` |
| `created_at` | DateTime | Query timestamp |
| `completed_at` | DateTime | Completion timestamp |

**Indexes:** `ix_interaction_session`, `ix_interaction_status`

### 11.5 `alert_thresholds`

Configurable per-agent metric thresholds for alert generation.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `agent_id` | String(30) | Agent ID |
| `metric_name` | String(100) | Metric being thresholded |
| `warning_threshold` | Float | Warning level |
| `critical_threshold` | Float | Critical level |
| `is_active` | Boolean | Whether threshold is active |
| `updated_at` | DateTime | Last update timestamp |

### 11.6 `suppression_rules`

Alert suppression rules to prevent alert fatigue for known issues.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `agent_id` | String(30) | Scoped to agent (NULL = all agents) |
| `site_id` | String(20) | Scoped to site (NULL = all sites) |
| `finding_type` | String(50) | Finding type to suppress |
| `reason` | Text | Suppression justification |
| `created_by` | String(100) | Rule creator |
| `created_at` | DateTime | Creation timestamp |
| `expires_at` | DateTime | Expiration timestamp |
| `is_active` | Boolean | Whether rule is active |

### 11.7 `agent_parameters`

Runtime-configurable agent parameters.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `agent_id` | String(30) | Agent ID |
| `parameter_name` | String(100) | Parameter name |
| `parameter_value` | JSONB | Parameter value |
| `updated_at` | DateTime | Last update timestamp |

### 11.8 `cache_entries`

Persistent binary cache (namespace-scoped).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `namespace` | String(50) | Cache namespace |
| `cache_key` | String(64) | Cache key |
| `value` | LargeBinary | Cached value |
| `created_at` | DateTime | Entry creation timestamp |

**Constraints:** Unique on `(namespace, cache_key)`
**Indexes:** `ix_cache_namespace` on `namespace`

---

## 12. Cross-Table Relationships

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
    ├── depot_shipments (site_id)                      │
    ├── vendor_site_assignments (site_id) ◄────────────┤
    ├── site_financial_metrics (site_id)               │
    └── agent_findings (site_id)                       │
                                                       │
vendors (vendor_id)                                    │
    ├── vendor_scope (vendor_id)                       │
    ├── vendor_site_assignments (vendor_id) ───────────┘
    ├── vendor_kpis (vendor_id)
    ├── vendor_milestones (vendor_id)
    ├── vendor_issues (vendor_id)
    ├── budget_line_items (vendor_id)
    ├── invoices (vendor_id)
    ├── change_orders (vendor_id)
    └── payment_milestones (vendor_id)

depots (depot_id)
    └── depot_shipments (depot_id)

drug_kit_types (kit_type_id)
    ├── kit_inventory (kit_type_id)
    └── depot_shipments (kit_type_id)

agent_findings (id)
    └── alert_log (finding_id)
         └── suppression_rules (id → suppression_rule_id)
```

**Subject journey traceability:** `screening_log` → `randomization_log` → `subject_visits` → `ecrf_entries` → `queries` → `data_corrections` → `randomization_events`

**Vendor attribution path:** `sites` → `vendor_site_assignments` → `vendors` — enables attributing any site-level operational signal to the responsible vendor by role.

---

## 13. Embedded Anomaly Sites

13 sites have embedded anomaly patterns for agent detection testing.

| Site | Country | Anomaly Type | Key Signal |
|------|---------|--------------|------------|
| SITE-012 | USA | High query burden | 2.5x query rate, 12% correction rate |
| SITE-045 | USA | High query burden | 2x rate on Lab Results + Drug Accountability |
| SITE-078 | CAN | High query burden | 2.2x rate, staff turnover pattern |
| SITE-031 | JPN | Enrollment stall | 48% screen failure rate, SF_ECOG/SF_SMOKING 3x overrepresented |
| SITE-055 | USA | Enrollment stall | Volume drops 60% after week 20 (competing trial) |
| SITE-089 | AUS | Enrollment stall | 45% failure rate, 50% screening rate reduction |
| SITE-022 | USA | Entry lag spike | CRA transition Sep 2024, +7 days for 6 weeks |
| SITE-067 | CAN | Entry lag spike | Coordinator leave Nov 2024, +5 days for 4 weeks |
| SITE-103 | JPN | Entry lag spike | IT migration Jan 2025, +6 days for 5 weeks |
| SITE-041 | NZL | Supply constraint | 2 stockout episodes: customs hold + depot delay |
| SITE-115 | AUS | Supply constraint | 1 stockout episode (weather delay) |
| SITE-033 | USA | Monitoring gap | 4 missed visits Oct-Mar, CRA reassignment |
| SITE-098 | JPN | Monitoring gap | 2 missed visits, travel restrictions |

Regional cluster (Chain 5): SITE-108, SITE-112, SITE-119 (JPN) — +2-3 days entry lag during Jan-Feb 2025.

---

*Generated from `data_generators/models.py` and `backend/models/governance.py`. Data produced by `data_generators/run_all.py` with seed=42 for reproducibility.*
