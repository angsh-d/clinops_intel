"""Tests for /api/dashboard endpoints."""


def test_data_quality_returns_200(client):
    resp = client.get("/api/dashboard/data-quality")
    assert resp.status_code == 200


def test_data_quality_structure(client):
    data = client.get("/api/dashboard/data-quality").json()
    assert "sites" in data
    assert "study_total_queries" in data
    for site in data["sites"]:
        assert "site_id" in site
        assert "total_queries" in site
        assert "open_queries" in site


def test_enrollment_funnel_returns_200(client):
    resp = client.get("/api/dashboard/enrollment-funnel")
    assert resp.status_code == 200


def test_enrollment_funnel_structure(client):
    data = client.get("/api/dashboard/enrollment-funnel").json()
    assert "sites" in data
    assert "study_target" in data
    assert "study_pct_of_target" in data
    for site in data["sites"]:
        assert "site_id" in site
        assert "randomized" in site
        assert "pct_of_target" in site
