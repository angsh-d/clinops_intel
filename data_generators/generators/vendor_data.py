"""Generate vendor management data: vendors, scope, site assignments, KPIs, milestones, issues.

8 vendors typical for a global Phase 3 oncology trial with 142 sites across 20 countries.
2-3 vendors have degrading performance patterns for agent detection.
"""

from datetime import date, timedelta

from numpy.random import Generator
from sqlalchemy.orm import Session

from data_generators.config import STUDY_START, SNAPSHOT_DATE
from data_generators.models import (
    Vendor, VendorScope, VendorSiteAssignment, VendorKPI,
    VendorMilestone, VendorIssue, Site,
)

# ── Vendor definitions ───────────────────────────────────────────────────────

VENDOR_DEFS = [
    {
        "vendor_id": "VEND-001",
        "name": "IQVIA",
        "vendor_type": "Global CRO",
        "country_hq": "USA",
        "contract_value": 27_000_000,
        "scope_type": "Monitoring",
        "countries": ["USA", "CAN", "GBR", "DEU", "ESP", "NLD", "DNK", "FIN", "HUN", "CZE", "RUS", "TUR", "ARG", "ISR", "ZAF", "KOR", "TWN", "AUS"],
        "deliverables": ["Site monitoring", "Data management", "Project management", "Medical monitoring support"],
        "role": "Primary Monitor",
    },
    {
        "vendor_id": "VEND-002",
        "name": "EPS Japan",
        "vendor_type": "Regional CRO",
        "country_hq": "JPN",
        "contract_value": 4_500_000,
        "scope_type": "Monitoring",
        "countries": ["JPN"],
        "deliverables": ["Site monitoring", "Data management", "Regulatory support", "Translation"],
        "role": "Primary Monitor",
    },
    {
        "vendor_id": "VEND-003",
        "name": "Covance Central Lab",
        "vendor_type": "Central Lab",
        "country_hq": "USA",
        "contract_value": 3_200_000,
        "scope_type": "Lab",
        "countries": ["USA", "CAN", "GBR", "DEU", "ESP", "NLD", "DNK", "FIN", "HUN", "CZE", "RUS", "TUR", "ARG", "ISR", "ZAF", "KOR", "TWN", "AUS", "JPN", "NZL"],
        "deliverables": ["Lab sample processing", "Results delivery", "Sample logistics", "Reference ranges"],
        "role": "Lab Coordinator",
    },
    {
        "vendor_id": "VEND-004",
        "name": "Bioclinica",
        "vendor_type": "Imaging",
        "country_hq": "USA",
        "contract_value": 2_800_000,
        "scope_type": "Imaging",
        "countries": ["USA", "CAN", "GBR", "DEU", "ESP", "NLD", "DNK", "FIN", "HUN", "CZE", "RUS", "TUR", "ARG", "ISR", "ZAF", "KOR", "TWN", "AUS", "JPN", "NZL"],
        "deliverables": ["Central imaging review", "RECIST assessments", "Image quality checks"],
        "role": "Imaging Reviewer",
    },
    {
        "vendor_id": "VEND-005",
        "name": "Medidata Rave",
        "vendor_type": "ePRO/EDC",
        "country_hq": "USA",
        "contract_value": 1_800_000,
        "scope_type": "ePRO",
        "countries": ["USA", "CAN", "GBR", "DEU", "ESP", "NLD", "DNK", "FIN", "HUN", "CZE", "RUS", "TUR", "ARG", "ISR", "ZAF", "KOR", "TWN", "AUS", "JPN", "NZL"],
        "deliverables": ["EDC build and maintenance", "Patient ePRO", "Edit checks", "Custom reports"],
        "role": "EDC Support",
    },
    {
        "vendor_id": "VEND-006",
        "name": "Almac",
        "vendor_type": "IRT/IWRS",
        "country_hq": "GBR",
        "contract_value": 1_200_000,
        "scope_type": "IRT",
        "countries": ["USA", "CAN", "GBR", "DEU", "ESP", "NLD", "DNK", "FIN", "HUN", "CZE", "RUS", "TUR", "ARG", "ISR", "ZAF", "KOR", "TWN", "AUS", "JPN", "NZL"],
        "deliverables": ["Randomization system", "Drug supply management", "Kit tracking"],
        "role": "IRT Manager",
    },
    {
        "vendor_id": "VEND-007",
        "name": "PharSafer",
        "vendor_type": "Safety/PV",
        "country_hq": "GBR",
        "contract_value": 1_500_000,
        "scope_type": "Safety",
        "countries": ["USA", "CAN", "GBR", "DEU", "ESP", "NLD", "DNK", "FIN", "HUN", "CZE", "RUS", "TUR", "ARG", "ISR", "ZAF", "KOR", "TWN", "AUS", "JPN", "NZL"],
        "deliverables": ["SAE processing", "Pharmacovigilance", "SUSAR reporting", "Safety database"],
        "role": "PV Specialist",
    },
    {
        "vendor_id": "VEND-008",
        "name": "StudyKIK",
        "vendor_type": "Patient Recruitment",
        "country_hq": "USA",
        "contract_value": 800_000,
        "scope_type": "Recruitment",
        "countries": ["USA", "CAN", "AUS", "NZL"],
        "deliverables": ["Digital patient recruitment", "Social media campaigns", "Pre-screening"],
        "role": "Recruitment Lead",
    },
]

# Anomaly vendors: VEND-002 (EPS Japan) degrading performance, VEND-008 (StudyKIK) underperforming
ANOMALY_VENDORS = {"VEND-002", "VEND-008"}

# KPI definitions with targets
KPI_DEFS = [
    ("Monitoring Visit Completion Rate", 95.0),
    ("Query Resolution Time (days)", 7.0),
    ("Data Entry Timeliness (%)", 90.0),
    ("Protocol Deviation Rate (%)", 5.0),
    ("Site Activation Time (days)", 60.0),
]


def generate_vendor_data(session: Session, ctx, rng: Generator) -> dict[str, int]:
    """Generate all vendor-related tables."""
    counts = {}

    # Get all sites for assignments
    all_sites = session.query(Site).all()
    site_by_country: dict[str, list] = {}
    for s in all_sites:
        site_by_country.setdefault(s.country, []).append(s)

    # 1. Vendors
    for vdef in VENDOR_DEFS:
        session.add(Vendor(
            vendor_id=vdef["vendor_id"],
            name=vdef["name"],
            vendor_type=vdef["vendor_type"],
            country_hq=vdef["country_hq"],
            contract_value=vdef["contract_value"],
            status="On Watch" if vdef["vendor_id"] in ANOMALY_VENDORS else "Active",
        ))
    counts["vendors"] = len(VENDOR_DEFS)

    # 2. Vendor Scope
    scope_count = 0
    for vdef in VENDOR_DEFS:
        session.add(VendorScope(
            vendor_id=vdef["vendor_id"],
            scope_type=vdef["scope_type"],
            countries=vdef["countries"],
            deliverables=vdef["deliverables"],
        ))
        scope_count += 1
    counts["vendor_scope"] = scope_count

    # 3. Vendor Site Assignments
    assign_count = 0
    for vdef in VENDOR_DEFS:
        for country_code in vdef["countries"]:
            country_sites = site_by_country.get(country_code, [])
            for site in country_sites:
                session.add(VendorSiteAssignment(
                    vendor_id=vdef["vendor_id"],
                    site_id=site.site_id,
                    role=vdef["role"],
                    is_active=True,
                ))
                assign_count += 1
    counts["vendor_site_assignments"] = assign_count

    # 4. Vendor KPIs — monthly snapshots
    kpi_count = 0
    snapshot_months = _monthly_dates(STUDY_START, SNAPSHOT_DATE)
    for vdef in VENDOR_DEFS:
        is_anomaly = vdef["vendor_id"] in ANOMALY_VENDORS
        for month_idx, snap_date in enumerate(snapshot_months):
            for kpi_name, target in KPI_DEFS:
                # Generate value with trend
                if is_anomaly and month_idx > len(snapshot_months) // 2:
                    # Degrading performance in second half
                    degradation = (month_idx - len(snapshot_months) // 2) * rng.uniform(0.5, 1.5)
                    if "Rate" in kpi_name or "Timeliness" in kpi_name:
                        value = max(50, target - degradation * 3)
                    elif "Resolution" in kpi_name or "Activation" in kpi_name:
                        value = target + degradation * 5
                    else:
                        value = target + degradation * 2
                else:
                    # Normal variation
                    if "Rate" in kpi_name or "Timeliness" in kpi_name:
                        value = target + rng.normal(0, 3)
                    elif "Resolution" in kpi_name or "Activation" in kpi_name:
                        value = max(1, target + rng.normal(0, 2))
                    else:
                        value = max(0, target + rng.normal(0, 1))

                value = round(value, 1)

                # Determine RAG status
                if "Rate" in kpi_name or "Timeliness" in kpi_name or "Completion" in kpi_name:
                    # Higher is better
                    if value >= target * 0.95:
                        status = "Green"
                    elif value >= target * 0.85:
                        status = "Amber"
                    else:
                        status = "Red"
                else:
                    # Lower is better (days, deviation rate)
                    if value <= target * 1.1:
                        status = "Green"
                    elif value <= target * 1.3:
                        status = "Amber"
                    else:
                        status = "Red"

                session.add(VendorKPI(
                    vendor_id=vdef["vendor_id"],
                    snapshot_date=snap_date,
                    kpi_name=kpi_name,
                    value=value,
                    target=target,
                    status=status,
                ))
                kpi_count += 1
    counts["vendor_kpis"] = kpi_count

    # 5. Vendor Milestones
    ms_count = 0
    milestone_templates = [
        ("Site Initiation Visits Complete", 90),
        ("50% Enrollment Milestone", 270),
        ("Database Lock Readiness", 540),
        ("Final Monitoring Complete", 600),
    ]
    for vdef in VENDOR_DEFS:
        if vdef["scope_type"] not in ("Monitoring", "Lab", "Imaging"):
            continue
        is_anomaly = vdef["vendor_id"] in ANOMALY_VENDORS
        for ms_name, planned_offset in milestone_templates:
            planned = STUDY_START + timedelta(days=planned_offset)
            if planned > SNAPSHOT_DATE:
                delay = int(rng.integers(10, 45)) if is_anomaly else 0
                actual = None
                status = "At Risk" if is_anomaly else "On Track"
            else:
                delay = int(rng.integers(15, 60)) if is_anomaly else int(rng.integers(0, 10))
                actual = planned + timedelta(days=delay)
                status = "Completed" if delay < 15 else "Delayed"

            session.add(VendorMilestone(
                vendor_id=vdef["vendor_id"],
                milestone_name=ms_name,
                planned_date=planned,
                actual_date=actual,
                status=status,
                delay_days=delay,
            ))
            ms_count += 1
    counts["vendor_milestones"] = ms_count

    # 6. Vendor Issues
    issue_count = 0
    issue_templates = [
        ("Quality", "Major", "Incomplete source data verification at multiple sites"),
        ("Timeliness", "Critical", "Monitoring visit backlog exceeding 6 weeks"),
        ("Staffing", "Major", "CRA turnover rate above 30% in past quarter"),
        ("Communication", "Minor", "Late submission of monitoring visit reports"),
        ("Compliance", "Critical", "Protocol deviation not reported within 24 hours"),
    ]
    for vdef in VENDOR_DEFS:
        is_anomaly = vdef["vendor_id"] in ANOMALY_VENDORS
        num_issues = rng.integers(3, 6) if is_anomaly else rng.integers(0, 2)
        for i in range(num_issues):
            template = issue_templates[i % len(issue_templates)]
            open_d = STUDY_START + timedelta(days=int(rng.integers(60, 500)))
            resolved = rng.random() < 0.4
            session.add(VendorIssue(
                vendor_id=vdef["vendor_id"],
                category=template[0],
                severity=template[1],
                description=template[2],
                open_date=open_d,
                resolution_date=open_d + timedelta(days=int(rng.integers(14, 60))) if resolved else None,
                status="Resolved" if resolved else "Open",
                resolution="Corrective action plan implemented" if resolved else None,
            ))
            issue_count += 1
    counts["vendor_issues"] = issue_count

    return counts


def _monthly_dates(start: date, end: date) -> list[date]:
    """Generate first-of-month dates between start and end."""
    months = []
    current = date(start.year, start.month, 1)
    while current <= end:
        months.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months
