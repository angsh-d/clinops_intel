"""Tool framework: BaseTool, ToolResult, ToolRegistry."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import logging

from backend.cache import sql_tool_cache, cache_key

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a tool execution."""
    tool_name: str
    success: bool
    data: Any = None
    error: str | None = None
    row_count: int = 0


class BaseTool(ABC):
    """Abstract base for all tools. Self-describes for LLM context."""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def execute(self, db_session, **kwargs) -> ToolResult:
        ...

    def describe(self) -> dict:
        """Return description dict for LLM tool selection."""
        return {"name": self.name, "description": self.description}


class ToolRegistry:
    """Registry of available tools. Tools self-describe for LLM context."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        """Return tool descriptions for LLM prompt injection."""
        return [t.describe() for t in self._tools.values()]

    def list_tools_text(self) -> str:
        """Return formatted tool descriptions for prompt inclusion."""
        lines = []
        for t in self._tools.values():
            lines.append(f"- {t.name}: {t.description}")
        return "\n".join(lines)

    async def invoke(self, name: str, db_session, **kwargs) -> ToolResult:
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(tool_name=name, success=False, error=f"Tool '{name}' not found")
        try:
            ck = cache_key(name, **kwargs)
            cached = sql_tool_cache.get(ck)
            if cached is not None:
                logger.debug("SQL tool cache hit: %s", name)
                return cached
            result = await tool.execute(db_session, **kwargs)
            if result.success:
                sql_tool_cache.set(ck, result)
            return result
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e, exc_info=True)
            return ToolResult(tool_name=name, success=False, error=str(e))
