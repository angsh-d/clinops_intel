"""Generate financial data: budget, line items, snapshots, invoices, change orders, site costs.

~$45M budget for a 142-site Phase 3 oncology trial.
Realistic cost structure: CRO ~60%, pass-through ~30%, contingency ~10%.
Monthly snapshots with ~8% overrun by month 18. 3-4 change orders.
"""

from datetime import date, timedelta

from numpy.random import Generator
from sqlalchemy.orm import Session

from data_generators.config import STUDY_START, SNAPSHOT_DATE
from data_generators.models import (
    StudyBudget, BudgetCategory, BudgetLineItem, FinancialSnapshot,
    Invoice, PaymentMilestone, ChangeOrder, SiteFinancialMetric,
    Site, RandomizationLog, ScreeningLog,
)
from sqlalchemy import func

TOTAL_BUDGET = 45_000_000

# Budget category structure
CATEGORIES = [
    ("CRO-MON", "CRO Monitoring Services", None, "Service Fee"),
    ("CRO-DM", "CRO Data Management", None, "Service Fee"),
    ("CRO-PM", "CRO Project Management", None, "Service Fee"),
    ("CRO-REG", "Regional CRO Services", None, "Service Fee"),
    ("LAB", "Central Lab Services", None, "Pass-Through"),
    ("IMG", "Central Imaging", None, "Pass-Through"),
    ("EDC", "EDC/ePRO Platform", None, "Pass-Through"),
    ("IRT", "IRT/IWRS System", None, "Pass-Through"),
    ("PV", "Pharmacovigilance", None, "Pass-Through"),
    ("RECRUIT", "Patient Recruitment", None, "Pass-Through"),
    ("SITE-FEE", "Site Fees & Grants", None, "Pass-Through"),
    ("TRAVEL", "Travel & Meetings", None, "Pass-Through"),
    ("CONT", "Contingency Reserve", None, "Contingency"),
]

# Budget allocation (approximate)
ALLOCATION = {
    "CRO-MON": 0.28,
    "CRO-DM": 0.10,
    "CRO-PM": 0.08,
    "CRO-REG": 0.10,
    "LAB": 0.07,
    "IMG": 0.06,
    "EDC": 0.04,
    "IRT": 0.03,
    "PV": 0.03,
    "RECRUIT": 0.02,
    "SITE-FEE": 0.08,
    "TRAVEL": 0.03,
    "CONT": 0.08,
}

# Vendor ID mapping for invoices
CATEGORY_VENDOR = {
    "CRO-MON": "VEND-001",
    "CRO-DM": "VEND-001",
    "CRO-PM": "VEND-001",
    "CRO-REG": "VEND-002",
    "LAB": "VEND-003",
    "IMG": "VEND-004",
    "EDC": "VEND-005",
    "IRT": "VEND-006",
    "PV": "VEND-007",
    "RECRUIT": "VEND-008",
}


def generate_financial_data(session: Session, ctx, rng: Generator) -> dict[str, int]:
    """Generate all financial tables."""
    counts = {}

    # 1. Study Budget
    service_fees = TOTAL_BUDGET * 0.56
    pass_through = TOTAL_BUDGET * 0.36
    contingency = TOTAL_BUDGET * 0.08

    session.add(StudyBudget(
        budget_version="v1.0",
        total_budget_usd=TOTAL_BUDGET,
        service_fees=service_fees,
        pass_through=pass_through,
        contingency=contingency,
        effective_date=STUDY_START - timedelta(days=30),
        status="Active",
    ))
    counts["study_budget"] = 1

    # 2. Budget Categories
    for code, name, parent, cost_type in CATEGORIES:
        session.add(BudgetCategory(
            category_code=code,
            name=name,
            parent_code=parent,
            cost_type=cost_type,
        ))
    counts["budget_categories"] = len(CATEGORIES)

    # 3. Budget Line Items
    line_count = 0
    sites = session.query(Site).all()
    country_list = list(set(s.country for s in sites if s.country))

    for code, alloc_pct in ALLOCATION.items():
        planned = TOTAL_BUDGET * alloc_pct
        vendor_id = CATEGORY_VENDOR.get(code)

        if code in ("CRO-MON", "SITE-FEE"):
            # Per-site allocation
            per_site = planned / max(len(sites), 1)
            for site in sites:
                actual = per_site * rng.uniform(0.85, 1.20)
                forecast = per_site * rng.uniform(0.95, 1.15)
                session.add(BudgetLineItem(
                    category_code=code,
                    country=site.country,
                    vendor_id=vendor_id,
                    unit_type="Per Site",
                    unit_cost=per_site,
                    planned_units=1,
                    actual_units=1,
                    planned_amount=round(per_site, 2),
                    actual_amount=round(actual, 2),
                    forecast_amount=round(forecast, 2),
                ))
                line_count += 1
        elif code == "CRO-REG":
            # Japan only
            actual = planned * rng.uniform(1.05, 1.20)
            session.add(BudgetLineItem(
                category_code=code,
                country="JPN",
                vendor_id=vendor_id,
                unit_type="Lump Sum",
                unit_cost=planned,
                planned_units=1,
                actual_units=1,
                planned_amount=round(planned, 2),
                actual_amount=round(actual, 2),
                forecast_amount=round(actual * 1.05, 2),
            ))
            line_count += 1
        else:
            # Lump sum per country or global
            actual_multiplier = rng.uniform(0.90, 1.12)
            actual = planned * actual_multiplier
            session.add(BudgetLineItem(
                category_code=code,
                country=None,
                vendor_id=vendor_id,
                unit_type="Lump Sum",
                unit_cost=planned,
                planned_units=1,
                actual_units=1,
                planned_amount=round(planned, 2),
                actual_amount=round(actual, 2),
                forecast_amount=round(actual * rng.uniform(1.0, 1.08), 2),
            ))
            line_count += 1
    counts["budget_line_items"] = line_count

    # 4. Financial Snapshots — monthly
    snap_count = 0
    months = _monthly_dates(STUDY_START, SNAPSHOT_DATE)
    total_months = len(months)
    planned_total = TOTAL_BUDGET * 0.92  # Exclude contingency from planned burn

    for i, snap_month in enumerate(months):
        month_frac = (i + 1) / total_months
        # S-curve for planned spend
        s_curve = _s_curve(month_frac)
        planned_cum = planned_total * s_curve
        monthly_planned = planned_cum - (planned_total * _s_curve((i) / total_months) if i > 0 else 0)

        # Actual: starts on track, grows ~8% overrun by end
        overrun_factor = 1.0 + 0.08 * (month_frac ** 1.5)
        noise = rng.normal(0, 0.01)
        actual_cum = planned_cum * (overrun_factor + noise)
        monthly_actual = actual_cum - (planned_total * _s_curve((i) / total_months) * (1.0 + 0.08 * (((i) / total_months) ** 1.5)) if i > 0 else 0)

        burn_rate = monthly_actual if monthly_actual > 0 else monthly_planned
        variance_pct = ((actual_cum - planned_cum) / max(planned_cum, 1)) * 100

        # Forecast: actual trajectory projected
        forecast_cum = actual_cum + (planned_total - planned_cum) * overrun_factor

        session.add(FinancialSnapshot(
            snapshot_month=snap_month,
            planned_cumulative=round(planned_cum, 2),
            actual_cumulative=round(actual_cum, 2),
            forecast_cumulative=round(forecast_cum, 2),
            monthly_planned=round(monthly_planned, 2),
            monthly_actual=round(max(0, monthly_actual), 2),
            burn_rate=round(max(0, burn_rate), 2),
            variance_pct=round(variance_pct, 2),
        ))
        snap_count += 1
    counts["financial_snapshots"] = snap_count

    # 5. Invoices — monthly per vendor
    inv_count = 0
    for snap_month in months:
        for code, vendor_id in CATEGORY_VENDOR.items():
            if not vendor_id:
                continue
            alloc = ALLOCATION.get(code, 0)
            monthly_amount = (TOTAL_BUDGET * alloc) / total_months
            amount = monthly_amount * rng.uniform(0.85, 1.15)

            statuses = ["Paid", "Paid", "Paid", "Approved", "Submitted"]
            if snap_month > SNAPSHOT_DATE - timedelta(days=60):
                status = rng.choice(["Submitted", "Approved", "Paid"])
            else:
                status = rng.choice(statuses)

            session.add(Invoice(
                vendor_id=vendor_id,
                invoice_number=f"INV-{vendor_id}-{snap_month.strftime('%Y%m')}",
                amount=round(amount, 2),
                category_code=code,
                invoice_date=snap_month,
                due_date=snap_month + timedelta(days=30),
                status=status,
            ))
            inv_count += 1
    counts["invoices"] = inv_count

    # 6. Payment Milestones
    pm_count = 0
    pm_defs = [
        ("VEND-001", "Study Start-up Complete", "All sites activated", 2_000_000),
        ("VEND-001", "50% Enrollment", "50% of target enrolled", 3_000_000),
        ("VEND-001", "100% Enrollment", "100% of target enrolled", 3_000_000),
        ("VEND-001", "Database Lock", "Database locked for analysis", 2_000_000),
        ("VEND-002", "Japan Sites Activated", "All Japan sites active", 500_000),
        ("VEND-003", "Lab Validation Complete", "Central lab validated", 300_000),
        ("VEND-004", "Imaging Charter Approved", "Imaging charter finalized", 200_000),
    ]
    for vendor_id, ms_name, trigger, planned_amount in pm_defs:
        triggered = rng.random() < 0.6
        session.add(PaymentMilestone(
            vendor_id=vendor_id,
            milestone_name=ms_name,
            trigger_condition=trigger,
            planned_amount=planned_amount,
            actual_amount=round(planned_amount * rng.uniform(0.95, 1.05), 2) if triggered else None,
            status="Paid" if triggered else "Pending",
        ))
        pm_count += 1
    counts["payment_milestones"] = pm_count

    # 7. Change Orders
    co_count = 0
    change_orders = [
        ("VEND-001", "CO-001", "Scope Increase", 1_200_000, 30, "Additional 15 sites added to protocol"),
        ("VEND-001", "CO-002", "Timeline Extension", 800_000, 90, "3-month enrollment extension due to slow recruitment"),
        ("VEND-002", "CO-003", "Rate Change", 350_000, 0, "CRA rate increase for Japan market adjustment"),
        ("VEND-003", "CO-004", "Scope Increase", 180_000, 0, "Additional biomarker assay added to protocol"),
    ]
    for vendor_id, co_num, category, amount, timeline_days, desc in change_orders:
        submitted = STUDY_START + timedelta(days=int(rng.integers(120, 400)))
        approved = rng.random() < 0.75
        session.add(ChangeOrder(
            vendor_id=vendor_id,
            change_order_number=co_num,
            category=category,
            amount=amount,
            timeline_impact_days=timeline_days,
            description=desc,
            status="Approved" if approved else "Proposed",
            submitted_date=submitted,
            approved_date=submitted + timedelta(days=int(rng.integers(14, 45))) if approved else None,
        ))
        co_count += 1
    counts["change_orders"] = co_count

    # 8. Site Financial Metrics
    sfm_count = 0
    # Get actual enrollment counts
    screening_counts = dict(
        session.query(ScreeningLog.site_id, func.count(ScreeningLog.id))
        .group_by(ScreeningLog.site_id).all()
    )
    randomization_counts = dict(
        session.query(RandomizationLog.site_id, func.count(RandomizationLog.id))
        .group_by(RandomizationLog.site_id).all()
    )

    for site in sites:
        screened = screening_counts.get(site.site_id, 0)
        randomized = randomization_counts.get(site.site_id, 0)

        # Base cost per site depends on country
        country_cost_mult = {
            "USA": 1.0, "CAN": 0.95, "GBR": 0.9, "DEU": 0.85, "ESP": 0.75,
            "JPN": 1.1, "AUS": 0.9, "NZL": 0.85, "KOR": 0.7, "TWN": 0.65,
            "NLD": 0.85, "DNK": 0.9, "FIN": 0.85, "HUN": 0.6, "CZE": 0.6,
            "RUS": 0.55, "TUR": 0.55, "ARG": 0.5, "ISR": 0.8, "ZAF": 0.55,
        }.get(site.country, 0.75)

        base_cost = 80_000 * country_cost_mult
        per_patient_cost = 15_000 * country_cost_mult
        cost_to_date = base_cost + (screened * per_patient_cost * 0.3) + (randomized * per_patient_cost * 0.7)
        cost_to_date *= rng.uniform(0.85, 1.20)

        planned_cost = base_cost + (site.target_enrollment or 4) * per_patient_cost
        variance_pct = ((cost_to_date - planned_cost * 0.7) / max(planned_cost * 0.7, 1)) * 100

        cost_per_screened = cost_to_date / max(screened, 1)
        cost_per_randomized = cost_to_date / max(randomized, 1)

        session.add(SiteFinancialMetric(
            site_id=site.site_id,
            snapshot_date=SNAPSHOT_DATE,
            cost_to_date=round(cost_to_date, 2),
            cost_per_patient_screened=round(cost_per_screened, 2),
            cost_per_patient_randomized=round(cost_per_randomized, 2),
            planned_cost_to_date=round(planned_cost * 0.7, 2),
            variance_pct=round(variance_pct, 2),
        ))
        sfm_count += 1
    counts["site_financial_metrics"] = sfm_count

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


def _s_curve(x: float) -> float:
    """S-curve for budget burn: slow start, ramp, plateau."""
    import math
    return 1.0 / (1.0 + math.exp(-10 * (x - 0.5)))
