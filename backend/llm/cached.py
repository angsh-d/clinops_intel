"""Caching wrapper for any LLMClient — avoids repeated API calls for identical prompts."""

import logging
from dataclasses import replace

from backend.llm.client import LLMClient, LLMResponse
from backend.cache import llm_cache, cache_key

logger = logging.getLogger(__name__)


class CachedLLMClient(LLMClient):
    """Wraps an LLMClient and caches responses keyed by prompt+system+temperature.

    Strips the `raw` field before caching to avoid pinning SDK response objects
    (HTTP connections, session pools) in memory for the full TTL.
    """

    def __init__(self, inner: LLMClient):
        self._inner = inner

    async def generate(self, prompt: str, *, system: str = "", temperature: float | None = None) -> LLMResponse:
        ck = cache_key("generate", prompt, system, temperature)
        cached = llm_cache.get(ck)
        if cached is not None:
            logger.debug("LLM cache hit (generate)")
            return cached
        response = await self._inner.generate(prompt, system=system, temperature=temperature)
        llm_cache.set(ck, replace(response, raw=None))
        return response

    async def generate_structured(self, prompt: str, *, system: str = "", temperature: float | None = None) -> LLMResponse:
        ck = cache_key("generate_structured", prompt, system, temperature)
        cached = llm_cache.get(ck)
        if cached is not None:
            logger.debug("LLM cache hit (generate_structured)")
            return cached
        response = await self._inner.generate_structured(prompt, system=system, temperature=temperature)
        llm_cache.set(ck, replace(response, raw=None))
        return response
