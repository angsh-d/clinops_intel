"""Shared LLM response utilities."""

import json
import re
from typing import Any


def parse_llm_json(text: str) -> dict | list:
    """Extract JSON from LLM response, handling markdown fences and preamble text."""
    cleaned = text.strip()
    # Strip markdown code fences
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]  # Drop opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # Drop closing fence
        cleaned = "\n".join(lines).strip()
    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object/array in the text
        match = re.search(r'[\[{]', cleaned)
        if match:
            candidate = cleaned[match.start():]
            # First try parsing the full candidate
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
            # If trailing text after JSON, find matching closing bracket
            open_char = candidate[0]
            close_char = ']' if open_char == '[' else '}'
            depth = 0
            in_string = False
            escape_next = False
            for i, ch in enumerate(candidate):
                if escape_next:
                    escape_next = False
                    continue
                if ch == '\\' and in_string:
                    escape_next = True
                    continue
                if ch == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == open_char:
                    depth += 1
                elif ch == close_char:
                    depth -= 1
                    if depth == 0:
                        return json.loads(candidate[:i + 1])
        raise


def safe_json_str(data: Any, max_chars: int = 30000) -> str:
    """Serialize data to JSON string with structural truncation (not mid-value)."""
    s = json.dumps(data, default=str)
    if len(s) <= max_chars:
        return s
    # Truncate lists structurally before serializing
    if isinstance(data, list):
        # Binary search for the max subset that fits
        lo, hi = 0, len(data)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            attempt = json.dumps(data[:mid], default=str)
            if len(attempt) <= max_chars - 100:
                lo = mid
            else:
                hi = mid - 1
        truncated = data[:lo]
        truncated.append({"_truncated": True, "_original_count": len(data), "_included_count": lo})
        return json.dumps(truncated, default=str)
    if isinstance(data, dict):
        # Progressively truncate large nested lists until the dict fits
        trimmed = {}
        for k, v in data.items():
            if isinstance(v, list) and len(json.dumps(v, default=str)) > max_chars // max(len(data), 1):
                trimmed[k] = v[:50]
                trimmed[k].append({"_truncated": True, "_original_count": len(v)})
            else:
                trimmed[k] = v
        result = json.dumps(trimmed, default=str)
        if len(result) <= max_chars:
            return result
        # Further reduce list sizes until it fits
        for limit in (20, 10, 5):
            for k, v in trimmed.items():
                if isinstance(v, list) and len(v) > limit:
                    original_count = len(v)
                    trimmed[k] = v[:limit]
                    trimmed[k].append({"_truncated": True, "_original_count": original_count})
            result = json.dumps(trimmed, default=str)
            if len(result) <= max_chars:
                return result
        return result
    return s[:max_chars]
