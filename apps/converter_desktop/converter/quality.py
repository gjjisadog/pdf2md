from __future__ import annotations

import json
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Any

from bookmd_core import validate_bookmd


_MARKDOWN_ASSET_PATTERN = re.compile(r"!\[[^\]]*]\((?:<([^>]+)>|([^) \t]+))(?:\s+['\"][^'\"]*['\"])?\)")
_HTML_SRC_PATTERN = re.compile(r"""src\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>"']+))""", re.IGNORECASE)


@dataclass(frozen=True)
class BookMdQualityReport:
    path: str
    valid: bool
    title: str
    chapter_count: int
    empty_chapter_count: int
    search_item_count: int
    source_map_block_count: int
    has_original_pdf: bool
    has_cover: bool
    asset_count: int
    referenced_asset_count: int
    broken_asset_references: list[str]
    missing_visual_asset_block_ids: list[str]
    missing_source_pages: list[int]
    translation_provider: str
    translation_block_count: int
    translated_block_count: int
    untranslated_block_count: int
    translation_coverage_ratio: float
    untranslated_block_ids: list[str]
    glossary_term_count: int
    missing_glossary_targets: list[str]
    markdown_risk_block_ids: list[str]
    overlong_translation_block_ids: list[str]
    warnings: list[str]
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_bookmd(
    path: str | PurePosixPath,
    *,
    strict: bool = False,
) -> BookMdQualityReport:
    archive_path = str(path)
    validation = validate_bookmd(archive_path, strict=strict)
    warnings = list(validation.warnings)
    errors = list(validation.errors)
    title = ""
    chapter_count = 0
    empty_chapter_count = 0
    search_item_count = 0
    source_map_block_count = 0
    has_original_pdf = False
    has_cover = False
    asset_count = 0
    referenced_assets: set[str] = set()
    broken_asset_references: list[str] = []
    missing_visual_asset_block_ids: list[str] = []
    missing_source_pages: set[int] = set()
    translation_provider = ""
    translation_block_count = 0
    translated_block_count = 0
    untranslated_block_ids: list[str] = []
    glossary_term_count = 0
    missing_glossary_targets: list[str] = []
    markdown_risk_block_ids: list[str] = []
    overlong_translation_block_ids: list[str] = []

    try:
        with zipfile.ZipFile(archive_path) as zf:
            names = set(zf.namelist())
            book = _read_json(zf, "book.json")
            title = str(book.get("title") or "")
            chapters = book.get("chapters")
            if isinstance(chapters, list):
                chapter_count = len(chapters)
                for chapter in chapters:
                    if not isinstance(chapter, dict):
                        continue
                    chapter_path = str(chapter.get("path") or "")
                    if not chapter_path or chapter_path not in names:
                        continue
                    chapter_text = zf.read(chapter_path).decode("utf-8", errors="replace")
                    if not chapter_text.strip():
                        empty_chapter_count += 1
                    referenced_assets.update(_asset_references_from_chapter(chapter_path, chapter_text))

            search_index = _read_json(zf, "search_index.json")
            search_items = search_index.get("items")
            search_item_count = len(search_items) if isinstance(search_items, list) else 0

            source_map = _read_json(zf, "source_map.json")
            source_blocks = source_map.get("blocks")
            if isinstance(source_blocks, list):
                source_map_block_count = len(source_blocks)
                missing_source_pages = _missing_source_pages(source_blocks)

            has_original_pdf = "source/original.pdf" in names
            asset_files = {
                name
                for name in names
                if name.startswith("assets/") and not name.endswith("/")
            }
            asset_count = len(asset_files)
            has_cover = any(
                name.startswith("assets/cover")
                or name.startswith("assets/generated/cover")
                or name.startswith("assets/pages/page_001")
                for name in asset_files
            )
            broken_asset_references = sorted(
                reference for reference in referenced_assets if _asset_archive_path(reference) not in asset_files
            )
            asset_generation = _read_json(zf, "asset_generation.json")
            failed_assets = asset_generation.get("failed")
            if isinstance(failed_assets, list):
                missing_visual_asset_block_ids = sorted(
                    {
                        str(item.get("block_id"))
                        for item in failed_assets
                        if isinstance(item, dict) and item.get("block_id")
                    }
                )

            translation = _read_json(zf, "translation.json")
            terms = _read_json(zf, "terms.json")
            translation_metrics = _translation_metrics(translation, terms)
            translation_provider = translation_metrics["provider"]
            translation_block_count = translation_metrics["block_count"]
            translated_block_count = translation_metrics["translated_count"]
            untranslated_block_ids = translation_metrics["untranslated_block_ids"]
            glossary_term_count = translation_metrics["glossary_term_count"]
            missing_glossary_targets = translation_metrics["missing_glossary_targets"]
            markdown_risk_block_ids = translation_metrics["markdown_risk_block_ids"]
            overlong_translation_block_ids = translation_metrics["overlong_translation_block_ids"]
    except (zipfile.BadZipFile, FileNotFoundError):
        pass

    untranslated_block_count = len(untranslated_block_ids)
    translation_coverage_ratio = (
        round(translated_block_count / translation_block_count, 4)
        if translation_block_count
        else 0.0
    )
    if not has_original_pdf:
        warnings.append("source/original.pdf is missing")
    if empty_chapter_count:
        warnings.append(f"empty chapters: {empty_chapter_count}")
    if broken_asset_references:
        warnings.append(f"broken asset references: {len(broken_asset_references)}")
    if missing_visual_asset_block_ids:
        warnings.append(f"missing visual assets: {len(missing_visual_asset_block_ids)}")
    if missing_source_pages:
        warnings.append(f"missing source pages: {len(missing_source_pages)}")
    if not has_cover:
        warnings.append("cover visual is missing")
    if untranslated_block_count:
        warnings.append(f"untranslated blocks: {untranslated_block_count}")
    if missing_glossary_targets:
        warnings.append(f"glossary targets missing: {len(missing_glossary_targets)}")
    if markdown_risk_block_ids:
        warnings.append(f"translation markdown risks: {len(markdown_risk_block_ids)}")
    if overlong_translation_block_ids:
        warnings.append(f"overlong translations: {len(overlong_translation_block_ids)}")

    return BookMdQualityReport(
        path=archive_path,
        valid=validation.valid,
        title=title,
        chapter_count=chapter_count,
        empty_chapter_count=empty_chapter_count,
        search_item_count=search_item_count,
        source_map_block_count=source_map_block_count,
        has_original_pdf=has_original_pdf,
        has_cover=has_cover,
        asset_count=asset_count,
        referenced_asset_count=len(referenced_assets),
        broken_asset_references=broken_asset_references,
        missing_visual_asset_block_ids=missing_visual_asset_block_ids,
        missing_source_pages=sorted(missing_source_pages),
        translation_provider=translation_provider,
        translation_block_count=translation_block_count,
        translated_block_count=translated_block_count,
        untranslated_block_count=untranslated_block_count,
        translation_coverage_ratio=translation_coverage_ratio,
        untranslated_block_ids=untranslated_block_ids,
        glossary_term_count=glossary_term_count,
        missing_glossary_targets=missing_glossary_targets,
        markdown_risk_block_ids=markdown_risk_block_ids,
        overlong_translation_block_ids=overlong_translation_block_ids,
        warnings=warnings,
        errors=errors,
    )


def render_quality_report_json(report: BookMdQualityReport) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def render_quality_report_markdown(report: BookMdQualityReport) -> str:
    warnings = "\n".join(f"  - {warning}" for warning in report.warnings) or "  - none"
    errors = "\n".join(f"  - {error}" for error in report.errors) or "  - none"
    broken_assets = "\n".join(f"  - {asset}" for asset in report.broken_asset_references) or "  - none"
    missing_visual_assets = "\n".join(
        f"  - {block_id}" for block_id in report.missing_visual_asset_block_ids
    ) or "  - none"
    untranslated_blocks = "\n".join(f"  - {block_id}" for block_id in report.untranslated_block_ids) or "  - none"
    missing_terms = "\n".join(f"  - {term}" for term in report.missing_glossary_targets) or "  - none"
    markdown_risks = "\n".join(f"  - {block_id}" for block_id in report.markdown_risk_block_ids) or "  - none"
    overlong_translations = "\n".join(f"  - {block_id}" for block_id in report.overlong_translation_block_ids) or "  - none"
    return "\n".join(
        [
            "# BookMD Quality Report",
            "",
            f"- Path: {report.path}",
            f"- Valid: {str(report.valid).lower()}",
            f"- Title: {report.title}",
            f"- Chapters: {report.chapter_count}",
            f"- Empty chapters: {report.empty_chapter_count}",
            f"- Search items: {report.search_item_count}",
            f"- Source-map blocks: {report.source_map_block_count}",
            f"- Original PDF: {str(report.has_original_pdf).lower()}",
            f"- Cover visual: {str(report.has_cover).lower()}",
            f"- Assets: {report.asset_count}",
            f"- Referenced assets: {report.referenced_asset_count}",
            f"- Translation provider: {report.translation_provider}",
            f"- Translation blocks: {report.translation_block_count}",
            f"- Translated blocks: {report.translated_block_count}",
            f"- Translation coverage: {report.translation_coverage_ratio:.2%}",
            f"- Glossary terms: {report.glossary_term_count}",
            "",
            "## Broken Asset References",
            broken_assets,
            "",
            "## Missing Visual Assets",
            missing_visual_assets,
            "",
            "## Translation Gaps",
            untranslated_blocks,
            "",
            "## Missing Glossary Targets",
            missing_terms,
            "",
            "## Translation Markdown Risks",
            markdown_risks,
            "",
            "## Overlong Translations",
            overlong_translations,
            "",
            "## Warnings",
            warnings,
            "",
            "## Errors",
            errors,
            "",
        ]
    )


def _read_json(zf: zipfile.ZipFile, name: str) -> dict[str, Any]:
    if name not in zf.namelist():
        return {}
    try:
        payload = zf.read(name).decode("utf-8")
        data = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError):
        return {}
    return data if isinstance(data, dict) else {}


def _asset_references_from_chapter(chapter_path: str, chapter_text: str) -> set[str]:
    references: set[str] = set()
    for match in _MARKDOWN_ASSET_PATTERN.finditer(chapter_text):
        reference = match.group(1) or match.group(2) or ""
        if reference:
            references.add(reference)
    for match in _HTML_SRC_PATTERN.finditer(chapter_text):
        reference = next((value for value in match.groups() if value), "")
        if reference:
            references.add(reference)
    return {
        reference
        for reference in references
        if _asset_archive_path(reference).startswith("assets/")
    }


def _asset_archive_path(reference: str) -> str:
    cleaned = reference.split("#", 1)[0].split("?", 1)[0]
    if cleaned.startswith("file://"):
        cleaned = cleaned.removeprefix("file://")
    if cleaned.startswith("../assets/"):
        cleaned = cleaned.removeprefix("../")
    if cleaned.startswith("./assets/"):
        cleaned = cleaned.removeprefix("./")
    if cleaned.startswith("assets/"):
        return PurePosixPath(cleaned).as_posix()
    return PurePosixPath(cleaned).as_posix()


def _missing_source_pages(source_blocks: list[object]) -> set[int]:
    missing: set[int] = set()
    for block in source_blocks:
        if not isinstance(block, dict):
            continue
        page = block.get("source_page") or block.get("page")
        try:
            source_page = int(page)
        except (TypeError, ValueError):
            missing.add(0)
            continue
        if source_page < 1:
            missing.add(source_page)
    return missing


def _translation_metrics(translation: dict[str, Any], terms_payload: dict[str, Any]) -> dict[str, Any]:
    provider = str(translation.get("provider") or "")
    terms = terms_payload.get("terms")
    if not isinstance(terms, list):
        terms = []
    glossary_terms = [
        (str(term.get("source") or ""), str(term.get("target") or ""))
        for term in terms
        if isinstance(term, dict) and term.get("source") and term.get("target")
    ]
    if not provider:
        return {
            "provider": "",
            "block_count": 0,
            "translated_count": 0,
            "untranslated_block_ids": [],
            "glossary_term_count": len(glossary_terms),
            "missing_glossary_targets": [],
            "markdown_risk_block_ids": [],
            "overlong_translation_block_ids": [],
        }
    blocks = translation.get("blocks")
    if not isinstance(blocks, list):
        blocks = []

    translated_count = 0
    untranslated_block_ids: list[str] = []
    missing_glossary_targets: set[str] = set()
    markdown_risk_block_ids: list[str] = []
    overlong_translation_block_ids: list[str] = []

    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_id = str(block.get("block_id") or "")
        source_text = str(block.get("source_text") or "")
        translated_text = str(block.get("translated_text") or "")
        status = str(block.get("status") or "")
        is_translated = bool(translated_text) and status == "translated"
        if is_translated:
            translated_count += 1
        elif block_id:
            untranslated_block_ids.append(block_id)
        if source_text and translated_text:
            missing_glossary_targets.update(
                _missing_glossary_targets(source_text, translated_text, glossary_terms)
            )
            if _has_markdown_translation_risk(source_text, translated_text) and block_id:
                markdown_risk_block_ids.append(block_id)
            if _is_overlong_translation(source_text, translated_text) and block_id:
                overlong_translation_block_ids.append(block_id)

    return {
        "provider": provider,
        "block_count": len(blocks),
        "translated_count": translated_count,
        "untranslated_block_ids": sorted(untranslated_block_ids),
        "glossary_term_count": len(glossary_terms),
        "missing_glossary_targets": sorted(missing_glossary_targets),
        "markdown_risk_block_ids": sorted(markdown_risk_block_ids),
        "overlong_translation_block_ids": sorted(overlong_translation_block_ids),
    }


def _missing_glossary_targets(
    source_text: str,
    translated_text: str,
    glossary_terms: list[tuple[str, str]],
) -> set[str]:
    source_lower = source_text.lower()
    missing: set[str] = set()
    for source, target in glossary_terms:
        if source.lower() in source_lower and target not in translated_text:
            missing.add(f"{source} -> {target}")
    return missing


def _has_markdown_translation_risk(source_text: str, translated_text: str) -> bool:
    return (
        source_text.count("$$") != translated_text.count("$$")
        or source_text.count("```") != translated_text.count("```")
        or source_text.count("[") != translated_text.count("[")
        or source_text.count("]") != translated_text.count("]")
    )


def _is_overlong_translation(source_text: str, translated_text: str) -> bool:
    source_len = len(source_text.strip())
    translated_len = len(translated_text.strip())
    return source_len > 0 and translated_len > max(120, source_len * 3)
