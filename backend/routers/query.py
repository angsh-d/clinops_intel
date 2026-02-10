"""Query router: submit queries, check status, follow up."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query as QueryParam
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_settings_dep
from backend.config import Settings, SessionLocal
from backend.cache import query_results_cache, invalidate_all
from backend.schemas.query import QueryRequest, QueryResponse, QueryStatus, FollowUpRequest
from backend.schemas.errors import ErrorResponse, ValidationErrorDetail
from backend.models.governance import ConversationalInteraction
from backend.conductor.router import ConductorRouter
from backend.llm.failover import FailoverLLMClient
from backend.llm.cached import CachedLLMClient
from backend.prompts.manager import get_prompt_manager
from backend.agents.registry import build_agent_registry
from backend.tools.sql_tools import build_tool_registry
from backend.services.alert_service import AlertService
from backend.services.conversation import ConversationService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["query"])


_query_results = query_results_cache


def _build_conductor(settings: Settings) -> ConductorRouter:
    llm = CachedLLMClient(FailoverLLMClient(settings))
    fast_llm = CachedLLMClient(FailoverLLMClient(settings, model_name=settings.fast_llm)) if settings.fast_llm else llm
    prompts = get_prompt_manager()
    agents = build_agent_registry()
    tools = build_tool_registry()
    return ConductorRouter(llm, prompts, agents, tools, fast_llm_client=fast_llm)


async def _process_query(query_id: str, question: str, session_id: str, settings: Settings):
    """Background task: run conductor pipeline and store results.

    Creates its own DB session — never shares the request-scoped session.
    For follow-up queries (those with parent_query_id), uses ConversationService
    to LLM-contextualize the question before routing.
    """
    db = SessionLocal()
    try:
        interaction = db.query(ConversationalInteraction).filter_by(query_id=query_id).first()
        if interaction:
            interaction.status = "processing"
            db.commit()

        llm = CachedLLMClient(FailoverLLMClient(settings))
        fast_llm = CachedLLMClient(FailoverLLMClient(settings, model_name=settings.fast_llm)) if settings.fast_llm else llm
        prompts = get_prompt_manager()
        conductor = ConductorRouter(llm, prompts, build_agent_registry(), build_tool_registry(), fast_llm_client=fast_llm)

        # Build session context
        session_context = ""
        effective_question = question
        if session_id:
            prior = db.query(ConversationalInteraction).filter_by(
                session_id=session_id
            ).filter(
                ConversationalInteraction.query_id != query_id
            ).order_by(ConversationalInteraction.created_at.desc()).limit(3).all()
            if prior:
                session_context = "\n".join(
                    f"Q: {p.user_query}\nA: {p.synthesized_response or '(pending)'}" for p in reversed(prior)
                )

        # For follow-ups, use ConversationService to LLM-contextualize the question
        if interaction and interaction.parent_query_id:
            conv_svc = ConversationService(llm_client=llm, prompt_manager=prompts)
            contextualized = await conv_svc.contextualize_followup(
                followup_query=question,
                session_id=session_id,
                parent_query_id=interaction.parent_query_id,
                db=db,
            )
            effective_question = contextualized.get("contextualized_query", question)
            logger.info("Follow-up contextualized: %s → %s", question[:80], effective_question[:80])

        result = await conductor.execute_query(effective_question, session_context, db)

        # Store result in bounded cache
        _query_results.set(query_id, result)

        # Invalidate dashboard/tool/LLM caches so next load gets fresh data
        invalidate_all()

        # Update DB
        interaction = db.query(ConversationalInteraction).filter_by(query_id=query_id).first()
        if interaction:
            interaction.status = "completed"
            interaction.routed_agents = result.get("routing", {}).get("selected_agents", [])
            interaction.agent_responses = result.get("agent_outputs", {})
            interaction.synthesized_response = result.get("synthesis", {}).get("executive_summary", "")
            interaction.synthesis_data = result.get("synthesis", {})
            interaction.completed_at = datetime.now(timezone.utc)
            db.commit()

    except Exception as e:
        logger.error("Query processing failed for %s: %s", query_id, e, exc_info=True)
        _query_results.set(query_id, {"error": str(e), "status": "failed"})
        try:
            db.rollback()  # Clear any dirty transaction state before re-querying
            interaction = db.query(ConversationalInteraction).filter_by(query_id=query_id).first()
            if interaction:
                interaction.status = "failed"
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


@router.post(
    "/query/",
    response_model=QueryResponse,
    status_code=202,
    summary="Submit a query",
    description="Submit a natural-language question for agentic investigation. "
    "Processing happens asynchronously; poll the status endpoint for results.",
    response_description="Accepted response with query ID for status polling.",
    responses={422: {"model": ValidationErrorDetail, "description": "Validation error"}},
)
async def submit_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    """Submit a natural language query for agentic investigation."""
    query_id = str(uuid.uuid4())
    session_id = request.session_id or str(uuid.uuid4())

    interaction = ConversationalInteraction(
        query_id=query_id,
        session_id=session_id,
        user_query=request.question,
        status="pending",
    )
    db.add(interaction)
    db.commit()

    # Background task creates its own session — do NOT pass db
    background_tasks.add_task(_process_query, query_id, request.question, session_id, settings)

    return QueryResponse(query_id=query_id, status="accepted")


@router.get(
    "/query/{query_id}/status",
    response_model=QueryStatus,
    summary="Get query status",
    description="Check the processing status and results of a submitted query.",
    response_description="Query status with optional routing, agent outputs, and synthesis.",
    responses={404: {"model": ErrorResponse, "description": "Query not found"}},
)
def get_query_status(query_id: str, db: Session = Depends(get_db)):
    """Check the status of a submitted query."""
    interaction = db.query(ConversationalInteraction).filter_by(query_id=query_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Query not found")

    result = _query_results.get(query_id)
    return QueryStatus(
        query_id=query_id,
        status=interaction.status,
        routing=result.get("routing") if result else None,
        agent_outputs=result.get("agent_outputs") if result else None,
        synthesis=result.get("synthesis") if result else None,
        created_at=interaction.created_at,
        completed_at=interaction.completed_at,
    )


@router.post(
    "/query/{query_id}/follow-up",
    response_model=QueryResponse,
    status_code=202,
    summary="Submit a follow-up question",
    description="Submit a follow-up question in the context of a prior query. "
    "The system LLM-contextualises the question using conversation history.",
    response_description="Accepted response with new query ID.",
    responses={
        404: {"model": ErrorResponse, "description": "Parent query not found"},
        422: {"model": ValidationErrorDetail, "description": "Validation error"},
    },
)
async def submit_follow_up(
    query_id: str,
    request: FollowUpRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    """Submit a follow-up question in the context of a prior query."""
    parent = db.query(ConversationalInteraction).filter_by(query_id=query_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent query not found")

    new_query_id = str(uuid.uuid4())
    interaction = ConversationalInteraction(
        query_id=new_query_id,
        session_id=parent.session_id,
        parent_query_id=query_id,
        user_query=request.question,
        status="pending",
    )
    db.add(interaction)
    db.commit()

    # Background task creates its own session
    background_tasks.add_task(
        _process_query, new_query_id, request.question, parent.session_id, settings
    )

    return QueryResponse(query_id=new_query_id, status="accepted")
