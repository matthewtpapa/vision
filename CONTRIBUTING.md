# Contributing

## Setup

```bash
git clone https://github.com/matthewtpapa/vision.git
cd vision
python -m venv .venv
source .venv/bin/activate
make setup

```

## Local checks

Run `make verify` before opening a pull request.

## Markdown lint

- `make mdlint` for strict lint.
- `make mdfix` to auto-fix issues.

## Coverage

Optional: `make test-cov && make cov-html`. Continuous integration always uploads coverage reports.

## PR rules

- Keep changes small and atomic.
- Link an issue in every pull request.
- CI must be green.
- Squash merge and delete the branch after merge.

`pre-commit` is optional but recommended: install with `pip install pre-commit && pre-commit install`.
