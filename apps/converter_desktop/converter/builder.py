from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import uuid
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bookmd_core import package_directory, validate_bookmd
from bookmd_core.visuals import crop_image as _portable_crop_image
from bookmd_core.visuals import render_pdf_page as _portable_render_pdf_page
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


MEDIA_BLOCK_TYPES = {"figure", "formula", "table"}
GENERATED_ASSET_TYPES = {"figure", "formula", "table"}
_PDFKIT_CROP_SWIFT = r'''
import Foundation
import PDFKit
import AppKit

let args = CommandLine.arguments

func fail(_ message: String) -> Never {
    fputs(message + "\n", stderr)
    exit(1)
}

if args.count != 8 {
    fail("usage: crop_pdfkit.swift input.pdf output.png page x1 y1 x2 y2")
}

let input = URL(fileURLWithPath: args[1])
let output = URL(fileURLWithPath: args[2])
guard let pageNumber = Int(args[3]),
      let x1 = Double(args[4]),
      let y1 = Double(args[5]),
      let x2 = Double(args[6]),
      let y2 = Double(args[7]) else {
    fail("invalid crop arguments")
}

guard let document = PDFDocument(url: input) else {
    fail("failed to open pdf")
}
guard let page = document.page(at: max(0, pageNumber - 1)) else {
    fail("page not found")
}

let bounds = page.bounds(for: .mediaBox)
let scale = min(bounds.width / max(x2, 1.0), bounds.height / max(y2, 1.0))
let margin = 8.0
let left = max(0.0, x1 * scale - margin)
let top = max(0.0, y1 * scale - margin)
let right = min(bounds.width, x2 * scale + margin)
let bottom = min(bounds.height, y2 * scale + margin)
let cropWidth = right - left
let cropHeight = bottom - top
if cropWidth < 4 || cropHeight < 4 {
    fail("crop too small")
}

let image = NSImage(size: NSSize(width: cropWidth * 2.0, height: cropHeight * 2.0))
image.lockFocus()
guard let context = NSGraphicsContext.current?.cgContext else {
    fail("failed to create graphics context")
}
context.setFillColor(NSColor.white.cgColor)
context.fill(CGRect(x: 0, y: 0, width: cropWidth * 2.0, height: cropHeight * 2.0))
context.scaleBy(x: 2.0, y: 2.0)
context.translateBy(x: -left, y: -(bounds.height - bottom))
page.draw(with: .mediaBox, to: context)
image.unlockFocus()

guard let tiff = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiff),
      let data = bitmap.representation(using: .png, properties: [:]) else {
    fail("failed to encode png")
}
try data.write(to: output)
'''


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

    validation = validate_bookmd(options.output, strict=True)
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
    cover_asset_path = ""
    if _config_value(options, "output", "preserve_cover", True):
        cover_asset_path = _generate_cover_asset(options.source_pdf, staging / "assets")
    if _config_value(options, "output", "generate_block_assets", False):
        blocks = _generate_missing_block_assets(options.source_pdf, blocks, staging / "assets")
        chapters = _replace_chapter_blocks(chapters, blocks)

    chapter_by_block: dict[str, tuple[str, str]] = {}
    bilingual = bool(_config_value(options, "translation", "bilingual", False))
    for chapter in chapters:
        chapter_text = "\n".join(
            render_block_markdown(block, bilingual=bilingual)
            for block in chapter.blocks
        )
        if chapter.order == 1 and cover_asset_path:
            chapter_text = f"![Cover](../{cover_asset_path})\n\n{chapter_text}"
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


def _generate_cover_asset(source_pdf: Path, assets_root: Path) -> str:
    if not source_pdf.exists() or source_pdf.stat().st_size < 1024:
        return ""
    relative_path = "assets/cover/page_001.png"
    output_path = assets_root.parent / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bookmd-cover-render-") as temp_name:
        page_image = _render_pdf_page_image(source_pdf, 1, Path(temp_name))
        if page_image is None or not page_image.exists():
            return ""
        shutil.copy2(page_image, output_path)
    return relative_path if output_path.exists() else ""


def _replace_chapter_blocks(chapters: list[Chapter], blocks: list[OcrBlock]) -> list[Chapter]:
    block_by_id = {block.block_id: block for block in blocks}
    return [
        Chapter(
            chapter_id=chapter.chapter_id,
            title=chapter.title,
            path=chapter.path,
            order=chapter.order,
            blocks=[block_by_id.get(block.block_id, block) for block in chapter.blocks],
        )
        for chapter in chapters
    ]


def _generate_missing_block_assets(
    source_pdf: Path,
    blocks: list[OcrBlock],
    assets_root: Path,
    page_renderer: Callable[[Path, int, Path], Path | None] | None = None,
    image_cropper: Callable[[Path, list[float], Path], bool] | None = None,
) -> list[OcrBlock]:
    targets = [
        block for block in blocks
        if _needs_generated_asset(block)
    ]
    if not targets:
        return blocks
    if source_pdf.stat().st_size < 1024:
        return blocks
    assets_root.mkdir(parents=True, exist_ok=True)
    generated_root = assets_root / "generated"
    generated_root.mkdir(parents=True, exist_ok=True)
    updated: list[OcrBlock] = []
    with tempfile.TemporaryDirectory(prefix="bookmd-page-render-") as temp_name:
        work_dir = Path(temp_name)
        page_images: dict[int, Path | None] = {}
        renderer = page_renderer or _render_pdf_page_image
        cropper = image_cropper or _crop_page_image
        for block in blocks:
            if not _needs_generated_asset(block):
                updated.append(block)
                continue
            relative_path = f"assets/generated/page_{block.page:03d}_{_safe_asset_name(block.block_id)}.png"
            output_path = assets_root.parent / relative_path
            if block.page not in page_images:
                page_images[block.page] = renderer(source_pdf, block.page, work_dir)
            page_image = page_images[block.page]
            if page_image is not None and cropper(page_image, block.bbox, output_path):
                updated.append(_with_asset_path(block, relative_path))
                continue
            updated.append(block)
    return updated


def _needs_generated_asset(block: OcrBlock) -> bool:
    return (
        block.type.lower() in GENERATED_ASSET_TYPES
        and not block.asset_path
        and len(block.bbox) >= 4
    )


def _render_pdf_block_asset(
    source_pdf: Path,
    page: int,
    bbox: list[float],
    output_path: Path,
    work_dir: Path,
) -> Path | None:
    rendered = _crop_pdf_block_with_pdfkit(source_pdf, page, bbox, output_path, work_dir)
    if rendered:
        return rendered
    page_image = _render_pdf_page_image(source_pdf, page, work_dir)
    if page_image and _crop_page_image(page_image, bbox, output_path):
        return output_path
    return None


def _crop_pdf_block_with_pdfkit(
    source_pdf: Path,
    page: int,
    bbox: list[float],
    output_path: Path,
    work_dir: Path,
) -> Path | None:
    swift = shutil.which("swift")
    if not swift or len(bbox) < 4:
        return None
    work_dir.mkdir(parents=True, exist_ok=True)
    script = work_dir / "crop_pdfkit.swift"
    script.write_text(_PDFKIT_CROP_SWIFT, encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            [
                swift,
                str(script),
                str(source_pdf),
                str(output_path),
                str(page),
                *[str(value) for value in bbox[:4]],
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=8,
        )
    except subprocess.TimeoutExpired:
        return None
    if completed.returncode != 0 or not output_path.exists():
        return None
    return output_path


def _render_pdf_page_image(source_pdf: Path, page: int, work_dir: Path) -> Path | None:
    work_dir.mkdir(parents=True, exist_ok=True)
    portable_output = work_dir / f"page_{page:03d}.png"
    try:
        return _portable_render_pdf_page(source_pdf, page, portable_output, scale=2.0)
    except (OSError, RuntimeError, ValueError):
        pass

    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        return None
    prefix = work_dir / f"page_{page:03d}"
    try:
        completed = subprocess.run(
            [
                pdftoppm,
                "-f",
                str(page),
                "-l",
                str(page),
                "-singlefile",
                "-png",
                "-r",
                "144",
                str(source_pdf),
                str(prefix),
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=8,
        )
    except subprocess.TimeoutExpired:
        return None
    output = prefix.with_suffix(".png")
    if completed.returncode != 0 or not output.exists():
        return None
    return output


def _crop_page_image(page_image: Path, bbox: list[float], output_path: Path) -> bool:
    if _portable_crop_image(page_image, bbox, output_path):
        return True

    sips = shutil.which("sips")
    if not sips:
        return False
    image_size = _sips_image_size(sips, page_image)
    if image_size is None:
        return False
    crop_box = _crop_box(bbox, image_size)
    if crop_box is None:
        return False
    left, top, right, bottom = crop_box
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            [
                sips,
                "-c",
                str(bottom - top),
                str(right - left),
                "--cropOffset",
                str(top),
                str(left),
                str(page_image),
                "--out",
                str(output_path),
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return False
    return completed.returncode == 0 and output_path.exists()


def _sips_image_size(sips: str, image_path: Path) -> tuple[int, int] | None:
    try:
        completed = subprocess.run(
            [sips, "-g", "pixelWidth", "-g", "pixelHeight", str(image_path)],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return None
    if completed.returncode != 0:
        return None
    width: int | None = None
    height: int | None = None
    for line in completed.stdout.splitlines():
        if "pixelWidth:" in line:
            width = int(line.rsplit(":", 1)[1].strip())
        if "pixelHeight:" in line:
            height = int(line.rsplit(":", 1)[1].strip())
    if not width or not height:
        return None
    return width, height


def _crop_box(bbox: list[float], image_size: tuple[int, int]) -> tuple[int, int, int, int] | None:
    try:
        x1, y1, x2, y2 = [float(value) for value in bbox[:4]]
    except (TypeError, ValueError):
        return None
    if x2 <= x1 or y2 <= y1:
        return None
    width, height = image_size
    if x2 > width or y2 > height:
        scale = min(width / max(x2, 1), height / max(y2, 1))
        x1, y1, x2, y2 = x1 * scale, y1 * scale, x2 * scale, y2 * scale
    margin = 8
    left = max(0, int(x1) - margin)
    top = max(0, int(y1) - margin)
    right = min(width, int(x2) + margin)
    bottom = min(height, int(y2) + margin)
    if right - left < 4 or bottom - top < 4:
        return None
    return left, top, right, bottom


def _safe_asset_name(block_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", block_id).strip("_")
    return safe or "block"


def _with_asset_path(block: OcrBlock, asset_path: str) -> OcrBlock:
    return OcrBlock(
        block_id=block.block_id,
        page=block.page,
        type=block.type,
        bbox=block.bbox,
        text=block.text,
        level=block.level,
        asset_path=asset_path,
        latex=block.latex,
        markdown=block.markdown,
        caption=block.caption,
        translated_text=block.translated_text,
    )


def _book_manifest(
    options: BuildOptions,
    ocr_data: dict[str, Any],
    chapters: list[Chapter],
) -> dict[str, Any]:
    metadata = ocr_data.get("metadata") if isinstance(ocr_data.get("metadata"), dict) else {}
    title = metadata.get("title") or (chapters[0].title if chapters else "Untitled Book")
    return {
        "format_version": "1.0",
        "book_id": str(uuid.uuid5(uuid.NAMESPACE_URL, str(options.source_pdf.resolve()))),
        "title": title or "Untitled Book",
        "author": metadata.get("author") or "",
        "source_pdf": options.source_pdf.name,
        "language": _target_lang(options),
        "created_at": datetime.fromtimestamp(
            options.source_pdf.stat().st_mtime,
            tz=timezone.utc,
        ).isoformat(),
        "version": "1.0",
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
