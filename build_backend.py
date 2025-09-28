from __future__ import annotations

import base64
import email.message
import hashlib
import os
import re
import tarfile
import tempfile
import textwrap
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # Python >=3.11
except ModuleNotFoundError:  # pragma: no cover - fallback for <3.11
    import tomli as tomllib  # type: ignore[no-redef]


REPO_ROOT = Path(__file__).resolve().parent
SRC_ROOT = REPO_ROOT / "src"
PYPROJECT = REPO_ROOT / "pyproject.toml"
README_CACHE: dict[str, str] = {}


def _normalize_version(version: str) -> str:
    """Return a PEP 440 compliant representation of *version*."""

    def repl(match: re.Match[str]) -> str:
        label = match.group(1).lower()
        number = match.group(2)
        mapping = {
            "alpha": "a",
            "beta": "b",
            "c": "rc",
            "pre": "rc",
            "preview": "rc",
            "rc": "rc",
            "post": "post",
            "rev": "post",
            "r": "post",
            "dev": "dev",
            "final": "",
            "ga": "",
        }
        prefix = mapping.get(label, label)
        return f"{prefix}{number}" if prefix else number

    canonical = re.sub(
        r"-(alpha|beta|rc|pre|preview|c|post|rev|r|dev|final|ga)\.?([0-9]*)",
        repl,
        version,
        flags=re.IGNORECASE,
    )
    return canonical.replace("-", ".")


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    version: str
    summary: str | None
    readme_text: str | None
    readme_content_type: str | None
    requires_python: str | None
    dependencies: list[str]
    optional_dependencies: dict[str, list[str]]
    urls: dict[str, str]
    scripts: dict[str, str]
    gui_scripts: dict[str, str]
    entry_points: dict[str, dict[str, str]]
    authors: list[dict[str, str]]

    @property
    def normalized_name(self) -> str:
        return re.sub(r"[-_.]+", "_", self.name).lower()

    @property
    def canonical_version(self) -> str:
        return _normalize_version(self.version)

    @property
    def dist_info(self) -> str:
        return f"{self.normalized_name}-{self.canonical_version}.dist-info"

    @property
    def wheel_filename(self) -> str:
        return f"{self.normalized_name}-{self.canonical_version}-py3-none-any.whl"


def _load_pyproject() -> dict[str, object]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):  # pragma: no cover - invalid configuration
        raise RuntimeError("pyproject.toml missing [project] table")
    return project  # type: ignore[return-value]


def _read_readme(entry: object) -> tuple[str | None, str | None]:
    if isinstance(entry, str):
        return entry, "text/plain"
    if isinstance(entry, dict):
        path = entry.get("file")
        if isinstance(path, str):
            cache_key = os.fspath(Path(path))
            if cache_key not in README_CACHE:
                README_CACHE[cache_key] = (REPO_ROOT / path).read_text(encoding="utf-8")
            content_type = entry.get("content-type")
            if isinstance(content_type, str):
                return README_CACHE[cache_key], content_type
            return README_CACHE[cache_key], "text/plain"
        text = entry.get("text")
        if isinstance(text, str):
            content_type = entry.get("content-type")
            return text, content_type if isinstance(content_type, str) else "text/plain"
    return None, None


def _load_config() -> ProjectConfig:
    data = _load_pyproject()
    name = str(data.get("name"))
    version = str(data.get("version"))
    summary = data.get("description")
    if summary is not None:
        summary = str(summary)
    readme_text: str | None = None
    readme_content_type: str | None = None
    readme_entry = data.get("readme")
    if readme_entry is not None:
        readme_text, readme_content_type = _read_readme(readme_entry)
    requires_python = data.get("requires-python")
    if requires_python is not None:
        requires_python = str(requires_python)
    dependencies = [str(dep) for dep in data.get("dependencies", [])]
    optional_dependencies = {
        str(extra): [str(dep) for dep in deps]
        for extra, deps in (data.get("optional-dependencies", {}) or {}).items()
        if isinstance(extra, str)
    }
    urls = {str(key): str(value) for key, value in (data.get("urls") or {}).items()}
    scripts = {str(k): str(v) for k, v in (data.get("scripts") or {}).items()}
    gui_scripts = {str(k): str(v) for k, v in (data.get("gui-scripts") or {}).items()}
    entry_points = {}
    for group, entries in (data.get("entry-points") or {}).items():
        if isinstance(group, str) and isinstance(entries, dict):
            entry_points[group] = {str(k): str(v) for k, v in entries.items()}
    authors = []
    for author in data.get("authors", []) or []:
        if isinstance(author, dict):
            authors.append({str(k): str(v) for k, v in author.items() if isinstance(v, str)})
    return ProjectConfig(
        name=name,
        version=version,
        summary=summary,
        readme_text=readme_text,
        readme_content_type=readme_content_type,
        requires_python=requires_python,
        dependencies=dependencies,
        optional_dependencies=optional_dependencies,
        urls=urls,
        scripts=scripts,
        gui_scripts=gui_scripts,
        entry_points=entry_points,
        authors=authors,
    )


def _format_metadata(config: ProjectConfig) -> str:
    message = email.message.EmailMessage()
    message["Metadata-Version"] = "2.1"
    message["Name"] = config.name
    message["Version"] = config.canonical_version
    if config.summary:
        message["Summary"] = config.summary
    home_page = config.urls.get("Homepage") or config.urls.get("Home")
    if home_page:
        message["Home-page"] = home_page
    if config.requires_python:
        message["Requires-Python"] = config.requires_python
    for author in config.authors:
        name = author.get("name")
        email_addr = author.get("email")
        if name and email_addr:
            message["Author-email"] = f"{name} <{email_addr}>"
        elif email_addr:
            message["Author-email"] = email_addr
        elif name:
            message["Author"] = name
    for url_name, url in config.urls.items():
        message["Project-URL"] = f"{url_name}, {url}"
    for dependency in config.dependencies:
        message["Requires-Dist"] = dependency
    for extra, deps in config.optional_dependencies.items():
        message["Provides-Extra"] = extra
        for dep in deps:
            dep = dep.strip()
            if ";" in dep:
                name, marker = dep.split(";", 1)
                combined = f'{name.strip()}; ({marker.strip()}) and extra == "{extra}"'
            else:
                combined = f'{dep}; extra == "{extra}"'
            message["Requires-Dist"] = combined
    if config.readme_text is not None:
        content_type = config.readme_content_type or "text/plain"
        message["Description-Content-Type"] = content_type
        message.set_content(config.readme_text)
    else:
        message.set_content("")
    raw = message.as_string()
    header, _, body = raw.partition("\n\n")
    filtered_header_lines = [
        line
        for line in header.splitlines()
        if not line.lower().startswith("content-type:")
        and not line.lower().startswith("content-transfer-encoding:")
        and line
    ]
    metadata_lines = filtered_header_lines + [""]
    if body:
        metadata_lines.append(body)
    return "\n".join(metadata_lines).strip("\n") + "\n"


def _write_metadata(destination: Path, config: ProjectConfig) -> Path:
    dist_info = destination / config.dist_info
    dist_info.mkdir(parents=True, exist_ok=True)
    (dist_info / "METADATA").write_text(_format_metadata(config), encoding="utf-8")
    wheel_text = (
        textwrap.dedent(
            """
        Wheel-Version: 1.0
        Generator: latency_vision.build_backend
        Root-Is-Purelib: true
        Tag: py3-none-any
        """
        ).strip()
        + "\n"
    )
    (dist_info / "WHEEL").write_text(wheel_text, encoding="utf-8")
    entry_points_sections = []
    if config.scripts:
        entry_points_sections.append("[console_scripts]")
        entry_points_sections.extend(
            f"{name} = {target}" for name, target in sorted(config.scripts.items())
        )
    if config.gui_scripts:
        entry_points_sections.append("[gui_scripts]")
        entry_points_sections.extend(
            f"{name} = {target}" for name, target in sorted(config.gui_scripts.items())
        )
    for group, entries in sorted(config.entry_points.items()):
        entry_points_sections.append(f"[{group}]")
        entry_points_sections.extend(
            f"{name} = {target}" for name, target in sorted(entries.items())
        )
    if entry_points_sections:
        (dist_info / "entry_points.txt").write_text(
            "\n".join(entry_points_sections) + "\n", encoding="utf-8"
        )
    return dist_info


def _iter_package_files() -> Iterable[tuple[Path, str]]:
    for path in SRC_ROOT.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            relative = path.relative_to(SRC_ROOT)
            yield path, str(relative).replace(os.sep, "/")


def _hash_record(data: bytes) -> tuple[str, int]:
    digest = hashlib.sha256(data).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"sha256={encoded}", len(data)


def _build_record_line(path: str, data: bytes) -> str:
    digest, size = _hash_record(data)
    return f"{path},{digest},{size}"


def prepare_metadata_for_build_wheel(
    metadata_directory: str, config_settings: dict[str, object] | None = None
) -> str:
    config = _load_config()
    dest = Path(metadata_directory)
    dist_info = _write_metadata(dest, config)
    return dist_info.name


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, object] | None = None,
    metadata_directory: str | None = None,
) -> str:
    config = _load_config()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        if metadata_directory:
            dist_info = Path(metadata_directory) / config.dist_info
            if not dist_info.exists():
                dist_info = _write_metadata(Path(metadata_directory), config)
        else:
            dist_info = _write_metadata(tmp_path, config)
        dist_info = dist_info if dist_info.exists() else _write_metadata(tmp_path, config)
        wheel_path = Path(wheel_directory) / config.wheel_filename
        records: list[str] = []
        with zipfile.ZipFile(wheel_path, "w") as zf:
            for source, arcname in _iter_package_files():
                data = source.read_bytes()
                zf.writestr(arcname, data)
                records.append(_build_record_line(arcname, data))
            for meta_file in sorted(dist_info.iterdir()):
                if meta_file.name == "RECORD":
                    continue
                data = meta_file.read_bytes()
                arcname = f"{config.dist_info}/{meta_file.name}"
                zf.writestr(arcname, data)
                records.append(_build_record_line(arcname, data))
            record_content = "\n".join(records + [f"{config.dist_info}/RECORD,,"]) + "\n"
            zf.writestr(f"{config.dist_info}/RECORD", record_content.encode("utf-8"))
        return wheel_path.name


def build_editable(
    wheel_directory: str,
    config_settings: dict[str, object] | None = None,
    metadata_directory: str | None = None,
) -> str:
    config = _load_config()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        if metadata_directory:
            dist_info = Path(metadata_directory) / config.dist_info
            if not dist_info.exists():
                dist_info = _write_metadata(Path(metadata_directory), config)
        else:
            dist_info = _write_metadata(tmp_path, config)
        wheel_path = Path(wheel_directory) / config.wheel_filename
        records: list[str] = []
        src_path = SRC_ROOT.resolve()
        pth_name = f"{config.normalized_name}.pth"
        pth_data = (str(src_path) + "\n").encode("utf-8")
        with zipfile.ZipFile(wheel_path, "w") as zf:
            zf.writestr(pth_name, pth_data)
            records.append(_build_record_line(pth_name, pth_data))
            for meta_file in sorted(dist_info.iterdir()):
                if meta_file.name == "RECORD":
                    continue
                data = meta_file.read_bytes()
                arcname = f"{config.dist_info}/{meta_file.name}"
                zf.writestr(arcname, data)
                records.append(_build_record_line(arcname, data))
            record_content = "\n".join(records + [f"{config.dist_info}/RECORD,,"]) + "\n"
            zf.writestr(f"{config.dist_info}/RECORD", record_content.encode("utf-8"))
        return wheel_path.name


def get_requires_for_build_wheel(config_settings: dict[str, object] | None = None) -> list[str]:
    return []


def get_requires_for_build_editable(config_settings: dict[str, object] | None = None) -> list[str]:
    return []


def get_requires_for_build_sdist(config_settings: dict[str, object] | None = None) -> list[str]:
    return []


def build_sdist(sdist_directory: str, config_settings: dict[str, object] | None = None) -> str:
    config = _load_config()
    archive_name = f"{config.normalized_name}-{config.canonical_version}.tar.gz"
    sdist_path = Path(sdist_directory) / archive_name
    with tarfile.open(sdist_path, "w:gz") as tar:
        for path in REPO_ROOT.rglob("*"):
            if "__pycache__" in path.parts:
                continue
            if path.is_file():
                tar.add(path, arcname=path.relative_to(REPO_ROOT))
    return archive_name
