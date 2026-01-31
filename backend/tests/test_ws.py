"""Tests for /ws/query/{query_id} WebSocket endpoint."""

import pytest
from unittest.mock import patch

from backend.models.governance import ConversationalInteraction
from backend.routers.query import _query_results


@pytest.fixture()
def _patch_ws_session(db_session):
    """Patch SessionLocal in the WS router to use the test session, with close() no-oped."""
    original_close = db_session.close
    db_session.close = lambda: None
    with patch("backend.routers.ws.SessionLocal", return_value=db_session):
        yield
    db_session.close = original_close


class TestWebSocket:

    def test_ws_query_not_found(self, client, _patch_ws_session):
        """WebSocket for unknown query_id sends error and closes."""
        with client.websocket_connect("/ws/query/does-not-exist") as ws:
            data = ws.receive_json()
            assert "error" in data
            assert "not found" in data["error"].lower()

    def test_ws_completed_query_returns_cached(self, client, db_session, _patch_ws_session):
        """WebSocket for a completed query returns cached synthesis."""
        interaction = ConversationalInteraction(
            query_id="ws-test-completed",
            session_id="ws-sess",
            user_query="test question",
            status="completed",
            synthesized_response="Test summary",
        )
        db_session.add(interaction)
        db_session.commit()

        _query_results["ws-test-completed"] = {
            "synthesis": {"executive_summary": "Test summary"},
            "agent_outputs": {},
        }

        try:
            with client.websocket_connect("/ws/query/ws-test-completed") as ws:
                data = ws.receive_json()
                assert data["phase"] == "complete"
                assert data["cached"] is True
        finally:
            _query_results.pop("ws-test-completed", None)

    def test_ws_processing_query_rejected(self, client, db_session, _patch_ws_session):
        """WebSocket for an already-processing query sends info and closes."""
        interaction = ConversationalInteraction(
            query_id="ws-test-processing",
            session_id="ws-sess-2",
            user_query="in-progress question",
            status="processing",
        )
        db_session.add(interaction)
        db_session.commit()

        with client.websocket_connect("/ws/query/ws-test-processing") as ws:
            data = ws.receive_json()
            assert data["phase"] == "info"
            assert "already being processed" in data["message"]
