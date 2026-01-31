"""Generate static/config tables: study_config, arms, strat factors, visits,
activities, eligibility criteria, screen_failure_codes, sites, CRAs, kits, depots."""

from datetime import date, timedelta

from numpy.random import Generator
from sqlalchemy.orm import Session

from data_generators.anomaly_profiles import ANOMALY_PROFILES, REGIONAL_CLUSTER_SITES
from data_generators.config import STUDY_START
from data_generators.models import (
    CRAAssignment, Depot, DrugKitType, EligibilityCriterion,
    ScreenFailureReasonCode, Site, StratificationFactor, StudyArm,
    StudyConfig, VisitActivity, VisitSchedule,
)
from data_generators.protocol_reader import ProtocolContext

# ── Country → code mapping ────────────────────────────────────────────────────
_COUNTRY_MAP = {"USA": "USA", "Japan": "JPN", "Australia": "AUS", "New Zealand": "NZL", "Canada": "CAN"}

# ── City pools by country ─────────────────────────────────────────────────────
_CITIES: dict[str, list[str]] = {
    "USA": [
        "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
        "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville",
        "Fort Worth", "Columbus", "Indianapolis", "Charlotte", "San Francisco",
        "Seattle", "Denver", "Nashville", "Baltimore", "Boston", "Memphis",
        "Louisville", "Portland", "Oklahoma City", "Las Vegas", "Milwaukee",
        "Albuquerque", "Tucson", "Fresno", "Sacramento", "Atlanta", "Kansas City",
        "Miami", "Raleigh", "Omaha", "Minneapolis", "Cleveland", "Tampa",
    ],
    "JPN": [
        "Tokyo", "Osaka", "Nagoya", "Yokohama", "Sapporo", "Kobe", "Kyoto",
        "Fukuoka", "Kawasaki", "Hiroshima", "Sendai", "Kitakyushu", "Chiba",
        "Sakai", "Niigata",
    ],
    "CAN": [
        "Toronto", "Montreal", "Vancouver", "Calgary", "Edmonton", "Ottawa",
        "Winnipeg", "Quebec City", "Hamilton", "Kitchener",
    ],
    "AUS": [
        "Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Gold Coast",
        "Canberra", "Newcastle", "Hobart", "Darwin",
    ],
    "NZL": [
        "Auckland", "Wellington", "Christchurch", "Hamilton", "Tauranga",
        "Dunedin", "Palmerston North", "Napier", "Nelson", "Rotorua",
    ],
}

# ── Site activation waves ─────────────────────────────────────────────────────
# (country, count, wave_month_offset_start, wave_month_offset_end)
_WAVES = [
    ("USA", 40, 0, 3),
    ("USA", 25, 3, 5),
    ("JPN", 15, 3, 5),
    ("CAN", 10, 5, 7),
    ("JPN", 15, 5, 7),
    ("USA", 10, 5, 7),
    ("AUS", 10, 7, 9),
    ("NZL", 5, 7, 9),
    ("CAN", 10, 7, 9),
    ("AUS", 5, 9, 11),
    ("NZL", 5, 9, 11),
]

# ── Screen failure reason code definitions ────────────────────────────────────
_SF_CODES = [
    ("SF_ECOG", "ECOG performance status ≥2", "INC_6", "Performance Status"),
    ("SF_HISTO", "Squamous histology", "EXC_1", "Histology"),
    ("SF_ORGAN", "Inadequate organ function", "INC_6", "Lab Values"),
    ("SF_PRIOR_CHEMO", "Prior systemic chemotherapy for metastatic disease", "INC_12", "Prior Therapy"),
    ("SF_SMOKING", "Insufficient smoking history (<20 pack-years)", "INC_5", "Smoking Status"),
    ("SF_BRAIN_METS", "Untreated brain metastases", "EXC_5", "CNS Disease"),
    ("SF_CONSENT", "Consent withdrawn during screening", None, "Consent"),
    ("SF_NEUROPATHY", "Peripheral neuropathy ≥ grade 2", "EXC_3", "Neuropathy"),
    ("SF_CARDIAC", "Significant cardiac risk", "EXC_7", "Cardiac"),
    ("SF_EGFR_ALK", "EGFR/ALK positive without prior targeted therapy", "INC_11", "Molecular"),
    ("SF_MEASURABLE", "No measurable disease per RECIST 1.1", "INC_13", "Measurable Disease"),
    ("SF_AGE", "Age below 18 years", "INC_1", "Demographics"),
    ("SF_OTHER", "Other exclusion criteria", None, "Other"),
    ("SF_HEPATIC", "Hepatic impairment", "EXC_9", "Lab Values"),
    ("SF_RENAL", "Renal impairment", "EXC_10", "Lab Values"),
]


def generate_static_config(
    session: Session, ctx: ProtocolContext, rng: Generator
) -> dict[str, int]:
    """Populate all static/config tables. Returns row counts."""
    counts: dict[str, int] = {}

    # 1. study_config
    sc = StudyConfig(
        study_id=ctx.study_id,
        nct_number=ctx.nct_number,
        phase=ctx.phase,
        target_enrollment=ctx.target_enrollment,
        planned_sites=ctx.planned_sites,
        cycle_length_days=ctx.cycle_length_days,
        max_cycles=ctx.max_cycles,
        screening_window_days=ctx.screening_window_days,
        countries=[_COUNTRY_MAP.get(c, c) for c in ctx.countries],
        study_start_date=STUDY_START,
    )
    session.add(sc)
    counts["study_config"] = 1

    # 2. study_arms
    arms_data = [
        ("ARM_A", "Veliparib + Carboplatin + Paclitaxel", "Experimental", 0.5),
        ("ARM_B", "Investigator's Choice Standard Chemotherapy", "Active Comparator", 0.5),
    ]
    for code, name, atype, ratio in arms_data:
        session.add(StudyArm(arm_code=code, arm_name=name, arm_type=atype, allocation_ratio=ratio))
    counts["study_arms"] = 2

    # 3. stratification_factors
    strat_data = [
        ("Gender", ["Male", "Female"]),
        ("ECOG", ["0", "1"]),
    ]
    for fname, levels in strat_data:
        session.add(StratificationFactor(factor_name=fname, factor_levels=levels))
    counts["stratification_factors"] = 2

    # 4. visit_schedule
    for v in ctx.visits:
        session.add(VisitSchedule(
            visit_id=v.visit_id,
            visit_name=v.name,
            visit_type=v.visit_type,
            timing_value=v.timing_value,
            timing_unit=v.timing_unit,
            timing_relative_to=v.timing_relative_to,
            window_early_bound=v.window_early,
            window_late_bound=v.window_late,
            recurrence_pattern=v.recurrence_pattern,
        ))
    counts["visit_schedule"] = len(ctx.visits)

    # 5. visit_activities (from scheduled instances)
    for si in ctx.scheduled_instances:
        session.add(VisitActivity(
            visit_id=si.visit_id,
            activity_id=si.activity_id,
            activity_name=si.activity_name,
            is_required=si.is_required,
        ))
    counts["visit_activities"] = len(ctx.scheduled_instances)

    # 6. eligibility_criteria
    all_criteria = ctx.inclusion_criteria + ctx.exclusion_criteria
    for c in all_criteria:
        short = c.original_text[:200] if len(c.original_text) > 200 else c.original_text
        session.add(EligibilityCriterion(
            criterion_id=c.criterion_id,
            type=c.type,
            original_text=c.original_text,
            short_label=short,
        ))
    counts["eligibility_criteria"] = len(all_criteria)

    # 7. screen_failure_reason_codes
    for code, desc, crit_id, cat in _SF_CODES:
        session.add(ScreenFailureReasonCode(
            reason_code=code, description=desc, criterion_id=crit_id, category=cat,
        ))
    counts["screen_failure_reason_codes"] = len(_SF_CODES)

    # 8. sites (150)
    all_anomaly_sites = set(ANOMALY_PROFILES.keys()) | set(REGIONAL_CLUSTER_SITES.keys())
    sites = _generate_sites(rng, all_anomaly_sites)
    for s in sites:
        session.add(s)
    counts["sites"] = len(sites)

    # 9. cra_assignments (~180)
    cras = _generate_cra_assignments(rng, sites)
    for c in cras:
        session.add(c)
    counts["cra_assignments"] = len(cras)

    # 10a. drug_kit_types
    kits = [
        DrugKitType(kit_type_id="KIT_VEL", kit_name="Veliparib 120mg BID Tablets", arm_code="ARM_A",
                    storage_conditions="15-25°C", shelf_life_days=365),
        DrugKitType(kit_type_id="KIT_CARBO", kit_name="Carboplatin IV Solution", arm_code="ARM_A",
                    storage_conditions="2-8°C", shelf_life_days=180),
        DrugKitType(kit_type_id="KIT_PAC", kit_name="Paclitaxel IV Solution", arm_code="ARM_A",
                    storage_conditions="15-25°C", shelf_life_days=365),
        DrugKitType(kit_type_id="KIT_STD", kit_name="Standard Chemotherapy Kit", arm_code="ARM_B",
                    storage_conditions="2-25°C", shelf_life_days=270),
    ]
    for k in kits:
        session.add(k)
    counts["drug_kit_types"] = len(kits)

    # 10b. depots
    depots = [
        Depot(depot_id="DEPOT_US", depot_name="US Central Depot", country="USA", city="Indianapolis", standard_shipping_days=3),
        Depot(depot_id="DEPOT_JP", depot_name="Japan Depot", country="JPN", city="Tokyo", standard_shipping_days=2),
        Depot(depot_id="DEPOT_CA", depot_name="Canada Depot", country="CAN", city="Toronto", standard_shipping_days=3),
        Depot(depot_id="DEPOT_AU", depot_name="Australia Depot", country="AUS", city="Melbourne", standard_shipping_days=4),
        Depot(depot_id="DEPOT_NZ", depot_name="New Zealand Depot", country="NZL", city="Auckland", standard_shipping_days=5),
    ]
    for d in depots:
        session.add(d)
    counts["depots"] = len(depots)

    session.flush()
    return counts


def _generate_sites(rng: Generator, anomaly_site_ids: set[str]) -> list[Site]:
    """Generate 150 sites across 5 countries in activation waves."""
    sites: list[Site] = []
    site_counter = 1
    country_city_idx: dict[str, int] = {c: 0 for c in _CITIES}

    # Pre-assign anomaly site IDs to their specified countries
    anomaly_country_map: dict[str, str] = {}
    for sid, prof in ANOMALY_PROFILES.items():
        anomaly_country_map[sid] = prof["country"]
    for sid, info in REGIONAL_CLUSTER_SITES.items():
        anomaly_country_map[sid] = info["country"]

    # Track which anomaly sites still need to be placed, keyed by country
    anomaly_remaining: dict[str, list[str]] = {}
    for sid, country in anomaly_country_map.items():
        anomaly_remaining.setdefault(country, []).append(sid)

    for country_code, count, month_start, month_end in _WAVES:
        for i in range(count):
            # Check if we should use an anomaly site ID for this country
            sid = None
            if country_code in anomaly_remaining and anomaly_remaining[country_code]:
                sid = anomaly_remaining[country_code].pop(0)
            else:
                sid = f"SITE-{site_counter:03d}"
                # Skip IDs that are reserved for anomaly sites
                while sid in anomaly_site_ids:
                    site_counter += 1
                    sid = f"SITE-{site_counter:03d}"

            city_list = _CITIES[country_code]
            city = city_list[country_city_idx[country_code] % len(city_list)]
            country_city_idx[country_code] += 1

            # Activation date within wave window
            start = STUDY_START + timedelta(days=month_start * 30)
            end = STUDY_START + timedelta(days=month_end * 30)
            act_date = start + timedelta(days=int(rng.integers(0, (end - start).days + 1)))

            exp = rng.choice(["High", "Medium", "Low"], p=[0.3, 0.5, 0.2])
            # Override experience level for anomaly sites
            if sid in ANOMALY_PROFILES and "experience_level" in ANOMALY_PROFILES[sid]:
                exp = ANOMALY_PROFILES[sid]["experience_level"]
            site_type = rng.choice(["Academic", "Community", "Hospital"], p=[0.35, 0.40, 0.25])
            target = int(rng.integers(3, 7))

            anomaly_type = None
            if sid in ANOMALY_PROFILES:
                anomaly_type = ANOMALY_PROFILES[sid]["anomaly_type"]

            sites.append(Site(
                site_id=sid,
                country=country_code,
                city=city,
                site_type=site_type,
                experience_level=exp,
                activation_date=act_date,
                target_enrollment=target,
                anomaly_type=anomaly_type,
            ))
            site_counter += 1

    return sites


def _generate_cra_assignments(rng: Generator, sites: list[Site]) -> list[CRAAssignment]:
    """Generate CRA assignments. ~30 sites get CRA transitions."""
    assignments: list[CRAAssignment] = []
    cra_counter = 1
    transition_sites = set()

    # Anomaly-driven transitions
    for sid, prof in ANOMALY_PROFILES.items():
        if prof.get("cra_transition_date") or prof.get("cra_reassignment_date"):
            transition_sites.add(sid)

    # Add ~28 more random transition sites
    non_anomaly_sids = [s.site_id for s in sites if s.site_id not in transition_sites]
    extra_transitions = rng.choice(non_anomaly_sids, size=min(28, len(non_anomaly_sids)), replace=False)
    transition_sites.update(extra_transitions)

    for site in sites:
        act = site.activation_date
        cra_id = f"CRA-{cra_counter:03d}"
        cra_counter += 1

        if site.site_id in transition_sites:
            # Determine transition date
            if site.site_id in ANOMALY_PROFILES:
                prof = ANOMALY_PROFILES[site.site_id]
                t_date = prof.get("cra_transition_date") or prof.get("cra_reassignment_date")
                if t_date is None:
                    t_date = act + timedelta(days=int(rng.integers(120, 360)))
            else:
                t_date = act + timedelta(days=int(rng.integers(120, 360)))

            # First CRA
            assignments.append(CRAAssignment(
                cra_id=cra_id, site_id=site.site_id,
                start_date=act, end_date=t_date, is_current=False,
            ))
            # Second CRA
            new_cra = f"CRA-{cra_counter:03d}"
            cra_counter += 1
            assignments.append(CRAAssignment(
                cra_id=new_cra, site_id=site.site_id,
                start_date=t_date + timedelta(days=1), end_date=None, is_current=True,
            ))
        else:
            assignments.append(CRAAssignment(
                cra_id=cra_id, site_id=site.site_id,
                start_date=act, end_date=None, is_current=True,
            ))

    return assignments
