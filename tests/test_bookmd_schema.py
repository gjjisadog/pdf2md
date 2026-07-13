from __future__ import annotations

import inspect
import json
import zipfile
from pathlib import Path

import pytest

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


def test_valid_v1_fixture_passes_strict_validation(tmp_path: Path):
    if "strict" not in inspect.signature(validate_bookmd).parameters:
        pytest.fail("validate_bookmd must expose strict mode")
    result = validate_bookmd(_archive_fixture("valid_v1", tmp_path), strict=True)

    assert result.valid is True
    assert result.errors == []


def test_invalid_v1_fixture_reports_unsafe_and_dangling_references(tmp_path: Path):
    result = validate_bookmd(_archive_fixture("invalid_v1", tmp_path), strict=True)

    assert result.valid is False
    assert any("assets/missing.png" in error for error in result.errors)
    assert any("block_id" in error or "duplicate" in error.lower() for error in result.errors)


def test_schema_loader_rejects_unknown_schema_name():
    from bookmd_core.schema import load_schema

    with pytest.raises(ValueError, match="Unknown BookMD schema"):
        load_schema("not-a-schema")


def test_v1_schema_requires_format_version():
    from bookmd_core.schema import load_schema

    schema = load_schema("book")

    assert "format_version" in schema["required"]
    assert schema["properties"]["format_version"]["const"] == "1.0"


def test_strict_validation_rejects_duplicate_and_unsafe_archive_entries(tmp_path: Path):
    archive = _archive_fixture("valid_v1", tmp_path)
    with zipfile.ZipFile(archive, "a") as zf:
        zf.writestr("book.json", zf.read("book.json"))
        zf.writestr("../escape.txt", "unsafe")

    result = validate_bookmd(archive, strict=True)

    assert any("Duplicate archive entry: book.json" in error for error in result.errors)
    assert any("Unsafe archive path: ../escape.txt" in error for error in result.errors)


def test_strict_validation_rejects_unknown_major_version(tmp_path: Path):
    archive = _archive_fixture("valid_v1", tmp_path)
    with zipfile.ZipFile(archive, "r") as source:
        members = {name: source.read(name) for name in source.namelist()}
    book = json.loads(members["book.json"])
    book["format_version"] = "2.0"
    members["book.json"] = json.dumps(book).encode("utf-8")
    with zipfile.ZipFile(archive, "w") as target:
        for name, payload in members.items():
            target.writestr(name, payload)

    result = validate_bookmd(archive, strict=True)

    assert result.valid is False
    assert any("Unsupported BookMD format major version: 2.0" in error for error in result.errors)
