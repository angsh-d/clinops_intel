"""WebSocket router: stream PRPA phases in real time."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.config import SessionLocal, get_settings
from backend.conductor.router import ConductorRouter
from backend.llm.failover import FailoverLLMClient
from backend.llm.cached import CachedLLMClient
from backend.cache import invalidate_all
from backend.prompts.manager import get_prompt_manager
from backend.agents.registry import build_agent_registry
from backend.tools.sql_tools import build_tool_registry
from backend.models.governance import ConversationalInteraction
from backend.routers.query import _query_results

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])

KEEPALIVE_INTERVAL = 15  # seconds


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

        # If already completed, simulate investigation phases then stream cached results
        if interaction.status == "completed":
            cached = _query_results.get(query_id)
            if cached:
                synthesis = cached.get("synthesis", {})
                agent_outputs = cached.get("agent_outputs", {})
                routing = cached.get("routing", {})
            else:
                # Fallback: reconstruct from DB columns
                synthesis = interaction.synthesis_data or {"executive_summary": interaction.synthesized_response or ""}
                agent_outputs = interaction.agent_responses or {}
                routing = {}

            # Simulate real-time phase progression (6-8s total)
            simulated_phases = [
                ("routing", "conductor", 1.0),
                ("perceive", list(agent_outputs.keys())[0] if agent_outputs else "data_quality", 1.5),
                ("reason", list(agent_outputs.keys())[0] if agent_outputs else "data_quality", 1.5),
                ("act", list(agent_outputs.keys())[0] if agent_outputs else "data_quality", 1.5),
                ("synthesize", "conductor", 1.5),
            ]
            for phase, agent_id, delay in simulated_phases:
                await websocket.send_json({
                    "phase": phase,
                    "agent_id": agent_id,
                    "query_id": query_id,
                    "data": {},
                })
                await asyncio.sleep(delay)

            await websocket.send_json({
                "phase": "complete",
                "query_id": query_id,
                "synthesis": synthesis,
                "agent_outputs": agent_outputs,
                "routing": routing,
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

        # Build conductor with tiered models (fast for routing/plan/reflect, full for reason/synthesize)
        settings = get_settings()
        llm = CachedLLMClient(FailoverLLMClient(settings))
        fast_llm = CachedLLMClient(FailoverLLMClient(settings, model_name=settings.fast_llm)) if settings.fast_llm else llm
        prompts = get_prompt_manager()
        agents = build_agent_registry()
        tools = build_tool_registry()
        conductor = ConductorRouter(llm, prompts, agents, tools, fast_llm_client=fast_llm)

        # on_step callback streams phases to WebSocket (errors swallowed by BaseAgent)
        async def on_step(phase: str, agent_id: str, data: dict):
            msg = {"phase": phase, "agent_id": agent_id, "data": data, "query_id": query_id}
            await websocket.send_json(msg)

        # Keepalive task to prevent proxy/browser timeouts
        keepalive_stop = asyncio.Event()

        async def keepalive():
            while not keepalive_stop.is_set():
                try:
                    await asyncio.wait_for(keepalive_stop.wait(), timeout=KEEPALIVE_INTERVAL)
                except asyncio.TimeoutError:
                    try:
                        await websocket.send_json({"phase": "keepalive", "query_id": query_id})
                    except Exception:
                        break

        keepalive_task = asyncio.create_task(keepalive())

        # Execute with streaming
        interaction.status = "processing"
        db.commit()

        try:
            result = await conductor.execute_query(question, "", db, on_step=on_step)
        finally:
            keepalive_stop.set()
            keepalive_task.cancel()
            try:
                await keepalive_task
            except asyncio.CancelledError:
                pass

        # Send final result
        await websocket.send_json({
            "phase": "complete",
            "query_id": query_id,
            "synthesis": result.get("synthesis", {}),
            "agent_outputs": result.get("agent_outputs", {}),
            "routing": result.get("routing", {}),
        })

        # Store in cache
        _query_results.set(query_id, result)

        # Invalidate dashboard/tool/LLM caches so next load gets fresh data
        invalidate_all()

        # Update DB
        interaction.status = "completed"
        interaction.synthesized_response = result.get("synthesis", {}).get("executive_summary", "")
        interaction.synthesis_data = result.get("synthesis", {})
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
