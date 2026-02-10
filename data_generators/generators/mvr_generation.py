"""Standalone MVR (Monitoring Visit Report) generator.

Generates 27 MVR PDFs across 5 priority anomaly sites using LLM-generated
structured content rendered into PDF via fpdf2. Inserts structured data into
the monitoring_visit_reports table for SQL querying by the MVR Analysis Agent.

Run independently:
    python -m data_generators.generators.mvr_generation
"""

import asyncio
import json
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fpdf import FPDF
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

# Project root for imports
_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")

from data_generators.config import engine, SessionLocal, SNAPSHOT_DATE, STUDY_START
from data_generators.models import (
    Base, MonitoringVisit, MonitoringVisitReport, Site, CRAAssignment,
    ScreeningLog, RandomizationLog, OverdueAction, StudyConfig,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# VISIT SELECTION MAP — Strategic visits per site from the plan
# ═══════════════════════════════════════════════════════════════════════════════

VISIT_SELECTION_MAP = {
    "SITE-012": {
        "anomaly": "High query burden / zombie findings",
        "visits": [
            {
                "visit_index": 0, "visit_label": "IMV1",
                "anomaly_context": (
                    "BASELINE visit. Generate a normal MVR — routine findings, sets expectations. "
                    "2-3 minor findings typical of a first monitoring visit. No major issues. "
                    "CRF completion is acceptable, no outstanding queries."
                ),
            },
            {
                "visit_index": 2, "visit_label": "Visit 3",
                "anomaly_context": (
                    "SDV issue FIRST APPEARS: checklist item 45 flags CRF completion errors on Lab Results page. "
                    "Action Required on item 45: 'SDV identified discrepancies between source lab reports and CRF entries "
                    "for 3 subjects. Site to correct Lab Results CRF entries.' Item 43 also flags: 'Open queries on Lab Results "
                    "and Vital Signs CRF pages — 5 queries remain unresolved from data management review.' "
                    "Summary mentions 'Data management queries have increased since last visit.'"
                ),
            },
            {
                "visit_index": 3, "visit_label": "Visit 4",
                "anomaly_context": (
                    "The Lab Results SDV finding from Visit 3 is now marked RESOLVED in follow_up_from_prior. "
                    "'Prior action: Correct Lab Results CRF entries — Status: Resolved — Comment: Site corrected 3 CRF entries.' "
                    "However, 2 NEW queries opened on different subjects for the same Lab Results page. "
                    "This visit appears routine — the resolution creates false confidence."
                ),
            },
            {
                "visit_index": 5, "visit_label": "Visit 6",
                "anomaly_context": (
                    "ZOMBIE FINDING: The IDENTICAL Lab Results SDV finding REAPPEARS despite prior 'resolution'. "
                    "Item 45: 'SDV identified discrepancies between source lab reports and CRF entries for 4 subjects — "
                    "same data field (lab result units) that was corrected in Visit 4 now shows errors in newly enrolled subjects.' "
                    "Summary MUST include: 'Queries remain open since last visit on Lab Results CRF pages. "
                    "The pattern of CRF completion errors on Lab Results appears systemic rather than isolated.' "
                    "Item 46: 'Query resolution timely? No — 8 queries aged >14 days on Lab Results and Vital Signs pages.' "
                    "Action Required count should be 4+."
                ),
            },
            {
                "visit_index": 6, "visit_label": "Visit 7",
                "anomaly_context": (
                    "SECOND ZOMBIE CYCLE begins on a DIFFERENT CRF page. Drug Accountability now shows the same pattern. "
                    "Item 45: 'SDV identified discrepancies in Drug Accountability log — IP dispensing dates do not match "
                    "source pharmacy records for 2 subjects.' Item 39: 'IP accountability current? No — discrepancies noted.' "
                    "The Lab Results zombie is ALSO still present: item 46 flags '6 queries still open on Lab Results.' "
                    "Summary: 'Two separate CRF domains now show recurring data quality issues despite prior corrective actions.'"
                ),
            },
            {
                "visit_index": 8, "visit_label": "Visit 9 (latest)",
                "anomaly_context": (
                    "SCATTERED compliance issues across MULTIPLE checklist sections — the systemic nature is now visible. "
                    "Item 34: 'GCP compliance? — Action Required: Training records not updated for 2 new staff members.' "
                    "Item 45: 'Lab Results CRF discrepancies persist — 5 subjects with unresolved SDV findings.' "
                    "Item 39: 'Drug Accountability discrepancies from prior visit partially resolved — 1 of 2 corrected.' "
                    "Item 46: '11 open queries across Lab Results, Drug Accountability, and AE Log pages.' "
                    "Items 32-34 all have comments about minor deviations. Action Required count: 6+. "
                    "Summary: 'Multiple open queries persist across several CRF domains. Site demonstrates difficulty "
                    "maintaining consistent data entry quality despite repeated corrective actions.'"
                ),
            },
        ],
    },
    "SITE-074": {
        "anomaly": "Suspicious perfection / CRA rubber-stamping",
        "visits": [
            {
                "visit_index": 1, "visit_label": "Visit 2",
                "anomaly_context": (
                    "SUSPICIOUSLY PERFECT: ALL 46 checklist items must be 'Yes' with NO comments. "
                    "Zero urgent issues. Zero SDV discrepancies. Executive summary ~400 words only. "
                    "Use EXACT phrase: 'No concerns noted during this monitoring visit.' "
                    "PI engagement: 'PI available and cooperative.' Overall impression: 'Site performing well.' "
                    "Zero action required items. SDV findings: 'All source data verified, no discrepancies noted' "
                    "for every subject reviewed. Follow-up from prior: empty (nothing to follow up). "
                    "CRA assessment: 'Site continues to demonstrate excellent compliance with protocol requirements. "
                    "No corrective actions needed at this time.'"
                ),
            },
            {
                "visit_index": 3, "visit_label": "Visit 4",
                "anomaly_context": (
                    "IDENTICAL structure to Visit 2 — same boilerplate language, same ~400 word count. "
                    "ALL items 'Yes', NO comments, NO findings. Use EXACT same phrases: "
                    "'No concerns noted during this monitoring visit.' "
                    "'PI available and cooperative.' 'Site performing well.' "
                    "CRA assessment uses IDENTICAL language to Visit 2. The copy-paste pattern begins."
                ),
            },
            {
                "visit_index": 4, "visit_label": "Visit 5",
                "anomaly_context": (
                    "THIRD identical visit. ALL items 'Yes', NO comments, NO findings, ~400 words. "
                    "EXACT same phrases repeated: 'No concerns noted during this monitoring visit.' "
                    "'PI available and cooperative.' 'Site performing well.' "
                    "CRA assessment: IDENTICAL to prior visits. Three visits with zero findings is notable."
                ),
            },
            {
                "visit_index": 6, "visit_label": "Visit 7",
                "anomaly_context": (
                    "FOURTH identical visit. Same template, same phrases, same word count (~400). "
                    "ALL items 'Yes', NO comments. PI engagement: 'PI available and cooperative' — "
                    "EXACT same phrase as every prior visit, word for word. Zero urgent issues. "
                    "Zero action required. Zero SDV discrepancies. Zero follow-up items."
                ),
            },
            {
                "visit_index": 7, "visit_label": "Visit 8",
                "anomaly_context": (
                    "FIFTH identical visit — the manufacturing is now unmistakable. "
                    "Same ~400 word count, same phrases, ALL items 'Yes', NO comments. "
                    "'No concerns noted during this monitoring visit.' "
                    "'PI available and cooperative.' 'Site performing well.' "
                    "Five consecutive visits with zero findings, zero issues, identical language."
                ),
            },
            {
                "visit_index": 9, "visit_label": "Visit 10 (latest)",
                "anomaly_context": (
                    "SIXTH identical visit — the CRA has NEVER reported a single issue in 10 visits. "
                    "Same ~400 word count, same boilerplate. ALL items 'Yes', NO comments. "
                    "'No concerns noted during this monitoring visit.' "
                    "'PI available and cooperative.' 'Site performing well.' "
                    "Reports look copy-pasted. Zero findings across 6 documented visits is statistically impossible "
                    "for a site with active enrollment. This is the pattern the agent must detect."
                ),
            },
        ],
    },
    "SITE-055": {
        "anomaly": "PI engagement decline / enrollment stall",
        "visits": [
            {
                "visit_index": 1, "visit_label": "Visit 2",
                "anomaly_context": (
                    "HEALTHY BASELINE: PI fully present and engaged. PI reviews enrollment plan during exit interview. "
                    "PI engagement: pi_present=true, engagement_quality='high', "
                    "notes='PI was present throughout the visit, actively reviewed enrollment strategy and patient pipeline.' "
                    "Recruitment rate adequate: Yes. Summary mentions 'adequate recruitment rate' and 'PI commitment to enrollment targets.' "
                    "2-3 minor routine findings. Normal word count (800-1000 words)."
                ),
            },
            {
                "visit_index": 3, "visit_label": "Visit 4",
                "anomaly_context": (
                    "FIRST SIGN of PI decline: 'PI briefly available during the visit; Sub-Investigator covered the majority "
                    "of the monitoring activities and exit interview.' PI engagement: pi_present=true (briefly), "
                    "engagement_quality='medium', notes='PI briefly available, Sub-I covered majority of visit.' "
                    "Enrollment still on track but items 5 and 9 note: 'PI delegation of monitoring activities to Sub-I increasing.' "
                    "Recruitment rate adequate: Yes (marginally). 2-3 routine findings."
                ),
            },
            {
                "visit_index": 5, "visit_label": "Visit 6",
                "anomaly_context": (
                    "PI ABSENT: 'PI unavailable due to competing study commitments; Sub-Investigator conducted all monitoring activities.' "
                    "PI engagement: pi_present=false, engagement_quality='low', "
                    "notes='PI unavailable due to competing study commitments. Sub-I expressed difficulty reaching PI for protocol questions.' "
                    "Item 5: 'PI available? No — PI on competing study leave.' Item 9: 'Delegation log updated for Sub-I responsibilities.' "
                    "Enrollment DECELERATING: recruitment_rate_adequate should be 'Borderline — screening volume declining.' "
                    "Summary must reference competing study and PI availability concerns."
                ),
            },
            {
                "visit_index": 6, "visit_label": "Visit 7",
                "anomaly_context": (
                    "ENROLLMENT STALL: recruitment_rate_adequate='No'. PI still absent — Sub-I managing all activities. "
                    "PI engagement: pi_present=false, engagement_quality='low', "
                    "notes='PI continues to be unavailable. Sub-I reports difficulty in patient recruitment without PI involvement in referral networks.' "
                    "Item 5: 'PI available? No — second consecutive visit without PI presence.' "
                    "Summary: 'Recruitment rate has fallen below target. Sub-I expressed concern about PI engagement "
                    "and its impact on recruitment pipeline.' Action Required: 'Escalate PI availability concerns to sponsor.' "
                    "4-5 findings, including enrollment-related items."
                ),
            },
            {
                "visit_index": 8, "visit_label": "Visit 9 (latest)",
                "anomaly_context": (
                    "CRITICAL PI DECLINE: 'PI on competing study, site leadership considering delegation of PI responsibilities.' "
                    "PI engagement: pi_present=false, engagement_quality='low', "
                    "notes='PI has not been available for the last 3 monitoring visits. Site is considering formal PI delegation. "
                    "Enrollment has effectively stalled — zero new screenings in the past 4 weeks.' "
                    "Item 5: 'PI available? No — third consecutive visit. Formal escalation to sponsor recommended.' "
                    "Recruitment rate adequate: 'No — enrollment effectively stopped. Zero screenings in past month.' "
                    "Summary: 'PI engagement has deteriorated significantly. The correlation between PI absence and enrollment decline "
                    "is clear. Site considering PI delegation. Recommend sponsor intervention.' "
                    "5-6 findings. Action Required count: 4+."
                ),
            },
        ],
    },
    "SITE-033": {
        "anomaly": "Monitoring gap / post-gap debt",
        "visits": [
            {
                "visit_index": 1, "visit_label": "Visit 2",
                "anomaly_context": (
                    "NORMAL BASELINE: Routine monitoring visit with 2-3 Action Required items. "
                    "Healthy monitoring cadence. Minor findings — typical of active enrollment. "
                    "Follow-up from prior visit completed. Word count 700-900 words."
                ),
            },
            {
                "visit_index": 2, "visit_label": "Visit 3 (last pre-gap)",
                "anomaly_context": (
                    "LAST VISIT BEFORE THE GAP: Normal visit with 2-3 findings. This is the last monitoring visit "
                    "before a 174-day gap in monitoring coverage begins. The visit itself is routine — "
                    "the gap is about to start but nothing in this visit signals it. This is also the last visit "
                    "by the outgoing CRA before transition. 2-3 Action Required items. Word count 700-900 words."
                ),
            },
            {
                "visit_index": 3, "visit_label": "Visit 4 (first post-gap)",
                "anomaly_context": (
                    "DEBT EXPLOSION — First visit after 174-day monitoring gap (nearly 6 months without oversight). "
                    "This is a NEW CRA making their first visit to this site after the CRA transition. "
                    "8+ Action Required items. The summary MUST include: "
                    "'Backlog of overdue queries discovered — 12 queries aged >30 days identified during SDV review.' "
                    "'Numerous data corrections made without monitor oversight during the gap period.' "
                    "'New CRA notes this is first visit to the site; familiarity with site operations still developing.' "
                    "Item 14: 'ISF complete? No — several documents not filed during gap period.' "
                    "Item 17: 'Prior visit follow-up complete? No — 3 prior actions remain unresolved for >5 months.' "
                    "Item 45: 'SDV identified significant discrepancies accumulated during monitoring gap — 8 subjects "
                    "with CRF data not matching source documents.' "
                    "Item 46: 'Query resolution? No — 12 overdue queries, 5 aged >45 days.' "
                    "Item 34: 'GCP compliance? Action Required — data corrections made without documented justification.' "
                    "Urgent issues: Yes — 'Accumulated data quality debt requires immediate remediation plan.' "
                    "Word count 1000-1200 words (thorough documentation of backlog). Action Required count: 8+."
                ),
            },
            {
                "visit_index": 4, "visit_label": "Visit 5",
                "anomaly_context": (
                    "PARTIAL RECOVERY: 5 findings (still elevated above pre-gap baseline of 2-3). "
                    "CRA working through backlog from post-gap Visit 4. Some prior actions resolved, others still open. "
                    "Follow-up from prior: '3 of 8 actions from Visit 4 resolved, 5 remain open.' "
                    "Summary: 'Progress made in addressing monitoring gap backlog, but significant work remains. "
                    "Query backlog reduced from 12 to 7 overdue queries. Data correction documentation still incomplete.' "
                    "4-5 Action Required items. Word count 800-1000 words."
                ),
            },
            {
                "visit_index": 6, "visit_label": "Visit 7 (latest)",
                "anomaly_context": (
                    "CONTINUED RECOVERY: 3-4 findings (approaching pre-gap baseline of 2-3). "
                    "CRA now familiar with site operations. Most backlog items from post-gap visit resolved. "
                    "Follow-up from prior: 'Majority of outstanding actions now closed. 2 legacy items remain.' "
                    "Summary: 'Site approaching pre-gap operational baseline. Query backlog substantially reduced. "
                    "Remaining items are administrative documentation gaps.' "
                    "3-4 Action Required items. Word count 700-900 words."
                ),
            },
        ],
    },
    "SITE-022": {
        "anomaly": "CRA transition / quality gap",
        "visits": [
            {
                "visit_index": 1, "visit_label": "Visit 2",
                "anomaly_context": (
                    "ORIGINAL CRA — thorough, detailed review. Substantive comments on checklist items. "
                    "Detailed SDV notes per subject with specific observations. Word count 900-1100 words. "
                    "3 findings with specific, actionable items. Executive summary is detailed and analytical. "
                    "CRA assessment references specific protocol sections and provides nuanced evaluation."
                ),
            },
            {
                "visit_index": 3, "visit_label": "Visit 4",
                "anomaly_context": (
                    "ORIGINAL CRA — continues thorough pattern. 3 findings with specific action items. "
                    "Detailed SDV notes per subject — identifies specific data discrepancies by CRF field name. "
                    "Word count 900-1100 words. Comments on checklist items are substantive and specific. "
                    "Follow-up from prior visit is detailed with specific resolution dates and evidence reviewed."
                ),
            },
            {
                "visit_index": 4, "visit_label": "Visit 5 (new CRA's first)",
                "anomaly_context": (
                    "NEW CRA'S FIRST VISIT — dramatic quality drop. Vague summary: 'Site appears cooperative and "
                    "willing to comply with study requirements.' Most checklist items marked 'Yes' with NO comments. "
                    "SDV review is superficial — no specific data discrepancies identified, generic 'all data reviewed' statements. "
                    "Word count drops to 400-500 words (vs original CRA's 900-1100). "
                    "Only 1 finding (vs original CRA's 3). Executive summary is generic and non-specific. "
                    "PI engagement notes are vague: 'PI was available.' (vs original CRA's detailed engagement description). "
                    "CRA assessment: 'Site is performing adequately. No major concerns.' — lacks specificity."
                ),
            },
            {
                "visit_index": 6, "visit_label": "Visit 7",
                "anomaly_context": (
                    "NEW CRA — 2 visits later, ESCALATING problems emerge. Action Required items about entry backlog. "
                    "Item 45: 'Batch corrections noted in multiple eCRF pages — CRF data for 4 subjects appeared to be "
                    "entered or corrected in bulk on a single date.' "
                    "Item 46: 'Query backlog increasing — 8 queries aged >14 days.' "
                    "Summary: 'Data entry backlog has accumulated since CRA transition. Batch data corrections observed.' "
                    "4 findings — problems that the original CRA might have caught earlier. "
                    "Word count still low: 500-600 words. CRA assessment remains vague."
                ),
            },
            {
                "visit_index": 7, "visit_label": "Visit 8 (latest)",
                "anomaly_context": (
                    "NEW CRA — backlog persists, prior actions NOT resolved. "
                    "Follow-up from prior: 'Prior visit action items regarding batch corrections — Status: Open — "
                    "Site has not provided explanation for batch data entry pattern.' "
                    "Item 45: 'Entry backlog persists — data entry lag exceeds 7 days for 6 subjects.' "
                    "Item 46: 'Prior visit queries remain open. 5 new queries generated.' "
                    "Summary: 'Ongoing data entry quality issues. Prior visit action items remain open. "
                    "Entry lag elevated compared to historical site performance.' "
                    "4-5 findings. Word count 500-650 words (still below original CRA baseline). "
                    "The quality gap between old and new CRA is measurable."
                ),
            },
        ],
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# LLM CLIENT (reuse backend Gemini client for generation)
# ═══════════════════════════════════════════════════════════════════════════════

async def _build_llm_client():
    """Build a Gemini client for MVR generation."""
    from backend.config import get_settings
    from backend.llm.gemini import GeminiClient
    settings = get_settings()
    return GeminiClient(settings)


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE QUERIES
# ═══════════════════════════════════════════════════════════════════════════════

def _get_site_context(session: Session, site_id: str) -> dict:
    """Get site metadata and study config."""
    site = session.query(Site).filter(Site.site_id == site_id).first()
    study = session.query(StudyConfig).first()
    if not site:
        return {}
    return {
        "site_id": site.site_id,
        "site_name": site.name,
        "country": site.country,
        "city": site.city,
        "site_type": site.site_type,
        "experience_level": site.experience_level,
        "activation_date": site.activation_date.isoformat() if site.activation_date else "",
        "target_enrollment": site.target_enrollment,
        "anomaly_type": site.anomaly_type,
        "study_title": study.study_title if study else "Phase III Oncology Trial",
        "protocol_name": study.study_id if study else "ONCO-2024-001",
        "nct_number": study.nct_number if study else "",
    }


def _get_enrollment_stats(session: Session, site_id: str, as_of_date=None) -> dict:
    """Get enrollment statistics for a site, optionally as of a specific date."""
    q_screened = session.query(func.count(ScreeningLog.id)).filter(
        ScreeningLog.site_id == site_id
    )
    q_consented = session.query(func.count(ScreeningLog.id)).filter(
        ScreeningLog.site_id == site_id,
        ScreeningLog.outcome.in_(["Passed", "Withdrawn"]),
    )
    q_failed = session.query(func.count(ScreeningLog.id)).filter(
        ScreeningLog.site_id == site_id,
        ScreeningLog.outcome == "Failed",
    )
    q_randomized = session.query(func.count(RandomizationLog.id)).filter(
        RandomizationLog.site_id == site_id
    )
    q_withdrawn = session.query(func.count(ScreeningLog.id)).filter(
        ScreeningLog.site_id == site_id,
        ScreeningLog.outcome == "Withdrawn",
    )

    if as_of_date:
        q_screened = q_screened.filter(ScreeningLog.screening_date <= as_of_date)
        q_consented = q_consented.filter(ScreeningLog.screening_date <= as_of_date)
        q_failed = q_failed.filter(ScreeningLog.screening_date <= as_of_date)
        q_randomized = q_randomized.filter(RandomizationLog.randomization_date <= as_of_date)
        q_withdrawn = q_withdrawn.filter(ScreeningLog.screening_date <= as_of_date)

    screened = q_screened.scalar() or 0
    consented = q_consented.scalar() or 0
    failed = q_failed.scalar() or 0
    randomized = q_randomized.scalar() or 0
    withdrawn = q_withdrawn.scalar() or 0

    return {
        "screened": screened,
        "consented": consented,
        "pre_randomization_failure": failed,
        "randomized": randomized,
        "completed": max(0, randomized - int(randomized * 0.15)),
        "ongoing": int(randomized * 0.15),
        "withdrawn": withdrawn,
    }


def _get_monitoring_visits(session: Session, site_id: str) -> list[dict]:
    """Get completed monitoring visits for a site, ordered by date."""
    visits = session.query(MonitoringVisit).filter(
        MonitoringVisit.site_id == site_id,
        MonitoringVisit.status == "Completed",
    ).order_by(MonitoringVisit.actual_date).all()

    return [
        {
            "id": v.id,
            "site_id": v.site_id,
            "cra_id": v.cra_id,
            "actual_date": v.actual_date.isoformat() if v.actual_date else "",
            "visit_type": v.visit_type,
            "findings_count": v.findings_count,
            "critical_findings": v.critical_findings,
        }
        for v in visits
    ]


def _get_overdue_actions(session: Session, site_id: str) -> list[dict]:
    """Get overdue actions for a site."""
    actions = session.query(OverdueAction).filter(
        OverdueAction.site_id == site_id,
        OverdueAction.status.in_(["Open", "Overdue"]),
    ).all()

    return [
        {
            "action_description": a.action_description,
            "category": a.category,
            "due_date": a.due_date.isoformat() if a.due_date else "",
            "status": a.status,
        }
        for a in actions
    ]


def _get_cra_for_visit(session: Session, site_id: str, visit_date: date) -> str:
    """Get the CRA assigned to a site at a given visit date."""
    assignment = session.query(CRAAssignment).filter(
        CRAAssignment.site_id == site_id,
        CRAAssignment.start_date <= visit_date,
        (CRAAssignment.end_date >= visit_date) | (CRAAssignment.end_date.is_(None)),
    ).first()

    if assignment:
        return assignment.cra_id

    # Fallback: get any CRA assigned to this site
    assignment = session.query(CRAAssignment).filter(
        CRAAssignment.site_id == site_id,
    ).order_by(CRAAssignment.start_date.desc()).first()
    return assignment.cra_id if assignment else "CRA-UNKNOWN"


# ═══════════════════════════════════════════════════════════════════════════════
# PDF RENDERING
# ═══════════════════════════════════════════════════════════════════════════════

def _sanitize_text(text: str) -> str:
    """Replace Unicode characters unsupported by standard PDF fonts with ASCII equivalents."""
    replacements = {
        "\u2014": "--",   # em dash
        "\u2013": "-",    # en dash
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote
        "\u201c": '"',    # left double quote
        "\u201d": '"',    # right double quote
        "\u2026": "...",  # ellipsis
        "\u2022": "*",    # bullet
        "\u00a0": " ",    # non-breaking space
        "\u2010": "-",    # hyphen
        "\u2011": "-",    # non-breaking hyphen
        "\u2012": "-",    # figure dash
        "\u00b7": "*",    # middle dot
        "\u2032": "'",    # prime
        "\u2033": '"',    # double prime
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    # Fallback: replace any remaining non-latin1 characters
    return text.encode("latin-1", errors="replace").decode("latin-1")


class MVRReport(FPDF):
    """Custom PDF class for MVR reports following ARBA template."""

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "MONITORING VISIT REPORT", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def _section_header(self, title: str):
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(230, 230, 240)
        self.cell(0, 8, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def _key_value(self, key: str, value: str, key_w: int = 60):
        self.set_font("Helvetica", "B", 9)
        self.cell(key_w, 6, _sanitize_text(key), new_x="RIGHT")
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 6, _sanitize_text(str(value)), new_x="LMARGIN", new_y="NEXT")

    def _narrative(self, text: str):
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 5, _sanitize_text(str(text)), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)


def render_mvr_pdf(mvr_data: dict, site_context: dict, output_path: Path):
    """Render an MVR PDF from structured JSON data."""
    pdf = MVRReport()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ── Page 1: Metadata + Summary ──
    pdf._section_header("VISIT INFORMATION")
    pdf._key_value("Protocol Title:", site_context.get("study_title", ""))
    pdf._key_value("Protocol Name:", site_context.get("protocol_name", ""))
    pdf._key_value("Site Name / Site #:", f"{site_context.get('site_name', '')} / {site_context.get('site_id', '')}")
    pdf._key_value("Site Address:", f"{site_context.get('city', '')}, {site_context.get('country', '')}")
    pdf._key_value("Site Activation Date:", site_context.get("activation_date", ""))
    pdf._key_value("Monitoring Visit Date:", mvr_data.get("visit_date", ""))
    pdf._key_value("Visit Type:", mvr_data.get("visit_type", "On-Site"))
    pdf._key_value("CRA:", mvr_data.get("cra_id", ""))
    pdf.ln(3)

    # Summary
    pdf._section_header("SUMMARY OF MONITORING VISIT")
    pdf._narrative(mvr_data.get("executive_summary", ""))

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, "Overall Impression:", new_x="LMARGIN", new_y="NEXT")
    pdf._narrative(mvr_data.get("overall_impression", ""))

    if mvr_data.get("exit_interview_comments"):
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, "Exit Interview Comments:", new_x="LMARGIN", new_y="NEXT")
        pdf._narrative(mvr_data.get("exit_interview_comments", ""))

    # ── Urgent Issues ──
    pdf._section_header("URGENT ISSUES")
    urgent = mvr_data.get("urgent_issues", [])
    if urgent:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, "Yes", new_x="LMARGIN", new_y="NEXT")
        for issue in urgent:
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, _sanitize_text(f"  {issue.get('letter', '')}. {issue.get('description', '')}"), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, "No", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # ── Persons Present ──
    pdf._section_header("PERSONS PRESENT")
    persons = mvr_data.get("persons_present", [])
    if persons:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(90, 6, "Name", border=1, new_x="RIGHT")
        pdf.cell(0, 6, "Position/Title", border=1, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for p in persons:
            pdf.cell(90, 6, _sanitize_text(p.get("name", "")), border=1, new_x="RIGHT")
            pdf.cell(0, 6, _sanitize_text(p.get("position", "")), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # ── Enrollment Status ──
    pdf._section_header("ENROLLMENT STATUS")
    enrollment = mvr_data.get("enrollment_status", {})
    for key in ["screened", "consented", "pre_randomization_failure", "randomized", "completed", "ongoing", "withdrawn"]:
        pdf._key_value(f"  {key.replace('_', ' ').title()}:", str(enrollment.get(key, 0)))

    if mvr_data.get("recruitment_plan_notes"):
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, "Recruitment Plan Notes:", new_x="LMARGIN", new_y="NEXT")
        pdf._narrative(mvr_data.get("recruitment_plan_notes", ""))

    rate_adequate = mvr_data.get("recruitment_rate_adequate", True)
    rate_str = "Yes" if rate_adequate is True else ("No" if rate_adequate is False else str(rate_adequate))
    pdf._key_value("Recruitment Rate Adequate?", rate_str)
    pdf.ln(2)

    # ── Monitoring Checklist ──
    pdf.add_page()
    pdf._section_header("MONITORING CHECKLIST")
    checklist = mvr_data.get("checklist_items", [])
    current_section = ""
    for item in checklist:
        section = item.get("section", "")
        if section != current_section:
            current_section = section
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(245, 245, 250)
            pdf.cell(0, 6, _sanitize_text(f"  {section}"), fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 8)
        item_num = str(item.get("item_number", ""))
        question = _sanitize_text(item.get("question", ""))[:80]
        response = _sanitize_text(item.get("response", ""))
        action = _sanitize_text(item.get("action_required", ""))

        pdf.cell(10, 5, item_num, border=1, new_x="RIGHT")
        pdf.cell(100, 5, question, border=1, new_x="RIGHT")
        pdf.cell(15, 5, response, border=1, align="C", new_x="RIGHT")

        if action:
            pdf.set_text_color(180, 0, 0)
            pdf.cell(0, 5, action[:60], border=1, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        else:
            comments = _sanitize_text(item.get("comments", ""))
            pdf.cell(0, 5, comments[:60] if comments else "", border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)

    # ── SDV Findings ──
    pdf.add_page()
    pdf._section_header("SOURCE DOCUMENT VERIFICATION & CHART REVIEW")
    sdv = mvr_data.get("sdv_findings", [])
    if sdv:
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(25, 6, "Subject", border=1, new_x="RIGHT")
        pdf.cell(40, 6, "Visits Reviewed", border=1, new_x="RIGHT")
        pdf.cell(60, 6, "Comments", border=1, new_x="RIGHT")
        pdf.cell(0, 6, "Action Required", border=1, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        for s in sdv:
            pdf.cell(25, 5, _sanitize_text(str(s.get("subject_id", "")))[:12], border=1, new_x="RIGHT")
            pdf.cell(40, 5, _sanitize_text(str(s.get("visits_reviewed", "")))[:25], border=1, new_x="RIGHT")
            pdf.cell(60, 5, _sanitize_text(str(s.get("comments", "")))[:40], border=1, new_x="RIGHT")
            action = _sanitize_text(str(s.get("action_required", "")))
            if action:
                pdf.set_text_color(180, 0, 0)
            pdf.cell(0, 5, action[:35], border=1, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    # ── Follow-up from Prior ──
    follow_up = mvr_data.get("follow_up_from_prior", [])
    if follow_up:
        pdf._section_header("FOLLOW-UP FROM PRIOR VISIT")
        for f in follow_up:
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, _sanitize_text(f"Action: {f.get('action', '')}  |  Status: {f.get('status', '')}  |  {f.get('comment', '')}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # ── CRA Assessment ──
    pdf._section_header("CRA ASSESSMENT")
    pdf._narrative(mvr_data.get("cra_assessment", ""))

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    logger.info("PDF saved: %s", output_path)


# ═══════════════════════════════════════════════════════════════════════════════
# LLM CONTENT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_llm_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove markdown fences
        lines = cleaned.split("\n")
        start = 1
        end = len(lines)
        for i, line in enumerate(lines):
            if i > 0 and line.strip().startswith("```"):
                end = i
                break
        cleaned = "\n".join(lines[start:end])
    return json.loads(cleaned)


async def _generate_mvr_content(
    llm_client,
    prompt_template: str,
    site_id: str,
    cra_id: str,
    visit_date: str,
    visit_type: str,
    visit_number: int,
    anomaly_context: str,
    prior_mvr_summaries: str,
    enrollment_stats: dict,
    site_context: dict,
    overdue_actions: list,
    findings_count: int,
    critical_findings: int,
) -> dict:
    """Call LLM to generate structured MVR content."""
    prompt = prompt_template.format(
        site_id=site_id,
        cra_id=cra_id,
        visit_date=visit_date,
        visit_type=visit_type,
        visit_number=visit_number,
        anomaly_context=anomaly_context,
        prior_mvr_summaries=prior_mvr_summaries or "No prior MVRs — this is the first documented visit.",
        enrollment_stats=json.dumps(enrollment_stats, indent=2),
        site_context=json.dumps(site_context, indent=2),
        overdue_actions=json.dumps(overdue_actions, indent=2) if overdue_actions else "No overdue actions.",
        findings_count=findings_count,
        critical_findings=critical_findings,
    )

    system = (
        "You are a clinical monitoring expert generating realistic Monitoring Visit Reports. "
        "Respond ONLY with valid JSON. No markdown fences, no commentary."
    )

    response = await llm_client.generate(prompt, system=system)
    return _parse_llm_json(response.text)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GENERATION PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

async def generate_all_mvrs(site_filter: list[str] | None = None):
    """Generate MVRs across priority sites. Optionally filter to specific site_ids."""
    # Ensure table exists
    Base.metadata.create_all(engine, checkfirst=True)

    session = SessionLocal()
    llm_client = await _build_llm_client()

    # Load prompt template
    prompt_path = _ROOT / "prompt" / "mvr_generate.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    output_base = _ROOT / "monitoring_reports" / "generated"
    total_generated = 0
    total_errors = 0

    # Determine which sites to process
    target_sites = site_filter if site_filter else list(VISIT_SELECTION_MAP.keys())

    # Clear existing MVR reports for target sites
    existing = session.query(MonitoringVisitReport).filter(
        MonitoringVisitReport.site_id.in_(target_sites)
    ).all()
    if existing:
        logger.info("Clearing %d existing MVR reports for regeneration", len(existing))
        for row in existing:
            session.delete(row)
        session.commit()

    try:
        for site_id, site_config in VISIT_SELECTION_MAP.items():
            if site_id not in target_sites:
                continue
            logger.info("=" * 60)
            logger.info("Generating MVRs for %s — %s", site_id, site_config["anomaly"])

            # Get site data
            site_context = _get_site_context(session, site_id)
            # enrollment_stats fetched per-visit below for temporal accuracy
            monitoring_visits = _get_monitoring_visits(session, site_id)
            overdue_actions = _get_overdue_actions(session, site_id)

            if not monitoring_visits:
                logger.warning("No completed monitoring visits found for %s — skipping", site_id)
                continue

            logger.info("  Found %d completed monitoring visits", len(monitoring_visits))

            # Track prior MVR summaries for temporal continuity
            prior_summaries = []

            for visit_spec in site_config["visits"]:
                visit_idx = visit_spec["visit_index"]
                visit_label = visit_spec["visit_label"]
                anomaly_context = visit_spec["anomaly_context"]

                if visit_idx >= len(monitoring_visits):
                    logger.warning("  Visit index %d out of range (only %d visits) for %s — skipping",
                                   visit_idx, len(monitoring_visits), site_id)
                    continue

                visit = monitoring_visits[visit_idx]
                visit_date = visit["actual_date"]
                cra_id = visit.get("cra_id") or _get_cra_for_visit(session, site_id, date.fromisoformat(visit_date))
                visit_type = visit.get("visit_type", "On-Site")
                visit_number = visit_idx + 1

                logger.info("  Generating MVR %d/%d: %s (%s) — CRA: %s",
                            visit_number, len(site_config["visits"]), visit_label, visit_date, cra_id)

                try:
                    # Temporal enrollment as of this visit date
                    enrollment_stats = _get_enrollment_stats(session, site_id, as_of_date=date.fromisoformat(visit_date))

                    # Generate content via LLM
                    mvr_content = await _generate_mvr_content(
                        llm_client=llm_client,
                        prompt_template=prompt_template,
                        site_id=site_id,
                        cra_id=cra_id,
                        visit_date=visit_date,
                        visit_type=visit_type,
                        visit_number=visit_number,
                        anomaly_context=anomaly_context,
                        prior_mvr_summaries=json.dumps(prior_summaries, indent=2) if prior_summaries else "",
                        enrollment_stats=enrollment_stats,
                        site_context=site_context,
                        overdue_actions=overdue_actions,
                        findings_count=visit.get("findings_count", 0),
                        critical_findings=visit.get("critical_findings", 0),
                    )

                    # Compute metrics
                    exec_summary = mvr_content.get("executive_summary", "")
                    overall = mvr_content.get("overall_impression", "")
                    cra_assess = mvr_content.get("cra_assessment", "")
                    all_text = f"{exec_summary} {overall} {cra_assess}"
                    word_count = len(all_text.split())

                    checklist = mvr_content.get("checklist_items", [])
                    _no_action = {"no", "n/a", "none", "no action required", "no action required.", ""}
                    action_count = sum(
                        1 for item in checklist
                        if item.get("action_required")
                        and str(item["action_required"]).strip().lower() not in _no_action
                    )

                    # Also count SDV action required items
                    sdv = mvr_content.get("sdv_findings", [])
                    action_count += sum(
                        1 for s in sdv
                        if s.get("action_required")
                        and str(s["action_required"]).strip().lower() not in _no_action
                    )

                    # Render PDF
                    pdf_filename = f"{site_id}/MVR_{site_id}_{visit_date}.pdf"
                    pdf_path = output_base / pdf_filename

                    mvr_content["visit_date"] = visit_date
                    mvr_content["cra_id"] = cra_id
                    render_mvr_pdf(mvr_content, site_context, pdf_path)

                    # Build findings JSONB
                    findings_json = [
                        {
                            "item_number": item.get("item_number"),
                            "section": item.get("section"),
                            "question": item.get("question"),
                            "response": item.get("response"),
                            "action_required": item.get("action_required", ""),
                            "comments": item.get("comments", ""),
                        }
                        for item in checklist
                        if item.get("action_required") or item.get("response") == "No"
                    ]

                    # Insert DB row
                    mvr_row = MonitoringVisitReport(
                        monitoring_visit_id=visit["id"],
                        site_id=site_id,
                        cra_id=cra_id,
                        visit_date=date.fromisoformat(visit_date),
                        visit_type=visit_type,
                        visit_number=visit_number,
                        pdf_filename=pdf_filename,
                        executive_summary=exec_summary,
                        overall_impression=overall,
                        urgent_issues=mvr_content.get("urgent_issues", []),
                        enrollment_status=mvr_content.get("enrollment_status", {}),
                        findings=findings_json,
                        sdv_findings=mvr_content.get("sdv_findings", []),
                        pi_engagement=mvr_content.get("pi_engagement", {}),
                        follow_up_from_prior=mvr_content.get("follow_up_from_prior", []),
                        cra_assessment=cra_assess,
                        word_count=word_count,
                        action_required_count=action_count,
                    )
                    session.add(mvr_row)
                    session.commit()

                    total_generated += 1
                    logger.info("    Generated: %s (words: %d, actions: %d)", pdf_filename, word_count, action_count)

                    # Track for temporal continuity
                    prior_summaries.append({
                        "visit_number": visit_number,
                        "visit_date": visit_date,
                        "visit_label": visit_label,
                        "executive_summary": exec_summary[:500],
                        "action_required_count": action_count,
                        "word_count": word_count,
                    })

                except Exception as e:
                    total_errors += 1
                    logger.error("    FAILED to generate MVR for %s %s: %s", site_id, visit_label, e, exc_info=True)
                    session.rollback()
                    continue

    finally:
        session.close()

    logger.info("=" * 60)
    logger.info("MVR GENERATION COMPLETE: %d generated, %d errors", total_generated, total_errors)
    logger.info("PDFs saved under: %s", output_base)

    # Verification
    verify_session = SessionLocal()
    try:
        count = verify_session.query(func.count(MonitoringVisitReport.id)).scalar()
        logger.info("Verification: %d rows in monitoring_visit_reports table", count)
        for site_id in VISIT_SELECTION_MAP:
            site_count = verify_session.query(func.count(MonitoringVisitReport.id)).filter(
                MonitoringVisitReport.site_id == site_id
            ).scalar()
            logger.info("  %s: %d MVRs", site_id, site_count)
    finally:
        verify_session.close()


def main():
    import sys
    site_filter = sys.argv[1:] if len(sys.argv) > 1 else None
    asyncio.run(generate_all_mvrs(site_filter=site_filter))


if __name__ == "__main__":
    main()
