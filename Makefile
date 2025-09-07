# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
.RECIPEPREFIX := >
.PHONY: setup test test-cov cov-html lint fmt format type mdlint mdfix verify hooks help

# Safer bash in make recipes
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

MDLINT_BIN := node_modules/.bin/markdownlint-cli2

help:
>echo "make setup     - install package + dev tools"
>echo "make lint      - ruff lint checks"
>echo "make fmt       - ruff format (check only)"
>echo "make format    - ruff format (write changes)"
>echo "make type      - mypy type checks"
>echo "make test      - run tests"
>echo "make test-cov  - run tests with coverage (requires pytest-cov)"
>echo "make cov-html  - build local HTML coverage report (if coverage data exists)"
>echo "make mdlint    - run markdownlint (same rules as CI)"
>echo "make mdfix     - auto-fix markdownlint issues (requires npx)"
>echo "make verify    - run all local checks (lint, fmt-check, type, test, markdownlint)"
>echo "make hooks     - install and autoupdate pre-commit hooks"
>echo "make hello     - print environment information"
>echo "make bench     - run fixture → eval → summary"
>echo "make demo      - run fixture → eval → plot demo"
>echo "make eval      - run evaluator on a directory of frames"
>echo ""
>echo "Tip: run 'npm ci' once to enable local markdownlint (make mdlint/mdfix)."

setup:
>if [ -n "$${CI:-}" ]; then \
>  pip install -e .; \
>  pip install -r requirements-dev.txt; \
>else \
>  pip install -e . || echo "⚠️ Skipped package install (pip blocked)"; \
>  pip install -r requirements-dev.txt || echo "⚠️ Skipped dev deps install (pip blocked)"; \
>fi

test:
>pytest

test-cov:
>@python -c "import pytest_cov" >/dev/null 2>&1 || (echo "pytest-cov not installed; run 'pip install -r requirements-dev.txt' or run in CI where it's provided." && exit 1)
>pytest --cov=vision --cov-report=term-missing --cov-report=xml

cov-html:
>@test -f .coverage || (echo "No .coverage file found. Run 'make test-cov' first (or download from CI artifacts)." && exit 1)
>coverage html

lint:
>ruff check .

fmt:
>ruff format --check .

format:
>ruff format .

type:
>mypy src/latency_vision

mdlint:
>if [ -x "$(MDLINT_BIN)" ]; then \
>  "$(MDLINT_BIN)"; \
>else \
>  echo "⚠️  markdownlint not installed locally; run 'npm ci' or rely on CI."; \
>fi

mdpush:
>@if command -v pre-commit >/dev/null 2>&1; then pre-commit run --all-files --hook-stage push || true; fi

mdfix:
>if [ -x "$(MDLINT_BIN)" ]; then \
>  "$(MDLINT_BIN)" --fix; \
>else \
>  echo "⚠️  markdownlint not installed locally; run 'npm ci'."; \
>fi

verify:
>@echo "==> Lint"
>@if command -v ruff >/dev/null 2>&1; then ruff check .; else echo "⚠️ ruff not installed; skipping lint"; fi
>@echo "==> Format check"
>@if command -v ruff >/dev/null 2>&1; then ruff format --check .; else echo "⚠️ ruff not installed; skipping format check"; fi
>@echo "==> Types"
>@if command -v mypy >/dev/null 2>&1; then mypy src/latency_vision; else echo "⚠️ mypy not installed; skipping type check"; fi
>@echo "==> Tests"
>@if [ -n "$${CI:-}" ]; then \
>  echo "(CI) tests run in separate coverage step"; \
>else \
>  if command -v pytest >/dev/null 2>&1; then \
>    pytest; \
>  else \
>    echo "⚠️ pytest not installed; skipping tests"; \
>  fi; \
>fi
>@echo "==> Markdownlint"
>@if [ -n "$${CI:-}" ]; then \
>  echo "(CI) markdownlint is advisory"; \
>  $(MAKE) mdlint || true; \
>else \
>  $(MAKE) mdlint; \
>fi
>$(MAKE) mdpush

hooks:
>pre-commit install
>pre-commit autoupdate

eval:
>if command -v latvision >/dev/null 2>&1; then \
>  latvision eval --input $(INPUT) --output $(OUTPUT) --warmup $(or $(WARMUP),100); \
>else \
>  PYTHONPATH=src latvision eval --input $(INPUT) --output $(OUTPUT) --warmup $(or $(WARMUP),100); \
>fi

hello:
>if command -v latvision >/dev/null 2>&1; then \
>  latvision hello; \
>else \
>  PYTHONPATH=src latvision hello; \
>fi

bench:
>python scripts/build_fixture.py --out bench/fixture --n 400
>latvision eval --input bench/fixture --output bench/out
>python scripts/print_summary.py --metrics bench/out/metrics.json

demo:
>python scripts/build_fixture.py --out bench/fixture --n 400
>latvision eval --input bench/fixture --output bench/out --warmup 0 --unknown-rate-band 0.0,1.0
>python scripts/print_summary.py --metrics bench/out/metrics.json
># Plot is best-effort locally (CI already warns if missing)
>python scripts/plot_latency.py --input bench/out/stage_timings.csv --output bench/out/latency.png --metrics bench/out/metrics.json || true

build:
>python -m pip install --upgrade build twine
>python -m build

check:
>python -m twine check dist/*

clean:
>rm -rf dist build *.egg-info

release: clean build check
>@echo "✅ Artifacts ready in ./dist"

release-rc:
>@echo "git tag -a v0.1.0-rc.2 -m \"M1.1 RC drill\""
>@echo "git push origin v0.1.0-rc.2"
