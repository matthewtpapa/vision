# Contributing

Thanks for contributing! This project keeps Charter and Specs separate:

## Docs model

- Charter (docs/charter.md): north star + roadmap; reviewed at milestones; external-friendly.
- Specs (docs/specs/m1.md, m2.md, ...): exact API/telemetry schemas, thresholds, CI gates; must stay in lockstep with code.

When changing runtime behavior or schemas, update the relevant Spec in the same PR. Charter updates should be rare and reviewed broadly.

## Dev workflow

- `make fmt` / `make lint` / `make type` / `make test` / `make verify`
- Open small, testable PRs; add unit tests for new code & schemas
- markdownlint runs on docs; keep lines readable and headings consistent
- CI enforces markdownlint via a pinned GitHub Action.
- Optional local run: `npm ci && npx markdownlint-cli2 "**/*.md"` (or install it globally).

### Local Markdown lint (pinned toolchain)

```bash
npm ci               # one-time per clone / after updates (requires npm registry access)
npm run mdlint       # or: make mdlint
# optional auto-fix:
npm run mdfix        # or: make mdfix
```

> If npm ci fails (e.g., corporate proxy or 403 from the npm registry), skip local markdownlint.
> CI will still enforce the exact same rules via a pinned GitHub Action.

## CI gates (M1)

- `vision --eval` must pass latency/bootstrap thresholds
- JSON schema snapshot + CSV header checks

## Issue labels

- `spec` — changes to `docs/specs/*`, schema/gates
- `charter` — roadmap/north star updates
- `m1`/`m2`/... — milestone targeting
