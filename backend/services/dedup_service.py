"""Finding deduplication: prevents duplicate findings within a time window."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from backend.models.governance import AgentFinding

logger = logging.getLogger(__name__)


def _sanitize_for_jsonb(obj):
    """Recursively convert Decimal and other non-JSON-serializable types to JSON-safe values."""
    if obj is None:
        return None
    return json.loads(json.dumps(obj, default=_json_default))


def _json_default(o):
    """JSON serializer fallback for types not supported by stdlib json."""
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, (datetime,)):
        return o.isoformat()
    return str(o)


class FindingDeduplicator:
    """Deduplicates findings using SHA-256 hash of agent_id + site_id + finding_type + date_bucket.

    Same agent + site + finding_type on the same calendar day → same hash → deduped.
    Next day creates fresh findings (desired for trend tracking).
    """

    def __init__(self, db: Session, date_bucket: str | None = None):
        self.db = db
        self._date_bucket = date_bucket or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def compute_hash(self, agent_id: str, site_id: str, finding_type: str, finding_index: int = 0) -> str:
        """Compute SHA-256 dedup hash for a finding.

        finding_index differentiates multiple findings from the same agent/site/type
        within a single scan. LLM at temp=0 produces findings in consistent order,
        so the same index maps to the same finding on re-scan.
        """
        key = f"{agent_id}|{site_id or 'STUDY'}|{finding_type}|{finding_index}|{self._date_bucket}"
        return hashlib.sha256(key.encode()).hexdigest()

    def is_duplicate(self, agent_id: str, site_id: str, finding_type: str) -> bool:
        """Check if a finding with this hash already exists."""
        dedup_hash = self.compute_hash(agent_id, site_id, finding_type)
        existing = self.db.query(AgentFinding.id).filter_by(dedup_hash=dedup_hash).first()
        return existing is not None

    def persist_finding_if_new(
        self,
        finding_data: dict,
        scan_id: str,
        directive_id: str,
        finding_index: int = 0,
    ) -> AgentFinding | None:
        """Persist a finding only if it's not a duplicate. Returns the finding or None.

        Uses unique constraint on dedup_hash to prevent TOCTOU races from
        concurrent agent executions.
        """
        agent_id = finding_data.get("agent_id", "")
        raw_site_id = finding_data.get("site_id")
        # LLM sometimes returns comma-separated site IDs; take the first one
        # and truncate to fit VARCHAR(20) column
        if raw_site_id and "," in str(raw_site_id):
            site_id = str(raw_site_id).split(",")[0].strip()[:20]
        elif raw_site_id:
            site_id = str(raw_site_id)[:20]
        else:
            site_id = None
        finding_type = finding_data.get("finding_type", "")

        dedup_hash = self.compute_hash(agent_id, site_id, finding_type, finding_index)

        finding = AgentFinding(
            agent_id=agent_id,
            finding_type=finding_type,
            severity=finding_data.get("severity", "info"),
            site_id=site_id,
            summary=finding_data.get("summary", "")[:5000],
            detail=_sanitize_for_jsonb(finding_data.get("detail")),
            data_signals=_sanitize_for_jsonb(finding_data.get("data_signals")),
            reasoning_trace=_sanitize_for_jsonb(finding_data.get("reasoning_trace")),
            confidence=finding_data.get("confidence"),
            dedup_hash=dedup_hash,
            scan_id=scan_id,
            directive_id=directive_id,
        )
        try:
            self.db.add(finding)
            self.db.commit()
            self.db.refresh(finding)
            logger.info("Persisted new finding id=%d (hash=%s)", finding.id, dedup_hash[:12])
            return finding
        except IntegrityError:
            self.db.rollback()
            logger.info("Dedup: duplicate finding detected for hash %s", dedup_hash[:12])
            return None
        except DataError as e:
            self.db.rollback()
            logger.error("Data error persisting finding (hash=%s): %s", dedup_hash[:12], e)
            return None
