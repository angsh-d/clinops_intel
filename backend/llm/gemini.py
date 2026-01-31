"""Gemini LLM client implementation using google-genai SDK.

This uses Replit AI Integrations for Gemini access without requiring your own API key.
"""

import asyncio
import logging
from google import genai
from google.genai import types

from backend.llm.client import LLMClient, LLMResponse
from backend.config import Settings

logger = logging.getLogger(__name__)


class GeminiClient(LLMClient):
    """Gemini client via google-genai SDK using Replit AI Integrations."""

    def __init__(self, settings: Settings):
        self._model_name = settings.primary_llm
        self._default_temp = settings.gemini_temperature
        self._max_tokens = settings.gemini_max_output_tokens
        self._top_p = settings.gemini_top_p
        self._timeout = settings.gemini_timeout
        self._client = genai.Client(
            api_key=settings.ai_integrations_gemini_api_key,
            http_options={
                'api_version': '',
                'base_url': settings.ai_integrations_gemini_base_url
            }
        )

    async def generate(self, prompt: str, *, system: str = "", temperature: float | None = None) -> LLMResponse:
        temp = temperature if temperature is not None else self._default_temp
        config = types.GenerateContentConfig(
            temperature=temp,
            top_p=self._top_p,
            max_output_tokens=self._max_tokens,
            system_instruction=system if system else None,
        )
        response = await asyncio.wait_for(
            self._client.aio.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config=config,
            ),
            timeout=self._timeout,
        )

        # Detect empty/blocked responses and raise so failover triggers
        if not response.text or not response.text.strip():
            finish_reason = "unknown"
            if response.candidates:
                finish_reason = getattr(response.candidates[0], "finish_reason", "unknown")
            raise ValueError(
                f"Gemini returned empty response (finish_reason={finish_reason}). "
                "Possible safety block or content filter."
            )

        usage = {}
        if response.usage_metadata:
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                "total_tokens": response.usage_metadata.total_token_count or 0,
            }
        return LLMResponse(
            text=response.text,
            model=self._model_name,
            usage=usage,
            raw=response,
        )

    async def generate_structured(self, prompt: str, *, system: str = "", temperature: float | None = None) -> LLMResponse:
        structured_system = (system + "\n\n" if system else "") + "Respond ONLY with valid JSON. No markdown fences, no commentary."
        return await self.generate(prompt, system=structured_system, temperature=temperature)
