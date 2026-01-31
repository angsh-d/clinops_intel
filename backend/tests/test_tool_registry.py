"""Tests for tool registry: registration, lookup, invocation, error handling."""

import pytest
from backend.tools.base import BaseTool, ToolResult, ToolRegistry


class _EchoTool(BaseTool):
    """Test tool that echoes its kwargs."""
    name = "echo"
    description = "Returns kwargs as data."

    async def execute(self, db_session, **kwargs) -> ToolResult:
        return ToolResult(tool_name=self.name, success=True, data=kwargs, row_count=1)


class _FailTool(BaseTool):
    """Test tool that always raises."""
    name = "fail"
    description = "Always raises an error."

    async def execute(self, db_session, **kwargs) -> ToolResult:
        raise RuntimeError("intentional failure")


class TestToolRegistry:

    def test_register_and_get(self):
        reg = ToolRegistry()
        reg.register(_EchoTool())
        assert reg.get("echo") is not None
        assert reg.get("nonexistent") is None

    def test_list_tools(self):
        reg = ToolRegistry()
        reg.register(_EchoTool())
        reg.register(_FailTool())
        tools = reg.list_tools()
        assert len(tools) == 2
        names = {t["name"] for t in tools}
        assert names == {"echo", "fail"}

    def test_list_tools_text(self):
        reg = ToolRegistry()
        reg.register(_EchoTool())
        text = reg.list_tools_text()
        assert "echo" in text
        assert "Returns kwargs" in text

    @pytest.mark.asyncio
    async def test_invoke_success(self):
        reg = ToolRegistry()
        reg.register(_EchoTool())
        result = await reg.invoke("echo", db_session=None, site_id="SITE-001")
        assert result.success is True
        assert result.data == {"site_id": "SITE-001"}

    @pytest.mark.asyncio
    async def test_invoke_nonexistent_tool(self):
        reg = ToolRegistry()
        result = await reg.invoke("nonexistent", db_session=None)
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_invoke_tool_exception_is_caught(self):
        reg = ToolRegistry()
        reg.register(_FailTool())
        result = await reg.invoke("fail", db_session=None)
        assert result.success is False
        assert "intentional failure" in result.error


class TestBuiltinToolRegistry:
    """Verify the production tool registry has all expected tools."""

    def test_build_tool_registry_contains_all_tools(self):
        from backend.tools.sql_tools import build_tool_registry
        reg = build_tool_registry()
        expected = {
            "entry_lag_analysis", "query_burden", "data_correction_analysis",
            "cra_assignment_history", "monitoring_visit_history", "site_summary",
            "screening_funnel", "enrollment_velocity", "screen_failure_pattern",
            "regional_comparison", "kit_inventory", "kri_snapshot",
        }
        for name in expected:
            assert reg.get(name) is not None, f"Missing tool: {name}"

    def test_all_tools_have_descriptions(self):
        from backend.tools.sql_tools import build_tool_registry
        reg = build_tool_registry()
        for tool_info in reg.list_tools():
            assert tool_info["name"], "Tool missing name"
            assert len(tool_info["description"]) > 10, f"Tool {tool_info['name']} has too-short description"
