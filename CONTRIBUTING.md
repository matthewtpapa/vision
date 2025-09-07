# Contributing

## Supported Python

3.10 – 3.12

## Local setup

```bash
pip install -e .
pip install -r requirements-dev.txt
make verify
```

Note: The local test suite uses optional dependencies. Installing `numpy` and `pillow` enables full coverage; without them you'll see skipped tests. CI installs both.

## Test policy

The public façade and result schema are frozen. Updates must refresh tests and `docs/schema.md`.

## CI gates

- ci-matrix
- latency-gate
- readme-smoke
- docs-gate

## Commit/PR guidance

Keep commits small and focused. Tests and docs should accompany behavioral changes. Open PRs against `main`.
