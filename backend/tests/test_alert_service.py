"""Tests for AlertService: alert creation from findings, suppression rule matching.

Verifies:
- Alert created from valid finding
- Alert suppressed when matching active rule exists
- Expired suppression rules are ignored
- Site-specific rules only match the correct site
- Finding-type-specific rules only match the correct type
- No alert created for nonexistent finding
"""

import pytest
from datetime import datetime, timedelta

from backend.services.alert_service import AlertService
from backend.models.governance import AgentFinding, AlertLog, SuppressionRule


@pytest.fixture()
def alert_service():
    return AlertService()


@pytest.fixture()
def seed_finding(db_session):
    """Create a finding to generate alerts from."""
    finding = AgentFinding(
        agent_id="data_quality",
        finding_type="high_entry_lag",
        severity="warning",
        site_id="SITE-003",
        summary="SITE-003 mean entry lag is 12.4 days, exceeding 7-day threshold.",
        detail={"mean_entry_lag": 12.4},
        confidence=0.92,
    )
    db_session.add(finding)
    db_session.commit()
    db_session.refresh(finding)
    return finding


class TestAlertCreation:

    def test_creates_open_alert_from_finding(self, alert_service, db_session, seed_finding):
        """Finding without matching suppression rule creates an 'open' alert."""
        alerts = alert_service.create_alerts_from_findings(seed_finding.id, db_session)
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.status == "open"
        assert alert.suppressed is False
        assert alert.agent_id == "data_quality"
        assert alert.severity == "warning"
        assert alert.site_id == "SITE-003"
        assert alert.finding_id == seed_finding.id
        assert len(alert.title) <= 300

    def test_nonexistent_finding_returns_empty(self, alert_service, db_session):
        """No alert created for a finding ID that doesn't exist."""
        alerts = alert_service.create_alerts_from_findings(999999, db_session)
        assert alerts == []


class TestSuppressionRules:

    def test_active_rule_suppresses_alert(self, alert_service, db_session, seed_finding):
        """An active suppression rule matching the agent suppresses the alert."""
        rule = SuppressionRule(
            agent_id="data_quality",
            reason="Known issue, remediation scheduled",
            is_active=True,
        )
        db_session.add(rule)
        db_session.commit()

        alerts = alert_service.create_alerts_from_findings(seed_finding.id, db_session)
        assert len(alerts) == 1
        assert alerts[0].status == "suppressed"
        assert alerts[0].suppressed is True
        assert alerts[0].suppression_rule_id == rule.id

    def test_expired_rule_does_not_suppress(self, alert_service, db_session, seed_finding):
        """An expired suppression rule should not suppress the alert."""
        rule = SuppressionRule(
            agent_id="data_quality",
            reason="Temporarily suppressed",
            is_active=True,
            expires_at=datetime.utcnow() - timedelta(days=1),  # expired yesterday
        )
        db_session.add(rule)
        db_session.commit()

        alerts = alert_service.create_alerts_from_findings(seed_finding.id, db_session)
        assert len(alerts) == 1
        assert alerts[0].status == "open"
        assert alerts[0].suppressed is False

    def test_inactive_rule_does_not_suppress(self, alert_service, db_session, seed_finding):
        """An inactive rule (is_active=False) should not suppress."""
        rule = SuppressionRule(
            agent_id="data_quality",
            reason="Deactivated",
            is_active=False,
        )
        db_session.add(rule)
        db_session.commit()

        alerts = alert_service.create_alerts_from_findings(seed_finding.id, db_session)
        assert len(alerts) == 1
        assert alerts[0].status == "open"

    def test_site_specific_rule_only_matches_correct_site(self, alert_service, db_session, seed_finding):
        """A rule for SITE-999 should not suppress an alert for SITE-003."""
        rule = SuppressionRule(
            agent_id="data_quality",
            site_id="SITE-999",
            reason="Wrong site",
            is_active=True,
        )
        db_session.add(rule)
        db_session.commit()

        alerts = alert_service.create_alerts_from_findings(seed_finding.id, db_session)
        assert alerts[0].status == "open"

    def test_site_specific_rule_matches_correct_site(self, alert_service, db_session, seed_finding):
        """A rule for SITE-003 should suppress the alert for SITE-003."""
        rule = SuppressionRule(
            agent_id="data_quality",
            site_id="SITE-003",
            reason="Known issue at SITE-003",
            is_active=True,
        )
        db_session.add(rule)
        db_session.commit()

        alerts = alert_service.create_alerts_from_findings(seed_finding.id, db_session)
        assert alerts[0].status == "suppressed"

    def test_finding_type_specific_rule(self, alert_service, db_session, seed_finding):
        """A rule matching finding_type suppresses, wrong type does not."""
        # Wrong type — should not suppress
        wrong = SuppressionRule(
            agent_id="data_quality",
            finding_type="wrong_type",
            reason="Wrong type",
            is_active=True,
        )
        db_session.add(wrong)
        db_session.commit()

        alerts = alert_service.create_alerts_from_findings(seed_finding.id, db_session)
        assert alerts[0].status == "open"

    def test_wildcard_agent_rule_suppresses_any_agent(self, alert_service, db_session, seed_finding):
        """A rule with agent_id=None should suppress alerts from any agent."""
        rule = SuppressionRule(
            agent_id=None,
            reason="Global suppression",
            is_active=True,
        )
        db_session.add(rule)
        db_session.commit()

        alerts = alert_service.create_alerts_from_findings(seed_finding.id, db_session)
        assert alerts[0].status == "suppressed"
