"""Directive catalog: loads and manages proactive investigation directives."""

import json
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

DIRECTIVES_DIR = Path(__file__).resolve().parents[2] / "prompt" / "directives"


class DirectiveCatalog:
    """Loads directive catalog from prompt/directives/catalog.json, provides CRUD."""

    def __init__(self, directives_dir: Path | None = None):
        self._dir = directives_dir or DIRECTIVES_DIR
        self._catalog_path = self._dir / "catalog.json"

    def _safe_path(self, filename: str) -> Path:
        """Resolve path and ensure it stays within the directives directory."""
        resolved = (self._dir / filename).resolve()
        if not resolved.is_relative_to(self._dir.resolve()):
            raise ValueError(f"Path traversal detected: {filename}")
        return resolved

    def load_catalog(self) -> list[dict]:
        """Load all directives from catalog.json."""
        if not self._catalog_path.exists():
            logger.warning("Directive catalog not found at %s", self._catalog_path)
            return []
        with open(self._catalog_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("directives", [])

    def _save_catalog(self, directives: list[dict]) -> None:
        """Write directives list via atomic temp-file + rename (POSIX-safe)."""
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._dir), suffix=".tmp", prefix=".catalog_"
        )
        try:
            with open(fd, "w", encoding="utf-8") as f:
                json.dump({"directives": directives}, f, indent=2)
            Path(tmp_path).rename(self._catalog_path)
        except BaseException:
            Path(tmp_path).unlink(missing_ok=True)
            raise

    def get_enabled_directives(self, agent_id: str | None = None) -> list[dict]:
        """Return enabled directives, optionally filtered by agent_id."""
        directives = self.load_catalog()
        enabled = [d for d in directives if d.get("enabled", True)]
        if agent_id:
            enabled = [d for d in enabled if d.get("agent_id") == agent_id]
        return enabled

    def get_directive_text(self, directive_id: str) -> str:
        """Read the .txt prompt file for a directive."""
        directives = self.load_catalog()
        entry = next((d for d in directives if d["directive_id"] == directive_id), None)
        if not entry:
            raise ValueError(f"Directive not found: {directive_id}")
        prompt_file = self._safe_path(entry["prompt_file"])
        if not prompt_file.exists():
            raise FileNotFoundError(f"Directive prompt file not found: {prompt_file}")
        return prompt_file.read_text(encoding="utf-8")

    def set_enabled(self, directive_id: str, enabled: bool) -> dict:
        """Enable or disable a directive. Returns the updated directive."""
        directives = self.load_catalog()
        for d in directives:
            if d["directive_id"] == directive_id:
                d["enabled"] = enabled
                self._save_catalog(directives)
                return d
        raise ValueError(f"Directive not found: {directive_id}")

    def add_directive(self, directive: dict, prompt_text: str) -> dict:
        """Add a new directive: creates .txt file and updates catalog.json."""
        directives = self.load_catalog()
        if any(d["directive_id"] == directive["directive_id"] for d in directives):
            raise ValueError(f"Directive already exists: {directive['directive_id']}")

        prompt_file = f"{directive['directive_id']}.txt"
        safe_path = self._safe_path(prompt_file)
        safe_path.write_text(prompt_text, encoding="utf-8")
        directive["prompt_file"] = prompt_file
        directives.append(directive)
        self._save_catalog(directives)
        return directive
