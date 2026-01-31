"""Tests for /api/feeds endpoints."""


def test_health_returns_200(client):
    resp = client.get("/api/feeds/health")
    assert resp.status_code == 200


def test_health_has_status_field(client):
    data = client.get("/api/feeds/health").json()
    assert data["status"] in ("healthy", "degraded")


def test_health_data_sources_structure(client):
    data = client.get("/api/feeds/health").json()
    assert "data_sources" in data
    for name, info in data["data_sources"].items():
        assert "row_count" in info
        assert "latest_date" in info


def test_health_row_counts_non_negative(client):
    data = client.get("/api/feeds/health").json()
    for info in data["data_sources"].values():
        assert info["row_count"] >= 0
