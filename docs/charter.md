# Project Charter and Vision

## North Star
Deliver a real-time, open-set recognition SDK: detect, track, embed, and match objects in live video against a continually growing exemplar knowledge base.

- Sustains latency-bounded performance on reference hardware  
- Modular and backend-agnostic  
- Exposes a simple, typed Python API  
- Serves AR, robotics, and vision pipelines as infrastructure  
- Not a consumer app — this is **FFmpeg-for-open-set recognition**: boring, reliable infra that others depend on.

## Milestones (Roadmap)
- **M0 (Complete)** — Foundations: stubs, CLI scaffolding, local KB, dev workflow  
- **M1 (In Progress)** — Latency-Bounded Vertical Slice: end-to-end loop; telemetry + `--eval`; incremental KB updates; factory-based matcher  
- **M2** — Developer SDK: stable API; exemplar management; packaging & distribution; AR/robotics demos  
- **M3** — Scaling: multi-backend abstraction (FAISS-GPU, Torch/ONNX); KB persistence/versioning; frozen telemetry schema; gRPC/REST API  
- **M4** — Production Hardening: continuous ingestion; pruning/compaction; robustness tests; deployment profiles  
- **M5 (Stretch)** — Enterprise: ARKit/ARCore/Vision Pro integrations; telemetry dashboard; licensing model; OSS + commercial split

## M1 Focus (Highlights)
- Real-time vertical slice (detect → track → embed → match)  
- Incremental KB updates  
- Telemetry with `--eval` export (latency, FPS, unknown-rate, KB size)  
- Matcher factory: FAISS (preferred) + NumPy fallback  
- Minimal Python API surface: `add_exemplar(...)`, `query_frame(...)`

## Acceptance Highlights
- p95 latency ≤ 33 ms on reference CPU (CLIP-B32 baseline)  
- KB bootstrap ≤ 50 ms (N=1k)  
- Deterministic eval fixture (≥2k frames, seeded)

## Process Guardrails
- **Charter (this doc)** → sets vision, roadmap, and themes. Evolves slowly (reviewed at major milestones)  
- **Specs (per milestone)** → exact contracts, telemetry schemas, CI gates. Evolve quickly, live close to code  
- Charter answers "what and why"; Specs answer "how and with what guarantees"
