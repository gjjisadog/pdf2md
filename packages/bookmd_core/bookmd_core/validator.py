from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path


REQUIRED_FILES = [
    "book.json",
    "source_map.json",
    "terms.json",
    "translation.json",
    "reading_config.json",
    "search_index.json",
]


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]


def validate_bookmd(path: str | Path) -> ValidationResult:
    archive_path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []

    if not archive_path.exists():
        return ValidationResult(False, [f"BookMD file does not exist: {archive_path}"], [])

    try:
        with zipfile.ZipFile(archive_path) as zf:
            names = set(zf.namelist())
            for required in REQUIRED_FILES:
                if required not in names:
                    errors.append(f"Missing required file: {required}")

            if not any(name.startswith("chapters/") and name.endswith(".md") for name in names):
                errors.append("Missing chapter Markdown files under chapters/")

            if "book.json" in names:
                _validate_book_manifest(zf.read("book.json"), names, errors)
    except zipfile.BadZipFile:
        errors.append(f"Invalid zip archive: {archive_path}")

    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)


def _validate_book_manifest(payload: bytes, names: set[str], errors: list[str]) -> None:
    try:
        data = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"book.json is not valid JSON: {exc}")
        return

    if "chapters" not in data or not isinstance(data["chapters"], list):
        errors.append("book.json must contain a chapters list")
        return

    for chapter in data["chapters"]:
        if not isinstance(chapter, dict):
            errors.append("book.json chapters must contain objects")
            continue
        path = chapter.get("path")
        if not path:
            errors.append("book.json chapter is missing path")
        elif path not in names:
            errors.append(f"Chapter file listed in book.json is missing: {path}")
