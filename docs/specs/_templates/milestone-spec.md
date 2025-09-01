# Milestone M?.? — <Name> (Spec v1)

## Gates (A–D)

- **Gate A — SDK Reality & API Freeze + Platform Matrix**: pip installable; import smoke; schema frozen; OS/Python matrix green.
- **Gate B — Bench Methodology**: monotonic_ns timing; NumPy percentile "linear"; warm-up excluded; GC/BLAS notes; CPU features logged.
- **Gate C — Docs & Attributions**: charter/spec/schema/latency/benchmarks/README; THIRD_PARTY.md complete.
- **Gate D — Readiness & Cold Start**: hello/eval/plot demo; cold-start path; name mapping.

## Scope

**In:** <bullets>
**Out:** <bullets>

## Deliverables (one PR per issue)

- Charter callout (if needed)
- Spec doc
- Schema updates (or “no change”)
- Latency doc updates
- Benchmarks doc updates
- README updates (demo/name mapping)
- Makefile targets (if new)
- Scripts (if new)

## Acceptance

```bash
# demo flow must pass on a clean machine (offline/headless)
python -m vision hello
python scripts/build_fixture.py --out bench/fixture --n 400
PYTHONPATH=src python -m vision eval --input bench/fixture --output bench/out
python scripts/print_summary.py --metrics bench/out/metrics.json
python scripts/plot_latency.py --input bench/out/stage_timings.csv
```

Exit codes

0 success

2 user/data error (bad path, empty/invalid files)

3 missing optional dependency (pillow, matplotlib)

Risks & Mitigations
<short bullets>

References

docs/schema.md

docs/latency.md

docs/benchmarks.md
