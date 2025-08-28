.PHONY: setup test test-cov lint fmt type

setup:
	pip install -e .
	pip install -r requirements-dev.txt

test:
	pytest

test-cov:
	pytest --cov=vision --cov-report=term-missing --cov-report=xml

lint:
	ruff check .

fmt:
	ruff format --check .

type:
	mypy src/vision
