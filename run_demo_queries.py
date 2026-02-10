"""Run all demo queries, validate results, and cache them in the database.

This script executes the conductor pipeline directly (same path as the WebSocket
handler) for each demo query, validates the response quality, and stores results
in both ConversationalInteraction and PersistentCache so the frontend can serve
them instantly during the demo.
"""

import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime, timezone

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("demo_runner")

# ── Demo Queries ─────────────────────────────────────────────────────────────

DEMO_QUERIES = [
    {
        "id": "demo_1",
        "query": "Show key findings from the last 2 monitoring visit reports for SITE-033",
        "label": "MVR Narrative Extraction",
        "expected_agents": ["mvr_analysis"],
        "min_evidence_items": 1,
    },
    {
        "id": "demo_2",
        "query": "SITE-033 has had missed monitoring visits. Is there hidden data quality debt that the KPIs aren't showing?",
        "label": "Cross-Domain MVR + DQ Synthesis",
        "expected_agents": ["mvr_analysis", "data_quality"],
        "min_evidence_items": 1,
    },
    {
        "id": "demo_3",
        "query": "Are there any CRAs who might be rubber-stamping their monitoring visit reports?",
        "label": "CRA Behavioral Detection",
        "expected_agents": ["mvr_analysis"],
        "min_evidence_items": 1,
    },
    {
        "id": "demo_4",
        "query": "Why is SITE-022 underperforming? Include insights from the monitoring visit reports.",
        "label": "Full Multi-Agent + MVR",
        "expected_agents": ["data_quality", "enrollment_funnel"],
        "min_evidence_items": 2,
    },
    {
        "id": "demo_5",
        "query": "Compare the quality of monitoring across SITE-012, SITE-033, and SITE-074 based on their visit reports",
        "label": "Cross-Site MVR Comparison",
        "expected_agents": ["mvr_analysis"],
        "min_evidence_items": 1,
    },
    {
        "id": "demo_6",
        "query": "Has PI engagement declined at any of our monitored sites?",
        "label": "PI Engagement Temporal Trajectory",
        "expected_agents": ["mvr_analysis"],
        "min_evidence_items": 1,
    },
    {
        "id": "demo_7",
        "query": "Which sites need attention this week?",
        "label": "Broad Triage",
        "expected_agents": ["data_quality", "enrollment_funnel"],
        "min_evidence_items": 2,
    },
    {
        "id": "demo_8",
        "query": "What is driving budget variance?",
        "label": "Financial Intelligence",
        "expected_agents": ["financial_intelligence"],
        "min_evidence_items": 1,
    },
    {
        "id": "demo_9",
        "query": "Show me enrollment bottlenecks",
        "label": "Enrollment Bottlenecks",
        "expected_agents": ["enrollment_funnel"],
        "min_evidence_items": 1,
    },
    {
        "id": "demo_10",
        "query": "Are there zombie findings at SITE-012 — issues that keep coming back despite being marked resolved?",
        "label": "Zombie Finding Recurrence",
        "expected_agents": ["mvr_analysis"],
        "min_evidence_items": 1,
    },
]


def validate_result(result: dict, demo: dict) -> dict:
    """Validate a conductor result for quality and completeness."""
    issues = []
    synthesis = result.get("synthesis", {})
    routing = result.get("routing", {})
    agent_outputs = result.get("agent_outputs", {})
    selected = routing.get("selected_agents", [])

    # 1. Check routing — expected agents invoked
    for expected in demo["expected_agents"]:
        if expected not in selected:
            issues.append(f"Expected agent '{expected}' not routed (got: {selected})")

    # 2. Check executive summary exists and is substantive
    exec_summary = synthesis.get("executive_summary", "")
    if not exec_summary:
        issues.append("Missing executive_summary")
    elif len(exec_summary) < 50:
        issues.append(f"executive_summary too short ({len(exec_summary)} chars)")

    # 3. Check cross-domain findings
    findings = synthesis.get("cross_domain_findings", [])
    single_findings = synthesis.get("single_domain_findings", [])
    total_findings = len(findings) + len(single_findings)
    if total_findings < demo["min_evidence_items"]:
        issues.append(f"Only {total_findings} findings (expected >= {demo['min_evidence_items']})")

    # 4. Check finding quality — causal chains, evidence
    for i, f in enumerate(findings):
        if not f.get("finding"):
            issues.append(f"Finding {i}: missing 'finding' text")
        if not f.get("causal_chain"):
            issues.append(f"Finding {i}: missing causal_chain")
        confirming = f.get("confirming_evidence", [])
        if not confirming:
            issues.append(f"Finding {i}: no confirming_evidence")
        if f.get("confidence") is None:
            issues.append(f"Finding {i}: missing confidence score")

    # 5. Check next best actions
    nbas = synthesis.get("next_best_actions", [])
    if not nbas:
        issues.append("No next_best_actions")

    # 6. Check agent outputs exist
    if not agent_outputs:
        issues.append("No agent_outputs returned")

    # 7. Check for error
    if result.get("error"):
        issues.append(f"Error in result: {result['error']}")

    verdict = "PASS" if len(issues) == 0 else "WARN" if len(issues) <= 2 else "FAIL"
    return {
        "verdict": verdict,
        "issues": issues,
        "finding_count": total_findings,
        "agents_invoked": selected,
        "exec_summary_length": len(exec_summary),
        "nba_count": len(nbas),
    }


def store_result(query_id: str, session_id: str, question: str, result: dict):
    """Store result in ConversationalInteraction and PersistentCache (same as ws.py)."""
    db = SessionLocal()
    try:
        # Check if interaction already exists
        interaction = db.query(ConversationalInteraction).filter_by(query_id=query_id).first()
        if not interaction:
            interaction = ConversationalInteraction(
                query_id=query_id,
                session_id=session_id,
                user_query=question,
                status="completed",
            )
            db.add(interaction)

        interaction.status = "completed"
        interaction.routed_agents = result.get("routing", {}).get("selected_agents", [])
        interaction.agent_responses = result.get("agent_outputs", {})
        interaction.synthesized_response = result.get("synthesis", {}).get("executive_summary", "")
        interaction.synthesis_data = result.get("synthesis", {})
        interaction.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("  Stored in ConversationalInteraction: %s", query_id)

        # Store in PersistentCache (L1 + L2)
        _query_results.set(query_id, result)
        logger.info("  Stored in PersistentCache: %s", query_id)
    finally:
        db.close()


def clear_previous_demo_results():
    """Remove any previous demo query results so we get fresh runs."""
    db = SessionLocal()
    try:
        for demo in DEMO_QUERIES:
            existing = db.query(ConversationalInteraction).filter_by(
                user_query=demo["query"], status="completed"
            ).all()
            for e in existing:
                logger.info("Removing previous result: %s (query_id=%s)", demo["id"], e.query_id)
                _query_results.delete(e.query_id) if hasattr(_query_results, 'delete') else None
                db.delete(e)
            # Also remove failed/pending
            stale = db.query(ConversationalInteraction).filter_by(
                user_query=demo["query"]
            ).filter(ConversationalInteraction.status.in_(["pending", "processing", "failed"])).all()
            for s in stale:
                db.delete(s)
        db.commit()
    finally:
        db.close()


async def run_single_query(conductor: ConductorRouter, demo: dict, index: int, total: int) -> dict:
    """Run a single demo query through the conductor pipeline."""
    query_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    question = demo["query"]

    logger.info("=" * 80)
    logger.info("[%d/%d] %s", index, total, demo["label"])
    logger.info("  Query: %s", question)
    logger.info("  query_id: %s", query_id)

    db = SessionLocal()
    try:
        result = await conductor.execute_query(question, "", db)
    finally:
        db.close()

    # Validate
    validation = validate_result(result, demo)
    logger.info("  Verdict: %s", validation["verdict"])
    logger.info("  Agents invoked: %s", validation["agents_invoked"])
    logger.info("  Findings: %d | NBAs: %d | Summary: %d chars",
                validation["finding_count"], validation["nba_count"], validation["exec_summary_length"])
    if validation["issues"]:
        for issue in validation["issues"]:
            logger.warning("  Issue: %s", issue)

    # Store in DB + cache
    store_result(query_id, session_id, question, result)

    # Print executive summary
    exec_summary = result.get("synthesis", {}).get("executive_summary", "")
    logger.info("  Executive Summary: %s", exec_summary[:200] + "..." if len(exec_summary) > 200 else exec_summary)

    return {
        "demo_id": demo["id"],
        "label": demo["label"],
        "query_id": query_id,
        "validation": validation,
    }


async def main():
    logger.info("=" * 80)
    logger.info("DEMO QUERY RUNNER — Running %d queries", len(DEMO_QUERIES))
    logger.info("=" * 80)

    # Clear previous results
    logger.info("Clearing previous demo results...")
    clear_previous_demo_results()

    # Build conductor (same as ws.py)
    settings = get_settings()
    llm = CachedLLMClient(FailoverLLMClient(settings))
    fast_llm = CachedLLMClient(FailoverLLMClient(settings, model_name=settings.fast_llm)) if settings.fast_llm else llm
    prompts = get_prompt_manager()
    agents = build_agent_registry()
    tools = build_tool_registry()
    conductor = ConductorRouter(llm, prompts, agents, tools, fast_llm_client=fast_llm)

    results = []
    for i, demo in enumerate(DEMO_QUERIES, 1):
        try:
            r = await run_single_query(conductor, demo, i, len(DEMO_QUERIES))
            results.append(r)
        except Exception as e:
            logger.error("[%d/%d] FAILED: %s — %s", i, len(DEMO_QUERIES), demo["label"], e, exc_info=True)
            results.append({
                "demo_id": demo["id"],
                "label": demo["label"],
                "query_id": None,
                "validation": {"verdict": "FAIL", "issues": [str(e)]},
            })

        # Invalidate caches between queries so each gets fresh data
        invalidate_all()

    # Print summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    pass_count = sum(1 for r in results if r["validation"]["verdict"] == "PASS")
    warn_count = sum(1 for r in results if r["validation"]["verdict"] == "WARN")
    fail_count = sum(1 for r in results if r["validation"]["verdict"] == "FAIL")

    for r in results:
        v = r["validation"]
        icon = {"PASS": "OK", "WARN": "!!", "FAIL": "XX"}[v["verdict"]]
        logger.info("  [%s] %s — %s", icon, r["label"], v["verdict"])
        if v.get("issues"):
            for issue in v["issues"][:3]:
                logger.info("       %s", issue)

    logger.info("")
    logger.info("  PASS: %d | WARN: %d | FAIL: %d | Total: %d", pass_count, warn_count, fail_count, len(results))
    logger.info("")
    logger.info("All cached results will be served instantly via WebSocket during the demo.")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
