"""Conversation management: session context and follow-up chaining."""

import json
import logging
from sqlalchemy.orm import Session

from backend.models.governance import ConversationalInteraction
from backend.llm.client import LLMClient
from backend.llm.utils import parse_llm_json
from backend.prompts.manager import PromptManager

logger = logging.getLogger(__name__)


class ConversationService:
    """Manages session context for multi-turn conversations."""

    def __init__(self, llm_client: LLMClient, prompt_manager: PromptManager):
        self.llm = llm_client
        self.prompts = prompt_manager

    def get_session_context(self, session_id: str, db: Session, limit: int = 5) -> str:
        """Retrieve recent conversation context for a session."""
        interactions = db.query(ConversationalInteraction).filter_by(
            session_id=session_id
        ).order_by(ConversationalInteraction.created_at.desc()).limit(limit).all()

        if not interactions:
            return ""

        context_parts = []
        for i in reversed(interactions):
            context_parts.append(f"Q: {i.user_query}")
            if i.synthesized_response:
                context_parts.append(f"A: {i.synthesized_response[:500]}")
        return "\n".join(context_parts)

    async def contextualize_followup(
        self, followup_query: str, session_id: str, parent_query_id: str, db: Session
    ) -> dict:
        """Use LLM to contextualize a follow-up query within the conversation."""
        parent = db.query(ConversationalInteraction).filter_by(query_id=parent_query_id).first()
        conversation_history = self.get_session_context(session_id, db)

        prompt = self.prompts.render(
            "conversational_followup",
            conversation_history=conversation_history,
            previous_query=parent.user_query if parent else "",
            previous_response=parent.synthesized_response[:1000] if parent and parent.synthesized_response else "",
            followup_query=followup_query,
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a clinical operations conversation manager. Respond with valid JSON only.",
        )
        try:
            return parse_llm_json(response.text)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Follow-up contextualization failed: %s", e)
            return {
                "query_type": "new_topic",
                "contextualized_query": followup_query,
                "selected_agents": ["data_quality", "enrollment_funnel"],
                "requires_synthesis": True,
            }
