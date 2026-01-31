"""Tests for /api/agents endpoints."""


def test_list_agents_returns_200(client):
    resp = client.get("/api/agents/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_list_agents_structure(client):
    data = client.get("/api/agents/").json()
    for agent in data:
        assert "agent_id" in agent
        assert "name" in agent
        assert "description" in agent


def test_invoke_unknown_agent_returns_404(client):
    resp = client.post(
        "/api/agents/nonexistent_agent/invoke",
        json={"query": "test question"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_findings_returns_list(client):
    resp = client.get("/api/agents/data_quality/findings?limit=5")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
