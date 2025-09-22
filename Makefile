# SPDX-License-Identifier: Apache-2.0

SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

.PHONY: eval-pack bench slo-check metrics-hash purity supplychain prove unknowns-guard api-freeze schema-bump kb-promote

FIXTURE_BANK := bench/fixtures/bank.jsonl
FIXTURE_QUERIES := bench/fixtures/queries.jsonl

bench:
	set -euo pipefail
	mkdir -p bench logs
	PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}" python scripts/bench_oracle.py --bank $(FIXTURE_BANK) --queries $(FIXTURE_QUERIES) --k 5 --out bench
	PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}" python scripts/bench_oracle_e2e.py --bank $(FIXTURE_BANK) --queries $(FIXTURE_QUERIES) --k 5 --out bench


slo-check:
	set -euo pipefail
	PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}" python scripts/check_slo.py


eval-pack:
	set -euo pipefail
	PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}" python scripts/validate_manifest.py


metrics-hash:
	set -euo pipefail
	PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}" python scripts/check_metrics_schema.py
	PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}" python scripts/write_metrics_hash.py


purity:
	set -euo pipefail
	bash scripts/purity_guard.sh


supplychain:
	set -euo pipefail
	PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}" python scripts/supplychain.py

kb-promote:
	set -euo pipefail
	PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}" python scripts/kb_promote.py


prove:
	set -euo pipefail
	$(MAKE) eval-pack
	$(MAKE) bench
	$(MAKE) slo-check
	$(MAKE) purity
	$(MAKE) metrics-hash
	$(MAKE) supplychain
	PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}" python scripts/step_summary.py


unknowns-guard:
	set -euo pipefail
	PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}" python scripts/unknowns_guard.py --samples bench/e2e_samples.jsonl --threshold 0.025


api-freeze:
	set -euo pipefail
	PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}" python scripts/check_public_api.py


schema-bump:
	set -euo pipefail
	GIT_DIFF_BASE="$${GIT_DIFF_BASE:-HEAD~1}" PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}" python scripts/check_schema_bump.py
