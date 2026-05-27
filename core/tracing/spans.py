"""Span helpers + the eval-harness span-type taxonomy.

MLflow 3 exposes `mlflow.trace` (decorator) and `mlflow.start_span` (context
manager) with a `span_type` argument. The CLEAR-S taxonomy + Quill's
multi-agent shape demand a few extra named types beyond MLflow's defaults,
so we register them as plain strings and standardize naming here.

Use:

    from core.tracing import tool_span, trace, SpanType

    @trace(span_type=SpanType.AGENT)
    def quill_supervisor(...):
        with tool_span("policy_exists_check", inputs={...}) as span:
            result = policy_exists(...)
            span.set_outputs(result)
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from enum import StrEnum
from typing import Any

import mlflow
from mlflow.entities import SpanType as MlflowSpanType

from core.tracing.mlflow_setup import init_mlflow


class SpanType(StrEnum):
    """eval-harness span vocabulary. Maps to MLflow built-ins where possible."""

    # Native MLflow span types
    AGENT = MlflowSpanType.AGENT
    CHAIN = MlflowSpanType.CHAIN
    TOOL = MlflowSpanType.TOOL
    RETRIEVER = MlflowSpanType.RETRIEVER
    LLM = MlflowSpanType.LLM
    PARSER = MlflowSpanType.PARSER
    EMBEDDING = MlflowSpanType.EMBEDDING

    # Custom Quill / harness span types
    SKILL_SELECT = "skill_select"
    SKILL_LOAD = "skill_load"
    SKILL_EXECUTE = "skill_execute"
    JUDGE = "judge"
    SCORER = "scorer"
    GEPA_REFLECT = "gepa_reflect"
    GEPA_MUTATE = "gepa_mutate"
    GEPA_PARETO = "gepa_pareto"


def trace(
    name: str | None = None,
    span_type: str | SpanType | None = SpanType.CHAIN,
    attributes: dict[str, Any] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator wrapper around `mlflow.trace` that lazy-initializes tracking."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        init_mlflow()
        return mlflow.trace(
            name=name or fn.__name__,
            span_type=str(span_type) if span_type else None,
            attributes=attributes,
        )(fn)

    return decorator


@contextmanager
def _named_span(
    name: str,
    span_type: SpanType,
    inputs: dict[str, Any] | None = None,
    attributes: dict[str, Any] | None = None,
) -> Iterator[Any]:
    init_mlflow()
    # MLflow 3.x dropped `inputs` from `start_span` — fold caller-supplied
    # inputs into attributes so existing call sites keep working.
    attrs = dict(attributes or {})
    if inputs:
        attrs.setdefault("inputs", inputs)
    with mlflow.start_span(
        name=name, span_type=str(span_type), attributes=attrs
    ) as span:
        if inputs:
            set_inputs = getattr(span, "set_inputs", None)
            if callable(set_inputs):
                try:
                    set_inputs(inputs)
                except Exception:  # noqa: BLE001
                    pass
        yield span


def agent_span(name: str, **kwargs: Any) -> Any:
    return _named_span(name=name, span_type=SpanType.AGENT, **kwargs)


def chain_span(name: str, **kwargs: Any) -> Any:
    return _named_span(name=name, span_type=SpanType.CHAIN, **kwargs)


def tool_span(name: str, **kwargs: Any) -> Any:
    return _named_span(name=name, span_type=SpanType.TOOL, **kwargs)


def retriever_span(name: str, **kwargs: Any) -> Any:
    return _named_span(name=name, span_type=SpanType.RETRIEVER, **kwargs)


def llm_span(name: str, **kwargs: Any) -> Any:
    return _named_span(name=name, span_type=SpanType.LLM, **kwargs)


def parser_span(name: str, **kwargs: Any) -> Any:
    return _named_span(name=name, span_type=SpanType.PARSER, **kwargs)


def add_attributes(attributes: dict[str, Any]) -> None:
    """Attach attributes to the currently-active span (no-op if none)."""
    span = mlflow.get_current_active_span()
    if span is None:
        return
    span.set_attributes(attributes)


def set_status(status: str, description: str | None = None) -> None:
    """Set status on the currently-active span. Status: OK | ERROR."""
    span = mlflow.get_current_active_span()
    if span is None:
        return
    span.set_status(status, description)
