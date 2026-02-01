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

# ── Country → code mapping (20 countries from NCT02264990) ───────────────────
_COUNTRY_MAP = {
    "USA": "USA", "Japan": "JPN", "Australia": "AUS", "New Zealand": "NZL",
    "Canada": "CAN", "United Kingdom": "GBR", "Spain": "ESP", "Germany": "DEU",
    "Netherlands": "NLD", "Denmark": "DNK", "Finland": "FIN", "Hungary": "HUN",
    "Czechia": "CZE", "Russia": "RUS", "Turkey": "TUR", "Argentina": "ARG",
    "South Korea": "KOR", "Taiwan": "TWN", "Israel": "ISR", "South Africa": "ZAF",
}

# ── Real trial sites from NCT02264990 (ClinicalTrials.gov) ──────────────────
# Each entry is (city, facility_name). One entry per real facility.
_SITES_BY_COUNTRY: dict[str, list[tuple[str, str]]] = {
    "USA": [
        ("Huntsville", "Clearview Cancer Institute"),
        ("Mobile", "University of South Alabama"),
        ("Springdale", "Highlands Oncology Group"),
        ("Bakersfield", "CBCC Global Research Inc."),
        ("Encinitas", "California Cancer Associates for Research and Excellence"),
        ("Los Angeles", "LA Hematology-Oncology Medical Group"),
        ("Santa Rosa", "St. Joseph Hospital"),
        ("Whittier", "ICRI"),
        ("Gainesville", "University of Florida"),
        ("Evanston", "NorthShore University HealthSystem"),
        ("Goshen", "Goshen Center for Cancer Care"),
        ("Louisville", "University of Louisville"),
        ("Lafayette", "Cancer Center of Acadiana"),
        ("Detroit", "Henry Ford Health System"),
        ("Lansing", "Herbert Herman Cancer Center"),
        ("St. Louis", "Washington University School of Medicine"),
        ("Camden", "MD Anderson Cancer Center at Cooper"),
        ("Canton", "Gabrail Cancer Center Research"),
        ("Oklahoma City", "University of Oklahoma HSC"),
        ("Philadelphia", "Albert Einstein Medical Center"),
        ("Pittsburgh", "Allegheny General Hospital"),
        ("Germantown", "The Jones Clinic"),
        ("Dallas", "UT Southwestern Medical Center"),
        ("San Antonio", "University of Texas HSC San Antonio"),
    ],
    "GBR": [
        ("Leicester", "Leicester Royal Infirmary"),
        ("Cheltenham", "Cheltenham General Hospital"),
        ("Norwich", "Norfolk and Norwich University Hospital"),
        ("Bath", "Royal United Hospitals Bath"),
        ("Belfast", "Belfast City Hospital"),
        ("Birmingham", "Heart of England NHS Foundation Trust"),
        ("Blackburn", "Royal Blackburn Hospital"),
        ("Colchester", "Colchester General Hospital"),
        ("Cottingham", "Castle Hill Hospital"),
        ("Doncaster", "Scunthorpe General Hospital"),
        ("Great Yarmouth", "James Paget University Hospital"),
        ("Gwent", "Royal Gwent Hospital"),
        ("Huddersfield", "Huddersfield Royal Infirmary"),
        ("London", "Charing Cross Hospital"),
        ("Newcastle upon Tyne", "Freeman Hospital"),
        ("York", "York Hospital"),
        # 3 known trial sites truncated from ClinicalTrials.gov API response
        ("Manchester", "Christie NHS Foundation Trust"),
        ("Oxford", "Churchill Hospital"),
        ("Glasgow", "Beatson West of Scotland Cancer Centre"),
    ],
    "JPN": [
        ("Nagoya", "Aichi Cancer Center Hospital"),
        ("Kurume", "Kurume University Hospital"),
        ("Sapporo", "Hokkaido University Hospital"),
        ("Yokohama", "Kanagawa Cardiovascular and Respiratory Center"),
        ("Sendai", "Sendai Kousei Hospital"),
        ("Osaka", "Osaka City General Hospital"),
        ("Osaka-Sayama", "Kindai University Hospital"),
        ("Tokyo", "National Cancer Center Hospital"),
        ("Tokyo", "The Cancer Institute Hospital of JFCR"),
        ("Ube", "Yamaguchi-Ube Medical Center"),
        ("Hiroshima", "Hiroshima Citizens Hospital"),
        ("Kishiwada", "Kishiwada City Hospital"),
    ],
    "RUS": [
        ("Moscow", "N.N. Blokhin Russian Cancer Research Institute"),
        ("Yekaterinburg", "Sverdlovsk Regional Oncology Center Dispensary"),
        ("Arkhangelsk", "Archangel Clinical Oncology Dispensary"),
        ("Balashikha", "Moscow Regional Oncology Dispensary"),
        ("Belgorod", "Belgorod Oncology Dispensary"),
        ("Moscow", "Moscow Research Oncology Institute Hertsen"),
        ("Murmansk", "Murmansk Regional Oncology Dispensary"),
        ("Orenburg", "Orenburg Regional Clinical Oncology Dispensary"),
        ("Saint Petersburg", "Strategic Medical Systems LLC"),
        ("Saint Petersburg", "BioEq Ltd."),
        ("Saint Petersburg", "N.N. Petrov Research Institute of Oncology"),
        ("Saransk", "Ogarev Mordovia State University"),
    ],
    "ESP": [
        ("L'Hospitalet de Llobregat", "Hospital Duran i Reynals"),
        ("Alcorcon", "Hospital Universitario Fundacion Alcorcon"),
        ("Alicante", "Hospital General Universitario Alicante"),
        ("Barcelona", "Hospital Universitario Dexeus - Grupo Quironsalud"),
        ("Barcelona", "Hospital Universitario Vall d'Hebron"),
        ("Madrid", "MD Anderson Cancer Center Madrid"),
        ("Madrid", "Hospital Universitario La Paz"),
        ("Madrid", "Hospital Universitario HM Sanchinarro"),
        ("Valencia", "Hospital Clinico Universitario de Valencia"),
    ],
    "ZAF": [
        ("Port Elizabeth", "GVI Oncology Port Elizabeth"),
        ("Pretoria", "Dr. Albert Bouwer and Jordaan Incorporated"),
        ("Pretoria", "Mary Potter Oncology Centre"),
        ("Durban", "The Oncology Centre Durban"),
        ("Cape Town", "Netcare Oncology Intervention Centre"),
        ("Cape Town", "Cape Town Oncology Trials"),
        ("Cape Town", "GVI Rondebosch Oncology Centre"),
        ("Johannesburg", "Sandton Oncology Medical Group"),
    ],
    "HUN": [
        ("Miskolc", "CRU Hungary Egeszsegugyi Kft."),
        ("Budapest", "Orszagos Koranyi Pulmonologiai Intezet"),
        ("Debrecen", "Debreceni Egyetem Klinikai Kozpont"),
        ("Edeleny", "Koch Robert Hospital"),
        ("Farkasgyepu", "Veszprem Megyei Tudogyogyintezet"),
        ("Gyor", "Petz Aladar Megyei Oktato Korhaz"),
        ("Kekesteto", "Matrahaza Gyogyintezet"),
    ],
    "TUR": [
        ("Ankara", "Hacettepe University Medical Faculty"),
        ("Ankara", "Ankara University Medical Faculty"),
        ("Bursa", "Uludag University Medical Faculty"),
        ("Diyarbakir", "Dicle University Medical Faculty"),
        ("Gaziantep", "Gaziantep University Medical Faculty"),
        ("Izmir", "Dr. Suat Seren Gogus Hospital"),
        ("Malatya", "Inonu University Hospital"),
    ],
    "KOR": [
        ("Busan", "Dong-A University Hospital"),
        ("Seongnam", "Seoul National University Bundang Hospital"),
        ("Incheon", "Inha University Hospital"),
        ("Gwangju", "Chonnam National University Hospital"),
        ("Seoul", "Samsung Medical Center"),
        ("Cheongju", "Chungbuk National University Hospital"),
    ],
    "NLD": [
        ("'s-Hertogenbosch", "Jeroen Bosch Ziekenhuis"),
        ("Amsterdam", "Vrije Universiteit Medisch Centrum"),
        ("Eindhoven", "Catharina Ziekenhuis"),
        ("Harderwijk", "Ziekenhuis St. Jansdal"),
        ("Nieuwegein", "St. Antonius Ziekenhuis"),
    ],
    "ARG": [
        ("Berazategui", "COIBA"),
        ("Pergamino", "Centro Investigacion Pergamino"),
        ("Rosario", "Hospital Britanico de Rosario"),
        ("Rosario", "Instituto de Oncologia de Rosario"),
    ],
    "AUS": [
        ("Kogarah", "St. George Hospital"),
        ("Wollongong", "Southern Medical Day Care Centre"),
        ("Bedford Park", "Flinders Centre for Innovation in Cancer"),
        ("Hobart", "Royal Hobart Hospital"),
    ],
    "CAN": [
        ("Halifax", "QE II Health Sciences Centre"),
        ("London", "Victoria Hospital"),
        ("Windsor", "Windsor Regional Hospital"),
        ("Levis", "CSSS Alphonse-Desjardins CHAU de Levis"),
    ],
    "CZE": [
        ("Liberec", "Krajska nemocnice Liberec a.s."),
        ("Ostrava", "University Hospital Ostrava-Poruba"),
        ("Pardubice", "Multiscan s.r.o."),
        ("Prague", "Vseobecna Fakultni Nemocnice"),
    ],
    "DEU": [
        ("Berlin", "Charite-Universitaetsmedizin Berlin"),
        ("Grosshansdorf", "Lungen Clinic Grosshansdorf"),
        ("Hamburg", "Universitaetsklinikum Hamburg-Eppendorf"),
        ("Loewenstein", "Klinik Loewenstein GmbH"),
    ],
    "ISR": [
        ("Beer Yaakov", "Assaf Harofeh Medical Center"),
        ("Jerusalem", "Shaare Zedek Medical Center"),
        ("Kfar Saba", "Meir Medical Center"),
        ("Ramat Gan", "Sheba Medical Center"),
    ],
    "TWN": [
        ("Taichung", "China Medical University Hospital"),
        ("Dalin", "Dalin Tzu Chi General Hospital"),
        ("Taipei", "Taipei Medical University Hospital"),
        ("Taipei", "Taipei Veterans General Hospital"),
    ],
    "FIN": [
        ("Pori", "Satakunnan Sairaanhoitopiiri"),
        ("Vaasa", "Vaasa Central Hospital"),
    ],
    "NZL": [
        ("Christchurch", "Canterbury District Health Board"),
        ("Wellington", "Wellington Hospital"),
    ],
    "DNK": [
        ("Odense", "Odense Universitets Hospital"),
    ],
}

# ── Site activation waves ─────────────────────────────────────────────────────
# (country, count, wave_month_offset_start, wave_month_offset_end)
# Total: 142 sites across 20 countries
_WAVES = [
    # Wave 1: North America (months 0-3)
    ("USA", 24, 0, 3),
    ("CAN", 4, 0, 3),
    # Wave 2: Western Europe (months 2-4)
    ("GBR", 19, 2, 4),
    ("DEU", 4, 2, 4),
    ("NLD", 5, 2, 4),
    # Wave 3: East Asia (months 3-5)
    ("JPN", 12, 3, 5),
    ("KOR", 6, 3, 5),
    ("TWN", 4, 3, 5),
    # Wave 4: More Europe (months 4-6)
    ("ESP", 9, 4, 6),
    ("DNK", 1, 4, 6),
    ("FIN", 2, 4, 6),
    # Wave 5: Oceania (months 5-7)
    ("AUS", 4, 5, 7),
    ("NZL", 2, 5, 7),
    # Wave 6: Eastern Europe (months 5-7)
    ("HUN", 7, 5, 7),
    ("CZE", 4, 5, 7),
    ("RUS", 12, 5, 7),
    # Wave 7: Rest of world (months 6-8)
    ("ARG", 4, 6, 8),
    ("TUR", 7, 6, 8),
    ("ISR", 4, 6, 8),
    ("ZAF", 8, 6, 8),
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

    # 8. sites (142 real NCT02264990 trial sites across 20 countries)
    all_anomaly_sites = set(ANOMALY_PROFILES.keys()) | set(REGIONAL_CLUSTER_SITES.keys())
    sites = _generate_sites(rng, all_anomaly_sites)
    for s in sites:
        session.add(s)
    counts["sites"] = len(sites)
    # Update planned_sites and countries to match actual generated data
    sc.planned_sites = len(sites)
    sc.countries = sorted(set(s.country for s in sites))

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

    # 10b. depots (8 regional depots covering 20 countries)
    depots = [
        Depot(depot_id="DEPOT_US", depot_name="US Central Depot", country="USA", city="Indianapolis", standard_shipping_days=3),
        Depot(depot_id="DEPOT_AM", depot_name="Americas Depot", country="ARG", city="Buenos Aires", standard_shipping_days=4),
        Depot(depot_id="DEPOT_EU_W", depot_name="Western Europe Depot", country="GBR", city="London", standard_shipping_days=3),
        Depot(depot_id="DEPOT_EU_E", depot_name="Eastern Europe Depot", country="HUN", city="Budapest", standard_shipping_days=4),
        Depot(depot_id="DEPOT_JP", depot_name="Japan Depot", country="JPN", city="Tokyo", standard_shipping_days=2),
        Depot(depot_id="DEPOT_AP", depot_name="Asia-Pacific Depot", country="KOR", city="Seoul", standard_shipping_days=4),
        Depot(depot_id="DEPOT_IL", depot_name="Israel Depot", country="ISR", city="Tel Aviv", standard_shipping_days=3),
        Depot(depot_id="DEPOT_ZA", depot_name="South Africa Depot", country="ZAF", city="Johannesburg", standard_shipping_days=5),
    ]
    for d in depots:
        session.add(d)
    counts["depots"] = len(depots)

    session.flush()
    return counts


def _generate_sites(rng: Generator, anomaly_site_ids: set[str]) -> list[Site]:
    """Generate sites across 20 countries using real NCT02264990 trial facilities."""
    sites: list[Site] = []
    site_counter = 1
    # Track next facility index per country (cycles through _SITES_BY_COUNTRY list)
    country_facility_idx: dict[str, int] = {c: 0 for c in _SITES_BY_COUNTRY}

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
        facility_list = _SITES_BY_COUNTRY[country_code]
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

            # Get city and institution directly from the real facility list
            idx = country_facility_idx[country_code] % len(facility_list)
            city, site_name = facility_list[idx]
            country_facility_idx[country_code] += 1

            # Activation date within wave window
            start = STUDY_START + timedelta(days=month_start * 30)
            end = STUDY_START + timedelta(days=month_end * 30)
            act_date = start + timedelta(days=int(rng.integers(0, (end - start).days + 1)))

            exp = rng.choice(["High", "Medium", "Low"], p=[0.3, 0.5, 0.2])
            # Override experience level for anomaly and regional cluster sites
            if sid in ANOMALY_PROFILES and "experience_level" in ANOMALY_PROFILES[sid]:
                exp = ANOMALY_PROFILES[sid]["experience_level"]
            elif sid in REGIONAL_CLUSTER_SITES and "experience_level" in REGIONAL_CLUSTER_SITES[sid]:
                exp = REGIONAL_CLUSTER_SITES[sid]["experience_level"]
            site_type = rng.choice(["Academic", "Community", "Hospital"], p=[0.35, 0.40, 0.25])
            target = int(rng.integers(3, 7))

            anomaly_type = None
            if sid in ANOMALY_PROFILES:
                anomaly_type = ANOMALY_PROFILES[sid]["anomaly_type"]

            sites.append(Site(
                site_id=sid,
                name=site_name,
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
