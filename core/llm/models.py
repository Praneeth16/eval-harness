"""Model registry + pricing for OpenRouter-routed models.

Prices are USD per 1M tokens. Treat them as guidance; OpenRouter exposes
authoritative pricing per-call but we keep a local table to compute estimated
costs without an extra round-trip.

If a model is missing from the registry, `price_for` returns zeros and the
cost-tracking layer marks the line as `cost_estimated=False` for later
back-fill against `/api/v1/usage` if needed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    slug: str
    family: str
    context_window: int
    price_in_per_mtok_usd: float
    price_out_per_mtok_usd: float
    supports_tools: bool = True
    supports_structured_output: bool = True


# Resolved at load time; latest-aliases are mapped to the current best-known
# concrete slug. Bare `gemini-*` slugs map to AI-Studio-flavored slugs (no
# provider prefix), `google/...` slugs map to OpenRouter-flavored slugs.
_ALIAS_MAP: dict[str, str] = {
    "google/gemini-flash-latest": "google/gemini-2.5-flash",
    # Strip `openrouter:` prefix used in PORTABILITY_MODELS for routing only.
    "openrouter:gemini-2.5-flash": "google/gemini-2.5-flash",
}


MODEL_REGISTRY: dict[str, ModelSpec] = {
    # ── Google Gemini (AI Studio native slugs — no provider prefix) ──
    "gemini-2.5-flash": ModelSpec(
        slug="gemini-2.5-flash",
        family="gemini",
        context_window=1_000_000,
        price_in_per_mtok_usd=0.075,
        price_out_per_mtok_usd=0.30,
    ),
    "gemini-2.5-pro": ModelSpec(
        slug="gemini-2.5-pro",
        family="gemini",
        context_window=2_000_000,
        price_in_per_mtok_usd=1.25,
        price_out_per_mtok_usd=5.0,
    ),
    "gemini-2.0-flash": ModelSpec(
        slug="gemini-2.0-flash",
        family="gemini",
        context_window=1_000_000,
        price_in_per_mtok_usd=0.075,
        price_out_per_mtok_usd=0.30,
    ),
    # ── OpenRouter-flavored slugs ──
    "google/gemini-2.5-flash": ModelSpec(
        slug="google/gemini-2.5-flash",
        family="gemini",
        context_window=1_000_000,
        price_in_per_mtok_usd=0.075,
        price_out_per_mtok_usd=0.30,
    ),
    # ── Meta Llama ──
    "meta-llama/llama-3.3-70b-instruct": ModelSpec(
        slug="meta-llama/llama-3.3-70b-instruct",
        family="llama",
        context_window=128_000,
        price_in_per_mtok_usd=0.40,
        price_out_per_mtok_usd=0.40,
    ),
    # ── Anthropic Claude ──
    "anthropic/claude-sonnet-4-6": ModelSpec(
        slug="anthropic/claude-sonnet-4-6",
        family="claude",
        context_window=200_000,
        price_in_per_mtok_usd=3.0,
        price_out_per_mtok_usd=15.0,
    ),
    # ── Qwen ──
    "qwen/qwen-2.5-72b-instruct": ModelSpec(
        slug="qwen/qwen-2.5-72b-instruct",
        family="qwen",
        context_window=128_000,
        price_in_per_mtok_usd=0.35,
        price_out_per_mtok_usd=0.40,
    ),
    # ── Mistral ──
    "mistralai/mixtral-8x22b-instruct": ModelSpec(
        slug="mistralai/mixtral-8x22b-instruct",
        family="mistral",
        context_window=64_000,
        price_in_per_mtok_usd=0.90,
        price_out_per_mtok_usd=0.90,
    ),
}


def resolve_alias(slug: str) -> str:
    """Resolve `*-latest` aliases to their current concrete slug."""
    return _ALIAS_MAP.get(slug, slug)


def get_spec(slug: str) -> ModelSpec | None:
    return MODEL_REGISTRY.get(resolve_alias(slug))


def price_for(slug: str) -> tuple[float, float]:
    """Return (price_in_per_mtok, price_out_per_mtok) in USD. Zeros if unknown."""
    spec = get_spec(slug)
    if spec is None:
        return (0.0, 0.0)
    return (spec.price_in_per_mtok_usd, spec.price_out_per_mtok_usd)


def estimate_cost_usd(slug: str, input_tokens: int, output_tokens: int) -> float:
    """Compute estimated cost in USD given a token split."""
    in_price, out_price = price_for(slug)
    return (input_tokens * in_price + output_tokens * out_price) / 1_000_000.0
