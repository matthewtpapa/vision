#!/usr/bin/env python
"""Emit supply-chain artifacts and enforce policy."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata as md
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"
ALLOWED_LICENSES = {
    "MIT",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "Apache-2.0",
    "ISC",
    "PSF-2.0",
    "HPND",
    "Unlicense",
}
LICENSE_ALIASES = {
    "MIT": "MIT",
    "MIT LICENSE": "MIT",
    "APACHE-2.0": "Apache-2.0",
    "APACHE LICENSE 2.0": "Apache-2.0",
    "APACHE LICENSE, VERSION 2.0": "Apache-2.0",
    "APACHE SOFTWARE LICENSE": "Apache-2.0",
    "BSD-2-CLAUSE": "BSD-2-Clause",
    "BSD 2-CLAUSE": "BSD-2-Clause",
    "BSD-3-CLAUSE": "BSD-3-Clause",
    "BSD 3-CLAUSE": "BSD-3-Clause",
    "BSD LICENSE": "BSD-3-Clause",
    "ISC": "ISC",
    "ISC LICENSE": "ISC",
    "PSF": "PSF-2.0",
    "PYTHON SOFTWARE FOUNDATION LICENSE": "PSF-2.0",
    "PSF LICENSE": "PSF-2.0",
    "UNLICENSE": "Unlicense",
    "THE UNLICENSE": "Unlicense",
    "HPND": "HPND",
    "HISTORICAL PERMISSION NOTICE AND DISCLAIMER": "HPND",
}
UNKNOWN_LICENSE = "UNKNOWN"


class SupplyChainError(RuntimeError):
    """Raised when supply-chain policy fails."""


@dataclass
class RuntimeContext:
    """Description of the runtime dependency closure."""

    root_distribution: str
    package_names: list[str]
    canonical_keys: set[str]
    package_info: dict[str, dict[str, str]]
    dependencies: dict[str, set[str]]


def _canonicalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _run_module(module: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: PLW1510
        [sys.executable, "-m", module, *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _write_text(path: Path, content: str) -> None:
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    _write_text(path, json.dumps(payload, indent=2, sort_keys=True))


def _discover_root_distribution() -> str:
    module_name = "latency_vision"
    try:
        mapping = md.packages_distributions()
    except Exception:  # pragma: no cover - best effort fallback
        mapping = {}
    candidates = mapping.get(module_name)
    if candidates:
        return candidates[0]

    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError as exc:  # pragma: no cover - should not happen in CI
        raise SupplyChainError("latency_vision is not installed") from exc

    normalized = module_name.replace("_", "-")
    for dist_name in (module_name, normalized):
        try:
            distribution = md.distribution(dist_name)
        except md.PackageNotFoundError:
            continue
        meta_name = distribution.metadata.get("Name")
        if meta_name:
            return meta_name
        return dist_name

    for distribution in md.distributions():
        try:
            top_level = distribution.read_text("top_level.txt")
        except FileNotFoundError:
            top_level = None
        if top_level:
            modules = [line.strip() for line in top_level.splitlines() if line.strip()]
            if module_name in modules or module_name.split(".")[0] in modules:
                meta_name = distribution.metadata.get("Name")
                if meta_name:
                    return meta_name
        requires = distribution.requires or []
        if any(module_name in requirement for requirement in requires):
            meta_name = distribution.metadata.get("Name")
            if meta_name:
                return meta_name

    raise SupplyChainError("Unable to determine runtime distribution for latency_vision")


def _parse_dependency_tree(tree: object) -> tuple[dict[str, dict[str, str]], dict[str, set[str]]]:
    package_info: dict[str, dict[str, str]] = {}
    dependencies: dict[str, set[str]] = {}
    visited: set[str] = set()

    def visit(node: object) -> None:
        if not isinstance(node, dict):
            return
        package = node.get("package")
        if not isinstance(package, dict):
            return
        raw_name = str(package.get("package_name") or package.get("key") or "").strip()
        key = _canonicalize_name(package.get("key") or raw_name)
        if not key:
            return
        version = str(package.get("installed_version") or "").strip()
        entry = package_info.setdefault(key, {"name": raw_name, "version": version})
        if not entry["name"] and raw_name:
            entry["name"] = raw_name
        if not entry["version"] and version:
            entry["version"] = version
        deps = dependencies.setdefault(key, set())
        children = node.get("dependencies")
        if not isinstance(children, list):
            return
        child_nodes = [child for child in children if isinstance(child, dict)]
        for child in child_nodes:
            child_package = child.get("package")
            if not isinstance(child_package, dict):
                continue
            child_raw_name = str(
                child_package.get("package_name") or child_package.get("key") or ""
            ).strip()
            child_key = _canonicalize_name(child_package.get("key") or child_raw_name)
            if not child_key:
                continue
            deps.add(child_key)
        if key in visited:
            return
        visited.add(key)
        for child in child_nodes:
            visit(child)

    if isinstance(tree, list):
        for entry in tree:
            visit(entry)
    else:
        visit(tree)

    return package_info, dependencies


def _subset_runtime_packages(
    package_info: dict[str, dict[str, str]],
    dependencies: dict[str, set[str]],
    root_key: str,
) -> tuple[dict[str, dict[str, str]], dict[str, set[str]], str] | None:
    if not package_info:
        return None

    target_key = root_key if root_key in package_info else None
    if target_key is None:
        for key, info in package_info.items():
            name = info.get("name")
            if isinstance(name, str) and _canonicalize_name(name) == root_key:
                target_key = key
                break
    if target_key is None:
        return None

    reachable: set[str] = set()
    stack: list[str] = [target_key]
    while stack:
        candidate = stack.pop()
        if candidate in reachable or candidate not in package_info:
            continue
        reachable.add(candidate)
        stack.extend(sorted(dependencies.get(candidate, set())))

    filtered_info = {key: package_info[key] for key in reachable}
    filtered_dependencies = {
        key: {dep for dep in dependencies.get(key, set()) if dep in reachable} for key in reachable
    }
    return filtered_info, filtered_dependencies, target_key


def _fallback_runtime_packages(
    root_key: str,
) -> tuple[dict[str, dict[str, str]], dict[str, set[str]], str] | None:
    try:
        result = _run_module("pipdeptree", "--json-tree")
    except subprocess.CalledProcessError:
        return None

    try:
        tree = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    package_info, dependencies = _parse_dependency_tree(tree)
    return _subset_runtime_packages(package_info, dependencies, root_key)


def _build_runtime_context() -> RuntimeContext:
    root_distribution = _discover_root_distribution()
    try:
        result = _run_module("pipdeptree", "--packages", root_distribution, "--json-tree")
    except subprocess.CalledProcessError as exc:
        raise SupplyChainError("pipdeptree failed to resolve runtime dependencies") from exc

    try:
        tree = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SupplyChainError("pipdeptree produced invalid JSON") from exc

    package_info, dependencies = _parse_dependency_tree(tree)
    root_key = _canonicalize_name(root_distribution)

    subset = _subset_runtime_packages(package_info, dependencies, root_key)
    if subset is not None:
        package_info, dependencies, root_key = subset
    else:
        fallback = _fallback_runtime_packages(root_key)
        if fallback is not None:
            package_info, dependencies, root_key = fallback
        else:
            package_info = {}
            dependencies = {}

    distribution = _distribution_from_name(root_distribution)
    entry = package_info.setdefault(root_key, {"name": "", "version": ""})
    if not entry.get("name"):
        if distribution is not None:
            meta_name = distribution.metadata.get("Name")
            entry["name"] = meta_name or root_distribution
        else:
            entry["name"] = root_distribution
    if not entry.get("version"):
        if distribution is not None:
            version = getattr(distribution, "version", "") or distribution.metadata.get("Version")
            if version:
                entry["version"] = version
        entry.setdefault("version", "")
    dependencies.setdefault(root_key, set())

    if not package_info:
        raise SupplyChainError("Runtime dependency set is empty")

    package_names = sorted(
        {info["name"] for info in package_info.values() if info["name"]},
        key=str.lower,
    )
    canonical_keys = set(package_info)

    return RuntimeContext(
        root_distribution=root_distribution,
        package_names=package_names,
        canonical_keys=canonical_keys,
        package_info=package_info,
        dependencies=dependencies,
    )


def _minimal_sbom(context: RuntimeContext) -> dict[str, object]:
    components = []
    for key in sorted(context.canonical_keys):
        info = context.package_info[key]
        components.append(
            {
                "type": "library",
                "name": info["name"],
                "version": info["version"],
            }
        )
    dependency_entries = []
    for key in sorted(context.canonical_keys):
        info = context.package_info[key]
        depends_on = [
            context.package_info[dep]["name"]
            for dep in sorted(context.dependencies.get(key, set()))
            if dep in context.package_info
        ]
        dependency_entries.append({"ref": info["name"], "dependsOn": depends_on})
    return {
        "bomFormat": "pipdeptree",
        "components": components,
        "dependencies": dependency_entries,
    }


def _filter_cyclonedx(raw_payload: str, context: RuntimeContext) -> dict[str, object]:
    try:
        bom = json.loads(raw_payload)
    except json.JSONDecodeError:
        return _minimal_sbom(context)
    if not isinstance(bom, dict):
        return _minimal_sbom(context)

    components = bom.get("components")
    if isinstance(components, list):
        filtered_components = []
        seen: set[str] = set()
        for component in components:
            if not isinstance(component, dict):
                continue
            name = component.get("name")
            if not isinstance(name, str):
                continue
            key = _canonicalize_name(name)
            if key in context.canonical_keys and key not in seen:
                filtered_components.append(component)
                seen.add(key)
        bom["components"] = filtered_components
    else:
        bom["components"] = []

    dependencies = bom.get("dependencies")
    if isinstance(dependencies, list):
        filtered_dependencies = []
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                continue
            ref = dependency.get("ref")
            if not isinstance(ref, str):
                continue
            ref_key = _canonicalize_name(ref)
            if ref_key not in context.canonical_keys:
                continue
            depends_on = dependency.get("dependsOn")
            filtered_depends = (
                [
                    dep
                    for dep in depends_on
                    if isinstance(dep, str) and _canonicalize_name(dep) in context.canonical_keys
                ]
                if isinstance(depends_on, list)
                else []
            )
            filtered_dependencies.append({"ref": ref, "dependsOn": filtered_depends})
        bom["dependencies"] = filtered_dependencies
    else:
        bom["dependencies"] = []

    return bom


def _ensure_sbom(context: RuntimeContext) -> None:
    destination = ARTIFACTS / "sbom.json"
    try:
        result = _run_module("cyclonedx_py", "-e")
    except (subprocess.CalledProcessError, FileNotFoundError):
        payload = _minimal_sbom(context)
    else:
        payload = _filter_cyclonedx(result.stdout, context)
    _write_json(destination, payload)


def _normalize_token(token: str) -> str | None:
    cleaned = re.sub(r"[()]+", " ", token).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return None
    key = cleaned.upper()
    normalized = LICENSE_ALIASES.get(key)
    if normalized:
        return normalized
    for allowed in ALLOWED_LICENSES:
        if allowed.upper() in key:
            return allowed
    return cleaned


def _extract_license_names(raw_value: str) -> set[str]:
    if not raw_value:
        return {UNKNOWN_LICENSE}
    parts = re.split(r"\s*(?:,|;|/|\bor\b|\band\b|\+|\|)\s*", raw_value, flags=re.IGNORECASE)
    normalized: set[str] = set()
    for part in parts:
        token = _normalize_token(part)
        if token:
            normalized.add(token)
    if not normalized:
        normalized.add(UNKNOWN_LICENSE)
    return normalized


@cache
def _distribution_from_name(name: str) -> md.Distribution | None:
    try:
        return md.distribution(name)
    except md.PackageNotFoundError:
        canonical = _canonicalize_name(name)
        for distribution in md.distributions():
            dist_name = distribution.metadata.get("Name")
            if dist_name and _canonicalize_name(dist_name) == canonical:
                return distribution
    return None


def _licenses_from_classifiers(name: str) -> set[str]:
    distribution = _distribution_from_name(name)
    if distribution is None:
        return set()
    metadata = distribution.metadata
    classifiers = metadata.get_all("Classifier") if hasattr(metadata, "get_all") else None
    if not classifiers:
        classifier = metadata.get("Classifier")
        classifiers = [classifier] if classifier else []
    normalized: set[str] = set()
    for classifier in classifiers:
        if not isinstance(classifier, str):
            continue
        if not classifier.startswith("License ::"):
            continue
        tail = classifier.split("::")[-1].strip()
        if tail:
            normalized.update(_extract_license_names(tail))
    return normalized


def _collect_licenses(context: RuntimeContext) -> None:
    result = _run_module("piplicenses", "--format=json", "--packages", *context.package_names)
    data = json.loads(result.stdout)
    if not isinstance(data, list):  # pragma: no cover - sanity guard
        raise SupplyChainError("pip-licenses returned unexpected payload")
    data = sorted(
        (entry for entry in data if isinstance(entry, dict)),
        key=lambda entry: str(entry.get("Name", "")).lower(),
    )
    destination = ARTIFACTS / "licenses.json"
    _write_json(destination, data)

    violations: list[str] = []
    for entry in data:
        name = str(entry.get("Name", "unknown"))
        raw_license = str(entry.get("License", ""))
        normalized = _extract_license_names(raw_license)
        if normalized == {UNKNOWN_LICENSE}:
            classifier_tokens = _licenses_from_classifiers(name)
            if classifier_tokens:
                normalized = classifier_tokens
        elif UNKNOWN_LICENSE in normalized:
            normalized.discard(UNKNOWN_LICENSE)
            if not normalized:
                normalized.add(UNKNOWN_LICENSE)
        if normalized.issubset(ALLOWED_LICENSES):
            continue
        violations.append(f"{name}: {raw_license or ', '.join(sorted(normalized))}")
    if violations:
        raise SupplyChainError("Disallowed licenses detected: " + ", ".join(sorted(violations)))


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_wheel_hashes(context: RuntimeContext) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        temp_path = Path(tmp)
        freeze_output = _run_module("pip", "freeze").stdout
        requirements: dict[str, str] = {}
        root_key = _canonicalize_name(context.root_distribution)
        for line in freeze_output.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("-e "):
                continue
            if " @ " in stripped or stripped.startswith("@"):
                continue
            if "==" not in stripped:
                continue
            name, version = stripped.split("==", 1)
            key = _canonicalize_name(name)
            if key == root_key:
                continue
            if key in context.canonical_keys:
                requirements[key] = f"{name}=={version}"
        requirement_lines = [
            requirements[key]
            for key in sorted(
                requirements,
                key=lambda candidate: context.package_info.get(candidate, {})
                .get("name", candidate)
                .lower(),
            )
        ]
        requirements_file = temp_path / "requirements.txt"
        if requirement_lines:
            requirements_file.write_text("\n".join(requirement_lines) + "\n", encoding="utf-8")
            try:
                subprocess.run(  # noqa: PLW1510
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "download",
                        "--only-binary",
                        ":all:",
                        "--no-deps",
                        "--dest",
                        str(temp_path),
                        "--requirement",
                        str(requirements_file),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as exc:
                message = exc.stderr or exc.stdout or "pip download failed"
                raise SupplyChainError(
                    "Failed to download wheels for runtime dependencies: "
                    f"{message.strip()}"
                ) from exc
        try:
            subprocess.run(  # noqa: PLW1510
                [
                    sys.executable,
                    "-m",
                    "build",
                    "--wheel",
                    "--no-isolation",
                    "--outdir",
                    str(temp_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                cwd=str(ROOT),
            )
        except FileNotFoundError as exc:  # pragma: no cover - depends on environment
            raise SupplyChainError(
                "build module is not available to produce the project wheel"
            ) from exc
        except subprocess.CalledProcessError as exc:
            message = exc.stderr or exc.stdout or "python -m build failed"
            raise SupplyChainError(
                "Failed to build project wheel for hashing: " + message.strip()
            ) from exc
        wheel_lines: list[str] = []
        for wheel in sorted(temp_path.glob("*.whl")):
            wheel_lines.append(f"{wheel.name}  sha256:{_hash_file(wheel)}")
        _write_text(ARTIFACTS / "wheels_hashes.txt", "\n".join(wheel_lines))


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    context = _build_runtime_context()
    _ensure_sbom(context)
    try:
        _collect_licenses(context)
    except SupplyChainError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error
    _collect_wheel_hashes(context)
    print("supply-chain ok")


if __name__ == "__main__":
    main()
