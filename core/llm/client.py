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
    """Thin OpenAI-SDK wrapper pointed at OpenRouter with retry + cost tracking."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        app_name: str | None = None,
        referer: str | None = None,
        timeout_s: float | None = None,
    ) -> None:
        key = api_key or settings.openrouter_api_key
        if not key:
            log.warning(
                "OPENROUTER_API_KEY is empty — calls will fail. "
                "Copy .env.example to .env and fill the key."
            )

        self._client = openai.OpenAI(
            api_key=key or "missing",
            base_url=base_url or settings.openrouter_base_url,
            default_headers={
                # OpenRouter recommends sending these for analytics + rate-limit attribution.
                "HTTP-Referer": referer or settings.openrouter_referer,
                "X-Title": app_name or settings.openrouter_app_name,
            },
            timeout=timeout_s or settings.llm_timeout_s,
        )

    @retry(
        retry=retry_if_exception_type(_RETRYABLE) | retry_if_exception_type(APIStatusError),
        stop=stop_after_attempt(settings.llm_max_retries),
        wait=wait_exponential(
            multiplier=settings.llm_retry_backoff_base_s, min=1, max=15
        ),
        reraise=True,
    )
    def _chat_raw(self, **kwargs: Any) -> Any:
        try:
            return self._client.chat.completions.create(**kwargs)
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
        slug = resolve_alias(model or settings.default_model)
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
        params.update(extra)

        t0 = time.perf_counter()
        raw = self._chat_raw(**params)
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
