from __future__ import annotations

import json
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bookmd_core import package_directory, validate_bookmd
from source_map_core import OcrBlock, build_source_map, normalize_blocks
from translator_core import (
    DeepSeekConfig,
    DeepSeekTranslator,
    NoopTranslator,
    TranslationBlock,
    TranslationCacheStore,
    TranslationResult,
    extract_terms,
    translation_cache_key,
)

from .chapters import Chapter, build_chapters
from .markdown import render_block_markdown


class ConverterError(RuntimeError):
    pass


@dataclass(frozen=True)
class BuildOptions:
    source_pdf: Path
    ocr_output: Path
    output: Path
    translate: bool = False
    target_lang: str = "zh"
    provider: str = "noop"
    config: dict[str, Any] | None = None


def build_bookmd(options: BuildOptions) -> Path:
    _validate_inputs(options)

    try:
        data = json.loads((options.ocr_output / "result.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConverterError(f"result.json is not valid JSON: {exc}") from exc
    blocks = normalize_blocks(data)
    if not blocks:
        raise ConverterError("OCR result contains no blocks")

    blocks = _apply_translation(blocks, options)
    chapters = build_chapters(blocks)

    with tempfile.TemporaryDirectory(prefix="bookmd-build-") as temp_name:
        staging = Path(temp_name)
        _write_book_directory(staging, options, data, blocks, chapters)
        package_directory(staging, options.output)

    validation = validate_bookmd(options.output)
    if not validation.valid:
        raise ConverterError("; ".join(validation.errors))
    return options.output


def _validate_inputs(options: BuildOptions) -> None:
    if not options.source_pdf.exists():
        raise ConverterError(f"Source PDF does not exist: {options.source_pdf}")
    if not options.ocr_output.exists():
        raise ConverterError(f"OCR output directory does not exist: {options.ocr_output}")
    if not (options.ocr_output / "result.json").exists():
        raise ConverterError(f"result.json does not exist: {options.ocr_output / 'result.json'}")
    if not (options.ocr_output / "result.md").exists():
        raise ConverterError(f"result.md does not exist: {options.ocr_output / 'result.md'}")


def _apply_translation(blocks: list[OcrBlock], options: BuildOptions) -> list[OcrBlock]:
    if not options.translate:
        return blocks

    translator = _translator_for_options(options)
    target_lang = _target_lang(options)
    cache_store = _translation_cache_store(options)
    terms = extract_terms(block.text for block in blocks)
    pending: list[TranslationBlock] = []
    source_by_id: dict[str, TranslationBlock] = {}
    translated_by_id: dict[str, str] = {}

    for block in blocks:
        if not block.text:
            continue
        translation_block = TranslationBlock(block_id=block.block_id, text=block.text)
        source_by_id[block.block_id] = translation_block
        cache_key = translation_cache_key(options.provider, target_lang, block.text)
        cached = cache_store.read(cache_key) if cache_store else None
        if cached:
            translated_by_id[block.block_id] = cached.translated_text
        else:
            pending.append(translation_block)

    if pending:
        results = _translate_pending(translator, pending, target_lang, terms)
        for result in results:
            translated_by_id[result.block_id] = result.translated_text
            if cache_store and result.block_id in source_by_id:
                block = source_by_id[result.block_id]
                cache_store.write(
                    key=translation_cache_key(options.provider, target_lang, block.text),
                    block=block,
                    translated_text=result.translated_text,
                    provider=options.provider,
                    target_lang=target_lang,
                )

    return [
        OcrBlock(
            block_id=block.block_id,
            page=block.page,
            type=block.type,
            bbox=block.bbox,
            text=block.text,
            level=block.level,
            asset_path=block.asset_path,
            latex=block.latex,
            markdown=block.markdown,
            caption=block.caption,
            translated_text=translated_by_id.get(block.block_id),
        )
        for block in blocks
    ]


def _translator_for_options(options: BuildOptions) -> object:
    if options.provider == "noop":
        return NoopTranslator()
    if options.provider == "deepseek":
        return DeepSeekTranslator(DeepSeekConfig.from_env())
    raise ConverterError(f"Unsupported translation provider: {options.provider}")


def _translate_pending(
    translator: object,
    pending: list[TranslationBlock],
    target_lang: str,
    terms: list[dict[str, str]],
) -> list[TranslationResult]:
    if isinstance(translator, DeepSeekTranslator):
        return translator.translate_blocks(pending, target_lang, terms=terms)
    translate_blocks = getattr(translator, "translate_blocks")
    return translate_blocks(pending, target_lang)


def _write_book_directory(
    staging: Path,
    options: BuildOptions,
    ocr_data: dict[str, Any],
    blocks: list[OcrBlock],
    chapters: list[Chapter],
) -> None:
    (staging / "chapters").mkdir(parents=True)
    (staging / "assets").mkdir(parents=True)
    (staging / "source").mkdir(parents=True)

    assets_source = options.ocr_output / "assets"
    if assets_source.exists():
        shutil.copytree(assets_source, staging / "assets", dirs_exist_ok=True)
    if _config_value(options, "output", "save_original_pdf", True):
        shutil.copy2(options.source_pdf, staging / "source" / "original.pdf")

    chapter_by_block: dict[str, tuple[str, str]] = {}
    bilingual = bool(_config_value(options, "translation", "bilingual", False))
    for chapter in chapters:
        chapter_text = "\n".join(
            render_block_markdown(block, bilingual=bilingual)
            for block in chapter.blocks
        )
        chapter_path = staging / chapter.path
        chapter_path.parent.mkdir(parents=True, exist_ok=True)
        chapter_path.write_text(chapter_text, encoding="utf-8")
        for block in chapter.blocks:
            chapter_by_block[block.block_id] = (chapter.chapter_id, chapter.path)

    _write_json(staging / "book.json", _book_manifest(options, ocr_data, chapters))
    _write_json(staging / "source_map.json", build_source_map(blocks, chapter_by_block))
    _write_json(staging / "terms.json", {"terms": extract_terms(block.text for block in blocks)})
    _write_json(staging / "translation.json", _translation_payload(blocks, options))
    _write_json(staging / "reading_config.json", _reading_config(options))
    _write_json(staging / "search_index.json", _search_index(blocks, chapter_by_block, chapters))


def _book_manifest(
    options: BuildOptions,
    ocr_data: dict[str, Any],
    chapters: list[Chapter],
) -> dict[str, Any]:
    metadata = ocr_data.get("metadata") if isinstance(ocr_data.get("metadata"), dict) else {}
    title = metadata.get("title") or (chapters[0].title if chapters else "Untitled Book")
    return {
        "book_id": str(uuid.uuid5(uuid.NAMESPACE_URL, str(options.source_pdf.resolve()))),
        "title": title or "Untitled Book",
        "author": metadata.get("author") or "",
        "source_pdf": options.source_pdf.name,
        "language": _target_lang(options),
        "created_at": datetime.fromtimestamp(
            options.source_pdf.stat().st_mtime,
            tz=timezone.utc,
        ).isoformat(),
        "version": "0.1",
        "chapters": [
            {
                "id": chapter.chapter_id,
                "title": chapter.title,
                "path": chapter.path,
                "order": chapter.order,
            }
            for chapter in chapters
        ],
    }


def _translation_payload(blocks: list[OcrBlock], options: BuildOptions) -> dict[str, Any]:
    target_lang = _target_lang(options)
    provider = options.provider if options.translate else ""
    model = _translation_model(options)
    return {
        "provider": provider,
        "model": model,
        "target_lang": target_lang,
        "blocks": [
            {
                "block_id": block.block_id,
                "source_text": block.text,
                "translated_text": block.translated_text or "",
                "provider": provider,
                "model": model,
                "status": "translated" if block.translated_text else "source",
                "cache_key": translation_cache_key(options.provider, target_lang, block.text)
                if options.translate and block.text
                else "",
                "error": "",
            }
            for block in blocks
            if block.text or block.translated_text
        ]
    }


def _reading_config(options: BuildOptions) -> dict[str, Any]:
    return {
        "default_mode": "zh",
        "layout": _config_value(options, "reading", "layout", "paged"),
        "font_size": _config_value(options, "reading", "font_size", 18),
        "line_height": _config_value(options, "reading", "line_height", 1.75),
        "theme": _config_value(options, "reading", "theme", "light"),
        "paragraph_indent": True,
    }


def _search_index(
    blocks: list[OcrBlock],
    chapter_by_block: dict[str, tuple[str, str]],
    chapters: list[Chapter],
) -> dict[str, list[dict[str, Any]]]:
    title_by_id = {chapter.chapter_id: chapter.title for chapter in chapters}
    items: list[dict[str, Any]] = []
    for block in blocks:
        text = block.translated_text or block.text
        if not text:
            continue
        chapter_id, _ = chapter_by_block.get(block.block_id, ("", ""))
        items.append(
            {
                "block_id": block.block_id,
                "chapter_id": chapter_id,
                "chapter_path": chapter_by_block.get(block.block_id, ("", ""))[1],
                "chapter_title": title_by_id.get(chapter_id, ""),
                "type": block.type,
                "text": text,
            }
        )
    return {"items": items}


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _target_lang(options: BuildOptions) -> str:
    return str(
        _config_value(
            options,
            "translation",
            "default_target_lang",
            options.target_lang,
        )
    )


def _translation_model(options: BuildOptions) -> str:
    if not options.translate:
        return ""
    if options.provider == "deepseek":
        return str(_config_value(options, "translation", "model", "deepseek-v4-flash"))
    if options.provider == "noop" and options.translate:
        return "noop"
    return ""


def _translation_cache_store(options: BuildOptions) -> TranslationCacheStore | None:
    if not bool(_config_value(options, "translation", "cache", True)):
        return None
    if not bool(_config_value(options, "translation", "cache_enabled", True)):
        return None
    configured_path = _config_value(options, "translation", "cache_path", "")
    cache_path = Path(configured_path) if configured_path else options.ocr_output / ".bookmd_translation_cache.jsonl"
    return TranslationCacheStore(cache_path)


def _config_value(
    options: BuildOptions,
    section: str,
    key: str,
    default: Any,
) -> Any:
    config = options.config or {}
    section_data = config.get(section)
    if isinstance(section_data, dict) and key in section_data:
        return section_data[key]
    return default
