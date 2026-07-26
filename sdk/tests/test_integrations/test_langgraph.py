"""Tests for the LangGraph integration patch.

Uses a stub ``langgraph.graph.StateGraph`` so the patch/unpatch logic can be
verified without the real langgraph package installed.
"""

from __future__ import annotations

import sys
import types

import pytest


@pytest.fixture
def fake_langgraph(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Inject a fake ``langgraph.graph`` module exposing ``StateGraph``."""

    class StateGraph:
        def add_node(self, node: str, action: object, **kwargs: object) -> object:
            return ("original", node, action)

    langgraph_pkg = types.ModuleType("langgraph")
    graph_mod = types.ModuleType("langgraph.graph")
    graph_mod.StateGraph = StateGraph
    langgraph_pkg.graph = graph_mod

    monkeypatch.setitem(sys.modules, "langgraph", langgraph_pkg)
    monkeypatch.setitem(sys.modules, "langgraph.graph", graph_mod)
    return graph_mod


def test_patch_replaces_add_node_and_unpatch_restores(
    fake_langgraph: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """patch_langgraph wraps add_node; unpatch_langgraph restores the original."""
    import agenttrace.integrations.langgraph as lg

    monkeypatch.setattr(lg, "_patched", False)
    monkeypatch.setattr(lg, "_original_add_node", None)

    original = fake_langgraph.StateGraph.add_node

    lg.patch_langgraph()
    assert fake_langgraph.StateGraph.add_node is not original  # patched

    lg.unpatch_langgraph()
    assert fake_langgraph.StateGraph.add_node is original  # restored in-process


def test_patch_wraps_node_action(
    fake_langgraph: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The patched add_node wraps the user's node function with tracing."""
    from agenttrace import tracer

    tracer.init(collector_url="http://localhost:8000")
    collected: list = []
    monkeypatch.setattr(tracer, "_emit", collected.append)

    import agenttrace.integrations.langgraph as lg

    monkeypatch.setattr(lg, "_patched", False)
    monkeypatch.setattr(lg, "_original_add_node", None)
    lg.patch_langgraph()

    sg = fake_langgraph.StateGraph()
    seen: list = []

    def my_node(state: object) -> str:
        seen.append(state)
        return "done"

    # add_node returns ("original", name, wrapped_action); extract the wrapper.
    result = sg.add_node("researcher", my_node)
    assert result[0] == "original"
    assert result[1] == "researcher"
    wrapped = result[2]

    out = wrapped("state-input")
    assert out == "done"
    assert seen == ["state-input"]
    # The node call was wrapped in a traced span (emitted on exit as agent_end).
    assert len(collected) == 1
    assert collected[0].event_type == "agent_end"
    assert collected[0].agent_name == "langgraph_agent.researcher"
