"""ChromaDB vector search tool for semantic retrieval of agent findings."""

import json
import logging
from pathlib import Path

from backend.tools.base import BaseTool, ToolResult
from backend.config import get_settings

logger = logging.getLogger(__name__)


class ContextSearchTool(BaseTool):
    name = "context_search"
    description = (
        "Searches previously generated agent findings by semantic similarity. "
        "Use to retrieve prior analyses relevant to the current investigation. "
        "Args: query_text (str), n_results (int, default 5), agent_id (optional filter)."
    )

    def __init__(self):
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            import chromadb
            settings = get_settings()
            persist_path = Path(settings.chroma_persist_path)
            persist_path.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(persist_path))
            self._collection = client.get_or_create_collection(
                name="agent_findings",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    async def execute(self, db_session, **kwargs) -> ToolResult:
        query_text = kwargs.get("query_text", "")
        n_results = int(kwargs.get("n_results", 5))
        agent_id = kwargs.get("agent_id")

        if not query_text:
            return ToolResult(tool_name=self.name, success=False, error="query_text is required")

        collection = self._get_collection()
        where_filter = {"agent_id": agent_id} if agent_id else None

        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_filter,
        )
        data = {
            "documents": results.get("documents", [[]])[0],
            "metadatas": results.get("metadatas", [[]])[0],
            "distances": results.get("distances", [[]])[0],
        }
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data["documents"]))

    def store_finding(self, finding_id: str, text: str, metadata: dict):
        """Store an agent finding for future retrieval."""
        collection = self._get_collection()
        collection.upsert(
            ids=[finding_id],
            documents=[text],
            metadatas=[metadata],
        )


# ── Module-level helper for indexing findings from any pipeline ──

_index_tool: ContextSearchTool | None = None


def index_finding(
    finding_id: str | int,
    agent_id: str,
    summary: str,
    detail: dict | None = None,
    site_id: str | None = None,
    finding_type: str | None = None,
    severity: str | None = None,
) -> None:
    """Index a finding in the vector store for semantic retrieval.

    Safe to call from any pipeline — failures are logged but never raised.
    """
    global _index_tool
    try:
        if _index_tool is None:
            _index_tool = ContextSearchTool()

        # Build searchable text: summary + truncated detail
        text_parts = [summary]
        if detail:
            text_parts.append(json.dumps(detail, default=str)[:3000])
        text = "\n".join(text_parts)

        # ChromaDB metadata values must be str, int, float, or bool
        metadata = {"agent_id": agent_id}
        if site_id:
            metadata["site_id"] = site_id
        if finding_type:
            metadata["finding_type"] = finding_type
        if severity:
            metadata["severity"] = severity

        _index_tool.store_finding(str(finding_id), text, metadata)
        logger.debug("Indexed finding %s in vector store", finding_id)
    except Exception:
        logger.warning("Failed to index finding %s in vector store", finding_id, exc_info=True)
