"""OpenRouter client wrapper.

OpenRouter exposes an OpenAI-compatible HTTP API at `/api/v1`. We use the
official `openai` SDK with `base_url` swapped and add:

  * tenacity-driven retry on transient 429 / 5xx / timeout / connection errors
  * per-call usage + cost accounting (estimated against the local registry)
  * MLflow span emission (lazy import — keeps `core.llm` usable in isolation)

Sync API only for now — call sites can wrap in `asyncio.to_thread` when
running concurrently from the FastAPI event loop.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import openai
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.config import settings
from core.llm.models import estimate_cost_usd, resolve_alias

log = logging.getLogger(__name__)


@dataclass
class UsageStats:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0

    def merge(self, other: UsageStats) -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cost_usd += other.cost_usd
        self.latency_ms += other.latency_ms


@dataclass
class LLMResponse:
    content: str
    model: str
    raw: Any
    usage: UsageStats = field(default_factory=UsageStats)
    finish_reason: str | None = None
    tool_calls: list[Any] | None = None


_RETRYABLE = (
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
)


def _is_retryable_status(exc: BaseException) -> bool:
    if isinstance(exc, _RETRYABLE):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code >= 500 or exc.status_code == 408
    return False


class LLMClient:
    """Thin OpenAI-SDK wrapper. Two providers, one client interface.

    Provider selection:
      * `LLM_PROVIDER=gemini`   → Google AI Studio's OpenAI-compatible
        endpoint (default). Bare slugs like `gemini-2.5-flash`.
      * `LLM_PROVIDER=openrouter` → OpenRouter. Slugs like
        `google/gemini-2.5-flash`, `anthropic/claude-sonnet-4-6`.

    A specific call can route to OpenRouter even when the default provider
    is Gemini by prefixing the model slug with `openrouter:` — used by the
    cross-model portability run for non-Google models.
    """

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        app_name: str | None = None,
        referer: str | None = None,
        timeout_s: float | None = None,
    ) -> None:
        self.provider = (provider or settings.llm_provider or "gemini").lower()
        self._or_client: openai.OpenAI | None = None
        self._gemini_client: openai.OpenAI | None = None

        # Gemini (AI Studio OpenAI-compat) client.
        gkey = (api_key if self.provider == "gemini" else None) or settings.gemini_api_key
        if gkey or self.provider == "gemini":
            if not gkey and self.provider == "gemini":
                log.warning(
                    "GEMINI_API_KEY is empty — Gemini calls will fail. "
                    "Drop the key into .env."
                )
            self._gemini_client = openai.OpenAI(
                api_key=gkey or "missing",
                base_url=base_url
                if self.provider == "gemini" and base_url
                else settings.gemini_base_url,
                timeout=timeout_s or settings.llm_timeout_s,
            )

        # OpenRouter client (used for `openrouter:` prefixed models, or as
        # the default if `LLM_PROVIDER=openrouter`).
        okey = (api_key if self.provider == "openrouter" else None) or settings.openrouter_api_key
        if okey or self.provider == "openrouter":
            if not okey and self.provider == "openrouter":
                log.warning(
                    "OPENROUTER_API_KEY is empty — OpenRouter calls will fail. "
                    "Drop the key into .env."
                )
            self._or_client = openai.OpenAI(
                api_key=okey or "missing",
                base_url=base_url
                if self.provider == "openrouter" and base_url
                else settings.openrouter_base_url,
                default_headers={
                    "HTTP-Referer": referer or settings.openrouter_referer,
                    "X-Title": app_name or settings.openrouter_app_name,
                },
                timeout=timeout_s or settings.llm_timeout_s,
            )

    def _route(self, slug: str) -> tuple[openai.OpenAI, str]:
        """Pick the right SDK client + clean slug for a given model string."""
        if slug.startswith("openrouter:"):
            if self._or_client is None:
                raise RuntimeError(
                    "model requested OpenRouter routing but OPENROUTER_API_KEY is unset"
                )
            return self._or_client, slug.removeprefix("openrouter:")
        # OpenRouter-flavored slug (`vendor/model`) → OpenRouter.
        if "/" in slug:
            if self._or_client is None:
                raise RuntimeError(
                    f"model {slug!r} looks like an OpenRouter slug but "
                    "OPENROUTER_API_KEY is unset"
                )
            return self._or_client, slug
        # Bare slug → default provider's client (Gemini for AI Studio).
        if self.provider == "gemini":
            if self._gemini_client is None:
                raise RuntimeError("Gemini client not initialized")
            return self._gemini_client, slug
        # OpenRouter as default but bare slug — pass through.
        assert self._or_client is not None
        return self._or_client, slug

    @retry(
        retry=retry_if_exception_type(_RETRYABLE) | retry_if_exception_type(APIStatusError),
        stop=stop_after_attempt(settings.llm_max_retries),
        wait=wait_exponential(
            multiplier=settings.llm_retry_backoff_base_s, min=1, max=15
        ),
        reraise=True,
    )
    def _chat_raw(self, *, _client: openai.OpenAI, **kwargs: Any) -> Any:
        try:
            return _client.chat.completions.create(**kwargs)
        except APIStatusError as e:
            if _is_retryable_status(e):
                raise
            raise

    def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        **extra: Any,
    ) -> LLMResponse:
        """Single chat completion call. Returns an `LLMResponse` with usage filled."""
        requested = model or settings.default_model
        client, routed_slug = self._route(requested)
        slug = resolve_alias(routed_slug)
        params: dict[str, Any] = {
            "model": slug,
            "messages": messages,
            "temperature": (
                temperature if temperature is not None else settings.llm_temperature
            ),
            "max_tokens": max_tokens or settings.llm_max_tokens,
        }
        if tools:
            params["tools"] = tools
        if response_format:
            params["response_format"] = response_format
        # Gemini-only knob: disable thinking by default to keep prebake fast.
        # No-op on OpenRouter / other providers (they ignore unknown params).
        if (
            self.provider == "gemini"
            and "reasoning_effort" not in extra
            and settings.llm_reasoning_effort
        ):
            params["reasoning_effort"] = settings.llm_reasoning_effort
        params.update(extra)

        t0 = time.perf_counter()
        raw = self._chat_raw(_client=client, **params)
        latency_ms = int((time.perf_counter() - t0) * 1000)

        choice = raw.choices[0]
        message = choice.message
        usage_raw = getattr(raw, "usage", None)
        in_toks = getattr(usage_raw, "prompt_tokens", 0) or 0
        out_toks = getattr(usage_raw, "completion_tokens", 0) or 0
        cost = estimate_cost_usd(slug, in_toks, out_toks)

        return LLMResponse(
            content=message.content or "",
            model=slug,
            raw=raw,
            usage=UsageStats(
                input_tokens=in_toks,
                output_tokens=out_toks,
                cost_usd=cost,
                latency_ms=latency_ms,
            ),
            finish_reason=choice.finish_reason,
            tool_calls=getattr(message, "tool_calls", None),
        )


_singleton: LLMClient | None = None


def get_client() -> LLMClient:
    """Lazily-constructed default client. Use this in agent / scorer code."""
    global _singleton
    if _singleton is None:
        _singleton = LLMClient()
    return _singleton
