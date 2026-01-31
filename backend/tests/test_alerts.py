"""Tests for /api/alerts endpoints."""

import pytest
from backend.models.governance import AlertLog, AgentFinding


@pytest.fixture()
def seed_alert(db_session):
    """Insert a finding + alert for tests."""
    finding = AgentFinding(
        agent_id="data_quality",
        finding_type="test_finding",
        severity="warning",
        summary="Test finding for alerts",
    )
    db_session.add(finding)
    db_session.flush()

    alert = AlertLog(
        finding_id=finding.id,
        agent_id="data_quality",
        severity="warning",
        site_id="SITE-TEST",
        title="Test alert",
        description="Created by test fixture",
        status="open",
        suppressed=False,
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    return alert


def test_list_alerts_returns_200(client):
    resp = client.get("/api/alerts/")
    assert resp.status_code == 200
    data = resp.json()
    assert "alerts" in data
    assert "total" in data


def test_get_alert_by_id(client, seed_alert):
    resp = client.get(f"/api/alerts/{seed_alert.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == seed_alert.id


def test_get_alert_not_found(client):
    resp = client.get("/api/alerts/999999")
    assert resp.status_code == 404


def test_suppress_alert(client, seed_alert):
    resp = client.post(
        f"/api/alerts/{seed_alert.id}/suppress",
        json={"reason": "Test suppression", "created_by": "tester"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "suppressed"


def test_suppress_alert_not_found(client):
    resp = client.post(
        "/api/alerts/999999/suppress",
        json={"reason": "does not exist"},
    )
    assert resp.status_code == 404


def test_acknowledge_alert(client, seed_alert):
    resp = client.post(
        f"/api/alerts/{seed_alert.id}/acknowledge",
        json={"acknowledged_by": "tester@clinops.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"


def test_acknowledge_alert_not_found(client):
    resp = client.post(
        "/api/alerts/999999/acknowledge",
        json={"acknowledged_by": "tester@clinops.com"},
    )
    assert resp.status_code == 404
