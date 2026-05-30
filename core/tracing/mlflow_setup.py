"""Initialize the MLflow tracking server + experiment for eval-harness."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import mlflow

from core.config import ensure_data_dirs, settings

log = logging.getLogger(__name__)

_initialized = False


def init_mlflow() -> None:
    """Set the tracking URI and create / select the experiment. Idempotent."""
    global _initialized
    if _initialized:
        return

    ensure_data_dirs()
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

    set_experiment(settings.mlflow_experiment_name)

    log.info(
        "MLflow tracking: uri=%s experiment=%s",
        settings.mlflow_tracking_uri,
        settings.mlflow_experiment_name,
    )
    _initialized = True


def set_experiment(name: str) -> None:
    """Create the experiment if missing and select it for the current process."""
    init_mlflow_if_needed()
    exp = mlflow.get_experiment_by_name(name)
    if exp is None:
        mlflow.create_experiment(
            name=name, artifact_location=settings.mlflow_artifact_root
        )
    mlflow.set_experiment(name)


def init_mlflow_if_needed() -> None:
    """Avoid recursion on the first `set_experiment` call from inside `init_mlflow`."""
    global _initialized
    if _initialized:
        return
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    _initialized = True


_experiment_id_cache: str | None = None


def _experiment_id() -> str:
    """Resolve the numeric experiment id. MLflow's UI routes key on the numeric
    id, not the name — `/#/experiments/eval-harness/...` 404s with
    'Experiment ID must be a valid integer'."""
    global _experiment_id_cache
    if _experiment_id_cache is not None:
        return _experiment_id_cache
    try:
        init_mlflow_if_needed()
        exp = mlflow.get_experiment_by_name(settings.mlflow_experiment_name)
        if exp is not None:
            _experiment_id_cache = str(exp.experiment_id)
    except Exception:
        _experiment_id_cache = None
    return _experiment_id_cache or "1"


def mlflow_trace_url(trace_id: str, *, ui_host: str = "http://localhost:5000") -> str:
    """Return a deep link into MLflow's native trace UI for a given trace id.

    We intentionally rely on MLflow's existing trace inspection UI rather than
    rebuilding one — our Next.js UI links out to this URL.
    """
    # MLflow 3.x routes traces by NUMERIC experiment id, and deep-links to a
    # single trace via the selectedTraceId query param on the traces tab.
    parsed = urlparse(ui_host)
    if not parsed.scheme:
        ui_host = f"http://{ui_host}"
    return (
        f"{ui_host.rstrip('/')}/#/experiments/{_experiment_id()}"
        f"/traces?selectedTraceId={trace_id}"
    )
