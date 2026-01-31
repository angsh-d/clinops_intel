"""Alert service: creates alerts from agent findings, checks suppression rules."""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models.governance import AlertLog, AgentFinding, SuppressionRule

logger = logging.getLogger(__name__)


class AlertService:
    """Creates and manages alerts from agent findings."""

    def create_alerts_from_findings(self, finding_id: int, db: Session) -> list[AlertLog]:
        """Create alerts from a stored agent finding, respecting suppression rules."""
        finding = db.query(AgentFinding).filter_by(id=finding_id).first()
        if not finding:
            logger.warning("Finding %d not found", finding_id)
            return []

        # Check active suppression rules
        active_suppressions = db.query(SuppressionRule).filter(
            SuppressionRule.is_active.is_(True),
            (SuppressionRule.agent_id == finding.agent_id) | (SuppressionRule.agent_id.is_(None)),
        ).all()

        suppressed = False
        suppression_rule_id = None
        for rule in active_suppressions:
            if rule.expires_at and rule.expires_at.replace(tzinfo=None) < datetime.utcnow():
                continue
            if rule.site_id and rule.site_id != finding.site_id:
                continue
            if rule.finding_type and rule.finding_type != finding.finding_type:
                continue
            suppressed = True
            suppression_rule_id = rule.id
            break

        alert = AlertLog(
            finding_id=finding_id,
            agent_id=finding.agent_id,
            severity=finding.severity,
            site_id=finding.site_id,
            title=finding.summary[:300],
            description=finding.summary,
            status="suppressed" if suppressed else "open",
            suppressed=suppressed,
            suppression_rule_id=suppression_rule_id,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        logger.info("Created alert %d from finding %d (suppressed=%s)", alert.id, finding_id, suppressed)
        return [alert]
