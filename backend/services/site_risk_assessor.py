"""LLM-driven site risk assessment service.

Replaces deterministic hardcoded thresholds with multi-dimensional LLM analysis.
Runs as part of proactive scans after intelligence brief generation.
"""

import json
import logging
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.llm.failover import FailoverLLMClient
from backend.llm.utils import parse_llm_json
from backend.models.governance import (
    AlertLog, SiteIntelligenceBrief, SiteRiskAssessment,
)
from backend.prompts.manager import get_prompt_manager
from data_generators.models import (
    CRAAssignment, ECRFEntry, MonitoringVisit, MonitoringVisitReport, Query,
    RandomizationLog, Site, StudyConfig, SubjectVisit,
)

logger = logging.getLogger(__name__)


class SiteRiskAssessor:
    """LLM-driven site risk assessment, run as part of proactive scans."""

    BATCH_SIZE = 20  # Sites per LLM call

    async def assess_all_sites(
        self, scan_id: str, db: Session,
    ) -> list[SiteRiskAssessment]:
        """Assess all sites in batches. Called after brief generation in proactive scan."""
        settings = get_settings()
        llm = FailoverLLMClient(settings)
        prompts = get_prompt_manager()

        sites = db.query(Site).all()
        if not sites:
            logger.warning("No sites found for risk assessment")
            return []

        # Gather study-level context
        study_context = self._build_study_context(db, len(sites))

        # Gather per-site operational signals
        site_signals = self._gather_site_signals(db, sites)

        # Load latest intelligence briefs for enrichment
        brief_map = self._load_latest_briefs(db)

        # Build per-site data packages
        site_packages = []
        for site in sites:
            package = self._build_site_package(site, site_signals, brief_map)
            site_packages.append(package)

        # Process in batches
        all_assessments: list[SiteRiskAssessment] = []
        for i in range(0, len(site_packages), self.BATCH_SIZE):
            batch = site_packages[i : i + self.BATCH_SIZE]
            try:
                batch_assessments = await self._assess_batch(
                    scan_id, batch, study_context, llm, prompts, db,
                )
                all_assessments.extend(batch_assessments)
            except Exception as e:
                site_ids = [p["site_id"] for p in batch]
                logger.error(
                    "Risk assessment batch failed for sites %s: %s",
                    site_ids, e,
                )

        logger.info(
            "Risk assessment complete for scan %s: %d/%d sites assessed",
            scan_id, len(all_assessments), len(sites),
        )
        return all_assessments

    def _build_study_context(self, db: Session, total_sites: int) -> str:
        """Build study-level context string for the prompt."""
        study = db.query(StudyConfig).first()

        total_enrolled = db.query(func.count(RandomizationLog.id)).scalar() or 0
        total_target = (
            db.query(func.sum(Site.target_enrollment)).scalar() or 0
        )
        avg_enrollment_pct = (
            round((total_enrolled / total_target) * 100, 1) if total_target else 0
        )

        context_parts = [
            f"Total sites: {total_sites}",
            f"Total enrolled: {total_enrolled} / {total_target} ({avg_enrollment_pct}%)",
        ]
        if study:
            if study.study_title:
                context_parts.insert(0, f"Study: {study.study_title}")
            if study.phase:
                context_parts.append(f"Phase: {study.phase}")
            if study.study_start_date:
                context_parts.append(f"Study start: {study.study_start_date}")
            today = date.today()
            if study.study_start_date:
                days_in = (today - study.study_start_date).days
                context_parts.append(f"Days since study start: {days_in}")

        return "\n".join(context_parts)

    def _gather_site_signals(
        self, db: Session, sites: list[Site],
    ) -> dict[str, dict]:
        """Gather operational signals for all sites in bulk queries."""
        # Open query counts
        query_counts = dict(
            db.query(Query.site_id, func.count(Query.id))
            .filter(Query.status == "Open")
            .group_by(Query.site_id)
            .all()
        )

        # Average entry lag
        avg_lags = dict(
            db.query(
                ECRFEntry.site_id,
                func.avg(ECRFEntry.entry_lag_days),
            )
            .group_by(ECRFEntry.site_id)
            .all()
        )

        # Enrollment counts
        enrollment_counts = dict(
            db.query(RandomizationLog.site_id, func.count(RandomizationLog.id))
            .group_by(RandomizationLog.site_id)
            .all()
        )

        # Open alert counts
        alert_counts = dict(
            db.query(AlertLog.site_id, func.count(AlertLog.id))
            .filter(AlertLog.status == "open")
            .group_by(AlertLog.site_id)
            .all()
        )

        # CRA assignment count (current)
        cra_counts = dict(
            db.query(CRAAssignment.site_id, func.count(CRAAssignment.id))
            .filter(CRAAssignment.is_current.is_(True))
            .group_by(CRAAssignment.site_id)
            .all()
        )

        # Monitoring visit count
        monitoring_counts = dict(
            db.query(MonitoringVisit.site_id, func.count(MonitoringVisit.id))
            .group_by(MonitoringVisit.site_id)
            .all()
        )

        # Visit compliance (missed visits per site)
        missed_visits = dict(
            db.query(
                Site.site_id,
                func.count(SubjectVisit.id),
            )
            .join(RandomizationLog, RandomizationLog.site_id == Site.site_id)
            .join(SubjectVisit, SubjectVisit.subject_id == RandomizationLog.subject_id)
            .filter(SubjectVisit.visit_status == "Missed")
            .group_by(Site.site_id)
            .all()
        )

        # MVR (Monitoring Visit Report) narrative signals per site
        mvr_signals = self._gather_mvr_signals(db)

        signals = {}
        for site in sites:
            sid = site.site_id
            target = site.target_enrollment or 0
            enrolled = enrollment_counts.get(sid, 0)
            enrollment_pct = (
                round((enrolled / target) * 100, 1) if target else 0
            )

            signals[sid] = {
                "open_queries": query_counts.get(sid, 0),
                "avg_entry_lag_days": round(float(avg_lags.get(sid, 0) or 0), 1),
                "enrolled": enrolled,
                "target_enrollment": target,
                "enrollment_pct": enrollment_pct,
                "open_alerts": alert_counts.get(sid, 0),
                "current_cra_count": cra_counts.get(sid, 0),
                "monitoring_visits": monitoring_counts.get(sid, 0),
                "missed_visits": missed_visits.get(sid, 0),
                "anomaly_type": site.anomaly_type,
                "activation_date": str(site.activation_date) if site.activation_date else None,
            }

            # Merge MVR signals if available for this site
            if sid in mvr_signals:
                signals[sid]["mvr_analysis"] = mvr_signals[sid]

        return signals

    def _gather_mvr_signals(self, db: Session) -> dict[str, dict]:
        """Extract MVR narrative signals per site for risk assessment.

        Analyses monitoring visit report narratives to surface:
        - Action required count trends (escalation or stagnation)
        - Word count patterns (rubber-stamping detection)
        - PI engagement trajectory
        - Zombie findings (recurring after resolution)
        - CRA transition quality gaps
        """
        mvrs = (
            db.query(MonitoringVisitReport)
            .order_by(MonitoringVisitReport.site_id, MonitoringVisitReport.visit_date)
            .all()
        )
        if not mvrs:
            return {}

        # Group by site
        from collections import defaultdict
        site_mvrs: dict[str, list] = defaultdict(list)
        for mvr in mvrs:
            site_mvrs[mvr.site_id].append(mvr)

        results = {}
        _no_action = {"no", "n/a", "none", "no action required", "no action required.", ""}

        for sid, reports in site_mvrs.items():
            report_count = len(reports)
            action_counts = [r.action_required_count or 0 for r in reports]
            word_counts = [r.word_count or 0 for r in reports]
            cra_ids = [r.cra_id for r in reports]
            unique_cras = list(dict.fromkeys(cra_ids))  # preserve order

            # PI engagement trajectory
            pi_trajectory = []
            for r in reports:
                pi = r.pi_engagement or {}
                pi_trajectory.append({
                    "visit_date": r.visit_date.isoformat() if r.visit_date else "",
                    "pi_present": pi.get("pi_present"),
                    "engagement_quality": pi.get("engagement_quality"),
                    "notes": pi.get("notes", "")[:100],
                })

            # Zombie findings: items resolved then reappearing
            zombie_count = 0
            for i, r in enumerate(reports):
                follow_ups = r.follow_up_from_prior or []
                for fu in follow_ups:
                    if str(fu.get("status", "")).lower() in ("resolved", "closed"):
                        # Check if similar finding reappears in later reports
                        action_text = str(fu.get("action", "")).lower()
                        for later in reports[i+1:]:
                            later_findings = later.findings or []
                            for f in later_findings:
                                ar = str(f.get("action_required", "")).strip().lower()
                                if ar not in _no_action and action_text and action_text[:30] in ar:
                                    zombie_count += 1
                                    break

            # Zero-finding visits (rubber-stamping indicator)
            zero_finding_visits = sum(1 for ac in action_counts if ac == 0)

            # CRA transition detection
            cra_transition = len(unique_cras) > 1

            # Latest MVR summary for the LLM
            latest = reports[-1]
            latest_summary = (latest.executive_summary or "")[:200]

            # Action trend: compare first half vs second half
            if report_count >= 4:
                mid = report_count // 2
                first_half_avg = sum(action_counts[:mid]) / mid
                second_half_avg = sum(action_counts[mid:]) / (report_count - mid)
                action_trend = "escalating" if second_half_avg > first_half_avg * 1.3 else (
                    "declining" if second_half_avg < first_half_avg * 0.7 else "stable"
                )
            else:
                action_trend = "insufficient_data"

            results[sid] = {
                "mvr_count": report_count,
                "action_required_trend": action_counts,
                "action_trend_direction": action_trend,
                "word_counts": word_counts,
                "avg_word_count": round(sum(word_counts) / report_count) if report_count else 0,
                "zero_finding_visits": zero_finding_visits,
                "zero_finding_pct": round(zero_finding_visits / report_count * 100) if report_count else 0,
                "zombie_finding_count": zombie_count,
                "cra_ids": unique_cras,
                "cra_transition": cra_transition,
                "pi_engagement_trajectory": pi_trajectory,
                "latest_summary": latest_summary,
            }

        return results

    def _load_latest_briefs(self, db: Session) -> dict[str, dict]:
        """Load the most recent intelligence brief per site."""
        # Get latest brief per site via subquery
        latest_per_site = (
            db.query(
                SiteIntelligenceBrief.site_id,
                func.max(SiteIntelligenceBrief.created_at).label("latest"),
            )
            .group_by(SiteIntelligenceBrief.site_id)
            .subquery()
        )

        briefs = (
            db.query(SiteIntelligenceBrief)
            .join(
                latest_per_site,
                (SiteIntelligenceBrief.site_id == latest_per_site.c.site_id)
                & (SiteIntelligenceBrief.created_at == latest_per_site.c.latest),
            )
            .all()
        )

        brief_map = {}
        for b in briefs:
            risk_summary = b.risk_summary or {}
            brief_map[b.site_id] = {
                "risk_level": risk_summary.get("overall_risk", "unknown"),
                "headline": risk_summary.get("headline"),
                "key_risks": b.key_risks[:3] if b.key_risks else [],
                "trend": b.trend_indicator,
                "contributing_agents": [
                    a.get("name") for a in (b.contributing_agents or [])
                ],
            }

        return brief_map

    def _build_site_package(
        self, site: Site, site_signals: dict, brief_map: dict,
    ) -> dict:
        """Build a single site's data package for the prompt."""
        sid = site.site_id
        signals = site_signals.get(sid, {})

        package = {
            "site_id": sid,
            "site_name": site.name or f"Site {sid}",
            "country": site.country,
            "signals": signals,
        }

        brief = brief_map.get(sid)
        if brief:
            package["intelligence_brief"] = brief

        return package

    async def _assess_batch(
        self,
        scan_id: str,
        batch: list[dict],
        study_context: str,
        llm: FailoverLLMClient,
        prompts,
        db: Session,
    ) -> list[SiteRiskAssessment]:
        """Assess a batch of sites via a single LLM call.

        Uses a fresh DB session for persistence to avoid SSL connection drops
        during long LLM calls (Neon pooler closes idle connections).
        """
        from backend.config import SessionLocal

        sites_data = json.dumps(batch, default=str)

        prompt = prompts.render(
            "site_risk_assessment",
            sites_data=sites_data,
            study_context=study_context,
        )

        response = await llm.generate_structured(
            prompt,
            system="You are a clinical operations risk assessment expert. Respond with valid JSON only.",
        )

        parsed = parse_llm_json(response.text)
        assessments_data = parsed.get("assessments", [])

        # Use fresh session for DB writes — the original session may have
        # dropped its SSL connection during the long LLM call
        write_db = SessionLocal()
        persisted: list[SiteRiskAssessment] = []
        try:
            for a in assessments_data:
                try:
                    assessment = SiteRiskAssessment(
                        scan_id=scan_id,
                        site_id=a["site_id"],
                        status=a["status"],
                        risk_score=float(a["risk_score"]),
                        confidence=float(a["confidence"]),
                        dimension_scores=a.get("dimension_scores", {}),
                        status_rationale=a.get("status_rationale", ""),
                        key_drivers=a.get("key_drivers", []),
                        trend=a.get("trend", "stable"),
                    )
                    write_db.add(assessment)
                    persisted.append(assessment)
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(
                        "Skipping malformed assessment for site %s: %s",
                        a.get("site_id", "?"), e,
                    )

            write_db.commit()
            for a in persisted:
                write_db.refresh(a)
        finally:
            write_db.close()

        logger.info(
            "Batch assessed %d/%d sites for scan %s",
            len(persisted), len(batch), scan_id,
        )
        return persisted
