"""WebSocket router: stream PRPA phases in real time."""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.config import SessionLocal, get_settings
from backend.conductor.router import ConductorRouter
from backend.llm.failover import FailoverLLMClient
from backend.prompts.manager import get_prompt_manager
from backend.agents.registry import build_agent_registry
from backend.tools.sql_tools import build_tool_registry
from backend.models.governance import ConversationalInteraction
from backend.routers.query import _query_results

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/query/{query_id}")
async def websocket_query(websocket: WebSocket, query_id: str):
    """WebSocket endpoint: streams PRPA phases as the conductor processes a query."""
    await websocket.accept()
    logger.info("WebSocket connected for query %s", query_id)

    db = SessionLocal()
    try:
        # Get the query from DB
        interaction = db.query(ConversationalInteraction).filter_by(query_id=query_id).first()
        if not interaction:
            await websocket.send_json({"error": "Query not found", "query_id": query_id})
            await websocket.close()
            return

        # If already completed, stream cached results instead of re-executing
        if interaction.status == "completed":
            cached = _query_results.get(query_id)
            await websocket.send_json({
                "phase": "complete",
                "query_id": query_id,
                "synthesis": cached.get("synthesis", {}) if cached else {"executive_summary": interaction.synthesized_response or ""},
                "agent_outputs": cached.get("agent_outputs", {}) if cached else interaction.agent_responses or {},
                "routing": cached.get("routing", {}) if cached else {},
                "cached": True,
            })
            await websocket.close()
            return

        if interaction.status == "failed":
            await websocket.send_json({"error": "Query previously failed", "query_id": query_id})
            await websocket.close()
            return

        if interaction.status == "processing":
            await websocket.send_json({
                "error": "Investigation is already in progress. Please wait for it to complete.",
                "query_id": query_id,
            })
            await websocket.close()
            return

        question = interaction.user_query
        session_id = interaction.session_id

        # Build conductor
        settings = get_settings()
        llm = FailoverLLMClient(settings)
        prompts = get_prompt_manager()
        agents = build_agent_registry()
        tools = build_tool_registry()
        conductor = ConductorRouter(llm, prompts, agents, tools)

        # on_step callback streams phases to WebSocket (errors swallowed by BaseAgent)
        async def on_step(phase: str, agent_id: str, data: dict):
            msg = {"phase": phase, "agent_id": agent_id, "data": data, "query_id": query_id}
            await websocket.send_json(msg)

        # Execute with streaming
        interaction.status = "processing"
        db.commit()

        result = await conductor.execute_query(question, "", db, on_step=on_step)

        # Send final result
        await websocket.send_json({
            "phase": "complete",
            "query_id": query_id,
            "synthesis": result.get("synthesis", {}),
            "agent_outputs": result.get("agent_outputs", {}),
            "routing": result.get("routing", {}),
        })

        # Store in cache
        _query_results[query_id] = result

        # Update DB
        interaction.status = "completed"
        interaction.synthesized_response = result.get("synthesis", {}).get("executive_summary", "")
        interaction.routed_agents = result.get("routing", {}).get("selected_agents", [])
        interaction.agent_responses = result.get("agent_outputs", {})
        db.commit()

        await websocket.close()

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for query %s", query_id)
        # Mark as failed so the record doesn't stay stuck in "processing"
        try:
            interaction = db.query(ConversationalInteraction).filter_by(query_id=query_id).first()
            if interaction and interaction.status == "processing":
                interaction.status = "failed"
                db.commit()
        except Exception:
            db.rollback()
    except Exception as e:
        logger.error("WebSocket error for query %s: %s", query_id, e, exc_info=True)
        # Mark as failed so retries don't get stuck on "processing"
        try:
            interaction = db.query(ConversationalInteraction).filter_by(query_id=query_id).first()
            if interaction and interaction.status == "processing":
                interaction.status = "failed"
                db.commit()
        except Exception:
            db.rollback()
        try:
            await websocket.send_json({"error": str(e), "query_id": query_id})
            await websocket.close()
        except Exception:
            pass
    finally:
        db.close()
