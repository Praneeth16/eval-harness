"""Centralized settings — reads from .env via pydantic-settings."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── LLM gateway ──
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="OPENROUTER_BASE_URL",
    )
    openrouter_app_name: str = Field(default="eval-harness", alias="OPENROUTER_APP_NAME")
    openrouter_referer: str = Field(
        default="http://localhost:3000", alias="OPENROUTER_REFERER"
    )

    default_model: str = Field(default="google/gemini-flash-latest", alias="DEFAULT_MODEL")
    judge_model: str = Field(default="google/gemini-flash-latest", alias="JUDGE_MODEL")
    portability_models: str = Field(
        default=(
            "google/gemini-flash-latest,"
            "meta-llama/llama-3.3-70b-instruct,"
            "anthropic/claude-sonnet-4-6,"
            "qwen/qwen-2.5-72b-instruct"
        ),
        alias="PORTABILITY_MODELS",
    )

    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2048, alias="LLM_MAX_TOKENS")
    llm_timeout_s: float = Field(default=60.0, alias="LLM_TIMEOUT_S")
    llm_max_retries: int = Field(default=4, alias="LLM_MAX_RETRIES")
    llm_retry_backoff_base_s: float = Field(default=1.0, alias="LLM_RETRY_BACKOFF_BASE_S")

    # ── MLflow ──
    mlflow_tracking_uri: str = Field(
        default="sqlite:///./.data/mlflow.db", alias="MLFLOW_TRACKING_URI"
    )
    mlflow_experiment_name: str = Field(
        default="eval-harness", alias="MLFLOW_EXPERIMENT_NAME"
    )
    mlflow_artifact_root: str = Field(
        default="./.data/mlflow-artifacts", alias="MLFLOW_ARTIFACT_ROOT"
    )

    # ── App DB (SQLite) ──
    database_url: str = Field(
        default="sqlite:///./.data/eval_harness.db", alias="DATABASE_URL"
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    database_wal: bool = Field(default=True, alias="DATABASE_WAL")

    # ── API ──
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_log_level: str = Field(default="info", alias="API_LOG_LEVEL")
    api_cors_origins: str = Field(default="http://localhost:3000", alias="API_CORS_ORIGINS")

    # ── Retrieval ──
    embed_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBED_MODEL"
    )
    embed_device: str = Field(default="cpu", alias="EMBED_DEVICE")
    faiss_index_dir: str = Field(default="./.data/indices", alias="FAISS_INDEX_DIR")

    # ── GEPA / DSPy ──
    gepa_max_iters: int = Field(default=12, alias="GEPA_MAX_ITERS")
    gepa_population: int = Field(default=8, alias="GEPA_POPULATION")
    gepa_reflection_sample_size: int = Field(
        default=20, alias="GEPA_REFLECTION_SAMPLE_SIZE"
    )
    gepa_pareto_objectives: str = Field(
        default="correctness,groundedness,safety,cost,latency",
        alias="GEPA_PARETO_OBJECTIVES",
    )

    # ── Cost guardrails ──
    cost_budget_per_eval_usd: float = Field(default=2.0, alias="COST_BUDGET_PER_EVAL_USD")
    cost_budget_per_opt_usd: float = Field(default=20.0, alias="COST_BUDGET_PER_OPT_USD")
    cost_hard_stop_usd: float = Field(default=50.0, alias="COST_HARD_STOP_USD")

    # ── Eval ──
    eval_parallelism: int = Field(default=4, alias="EVAL_PARALLELISM")
    eval_trace_sample_rate: float = Field(default=1.0, alias="EVAL_TRACE_SAMPLE_RATE")

    # ── Logging ──
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=False, alias="LOG_JSON")

    # ── Demo toggles ──
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")
    demo_preload_traces: str = Field(
        default="./.data/prebaked/traces.sqlite", alias="DEMO_PRELOAD_TRACES"
    )
    demo_preload_gepa: str = Field(
        default="./.data/prebaked/gepa_runs.json", alias="DEMO_PRELOAD_GEPA"
    )

    # ── Derived ──
    @property
    def portability_model_list(self) -> list[str]:
        return [m.strip() for m in self.portability_models.split(",") if m.strip()]

    @property
    def gepa_objective_list(self) -> list[str]:
        return [o.strip() for o in self.gepa_pareto_objectives.split(",") if o.strip()]

    @property
    def api_cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @property
    def data_dir(self) -> Path:
        return REPO_ROOT / ".data"


settings = Settings()


def ensure_data_dirs() -> None:
    """Create local data dirs so SQLite + MLflow + FAISS have a home."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Path(settings.mlflow_artifact_root).mkdir(parents=True, exist_ok=True)
    Path(settings.faiss_index_dir).mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "prebaked").mkdir(parents=True, exist_ok=True)
