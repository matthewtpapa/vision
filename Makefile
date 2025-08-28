.PHONY: setup test test-cov lint fmt type

setup:
	pip install -e .
	pip install -r requirements-dev.txt

test:
	pytest

test-cov:
	@python -c "import pytest_cov" >/dev/null 2>&1 || (echo "pytest-cov not installed; run 'pip install -r requirements-dev.txt' or run in CI where it's provided." && exit 1)
	pytest --cov=vision --cov-report=term-missing --cov-report=xml

lint:
	ruff check .

fmt:
	ruff format --check .

type:
	mypy src/vision
