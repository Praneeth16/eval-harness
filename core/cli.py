"""evalh — Click CLI."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import click

from core.config import settings
from core.eval import run_eval
from core.store.db import init_db
from core.tracing import init_mlflow

logging.basicConfig(level=logging.INFO, format="%(message)s")


@click.group()
def main() -> None:
    """eval-harness — self-evolving eval harness for production AI agents."""
    init_mlflow()
    init_db()


@main.command("run")
@click.option("--example", default="quill", show_default=True)
@click.option(
    "--golden",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option("--model", default=None, help=f"defaults to {settings.default_model}")
@click.option("--no-judges", is_flag=True, help="skip L2 (LLM) scorers")
@click.option("--notes", default="")
def cmd_run(
    example: str, golden: Path, model: str | None, no_judges: bool, notes: str
) -> None:
    """Run an eval pass over a golden set."""
    summary = run_eval(
        example=example,
        golden_path=golden,
        model=model,
        include_judges=not no_judges,
        notes=notes,
    )
    click.echo(json.dumps(summary.__dict__, indent=2))


@main.command("build-index")
@click.option("--example", default="quill", show_default=True)
@click.option("--force", is_flag=True)
def cmd_build_index(example: str, force: bool) -> None:
    """Build the FAISS index for the example."""
    if example != "quill":
        raise click.ClickException(f"unknown example: {example}")
    from examples.quill.retrieval import build_index

    build_index(force=force)
    click.echo("index built.")


@main.command("init")
def cmd_init() -> None:
    """Initialize local data dirs + DB."""
    init_db()
    click.echo("eval-harness initialized.")


if __name__ == "__main__":
    main()
