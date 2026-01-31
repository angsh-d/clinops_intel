"""Tests for ConversationService: session context retrieval and follow-up contextualization.

Verifies:
- Session context builds correct conversation history string
- Empty session returns empty context
- Follow-up contextualization uses LLM to rewrite question
- LLM parse failure returns safe default
- Parent query context is included in prompt
"""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock

from backend.services.conversation import ConversationService
from backend.models.governance import ConversationalInteraction
from backend.llm.client import LLMClient, LLMResponse
from backend.prompts.manager import PromptManager


@pytest.fixture()
def mock_prompts():
    pm = MagicMock(spec=PromptManager)
    pm.render = MagicMock(side_effect=lambda name, **kw: f"[{name}] {json.dumps(kw, default=str)[:200]}")
    return pm


class TestSessionContext:

    def test_empty_session_returns_empty(self, db_session, mock_prompts):
        """No prior interactions should yield empty context."""
        llm = MagicMock(spec=LLMClient)
        svc = ConversationService(llm_client=llm, prompt_manager=mock_prompts)
        context = svc.get_session_context("nonexistent-session", db_session)
        assert context == ""

    def test_session_context_includes_prior_exchanges(self, db_session, mock_prompts):
        """Context should contain Q/A pairs from prior interactions."""
        for i in range(3):
            interaction = ConversationalInteraction(
                query_id=f"ctx-q-{i}",
                session_id="ctx-session",
                user_query=f"Question {i}",
                synthesized_response=f"Answer {i}",
                status="completed",
            )
            db_session.add(interaction)
        db_session.commit()

        llm = MagicMock(spec=LLMClient)
        svc = ConversationService(llm_client=llm, prompt_manager=mock_prompts)
        context = svc.get_session_context("ctx-session", db_session)

        assert "Question 0" in context
        assert "Answer 0" in context
        assert "Question 2" in context

    def test_context_truncates_long_responses(self, db_session, mock_prompts):
        """Synthesized responses are truncated to 500 chars in context."""
        interaction = ConversationalInteraction(
            query_id="ctx-long",
            session_id="ctx-long-session",
            user_query="Short question",
            synthesized_response="A" * 1000,
            status="completed",
        )
        db_session.add(interaction)
        db_session.commit()

        llm = MagicMock(spec=LLMClient)
        svc = ConversationService(llm_client=llm, prompt_manager=mock_prompts)
        context = svc.get_session_context("ctx-long-session", db_session)

        # Response is in context but truncated
        assert "A" * 500 in context
        assert "A" * 501 not in context


class TestFollowUpContextualization:

    @pytest.mark.asyncio
    async def test_successful_contextualization(self, db_session, mock_prompts):
        """LLM contextualizes follow-up query successfully."""
        # Seed parent interaction
        parent = ConversationalInteraction(
            query_id="parent-q",
            session_id="fu-session",
            user_query="Which sites have data quality issues?",
            synthesized_response="Sites SITE-003 and SITE-005 have issues.",
            status="completed",
        )
        db_session.add(parent)
        db_session.commit()

        llm_response = json.dumps({
            "query_type": "followup",
            "contextualized_query": "What specific data quality issues does SITE-003 have in terms of entry lag and query burden?",
            "selected_agents": ["agent_1"],
            "requires_synthesis": False,
        })

        llm = MagicMock(spec=LLMClient)
        llm.generate_structured = AsyncMock(
            return_value=LLMResponse(text=llm_response, model="mock", usage={})
        )

        svc = ConversationService(llm_client=llm, prompt_manager=mock_prompts)
        result = await svc.contextualize_followup(
            followup_query="Tell me more about SITE-003",
            session_id="fu-session",
            parent_query_id="parent-q",
            db=db_session,
        )

        assert result["query_type"] == "followup"
        assert "SITE-003" in result["contextualized_query"]
        assert result["selected_agents"] == ["agent_1"]

    @pytest.mark.asyncio
    async def test_llm_failure_returns_safe_default(self, db_session, mock_prompts):
        """If LLM returns invalid JSON, service returns safe default routing."""
        parent = ConversationalInteraction(
            query_id="parent-fail",
            session_id="fu-fail-session",
            user_query="Original question",
            synthesized_response="Original answer",
            status="completed",
        )
        db_session.add(parent)
        db_session.commit()

        llm = MagicMock(spec=LLMClient)
        llm.generate_structured = AsyncMock(
            return_value=LLMResponse(text="not json", model="mock", usage={})
        )

        svc = ConversationService(llm_client=llm, prompt_manager=mock_prompts)
        result = await svc.contextualize_followup(
            followup_query="follow up",
            session_id="fu-fail-session",
            parent_query_id="parent-fail",
            db=db_session,
        )

        # Should return safe defaults
        assert result["query_type"] == "new_topic"
        assert result["contextualized_query"] == "follow up"
        assert set(result["selected_agents"]) == {"agent_1", "agent_3"}

    @pytest.mark.asyncio
    async def test_prompt_includes_conversation_history(self, db_session, mock_prompts):
        """The prompt rendered for contextualization should include history."""
        parent = ConversationalInteraction(
            query_id="parent-hist",
            session_id="fu-hist-session",
            user_query="First question",
            synthesized_response="First answer",
            status="completed",
        )
        db_session.add(parent)
        db_session.commit()

        llm = MagicMock(spec=LLMClient)
        llm.generate_structured = AsyncMock(
            return_value=LLMResponse(
                text=json.dumps({"query_type": "followup", "contextualized_query": "q", "selected_agents": ["agent_1"], "requires_synthesis": False}),
                model="mock", usage={}
            )
        )

        svc = ConversationService(llm_client=llm, prompt_manager=mock_prompts)
        await svc.contextualize_followup(
            followup_query="Tell me more",
            session_id="fu-hist-session",
            parent_query_id="parent-hist",
            db=db_session,
        )

        # Check the prompt was rendered with the right template
        mock_prompts.render.assert_called_once()
        call_kwargs = mock_prompts.render.call_args[1]
        assert "previous_query" in call_kwargs
        assert call_kwargs["previous_query"] == "First question"
        assert call_kwargs["followup_query"] == "Tell me more"
