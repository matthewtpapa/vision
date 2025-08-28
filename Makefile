.RECIPEPREFIX := >
.PHONY: setup test test-cov cov-html lint fmt format type mdlint verify help

# Safer bash in make recipes
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

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
>echo "make verify    - run all local checks (lint, fmt-check, type, test, markdownlint)"

setup:
>pip install -e .
>pip install -r requirements-dev.txt

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
>mypy src/vision

mdlint:
>if command -v pre-commit >/dev/null 2>&1; then \
>pre-commit run markdownlint-cli2 --all-files; \
>else \
>npx -y markdownlint-cli2-fix "**/*.md" --config .markdownlint-cli2.yaml; \
>fi

verify:
>@echo "==> Lint"
>ruff check .
>@echo "==> Format check"
>ruff format --check .
>@echo "==> Types"
>mypy src/vision
>@echo "==> Tests"
>pytest
>@echo "==> Markdownlint"
>pre-commit run markdownlint-cli2 --all-files
