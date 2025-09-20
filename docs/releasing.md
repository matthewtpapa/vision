# Releasing

This document outlines how to cut a release candidate (RC) tag.

## Cut an RC tag

Run the following commands:

```bash
git fetch origin
git checkout main
git pull --ff-only
git tag -a v0.1.0-rc.2 -m "M2 RC drill"
git push origin v0.1.0-rc.2
```

## Verify artifacts

When the tag job runs, confirm it produces:

- `bench/out/metrics.json`
- `bench/out/stage_times.csv`
- `bench/out/latency.png` (optional)
- `dist/*.whl`

## Purity artifact

CI emits `artifacts/purity_report.json` with counts for sockets/DNS. Release gates require zeros.
