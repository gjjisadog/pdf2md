from __future__ import annotations

import zipfile
from pathlib import Path

from bookmd_core import validate_bookmd


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "bookmd"


def _archive_fixture(name: str, tmp_path: Path) -> Path:
    source = FIXTURES / name
    output = tmp_path / f"{name}.bookmd"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            archive.write(path, path.relative_to(source).as_posix())
    return output


def test_legacy_v01_fixture_passes_with_migration_warning(tmp_path: Path):
    result = validate_bookmd(_archive_fixture("legacy_v0_1", tmp_path), strict=True)

    assert result.valid is True
    assert result.errors == []
    assert any("legacy" in warning.lower() or "migration" in warning.lower() for warning in result.warnings)


def test_legacy_fixture_is_valid_in_default_compatibility_mode(tmp_path: Path):
    result = validate_bookmd(_archive_fixture("legacy_v0_1", tmp_path))

    assert result.valid is True
