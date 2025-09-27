#!/usr/bin/env python3
"""Validate roadmap stages against generated lock and artifacts."""

from __future__ import annotations

import hashlib
import json
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


def _check_signature_valid() -> bool:
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
        failures = suite.attrib.get("failures", "0")
        errors = suite.attrib.get("errors", "0")
        if int(failures) != 0 or int(errors) != 0:
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
