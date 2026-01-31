"""Tests for /api/query endpoints."""


def test_submit_query_returns_accepted(client):
    resp = client.post("/api/query/", json={"question": "Which sites are behind?"})
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "accepted"
    assert "query_id" in data


def test_submit_query_empty_question_returns_422(client):
    resp = client.post("/api/query/", json={"question": ""})
    assert resp.status_code == 422


def test_query_status_not_found(client):
    resp = client.get("/api/query/nonexistent-id/status")
    assert resp.status_code == 404


def test_follow_up_parent_not_found(client):
    resp = client.post(
        "/api/query/nonexistent-id/follow-up",
        json={"question": "Tell me more"},
    )
    assert resp.status_code == 404
