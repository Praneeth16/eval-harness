.DEFAULT_GOAL := help

# ── Paths
VENV       ?= .venv
PY         := $(VENV)/bin/python
PIP        := $(VENV)/bin/pip
UV         ?= uv
UI_DIR     := ui

# ── Setup ─────────────────────────────────────────────────────────────────────

.PHONY: venv
venv: ## Create the Python 3.11 venv via uv
	@$(UV) python install 3.11 >/dev/null 2>&1 || true
	@$(UV) venv --python 3.11 $(VENV)

.PHONY: install
install: venv ## Install Python deps (editable) + UI deps
	@source $(VENV)/bin/activate && $(UV) pip install -e ".[dev]"
	@cd $(UI_DIR) && npm install --no-audit --no-fund

.PHONY: init
init: ## Initialize local data dirs + SQLite store + FAISS index
	@source $(VENV)/bin/activate && evalh init && evalh build-index --example quill

.PHONY: seed
seed: init ## Seed the offline demo (Pareto + headline + portability)
	@source $(VENV)/bin/activate && $(PY) -m scripts.seed_demo_data

# ── Run ──────────────────────────────────────────────────────────────────────

.PHONY: api
api: ## Run FastAPI on :8000
	@source $(VENV)/bin/activate && uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

.PHONY: ui
ui: ## Run Next.js dev server on :3000
	@cd $(UI_DIR) && npm run dev

.PHONY: mlflow
mlflow: ## Run MLflow UI on :5000 against local tracking db
	@source $(VENV)/bin/activate && mlflow ui --backend-store-uri sqlite:///./.data/mlflow.db --host 127.0.0.1 --port 5000

# ── Eval ─────────────────────────────────────────────────────────────────────

.PHONY: eval-soc2
eval-soc2: ## Run baseline Quill eval on SOC2 golden set
	@source $(VENV)/bin/activate && evalh run --example quill --golden examples/quill/golden/soc2.jsonl

.PHONY: eval-iso
eval-iso: ## Run Quill eval on ISO27001 holdout
	@source $(VENV)/bin/activate && evalh run --example quill --golden examples/quill/golden/iso27001_holdout.jsonl

.PHONY: eval-injection
eval-injection: ## Run Quill eval on prompt-injection corpus
	@source $(VENV)/bin/activate && evalh run --example quill --golden examples/quill/golden/injection.jsonl

# ── Demo ─────────────────────────────────────────────────────────────────────

.PHONY: prebake
prebake: ## Materialize real demo artifacts (requires OPENROUTER_API_KEY)
	@source $(VENV)/bin/activate && $(PY) -m scripts.prebake

.PHONY: demo
demo: seed ## Start everything for the stage demo (UI + API + MLflow)
	@printf "\n\033[1;32m▌ eval-harness demo path ready\033[0m\n\n"
	@printf "  UI       http://localhost:3000\n"
	@printf "  API      http://localhost:8000/docs\n"
	@printf "  MLflow   http://localhost:5000\n\n"
	@printf "Open three terminals (or use tmux/zellij):\n"
	@printf "  1)  make api\n"
	@printf "  2)  make ui\n"
	@printf "  3)  make mlflow\n\n"

# ── Quality ──────────────────────────────────────────────────────────────────

.PHONY: lint
lint: ## ruff check + tsc --noEmit
	@source $(VENV)/bin/activate && ruff check core/ api/ examples/ scripts/
	@cd $(UI_DIR) && npx tsc --noEmit

.PHONY: fmt
fmt: ## ruff format
	@source $(VENV)/bin/activate && ruff format core/ api/ examples/ scripts/

.PHONY: build-ui
build-ui: ## next build (verifies UI compiles)
	@cd $(UI_DIR) && npm run build

.PHONY: test
test: ## pytest (placeholder)
	@source $(VENV)/bin/activate && pytest -q

# ── Housekeeping ─────────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Drop local .data/, FAISS indices, Next caches (keeps committed prebaked artifacts)
	@rm -rf .data/ $(UI_DIR)/.next $(UI_DIR)/.turbo
	@find . -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@printf "cleaned local data + caches.\n"

.PHONY: help
help: ## Show this help
	@printf "\n\033[1meval-harness\033[0m — make targets:\n\n"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf "\n"
