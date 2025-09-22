# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
.RECIPEPREFIX := >
.PHONY: setup test test-cov cov-html lint fmt format type mdlint mdfix verify readme-smoke hooks help
.PHONY: plot
.PHONY: bench-oracle
.PHONY: bench-oracle-e2e
.PHONY: gallery-dedupe-audit

# Safer bash in make recipes
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

MDLINT_BIN := node_modules/.bin/markdownlint-cli2

help:
>echo "make setup     - install package + dev tools"
>echo "make lint      - ruff lint checks"
>echo "make fmt       - ruff format (check only)"
>echo "make format    - ruff format (write changes)"
>echo "make type      - mypy type checks"
>echo "make test      - run tests"
>echo "make test-cov  - run tests with coverage (requires pytest-cov)"
>echo "make cov-html  - build local HTML coverage report (if coverage data exists)"
>echo "make mdlint    - run markdownlint (same rules as CI)"
>echo "make mdfix     - auto-fix markdownlint issues (requires npx)"
>echo "make verify    - run all local checks (lint, fmt-check, type, test, markdownlint)"
>echo "make hooks     - install and autoupdate pre-commit hooks"
>echo "make readme-smoke - run README Quickstart smoke test"
>echo "make hello     - print environment information"
>echo "make bench     - run fixture → eval → summary"
>echo "make demo      - run fixture → eval → plot demo"
>echo "make plot      - render latency PNG from metrics.json"
>echo "make kb-promote - promote accepted verify embeddings into capped int8 medoids"
>echo "make eval      - run evaluator on a directory of frames"
>echo ""
>echo "Tip: run 'npm ci' once to enable local markdownlint (make mdlint/mdfix)."

setup:
>if [ -n "$${CI:-}" ]; then \
>  pip install -e .; \
>  pip install -r requirements-dev.txt; \
>else \
>  pip install -e . || echo "⚠️ Skipped package install (pip blocked)"; \
>  pip install -r requirements-dev.txt || echo "⚠️ Skipped dev deps install (pip blocked)"; \
>fi

test:
>pytest

test-cov:
>@python -c "import pytest_cov" >/dev/null 2>&1 || (echo "pytest-cov not installed; run 'pip install -r requirements-dev.txt' or run in CI where it's provided." && exit 1)
>pytest --cov=latency_vision --cov-report=term-missing --cov-report=xml

cov-html:
>@test -f .coverage || (echo "No .coverage file found. Run 'make test-cov' first (or download from CI artifacts)." && exit 1)
>coverage html

lint:
>ruff check .

fmt:
>ruff format --check .

format:
>ruff format .

type:
>mypy src/latency_vision

mdlint:
>if [ -x "$(MDLINT_BIN)" ]; then \
>  "$(MDLINT_BIN)"; \
>else \
>  echo "⚠️  markdownlint not installed locally; run 'npm ci' or rely on CI."; \
>fi

mdpush:
>@if command -v pre-commit >/dev/null 2>&1; then pre-commit run --all-files --hook-stage push || true; fi

mdfix:
>if [ -x "$(MDLINT_BIN)" ]; then \
>  "$(MDLINT_BIN)" --fix; \
>else \
>  echo "⚠️  markdownlint not installed locally; run 'npm ci'."; \
>fi

verify:
>@echo "==> Lint"
>@if command -v ruff >/dev/null 2>&1; then ruff check .; else echo "⚠️ ruff not installed; skipping lint"; fi
>@echo "==> Format check"
>@if command -v ruff >/dev/null 2>&1; then ruff format --check .; else echo "⚠️ ruff not installed; skipping format check"; fi
>@echo "==> Types"
>@if command -v mypy >/dev/null 2>&1; then mypy src/latency_vision; else echo "⚠️ mypy not installed; skipping type check"; fi
>@echo "==> Tests"
>@if [ -n "$${CI:-}" ]; then \
>  echo "(CI) tests run in separate coverage step"; \
>else \
>  if command -v pytest >/dev/null 2>&1; then \
>    pytest; \
>  else \
>    echo "⚠️ pytest not installed; skipping tests"; \
>  fi; \
>fi
>@echo "==> Markdownlint"
>@if [ -n "$${CI:-}" ]; then \
>  echo "(CI) markdownlint is advisory"; \
>  $(MAKE) mdlint || true; \
>else \
>  $(MAKE) mdlint; \
>fi
>$(MAKE) mdpush

readme-smoke:
>@python -c "import numpy" 2>/dev/null || { \
  echo "NumPy not found. Install with 'pip install numpy' (or run CI workflow: readme-smoke)."; \
  exit 1; \
}
>python scripts/smoke_readme.py

hooks:
>pre-commit install
>pre-commit autoupdate

eval:
>if command -v latvision >/dev/null 2>&1; then \
>  latvision eval --input $(INPUT) --output $(OUTPUT) --warmup $(or $(WARMUP),100); \
>else \
>  PYTHONPATH=src latvision eval --input $(INPUT) --output $(OUTPUT) --warmup $(or $(WARMUP),100); \
>fi

hello:
>if command -v latvision >/dev/null 2>&1; then \
>  latvision hello; \
>else \
>  PYTHONPATH=src latvision hello; \
>fi

bench: bench-deps
>python scripts/build_fixture.py --seed 42 --out bench/fixture --n 400
>latvision eval --input bench/fixture --output bench/out
>python scripts/print_summary.py --metrics bench/out/metrics.json

bench-oracle:
>python scripts/build_oracle_fixture.py --out bench/oracle_fixture --n 500 --dim 32 --seed 7
>python scripts/bench_oracle.py \
>  --bank bench/oracle_fixture/bank.jsonl \
>  --queries bench/oracle_fixture/queries.jsonl \
>  --k 5 \
>  --out bench

bench-oracle-e2e:
>python scripts/build_oracle_fixture.py --out bench/oracle_fixture --n 500 --dim 32 --seed 7
>python scripts/bench_oracle_e2e.py --bank bench/oracle_fixture/bank.jsonl --queries bench/oracle_fixture/queries.jsonl --k 5 --out bench

bench-deps:
>@python scripts/check_bench_deps.py

demo:
>python scripts/build_fixture.py --seed 42 --out bench/fixture --n 400
>latvision eval --input bench/fixture --output bench/out --warmup 0 --unknown-rate-band 0.0,1.0
>python scripts/print_summary.py --metrics bench/out/metrics.json
># Plot is best-effort locally (CI already warns if missing)
>python scripts/plot_latency.py --input bench/out/stage_times.csv --output bench/out/latency.png --metrics bench/out/metrics.json || true

plot:
>python scripts/plot_latency.py --metrics bench/out/metrics.json --out bench/out/latency.png
>@test -f bench/out/latency.png && echo "Wrote bench/out/latency.png"

repro:
>python scripts/repro_check.py bench/out/metrics.json bench/out/metrics.json --pretty

labelbank-shard:
>python scripts/build_labelbank_shard.py --seed 1234 --in data/labelbank/seed.jsonl --out bench/labelbank/shard --dim 256 --max-n $${LB_N:-10000}

calib:
>python scripts/bench_calibration.py --shard bench/labelbank/shard --seed 999 --k 10 --out bench/calib_stats.json --hash-out bench/calib_hash.txt

gate-calib:
>python - <<'PY'
>import json
>stats = json.load(open("bench/calib_stats.json", encoding="utf-8"))
>assert stats["ece"] <= 0.05, f"ece={stats['ece']}"
>assert stats["auroc_min"] >= 0.95, f"auroc_min={stats['auroc_min']}"
>assert stats.get("lookup_p95_delta", 0.0) <= 0.05, "lookup_p95_delta gate"
>assert stats.get("oracle_p95_ms", 0.0) <= 10.0, "oracle_p95_ms gate"
>verify = stats.get("verify", {})
>called = int(verify.get("called", 0))
>accepted = int(verify.get("accepted", 0))
>rejected = int(verify.get("rejected", 0))
>assert called == accepted + rejected, "verify accounting mismatch"
>assert int(verify.get("known_wrong_after_verify", 0)) == 0, "known_wrong_after_verify must be 0"
>print("calibration gates ok")
>PY

gate-purity:
>scripts/verify_syscalls.sh

.PHONY: purity
purity:
>bash scripts/purity_guard.sh

gallery-dedupe-audit:
>python scripts/gallery_dedupe_audit.py

labelbank-bench: labelbank-shard
>python scripts/bench_labelbank.py --shard bench/labelbank/shard --out bench/labelbank_stats.json --seed 999 --queries $${LB_Q:-500} --k 10
>@echo "LabelBank stats written to bench/labelbank_stats.json"

verify-calibrate:
>python scripts/verify_calibrate.py --manifest bench/verify/gallery_manifest.jsonl --out bench/verify/calibration.json --seed 4242

verify-eval:
>python scripts/build_fixture.py --seed 42 --out bench/fixture --n 200
>VISION__ORACLE__MAXLEN=64 latvision eval --input bench/fixture --output bench/out --warmup 0 --unknown-rate-band 0.10,0.40
>python scripts/print_summary.py --metrics bench/out/metrics.json

kb-promote:
>PYTHONPATH=src python - <<'PY'
>from __future__ import annotations
>
>import json
>from collections import defaultdict
>from pathlib import Path
>
>from latency_vision.kb import KBPromotionImpl
>
>ledger_path = Path("bench/verify/ledger.jsonl")
>if not ledger_path.exists():
>    print("No verify ledger found; nothing to promote")
>    raise SystemExit(0)
>
>records = []
>for line in ledger_path.read_text(encoding="utf-8").splitlines():
>    data = line.strip()
>    if not data:
>        continue
>    try:
>        rec = json.loads(data)
>    except json.JSONDecodeError:
>        continue
>    embedding = rec.get("embedding")
>    if not isinstance(embedding, list):
>        continue
>    records.append((rec.get("label"), embedding))
>
>if not records:
>    print("No accepted verify embeddings found; nothing to promote")
>    raise SystemExit(0)
>
>by_label: dict[str, list[list[float]]] = defaultdict(list)
>for raw_label, embedding in records:
>    if not raw_label:
>        continue
>    floats = [float(x) for x in embedding]
>    by_label[str(raw_label)].append(floats)
>
>if not by_label:
>    print("No embeddings available for promotion")
>    raise SystemExit(0)
>
>promoter = KBPromotionImpl(output_dir="bench/kb")
>
>for label in sorted(by_label):
>    result = promoter.promote(label, by_label[label])
>    print(
>        f"promoted {label}: medoids={result['medoids']} bytes={result['bytes']} updated={result['updated']}"
>    )
>PY

build:
>python -m pip install --upgrade build twine
>python -m build

check:
>python -m twine check dist/*

clean:
>rm -rf dist build *.egg-info

release: clean build check
>@echo "✅ Artifacts ready in ./dist"

release-rc:
>@echo "git tag -a v0.1.0-rc.2 -m \"M1.1 RC drill\""
>@echo "git push origin v0.1.0-rc.2"

.PHONY: metrics-hash
metrics-hash:
>python scripts/write_metrics_hash.py

.PHONY: config-artifact
config-artifact:
>mkdir -p artifacts
>python -c "import json, pathlib; pathlib.Path('artifacts/config_precedence.json').write_text(json.dumps({'precedence': 'CLI>ENV>MANIFEST'}, indent=2) + '\\n', encoding='utf-8')"

.PHONY: check-metrics-schema
check-metrics-schema:
>python scripts/check_metrics_schema.py

.PHONY: verify-static
verify-static:
>@echo "==> Lint"; ruff check .
>@echo "==> Format check"; ruff format --check .
>@echo "==> Types"; mypy --config-file mypy.ini
