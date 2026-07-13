from __future__ import annotations

import json
import math
import posixpath
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator

from .schema import SCHEMA_NAMES, load_schema


REQUIRED_FILES = [
    "book.json",
    "source_map.json",
    "terms.json",
    "translation.json",
    "reading_config.json",
    "search_index.json",
]

MAX_ARCHIVE_ENTRIES = 10_000
MAX_MEMBER_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
MAX_COMPRESSION_RATIO = 1_000

_MARKDOWN_ASSET_PATTERN = re.compile(
    r"!\[[^\]]*\]\((?:<([^>]+)>|([^) \t]+))(?:\s+['\"][^'\"]*['\"])?\)"
)
_HTML_SRC_PATTERN = re.compile(
    r'''src\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>"']+))''', re.IGNORECASE
)


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]


def validate_bookmd(path: str | Path, *, strict: bool = False) -> ValidationResult:
    """Validate a BookMD archive.

    The default mode intentionally keeps the historical structural checks so old
    archives remain readable.  ``strict=True`` additionally validates the 1.0
    schemas, ZIP safety, and all cross-file references.
    """

    archive_path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []

    if not archive_path.exists():
        return ValidationResult(False, [f"BookMD file does not exist: {archive_path}"], [])

    try:
        with zipfile.ZipFile(archive_path) as zf:
            infos = zf.infolist()
            names = [info.filename for info in infos]
            name_set = set(names)
            for required in REQUIRED_FILES:
                if required not in name_set:
                    errors.append(f"Missing required file: {required}")

            if not any(name.startswith("chapters/") and name.endswith(".md") for name in name_set):
                errors.append("Missing chapter Markdown files under chapters/")

            if strict:
                _validate_zip_safety(infos, errors)

            payloads: dict[str, Any] = {}
            for member in REQUIRED_FILES:
                if member not in name_set:
                    continue
                payload = _read_json_member(zf, member, errors)
                if payload is not None:
                    payloads[member] = payload

            book = payloads.get("book.json")
            if isinstance(book, dict):
                _validate_book_manifest(book, name_set, errors)
                if strict:
                    schema_version = _book_schema_version(book, warnings, errors)
                    if schema_version == "1.0":
                        _validate_schemas(payloads, errors)
                        _validate_cross_references(zf, name_set, payloads, errors)
            elif "book.json" in name_set:
                # _read_json_member already reported malformed JSON. Keep the
                # historical manifest error for non-object JSON payloads.
                errors.append("book.json must contain a JSON object")
    except zipfile.BadZipFile:
        errors.append(f"Invalid zip archive: {archive_path}")
    except OSError as exc:
        errors.append(f"Unable to read BookMD archive {archive_path}: {exc}")

    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)


def _read_json_member(zf: zipfile.ZipFile, name: str, errors: list[str]) -> Any | None:
    try:
        return json.loads(zf.read(name).decode("utf-8"))
    except UnicodeDecodeError as exc:
        errors.append(f"{name} is not valid UTF-8: {exc}")
    except json.JSONDecodeError as exc:
        errors.append(f"{name} is not valid JSON: {exc}")
    except KeyError:
        return None
    return None


def _validate_book_manifest(data: dict[str, Any], names: set[str], errors: list[str]) -> None:
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


def _book_schema_version(book: dict[str, Any], warnings: list[str], errors: list[str]) -> str | None:
    raw = book.get("format_version")
    if raw is None:
        legacy = book.get("version", "0.1")
        warnings.append(
            f"Legacy BookMD format {legacy!r} detected; readable in compatibility mode, migrate to format_version 1.0"
        )
        return None

    version = str(raw)
    if version == "1.0":
        return version
    major = version.split(".", 1)[0]
    if major != "1":
        errors.append(f"Unsupported BookMD format major version: {version}")
    else:
        warnings.append(
            f"BookMD format minor version {version!r} is newer than 1.0; validating the 1.0 compatibility profile"
        )
        return "1.0"
    return None


def _validate_schemas(payloads: dict[str, Any], errors: list[str]) -> None:
    for member in REQUIRED_FILES:
        payload = payloads.get(member)
        if payload is None:
            continue
        schema_name = member.removesuffix(".json")
        if schema_name not in SCHEMA_NAMES:
            continue
        schema_payload = payload
        if member == "book.json" and isinstance(payload, dict) and payload.get("format_version") != "1.0":
            schema_payload = {**payload, "format_version": "1.0"}
        try:
            schema = load_schema(schema_name, "1.0")
            validator = Draft202012Validator(schema)
            for error in sorted(
                validator.iter_errors(schema_payload),
                key=lambda item: tuple(str(part) for part in item.path),
            ):
                location = ".".join(str(part) for part in error.path) or "$"
                errors.append(f"{member} schema error at {location}: {error.message}")
        except (ValueError, OSError) as exc:
            errors.append(f"Unable to load schema for {member}: {exc}")


def _validate_zip_safety(infos: list[zipfile.ZipInfo], errors: list[str]) -> None:
    if len(infos) > MAX_ARCHIVE_ENTRIES:
        errors.append(f"Archive contains too many entries: {len(infos)} > {MAX_ARCHIVE_ENTRIES}")

    seen: set[str] = set()
    total_size = 0
    for info in infos:
        name = info.filename
        if name in seen:
            errors.append(f"Duplicate archive entry: {name}")
        seen.add(name)
        if _unsafe_archive_path(name):
            errors.append(f"Unsafe archive path: {name}")
        if _is_symlink(info):
            errors.append(f"Symlink archive entry is not allowed: {name}")
        if info.file_size > MAX_MEMBER_UNCOMPRESSED_BYTES:
            errors.append(
                f"Archive member exceeds size limit: {name} ({info.file_size} bytes)"
            )
        if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
            errors.append(f"Suspicious compression ratio for archive member: {name}")
        total_size += info.file_size
    if total_size > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
        errors.append(
            f"Archive exceeds total uncompressed size limit: {total_size} bytes"
        )


def _unsafe_archive_path(name: str) -> bool:
    if not name or "\\" in name:
        return True
    path = PurePosixPath(name)
    return path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return ((info.external_attr >> 16) & 0o170000) == 0o120000


def _validate_cross_references(
    zf: zipfile.ZipFile,
    names: set[str],
    payloads: dict[str, Any],
    errors: list[str],
) -> None:
    book = payloads.get("book.json")
    if not isinstance(book, dict):
        return

    chapters = book.get("chapters")
    chapter_ids: set[str] = set()
    chapter_paths: set[str] = set()
    if isinstance(chapters, list):
        orders: set[int] = set()
        for chapter in chapters:
            if not isinstance(chapter, dict):
                continue
            chapter_id = chapter.get("id")
            chapter_path = chapter.get("path")
            order = chapter.get("order")
            if isinstance(chapter_id, str):
                if chapter_id in chapter_ids:
                    errors.append(f"Duplicate chapter id: {chapter_id}")
                chapter_ids.add(chapter_id)
            if isinstance(chapter_path, str):
                if chapter_path in chapter_paths:
                    errors.append(f"Duplicate chapter path: {chapter_path}")
                chapter_paths.add(chapter_path)
                _validate_chapter_path(chapter_path, names, errors)
            if isinstance(order, int):
                if order in orders:
                    errors.append(f"Duplicate chapter order: {order}")
                orders.add(order)

    source_map = payloads.get("source_map.json")
    block_ids: set[str] = set()
    if isinstance(source_map, dict) and isinstance(source_map.get("blocks"), list):
        for block in source_map["blocks"]:
            if not isinstance(block, dict):
                continue
            block_id = block.get("block_id")
            if isinstance(block_id, str):
                if block_id in block_ids:
                    errors.append(f"Duplicate source-map block_id: {block_id}")
                block_ids.add(block_id)
            chapter_id = block.get("chapter_id")
            if chapter_id not in chapter_ids:
                errors.append(f"Source-map block {block_id!r} references unknown chapter_id: {chapter_id}")
            markdown_path = block.get("markdown_path")
            if markdown_path not in chapter_paths:
                errors.append(f"Source-map block {block_id!r} references unknown markdown_path: {markdown_path}")
            source_page = block.get("source_page")
            if not isinstance(source_page, int) or source_page < 1:
                errors.append(f"Source-map block {block_id!r} has invalid source_page: {source_page}")
            bbox = block.get("bbox")
            if not _valid_bbox(bbox):
                errors.append(f"Source-map block {block_id!r} has invalid bbox: {bbox}")

    search_index = payloads.get("search_index.json")
    if isinstance(search_index, dict) and isinstance(search_index.get("items"), list):
        for item in search_index["items"]:
            if not isinstance(item, dict):
                continue
            item_id = item.get("block_id")
            if item_id not in block_ids:
                errors.append(f"Search index item references unknown block_id: {item_id}")
            if item.get("chapter_id") not in chapter_ids:
                errors.append(f"Search index item references unknown chapter_id: {item.get('chapter_id')}")
            if item.get("chapter_path") not in chapter_paths:
                errors.append(f"Search index item references unknown chapter_path: {item.get('chapter_path')}")

    translation = payloads.get("translation.json")
    if isinstance(translation, dict) and isinstance(translation.get("blocks"), list):
        for item in translation["blocks"]:
            if isinstance(item, dict) and item.get("block_id") not in block_ids:
                errors.append(f"Translation block references unknown block_id: {item.get('block_id')}")

    for chapter_path in chapter_paths:
        try:
            markdown = zf.read(chapter_path).decode("utf-8")
        except (KeyError, UnicodeDecodeError):
            continue
        for reference in _asset_references(markdown):
            resolved = _resolve_asset_reference(chapter_path, reference)
            if resolved is None:
                errors.append(f"Unsafe asset reference in {chapter_path}: {reference}")
            elif resolved not in names:
                errors.append(
                    f"Missing asset referenced by {chapter_path}: {reference} ({resolved})"
                )


def _validate_chapter_path(path: str, names: set[str], errors: list[str]) -> None:
    if _unsafe_archive_path(path) or not path.startswith("chapters/") or not path.endswith(".md"):
        errors.append(f"Invalid chapter path: {path}")
    elif path not in names:
        errors.append(f"Chapter file listed in book.json is missing: {path}")


def _valid_bbox(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 4:
        return False
    if not all(isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(item) for item in value):
        return False
    x1, y1, x2, y2 = value
    return x2 > x1 and y2 > y1


def _asset_references(markdown: str) -> set[str]:
    references: set[str] = set()
    for match in _MARKDOWN_ASSET_PATTERN.finditer(markdown):
        references.add(match.group(1) or match.group(2) or "")
    for match in _HTML_SRC_PATTERN.finditer(markdown):
        references.add(match.group(1) or match.group(2) or match.group(3) or "")
    return {reference.strip() for reference in references if reference.strip()}


def _resolve_asset_reference(chapter_path: str, reference: str) -> str | None:
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", reference) or reference.startswith("#"):
        return chapter_path
    cleaned = reference.split("#", 1)[0].split("?", 1)[0]
    if cleaned.startswith("file://"):
        cleaned = cleaned.removeprefix("file://")
    if "\\" in reference:
        return None
    if cleaned.startswith("assets/"):
        return PurePosixPath(cleaned).as_posix()
    if cleaned.startswith("./assets/"):
        return PurePosixPath(cleaned.removeprefix("./")).as_posix()
    if not cleaned.startswith("../assets/"):
        return chapter_path
    resolved = PurePosixPath(chapter_path).parent.joinpath(cleaned)
    normalized_text = posixpath.normpath(resolved.as_posix())
    normalized = PurePosixPath(normalized_text)
    if normalized.is_absolute() or normalized_text == ".." or normalized_text.startswith("../"):
        return None
    value = normalized.as_posix()
    return value if value.startswith("assets/") else chapter_path
