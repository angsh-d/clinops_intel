"""Prompt manager: loads .txt templates from /prompt/ and substitutes variables."""

import logging
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompt"


class PromptManager:
    """Loads prompt templates from .txt files and applies variable substitution."""

    def __init__(self, prompt_dir: Path | None = None):
        self._dir = prompt_dir or PROMPT_DIR
        self._cache: dict[str, str] = {}

    def _load(self, name: str) -> str:
        if name not in self._cache:
            path = self._dir / f"{name}.txt"
            if not path.exists():
                raise FileNotFoundError(f"Prompt template not found: {path}")
            self._cache[name] = path.read_text(encoding="utf-8")
            logger.debug("Loaded prompt template: %s", name)
        return self._cache[name]

    def render(self, name: str, **kwargs) -> str:
        """Load prompt template by name and substitute {variables}."""
        template = self._load(name)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing variable {e} in prompt '{name}'") from e

    def reload(self, name: str | None = None):
        """Clear cache for a specific prompt or all prompts."""
        if name:
            self._cache.pop(name, None)
        else:
            self._cache.clear()


@lru_cache()
def get_prompt_manager() -> PromptManager:
    return PromptManager()
