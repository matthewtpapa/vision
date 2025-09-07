# Releasing

This document outlines how to cut a release candidate (RC) tag.

## Cut an RC tag

Run the following commands:

```bash
git fetch origin
git checkout main
git pull --ff-only
git tag -a v0.1.0-rc.2 -m "M1.1 RC drill"
git push origin v0.1.0-rc.2
```

## Verify artifacts

When the tag job runs, confirm it produces:

- `bench/out/metrics.json`
- `bench/out/stage_timings.csv`
- `bench/out/latency.png` (optional)
- `dist/*.whl`
