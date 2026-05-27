"""Tools the Quill agent can (and should) call.

Each tool emits its own MLflow span so the trajectory scorer can detect
whether the agent invoked `policy_exists_check` before citing a policy ID
in its draft.
"""

from __future__ import annotations

import contextlib
from typing import Any

from core.tracing import SpanType, tool_span
from examples.quill.retrieval import framework_clause_resolves, policy_exists


def call_policy_exists_check(policy_id: str) -> bool:
    """Verify a policy ID resolves in the corpus before citing it."""
    with tool_span(
        "policy_exists_check",
        inputs={"policy_id": policy_id},
        attributes={"tool": "policy_exists_check"},
    ) as span:
        result = policy_exists(policy_id)
        with contextlib.suppress(AttributeError):
            span.set_outputs({"exists": result})
        return result


def call_framework_clause_check(framework: str, clause_id: str) -> bool:
    """Verify a framework clause resolves before citing it."""
    with tool_span(
        "framework_clause_check",
        inputs={"framework": framework, "clause_id": clause_id},
        attributes={"tool": "framework_clause_check"},
    ) as span:
        result = framework_clause_resolves(framework, clause_id)
        with contextlib.suppress(AttributeError):
            span.set_outputs({"exists": result})
        return result


TOOL_NAMES = ("policy_exists_check", "framework_clause_check")


__all__ = [
    "TOOL_NAMES",
    "Any",
    "SpanType",  # re-export for convenience
    "call_framework_clause_check",
    "call_policy_exists_check",
]
