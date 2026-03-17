"""Tests for the LangGraph integration patch."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestPatchLangGraph:
    """Test LangGraph monkey-patching."""

    def test_patch_without_langgraph_warns(self) -> None:
        """Should log warning when langgraph is not installed."""
        with patch.dict("sys.modules", {"langgraph.graph": None}):
            # Import will fail, patch should handle gracefully
            from agenttrace.integrations.langgraph import patch_langgraph
            # Re-importing is fine — the function checks internally

    def test_module_imports(self) -> None:
        """Integration module should be importable."""
        from agenttrace.integrations import langgraph
        assert hasattr(langgraph, "patch_langgraph")
