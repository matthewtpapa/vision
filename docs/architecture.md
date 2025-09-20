# Architecture

## Module Map

- **detect:** runtime detector wrapper (tests use fake stubs)
- **track:** association and trajectory management
- **embed:** frame-to-vector embedding stage
- **match:** similarity search over the local LabelBank
- **oracle/** — offline candidate generation
- **verify/** — gallery check + re-embed
- **telemetry:** structured metrics and logging hooks

> **WARNING:** `ris.py` exists only for tests/offline ingestion. Never called in the hot loop.

## Hot loop dataflow

Detector → Tracker → Embedder → Match → (if unknown) Oracle → Verify → Ledger.

## Notes

- LabelBank lookups and candidate generation are offline-first; runtime reads immutable shards.
- Verify uses a curated local gallery and re-embeds evidence before ledger writes.
- Ledger outputs feed capped int8 medoids during offline promotion.
- No network in the hot loop; runtime relies solely on local and cached artifacts.
