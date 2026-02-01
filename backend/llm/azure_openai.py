"""Azure OpenAI LLM client implementation."""

import logging
import httpx
from openai import AsyncAzureOpenAI

from backend.llm.client import LLMClient, LLMResponse
from backend.config import Settings

logger = logging.getLogger(__name__)


class AzureOpenAIClient(LLMClient):
    """Azure OpenAI client for gpt-5.2 fallback."""

    def __init__(self, settings: Settings):
        self._deployment = settings.azure_openai_deployment
        self._model_name = settings.azure_openai_model_name
        self._max_tokens = settings.azure_openai_max_tokens
        self._client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
            timeout=httpx.Timeout(settings.gemini_timeout, connect=10),
        )

    async def generate(self, prompt: str, *, system: str = "", temperature: float | None = None) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._deployment,
            messages=messages,
            temperature=temperature if temperature is not None else 0.0,
            max_completion_tokens=self._max_tokens,
        )
        choice = response.choices[0]
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens or 0,
                "completion_tokens": response.usage.completion_tokens or 0,
                "total_tokens": response.usage.total_tokens or 0,
            }
        return LLMResponse(
            text=choice.message.content or "",
            model=self._model_name,
            usage=usage,
            raw=response,
        )

    async def generate_structured(self, prompt: str, *, system: str = "", temperature: float | None = None) -> LLMResponse:
        structured_system = (system + "\n\n" if system else "") + "Respond ONLY with valid JSON. No markdown fences, no commentary."
        return await self.generate(prompt, system=structured_system, temperature=temperature)
