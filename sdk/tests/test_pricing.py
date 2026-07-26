"""Tests for the pricing calculator."""

from __future__ import annotations

from agenttrace.pricing import estimate_cost


def test_known_model_cost() -> None:
    """Exact model match computes cost from per-1k-token prices."""
    # gpt-4o: 0.0025/1k in, 0.01/1k out -> 1000+1000 tokens.
    cost = estimate_cost("gpt-4o", 1000, 1000)
    assert cost is not None
    assert cost == round(0.0025 + 0.01, 8)


def test_dated_variant_matches_family() -> None:
    """A dated snapshot like gpt-4o-2024-08-06 resolves to the gpt-4o family."""
    assert estimate_cost("gpt-4o-2024-08-06", 1000, 1000) == estimate_cost(
        "gpt-4o", 1000, 1000
    )


def test_short_model_does_not_match_broader_key() -> None:
    """A bare prefix like 'gpt' must NOT silently resolve to 'gpt-4o' pricing.

    The previous fuzzy match used ``key.startswith(model)`` which would have let
    'gpt' match 'gpt-4o'. The boundary-aware match returns None instead.
    """
    assert estimate_cost("gpt", 1000, 1000) is None
    assert estimate_cost("gpt-4", 1000, 1000) is None


def test_unknown_model_returns_none() -> None:
    assert estimate_cost("totally-unknown-model", 100, 100) is None


def test_missing_tokens_returns_none() -> None:
    assert estimate_cost("gpt-4o", None, 100) is None
    assert estimate_cost("gpt-4o", 100, None) is None


def test_missing_model_returns_none() -> None:
    assert estimate_cost(None, 100, 100) is None
    assert estimate_cost("", 100, 100) is None


def test_local_model_is_free() -> None:
    """Local Ollama models are priced at 0, not None."""
    assert estimate_cost("llama4-scout", 500, 500) == 0.0
