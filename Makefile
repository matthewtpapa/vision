.PHONY: test test-cov lint fmt type

test:
	pytest

test-cov:
	pip install pytest-cov
	pytest --cov=vision --cov-report=term-missing --cov-report=xml

lint:
	ruff check .

fmt:
	ruff format --check .

type:
	mypy src/vision
