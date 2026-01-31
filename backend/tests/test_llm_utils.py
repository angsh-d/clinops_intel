"""Tests for LLM utility functions: JSON parsing and structural truncation.

These are critical for the agentic pipeline — every LLM response flows through
parse_llm_json, and large data payloads flow through safe_json_str.
"""

import json
import pytest

from backend.llm.utils import parse_llm_json, safe_json_str


class TestParseLLMJson:

    def test_plain_json_object(self):
        result = parse_llm_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_plain_json_array(self):
        result = parse_llm_json('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_markdown_fenced_json(self):
        text = '```json\n{"hypotheses": [{"id": "H1"}]}\n```'
        result = parse_llm_json(text)
        assert result["hypotheses"][0]["id"] == "H1"

    def test_markdown_fenced_no_language_tag(self):
        text = '```\n{"key": "value"}\n```'
        result = parse_llm_json(text)
        assert result["key"] == "value"

    def test_preamble_text_before_json(self):
        text = 'Here is the analysis:\n{"findings": [1, 2, 3]}'
        result = parse_llm_json(text)
        assert result["findings"] == [1, 2, 3]

    def test_trailing_text_after_json(self):
        text = '{"result": true}\nI hope this helps!'
        result = parse_llm_json(text)
        assert result["result"] is True

    def test_nested_json_with_strings_containing_braces(self):
        obj = {"text": "value with {curly} braces", "nested": {"a": 1}}
        text = json.dumps(obj)
        result = parse_llm_json(text)
        assert result["nested"]["a"] == 1

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_llm_json("completely invalid text with no json")

    def test_whitespace_padded(self):
        result = parse_llm_json('   \n  {"key": "value"}  \n   ')
        assert result["key"] == "value"

    def test_complex_agent_response(self):
        """Parse a realistic agent reflection response."""
        response = json.dumps({
            "is_goal_satisfied": True,
            "findings_summary": [
                {"site_id": "SITE-003", "finding": "High entry lag", "confidence": 0.92},
                {"site_id": "SITE-005", "finding": "CRA transition impact", "confidence": 0.78},
            ],
            "remaining_gaps": [],
            "overall_severity": "high",
        })
        result = parse_llm_json(f"```json\n{response}\n```")
        assert result["is_goal_satisfied"] is True
        assert len(result["findings_summary"]) == 2


class TestSafeJsonStr:

    def test_small_data_unchanged(self):
        data = {"key": "value"}
        result = safe_json_str(data)
        assert json.loads(result) == data

    def test_large_list_truncated(self):
        data = [{"id": i, "value": "x" * 100} for i in range(1000)]
        result = safe_json_str(data, max_chars=5000)
        parsed = json.loads(result)
        assert len(parsed) < 1000
        # Last element should be truncation marker
        assert parsed[-1].get("_truncated") is True
        assert parsed[-1]["_original_count"] == 1000

    def test_large_dict_with_nested_lists_truncated(self):
        data = {
            "small": "value",
            "big_list": [{"id": i} for i in range(500)],
        }
        result = safe_json_str(data, max_chars=3000)
        parsed = json.loads(result)
        assert len(parsed["big_list"]) < 500
        assert parsed["small"] == "value"

    def test_empty_structures(self):
        assert safe_json_str([]) == "[]"
        assert safe_json_str({}) == "{}"

    def test_date_serialization(self):
        """safe_json_str should handle date objects via default=str."""
        from datetime import date
        data = {"date": date(2025, 1, 15)}
        result = safe_json_str(data)
        assert "2025-01-15" in result
