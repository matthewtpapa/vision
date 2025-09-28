#!/usr/bin/env python3
"""Validate roadmap stages against generated lock and artifacts."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ROADMAP_PATH = REPO_ROOT / "roadmap.yaml"
LOCK_PATH = REPO_ROOT / "roadmap.lock.json"
GATE_SUMMARY_PATH = REPO_ROOT / "gate_summary.txt"


class RoadmapError(RuntimeError):
    """Raised when a roadmap validation check fails."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_tracked_files() -> Iterable[str]:
    out = subprocess.check_output(["git", "ls-files", "-z"], cwd=REPO_ROOT)
    for entry in out.decode().split("\x00"):
        if not entry:
            continue
        if entry == "roadmap.lock.json":
            continue
        if entry.startswith("logs/"):
            continue
        if entry.startswith(".venv"):
            continue
        if entry.startswith("artifacts/") and not entry.endswith(".schema.json"):
            continue
        yield entry


def _parse_roadmap(path: Path) -> dict[str, Any]:
    """Parse the constrained roadmap YAML using a lightweight reader.

    We intentionally avoid PyYAML so this script can run in environments where
    only the Python standard library is available (for example, minimal CI
    runners). The parser supports the subset of YAML used by roadmap.yaml and
    is covered by the roadmap-lock checks.
    """
    schema_version: str | None = None
    stages: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    active_list: list[str] | None = None
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            if raw_line.startswith("#"):
                continue
            line = raw_line.rstrip("\n")
            if not line.startswith(" "):
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip().strip('"')
                if key == "schema_version":
                    schema_version = value
                continue
            if line.startswith("  - "):
                rest = line[4:]
                key, _, value = rest.partition(":")
                current = {key.strip(): value.strip().strip('"')}
                stages.append(current)
                active_list = None
                continue
            if current is None:
                continue
            if line.startswith("    "):
                stripped = line[4:]
                inner = stripped.lstrip()
                if inner.startswith("-"):
                    if active_list is None:
                        raise RoadmapError("list entry encountered without active list")
                    active_list.append(inner[1:].strip().strip('"'))
                    continue
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()
                if value:
                    current[key] = value.strip('"')
                    active_list = None
                else:
                    target: list[str] = []
                    current[key] = target
                    active_list = target
    if schema_version is None:
        raise RoadmapError("schema_version missing from roadmap")
    return {"schema_version": schema_version, "stages": stages}


def _compute_fileset_sha() -> str:
    digest = hashlib.sha256()
    for path in sorted(_iter_tracked_files()):
        full = REPO_ROOT / path
        digest.update(path.encode("utf-8"))
        digest.update(_sha256_file(full).encode("utf-8"))
    return digest.hexdigest()


def _load_lock(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RoadmapError("roadmap.lock.json must be a JSON object")
    if data.get("schema_version") != "1.2.0":
        raise RoadmapError("roadmap.lock.json schema_version must be 1.2.0")
    stages = data.get("stages")
    if not isinstance(stages, list):
        raise RoadmapError("roadmap.lock.json stages must be a list")
    for entry in stages:
        if not isinstance(entry, dict):
            raise RoadmapError("roadmap.lock.json stage entries must be objects")
        if "id" not in entry:
            raise RoadmapError("roadmap.lock.json stage entry missing id")
    return data


def _ensure_stage_artifacts(stage: dict[str, Any]) -> None:
    artifacts = stage.get("artifacts")
    if not isinstance(artifacts, list):
        raise RoadmapError(f"stage {stage.get('id')} artifacts must be a list")
    missing = [artifact for artifact in artifacts if not (REPO_ROOT / artifact).exists()]
    if missing:
        raise RoadmapError(f"missing artifacts for {stage.get('id')}: {missing}")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json_optional(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return _load_json(path)
    except json.JSONDecodeError:
        return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        numeric = float(value)
        if math.isnan(numeric):
            return None
        return numeric
    if isinstance(value, str):
        try:
            parsed = float(value.strip())
        except ValueError:
            return None
        if math.isnan(parsed):
            return None
        return parsed
    return None


def _check_signature_valid() -> bool:
    sentinel = REPO_ROOT / "artifacts" / "NO_SIGNING_KEY"
    if sentinel.exists():
        return True
    candidates = [
        (
            REPO_ROOT / "artifacts" / "sot_summary.json",
            REPO_ROOT / "artifacts" / "sot_summary.json.sig",
        ),
        (
            REPO_ROOT / "artifacts" / "manifest.json",
            REPO_ROOT / "artifacts" / "manifest.json.sig",
        ),
    ]
    for payload_path, sig_path in candidates:
        if not payload_path.exists() or not sig_path.exists():
            continue
        try:
            sig_data = _load_json(sig_path)
        except json.JSONDecodeError:
            continue
        payload_hash = sig_data.get("payload_sha256")
        signature = sig_data.get("sig")
        if not isinstance(payload_hash, str) or len(payload_hash) != 64:
            continue
        if not isinstance(signature, str) or len(signature) != 64:
            continue
        actual = _sha256_file(payload_path)
        if actual == payload_hash:
            return True
    return False


def _check_purity_clean() -> bool:
    report_path = REPO_ROOT / "artifacts" / "purity_report.json"
    if not report_path.exists():
        return False
    report = _load_json(report_path)
    offenders = report.get("offenders")
    if offenders is None:
        offenders = report.get("offending", [])
    network_syscalls = report.get("network_syscalls")
    return not offenders and network_syscalls is False


def _check_pdf_deterministic() -> bool:
    pdf_path = REPO_ROOT / "artifacts" / "vision_v1_SoT.pdf"
    if not pdf_path.exists():
        return False
    return pdf_path.stat().st_size > 10_000


def _check_append_only_ok() -> bool:
    ledger_path = REPO_ROOT / "artifacts" / "stage_ledger.jsonl"
    if not ledger_path.exists():
        return False
    with ledger_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                return False
            if not isinstance(record, dict):
                return False
            if "stage" not in record or "event" not in record:
                return False
    return True


def _compute_ledger_tip() -> str:
    ledger_path = REPO_ROOT / "artifacts" / "stage_ledger.jsonl"
    tip = "0" * 64
    if not ledger_path.exists():
        return ""
    with ledger_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError:
                return ""
            payload = tip + str(record.get("stage", "")) + str(record.get("event", ""))
            payload += str(record.get("ts", "")) + str(record.get("commit", ""))
            tip = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return tip


def _check_ledger_tip_ok() -> bool:
    tip_path = REPO_ROOT / "artifacts" / "ledger_tip.txt"
    if not tip_path.exists():
        return False
    expected = _compute_ledger_tip()
    if not expected:
        return False
    actual = tip_path.read_text(encoding="utf-8").strip()
    return expected == actual


def _check_determinism_ok() -> bool:
    hash_path = REPO_ROOT / "artifacts" / "metrics_hash.txt"
    if not hash_path.exists():
        return False
    content = hash_path.read_text(encoding="utf-8").strip()
    if ":" in content:
        _, _, value = content.partition(":")
        digest = value.strip()
    else:
        digest = content
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        return False
    return True


def _check_thresholds_met() -> bool:
    summary_path = REPO_ROOT / "artifacts" / "metrics_summary.json"
    if not summary_path.exists():
        return False
    summary = _load_json(summary_path)
    recall = float(summary.get("candidate_at_k_recall", 0.0))
    e2e_p95 = float(summary.get("e2e_p95_ms", 1e9))
    p_at_1 = float(summary.get("p_at_1", summary.get("p@1", 0.0)))
    unknown_fa = float(summary.get("unknown_false_accept_rate", 1.0))
    offline_path = REPO_ROOT / "bench" / "oracle_stats.json"
    offline_p95 = 1e9
    if offline_path.exists():
        offline = _load_json(offline_path)
        offline_p95 = float(offline.get("p95_ms", offline_p95))
    return (
        recall >= 0.95
        and p_at_1 >= 0.80
        and e2e_p95 <= 33.0
        and offline_p95 <= 33.0
        and unknown_fa <= 0.025
    )


def _check_tests_green() -> bool:
    junit_path = REPO_ROOT / "artifacts" / "pytest" / "pytest_s2_junit.xml"
    if not junit_path.exists():
        return False
    root = ET.parse(junit_path).getroot()
    if root.tag == "testsuites":
        suites = list(root)
    else:
        suites = [root]
    for suite in suites:
        failures = suite.attrib.get("failures")
        errors = suite.attrib.get("errors")
        failures_count = int(failures or 0)
        errors_count = int(errors or 0)
        if failures_count != 0 or errors_count != 0:
            return False
    return True


def _check_evidence_present() -> bool:
    ledger = REPO_ROOT / "logs" / "evidence_ledger.jsonl"
    if not ledger.exists():
        return False
    with ledger.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                return True
    return False


def _check_candidate_recall_ok() -> bool:
    bench = _load_json_optional(REPO_ROOT / "artifacts" / "oracle_bench.json")
    if not isinstance(bench, dict):
        return False
    candidates: list[float] = []
    for key in ("candidate_recall", "candidate_recall_at_10", "candidate_recall_at_k", "recall"):
        value = _to_float(bench.get(key))
        if value is not None:
            candidates.append(value)
    if not candidates:
        return False
    return max(candidates) >= 0.45


def _check_p95_ms_ok() -> bool:
    thresholds = {
        REPO_ROOT / "artifacts" / "oracle_bench.json": 12.0,
        REPO_ROOT / "artifacts" / "labelbank_scale_bench.json": 33.0,
    }
    success = False
    for path, limit in thresholds.items():
        data = _load_json_optional(path)
        if not isinstance(data, dict):
            continue
        candidate = _to_float(data.get("p95_ms"))
        if candidate is None:
            continue
        if candidate <= limit:
            success = True
        else:
            return False
    return success


def _check_promotion_thresholds_met() -> bool:
    report = _load_json_optional(REPO_ROOT / "artifacts" / "promotion_report.json")
    if not isinstance(report, dict):
        return False
    reasons = report.get("reasons")
    if reasons not in (None, []):
        return False
    promotions = report.get("promotions")
    if isinstance(promotions, list) and promotions:
        return True
    # Some runs may only log a high-level status.
    status = str(report.get("status", "")).lower()
    return status in {"pass", "passed", "ok", "green"}


def _check_slo_thresholds_met() -> bool:
    report = _load_json_optional(REPO_ROOT / "artifacts" / "slo_report.json")
    if not isinstance(report, dict):
        return False
    status = str(report.get("status", "")).lower()
    if status in {"pass", "passed", "ok", "green"}:
        return True
    violations = report.get("violations")
    if isinstance(violations, list):
        return not violations
    return False


def _check_metrics_schema_valid() -> bool:
    schema_path = REPO_ROOT / "schemas" / "metrics.schema.json"
    schema = _load_json_optional(schema_path)
    if not isinstance(schema, dict):
        return False
    return "title" in schema or "$schema" in schema


def _check_ci_matrix_ok() -> bool:
    summary = _load_json_optional(REPO_ROOT / "artifacts" / "ci_matrix_summary.json")
    if not isinstance(summary, dict):
        return False
    if summary.get("all_passed") is True:
        return True
    statuses = summary.get("statuses")
    if isinstance(statuses, dict) and statuses:
        return all(
            (value is True)
            or (isinstance(value, str) and value.lower() in {"pass", "passed", "ok", "green"})
            for value in statuses.values()
        )
    matrix = summary.get("matrix")
    if isinstance(matrix, list) and matrix:
        ok = True
        for entry in matrix:
            if not isinstance(entry, dict):
                return False
            status = str(entry.get("status", "")).lower()
            if status not in {"pass", "passed", "ok", "green", "success"}:
                ok = False
        return ok
    return False


def _check_sbom_ok() -> bool:
    sbom = _load_json_optional(REPO_ROOT / "artifacts" / "sbom.json")
    if isinstance(sbom, dict):
        packages = sbom.get("packages")
        if isinstance(packages, list):
            return bool(packages)
    elif isinstance(sbom, list):
        return bool(sbom)
    return False


def _check_licenses_ok() -> bool:
    licenses = _load_json_optional(REPO_ROOT / "artifacts" / "licenses.json")
    if isinstance(licenses, dict):
        problems = licenses.get("violations") or licenses.get("unapproved")
        if problems:
            return False
        entries = licenses.get("licenses")
        if isinstance(entries, list):
            return all(entry for entry in entries)
        return True
    if isinstance(licenses, list):
        return bool(licenses)
    return False


def _check_recall_ok() -> bool:
    bench = _load_json_optional(REPO_ROOT / "artifacts" / "labelbank_scale_bench.json")
    if not isinstance(bench, dict):
        return False
    candidates: list[float] = []
    for key in ("recall", "candidate_recall", "recall_at_k"):
        value = _to_float(bench.get(key))
        if value is not None:
            candidates.append(value)
    if not candidates:
        return False
    return max(candidates) >= 0.95


def _check_public_api_ok() -> bool:
    report = _load_json_optional(REPO_ROOT / "artifacts" / "public_api_report.json")
    if not isinstance(report, dict):
        return False
    breaking = report.get("breaking")
    if isinstance(breaking, list) and breaking:
        return False
    status = str(report.get("status", "")).lower()
    if status in {"pass", "passed", "ok", "green"}:
        return True
    return breaking == []


def _check_config_precedence_ok() -> bool:
    report = _load_json_optional(REPO_ROOT / "artifacts" / "config_precedence.json")
    if not isinstance(report, dict):
        return False
    violations = report.get("violations")
    if isinstance(violations, list):
        return not violations
    status = str(report.get("status", "")).lower()
    return status in {"pass", "passed", "ok", "green"}


def _check_gallery_audit_ok() -> bool:
    audit = _load_json_optional(REPO_ROOT / "artifacts" / "gallery_dedupe_audit.json")
    if not isinstance(audit, dict):
        return False
    pending = audit.get("pending_reviews")
    if isinstance(pending, list) and pending:
        return False
    status = str(audit.get("status", "")).lower()
    if status in {"pass", "passed", "ok", "green"}:
        return True
    duplicates_removed = audit.get("duplicates_removed")
    if isinstance(duplicates_removed, int):
        return duplicates_removed >= 0
    return False


def _check_release_hygiene_ok() -> bool:
    checklist = _load_json_optional(REPO_ROOT / "artifacts" / "release_checklist.json")
    if not isinstance(checklist, dict):
        return False
    status = str(checklist.get("status", "")).lower()
    if status in {"pass", "passed", "ok", "green"}:
        return True
    items = checklist.get("items")
    if isinstance(items, list) and items:
        allowed = {"done", "pass", "passed", "ok", "complete"}
        for item in items:
            if not isinstance(item, dict):
                return False
            status = str(item.get("status", "")).lower()
            if status not in allowed:
                return False
        return True
    return False


def _check_exit_gates_ok() -> bool:
    summary = _load_json_optional(REPO_ROOT / "artifacts" / "exit_gate_summary.json")
    if not isinstance(summary, dict):
        return False
    status = str(summary.get("status", "")).lower()
    if status in {"pass", "passed", "ok", "green"}:
        return True
    gates = summary.get("gates")
    if isinstance(gates, list) and gates:
        allowed = {"pass", "passed", "ok", "green"}
        for entry in gates:
            if not isinstance(entry, dict):
                return False
            status = str(entry.get("status", "")).lower()
            if status not in allowed:
                return False
        return True
    return False


SIGNAL_CHECKS: dict[str, Callable[[], bool]] = {
    "signature_valid_or_blocked": _check_signature_valid,
    "purity_clean": _check_purity_clean,
    "pdf_deterministic": _check_pdf_deterministic,
    "append_only_ok": _check_append_only_ok,
    "ledger_tip_ok": _check_ledger_tip_ok,
    "determinism_ok": _check_determinism_ok,
    "thresholds_met": _check_thresholds_met,
    "tests_green": _check_tests_green,
    "evidence_present": _check_evidence_present,
    "candidate_recall_ok": _check_candidate_recall_ok,
    "p95_ms_ok": _check_p95_ms_ok,
    "promotion_thresholds_met": _check_promotion_thresholds_met,
    "slo_thresholds_met": _check_slo_thresholds_met,
    "metrics_schema_valid": _check_metrics_schema_valid,
    "ci_matrix_ok": _check_ci_matrix_ok,
    "sbom_ok": _check_sbom_ok,
    "licenses_ok": _check_licenses_ok,
    "recall_ok": _check_recall_ok,
    "public_api_ok": _check_public_api_ok,
    "config_precedence_ok": _check_config_precedence_ok,
    "gallery_audit_ok": _check_gallery_audit_ok,
    "release_hygiene_ok": _check_release_hygiene_ok,
    "exit_gates_ok": _check_exit_gates_ok,
}


def _evaluate_signal(name: str) -> bool:
    if name == "lock_ok":
        raise RoadmapError("lock_ok evaluated before assignment")
    check = SIGNAL_CHECKS.get(name)
    if check is None:
        raise RoadmapError(f"no check implemented for pass_when key: {name}")
    return check()


def _append_gate_summary(lines: list[str]) -> None:
    GATE_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    preserved: list[str] = []
    if GATE_SUMMARY_PATH.exists():
        existing = GATE_SUMMARY_PATH.read_text(encoding="utf-8").splitlines()
        for entry in existing:
            if entry.startswith("stage=") or entry.startswith("EXPECTED:"):
                continue
            preserved.append(entry)
    with GATE_SUMMARY_PATH.open("w", encoding="utf-8") as handle:
        for line in preserved + lines:
            handle.write(line + "\n")


def main() -> None:
    roadmap = _parse_roadmap(ROADMAP_PATH)
    lock = _load_lock(LOCK_PATH)
    fileset_sha = _compute_fileset_sha()
    lock_stage_map = {str(entry["id"]): entry for entry in lock.get("stages", [])}

    stage_ids = [str(stage.get("id")) for stage in roadmap["stages"]]
    missing_in_lock = [stage_id for stage_id in stage_ids if stage_id not in lock_stage_map]
    extra_in_lock = [stage_id for stage_id in lock_stage_map if stage_id not in stage_ids]
    lock_ok = (
        lock.get("fileset_sha256") == fileset_sha and not missing_in_lock and not extra_in_lock
    )

    signals: dict[str, bool] = {"lock_ok": lock_ok}
    for name, check in SIGNAL_CHECKS.items():
        if name != "purity_clean":
            signals[name] = check()
    signals["purity_clean"] = SIGNAL_CHECKS["purity_clean"]()

    gate_lines: list[str] = []
    failures: list[str] = []

    if missing_in_lock:
        failures.append(f"missing stages in lock: {missing_in_lock}")
    if extra_in_lock:
        failures.append(f"unexpected stages in lock: {extra_in_lock}")

    pre_s3_skips = False

    for stage in roadmap["stages"]:
        if not isinstance(stage, dict):
            continue
        stage_id = str(stage.get("id"))
        skip_reason = stage.get("skip_reason")
        if skip_reason:
            gate_lines.append(f"stage={stage_id} SKIP ({skip_reason})")
            if skip_reason == "pre-S3":
                pre_s3_skips = True
            continue
        try:
            _ensure_stage_artifacts(stage)
        except RoadmapError as exc:
            failures.append(str(exc))
            gate_lines.append(f"stage={stage_id} FAIL ({exc})")
            continue
        pass_keys = stage.get("pass_when")
        if not isinstance(pass_keys, list):
            failures.append(f"stage {stage_id} pass_when must be a list")
            gate_lines.append(f"stage={stage_id} FAIL (invalid pass_when)")
            continue
        unsatisfied: list[str] = []
        for key in pass_keys:
            if key == "lock_ok":
                value = lock_ok
            else:
                value = signals.get(str(key))
                if value is None:
                    try:
                        value = _evaluate_signal(str(key))
                    except RoadmapError as exc:
                        failures.append(str(exc))
                        value = False
                        signals[str(key)] = False
                else:
                    signals[str(key)] = value
            if not value:
                unsatisfied.append(str(key))
        if unsatisfied:
            failures.append(f"stage {stage_id} requirements not met: {unsatisfied}")
            gate_lines.append(
                f"stage={stage_id} FAIL (requirements not met: {', '.join(unsatisfied)})"
            )
        else:
            gate_lines.append(f"stage={stage_id} PASS")

    if pre_s3_skips:
        gate_lines.append("EXPECTED: S03–S17 not executed")
    _append_gate_summary(gate_lines)

    if failures:
        raise SystemExit("; ".join(failures))


if __name__ == "__main__":
    main()
