"""LLM client abstract base class and response dataclass."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """Standardised response from any LLM provider."""
    text: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    raw: Any = None
    is_fallback: bool = False


class LLMClient(ABC):
    """Abstract LLM client interface."""

    @abstractmethod
    async def generate(self, prompt: str, *, system: str = "", temperature: float | None = None) -> LLMResponse:
        """Generate a text completion."""
        ...

    @abstractmethod
    async def generate_structured(self, prompt: str, *, system: str = "", temperature: float | None = None) -> LLMResponse:
        """Generate a completion expected to contain JSON."""
        ...
