"""Failover LLM client: Gemini first, Azure OpenAI on error."""

import logging

from backend.llm.client import LLMClient, LLMResponse
from backend.llm.gemini import GeminiClient
from backend.llm.azure_openai import AzureOpenAIClient
from backend.config import Settings

logger = logging.getLogger(__name__)


class FailoverLLMClient(LLMClient):
    """Tries Gemini first; falls back to Azure OpenAI on any error.

    Every fallback event is logged — no silent degradation.
    """

    def __init__(self, settings: Settings, model_name: str = ""):
        self._primary = GeminiClient(settings, model_name=model_name)
        self._fallback = AzureOpenAIClient(settings)

    async def generate(self, prompt: str, *, system: str = "", temperature: float | None = None) -> LLMResponse:
        try:
            return await self._primary.generate(prompt, system=system, temperature=temperature)
        except Exception as e:
            logger.warning("Gemini generate failed (%s: %s), falling back to Azure OpenAI", type(e).__name__, e)
            response = await self._fallback.generate(prompt, system=system, temperature=temperature)
            response.is_fallback = True
            return response

    async def generate_structured(self, prompt: str, *, system: str = "", temperature: float | None = None) -> LLMResponse:
        try:
            return await self._primary.generate_structured(prompt, system=system, temperature=temperature)
        except Exception as e:
            logger.warning("Gemini generate_structured failed (%s: %s), falling back to Azure OpenAI", type(e).__name__, e)
            response = await self._fallback.generate_structured(prompt, system=system, temperature=temperature)
            response.is_fallback = True
            return response
