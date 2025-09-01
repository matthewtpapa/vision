import difflib
import re
from pathlib import Path


def _extract_block(path: Path) -> str:
    text = path.read_text()
    marker = "Example `MatchResult`"
    idx = text.find(marker)
    if idx == -1:
        raise AssertionError(f"{path} missing '{marker}' section")
    after = text[idx:]
    match = re.search(r"```json\n(.*?)```", after, re.DOTALL)
    if not match:
        raise AssertionError(f"{path} missing json block after '{marker}'")
    return match.group(1).rstrip("\n")


def test_readme_schema_sync():
    readme_block = _extract_block(Path("README.md"))
    schema_block = _extract_block(Path("docs/schema.md"))
    if readme_block != schema_block:
        diff_lines = list(
            difflib.unified_diff(
                readme_block.splitlines(),
                schema_block.splitlines(),
                fromfile="README.md",
                tofile="docs/schema.md",
                lineterm="",
            )
        )[:40]
        diff = "\n".join(diff_lines)
        raise AssertionError("README.md and docs/schema.md examples differ:\n" + diff)
