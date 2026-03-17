"""Cost calculator using pricing.json model pricing table."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_PRICING_DATA: Optional[dict[str, object]] = None


def _load_pricing() -> dict[str, object]:
    """Load pricing data from pricing.json."""
    global _PRICING_DATA
    if _PRICING_DATA is not None:
        return _PRICING_DATA

    pricing_path = Path(__file__).parent / "pricing.json"
    if not pricing_path.exists():
        logger.warning("pricing.json not found at %s", pricing_path)
        _PRICING_DATA = {"models": {}}
        return _PRICING_DATA

    with open(pricing_path, encoding="utf-8") as f:
        _PRICING_DATA = json.load(f)
    return _PRICING_DATA


def estimate_cost(
    model: Optional[str],
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
) -> Optional[float]:
    """Estimate the cost of an LLM call based on model pricing.

    Returns None if model is not found in pricing table or tokens are missing.
    Cost = (prompt_tokens / 1000 * input_price) + (completion_tokens / 1000 * output_price)
    """
    if not model or prompt_tokens is None or completion_tokens is None:
        return None

    pricing = _load_pricing()
    models = pricing.get("models", {})
    if not isinstance(models, dict):
        return None

    model_pricing = models.get(model)
    if model_pricing is None:
        # Try matching with common prefixes stripped
        for key, value in models.items():
            if model.startswith(key) or key.startswith(model):
                model_pricing = value
                break

    if model_pricing is None or not isinstance(model_pricing, dict):
        return None

    input_price = model_pricing.get("input_per_1k_tokens", 0)
    output_price = model_pricing.get("output_per_1k_tokens", 0)

    if not isinstance(input_price, (int, float)) or not isinstance(output_price, (int, float)):
        return None

    cost = (prompt_tokens / 1000 * input_price) + (completion_tokens / 1000 * output_price)
    return round(cost, 8)


def reload_pricing() -> None:
    """Force reload of pricing data from disk."""
    global _PRICING_DATA
    _PRICING_DATA = None
    _load_pricing()
