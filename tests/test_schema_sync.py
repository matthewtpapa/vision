from __future__ import annotations

from scripts.check_schema_sync import main


def test_readme_schema_matches_schema_md():
    assert main() == 0
