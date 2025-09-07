# Contributing

Thanks for contributing! This project keeps Charter and Specs separate:

## Docs model

- Charter (docs/charter.md): north star + roadmap; reviewed at milestones; external-friendly.
- Specs (docs/specs/m1.md, m2.md, ...): exact API/telemetry schemas, thresholds, CI gates; must stay in lockstep with code.

When changing runtime behavior or schemas, update the relevant Spec in the same PR. Charter updates should be rare and reviewed broadly.

## Dev setup

```bash
python -m pip install -r requirements-dev.txt
pre-commit install           # or: make hooks
pre-commit run --all-files   # optional first run
```

Hooks run on staged files (ruff + format + basic hygiene). CI does not run pre-commit; ruff/mypy/pytest remain the enforcement gates.
The `make hooks` target installs and autoupdates the pre-commit hooks. Autoupdate may change hook revs; don’t commit those bumps unless explicitly requested.

Run a single hook:

```bash
pre-commit run ruff --all-files
```

Skip a hook:

```bash
SKIP=ruff pre-commit run --all-files
```

## Dev workflow

- `make fmt` / `make lint` / `make type` / `make test` / `make verify`
- Open small, testable PRs; add unit tests for new code & schemas
- markdownlint runs on docs; keep lines readable and headings consistent
- CI enforces markdownlint via a pinned GitHub Action.
- Optional local run: `npm ci && npx markdownlint-cli2 "**/*.md"` (or install it globally).

### Docs hygiene

- Update `THIRD_PARTY.md` whenever docs or examples add a new external reference.

### Local Markdown lint (pinned toolchain)

```bash
npm ci               # one-time per clone / after updates (requires npm registry access)
npm run mdlint       # or: make mdlint
# optional auto-fix:
npm run mdfix        # or: make mdfix
```

> If npm ci fails (e.g., corporate proxy or 403 from the npm registry), skip local markdownlint.
> CI will still enforce the exact same rules via a pinned GitHub Action.

### License headers

New source files must begin with:

```text
SPDX-License-Identifier: Apache-2.0
Copyright (c) 2025 The Vision Authors
```

## CI gates (M1)

- `vision --eval` must pass latency/bootstrap thresholds
- JSON schema snapshot + CSV header checks

## Issue labels

- `spec` — changes to `docs/specs/*`, schema/gates
- `charter` — roadmap/north star updates
- `m1`/`m2`/... — milestone targeting

