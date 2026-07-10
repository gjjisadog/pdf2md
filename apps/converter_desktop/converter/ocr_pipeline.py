from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

from ocr_client import OcrApiConfig, OcrHttpClient, OcrJobClient, write_ocr_output
from source_map_core import build_source_map, normalize_blocks

from .markdown import render_block_markdown


_PDFKIT_SPLITTER_SWIFT = r'''
import Foundation
import PDFKit

let args = CommandLine.arguments

func fail(_ message: String) -> Never {
    fputs(message + "\n", stderr)
    exit(1)
}

if args.count < 3 {
    fail("usage: split_pdfkit.swift count input.pdf | split input.pdf output.pdf first_page count")
}

let command = args[1]

if command == "count" {
    let input = URL(fileURLWithPath: args[2])
    guard let source = PDFDocument(url: input) else {
        fail("failed to open pdf")
    }
    print(source.pageCount)
} else if command == "split" {
    if args.count != 6 {
        fail("usage: split input.pdf output.pdf first_page count")
    }
    let input = URL(fileURLWithPath: args[2])
    let output = URL(fileURLWithPath: args[3])
    guard let first = Int(args[4]), let count = Int(args[5]) else {
        fail("invalid page range")
    }
    guard let source = PDFDocument(url: input) else {
        fail("failed to open pdf")
    }
    let target = PDFDocument()
    let startIndex = max(0, first - 1)
    let endIndex = min(source.pageCount, startIndex + count)
    for index in startIndex..<endIndex {
        if let page = source.page(at: index) {
            target.insert(page, at: target.pageCount)
        }
    }
    if target.pageCount == 0 {
        fail("no pages selected")
    }
    if !target.write(to: output) {
        fail("failed to write pdf")
    }
} else {
    fail("unknown command")
}
'''


@dataclass(frozen=True)
class OcrOptions:
    source_pdf: Path
    output_dir: Path
    batch_size: int = 0
    max_pages: int | None = None
    page_range: tuple[int, int] | None = None


@dataclass(frozen=True)
class OcrBatch:
    path: Path
    first_page: int


def run_ocr(options: OcrOptions) -> Path:
    if not options.source_pdf.exists():
        raise FileNotFoundError(f"Source PDF does not exist: {options.source_pdf}")
    if options.batch_size > 0 or options.page_range:
        return run_ocr_batches(options)
    client = _ocr_client_from_env()
    if hasattr(client, "parse_to_output"):
        return client.parse_to_output(options.source_pdf, options.output_dir)
    response = client.parse_pdf(options.source_pdf)
    return write_ocr_output(response, options.output_dir)


def run_ocr_batches(options: OcrOptions) -> Path:
    client = _ocr_client_from_env()
    batch_size = _effective_batch_size(options)
    batch_input_dir = options.output_dir / "batch_inputs"
    batch_output_root = options.output_dir / "batches"
    batches = split_pdf_batches(
        options.source_pdf,
        batch_size,
        batch_input_dir,
        options.max_pages,
        options.page_range,
    )
    batch_output_root.mkdir(parents=True, exist_ok=True)
    manifest_entries = _batch_manifest_entries(batches, batch_output_root)
    _write_batch_manifest(options.output_dir, options, manifest_entries)
    batch_outputs: list[tuple[OcrBatch, Path]] = []
    for index, batch in enumerate(batches, start=1):
        batch_output = batch_output_root / f"batch_{index:03d}"
        entry = manifest_entries[index - 1]
        if _batch_output_complete(batch_output):
            entry["status"] = "succeeded"
            entry.pop("error", None)
            batch_outputs.append((batch, batch_output))
            _write_batch_manifest(options.output_dir, options, manifest_entries)
            continue
        entry["status"] = "running"
        entry.pop("error", None)
        _write_batch_manifest(options.output_dir, options, manifest_entries)
        try:
            if hasattr(client, "parse_to_output"):
                client.parse_to_output(batch.path, batch_output)
            else:
                response = client.parse_pdf(batch.path)
                write_ocr_output(response, batch_output)
        except Exception as exc:
            entry["status"] = "failed"
            entry["error"] = str(exc)
            _write_batch_manifest(options.output_dir, options, manifest_entries)
            raise
        entry["status"] = "succeeded"
        entry.pop("error", None)
        batch_outputs.append((batch, batch_output))
        _write_batch_manifest(options.output_dir, options, manifest_entries)
    return merge_ocr_batch_outputs(batch_outputs, options.output_dir)


def split_pdf_batches(
    source_pdf: Path,
    batch_size: int,
    work_dir: Path,
    max_pages: int | None = None,
    page_range: tuple[int, int] | None = None,
) -> list[OcrBatch]:
    if shutil.which("swift"):
        try:
            return _split_pdf_batches_with_pdfkit(source_pdf, batch_size, work_dir, max_pages, page_range)
        except RuntimeError:
            pass
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise RuntimeError(
            "Batch OCR requires macOS Swift/PDFKit or pypdf to split PDFs. Install pypdf or provide pre-split input."
        ) from exc

    work_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(source_pdf))
    batches: list[OcrBatch] = []
    first_page, last_page = _selected_page_bounds(len(reader.pages), max_pages, page_range)
    for start_page in range(first_page, last_page + 1, batch_size):
        writer = PdfWriter()
        end_page = min(start_page + batch_size - 1, last_page)
        for page_index in range(start_page - 1, end_page):
            writer.add_page(reader.pages[page_index])
        output = work_dir / f"batch_{len(batches) + 1:03d}.pdf"
        with output.open("wb") as handle:
            writer.write(handle)
        batches.append(OcrBatch(path=output, first_page=start_page))
    return batches


def _split_pdf_batches_with_pdfkit(
    source_pdf: Path,
    batch_size: int,
    work_dir: Path,
    max_pages: int | None = None,
    page_range: tuple[int, int] | None = None,
) -> list[OcrBatch]:
    work_dir.mkdir(parents=True, exist_ok=True)
    script = work_dir / "split_pdfkit.swift"
    script.write_text(_PDFKIT_SPLITTER_SWIFT, encoding="utf-8")
    first_page, last_page = _selected_page_bounds(_pdfkit_page_count(source_pdf, script), max_pages, page_range)
    batches: list[OcrBatch] = []
    for first_page in range(first_page, last_page + 1, batch_size):
        output = work_dir / f"batch_{len(batches) + 1:03d}.pdf"
        pages_in_batch = min(batch_size, last_page - first_page + 1)
        completed = subprocess.run(
            [
                "swift",
                str(script),
                "split",
                str(source_pdf),
                str(output),
                str(first_page),
                str(pages_in_batch),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
        batches.append(OcrBatch(path=output, first_page=first_page))
    return batches


def _selected_page_bounds(
    total_pages: int,
    max_pages: int | None = None,
    page_range: tuple[int, int] | None = None,
) -> tuple[int, int]:
    if total_pages < 1:
        raise RuntimeError("PDF contains no pages")
    if page_range:
        first_page, requested_last_page = page_range
    else:
        first_page, requested_last_page = 1, total_pages
    if first_page < 1 or requested_last_page < first_page:
        raise ValueError("page range must be in START-END form with START >= 1 and END >= START")
    last_page = min(requested_last_page, total_pages)
    if max_pages is not None:
        if max_pages < 1:
            raise ValueError("max_pages must be greater than 0")
        last_page = min(last_page, first_page + max_pages - 1)
    if first_page > total_pages:
        raise ValueError(f"page range starts after the PDF ends: start={first_page}, total_pages={total_pages}")
    return first_page, last_page


def _pdfkit_page_count(source_pdf: Path, script: Path) -> int:
    completed = subprocess.run(
        ["swift", str(script), "count", str(source_pdf)],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return int(completed.stdout.strip())


def merge_ocr_batch_outputs(batch_outputs: list[tuple[OcrBatch, Path]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "assets").mkdir(exist_ok=True)
    pages: list[dict[str, Any]] = []
    markdown_parts: list[str] = []
    log_parts: list[str] = []
    for index, (batch, batch_output) in enumerate(batch_outputs, start=1):
        result_json = json.loads((batch_output / "result.json").read_text(encoding="utf-8"))
        pages.extend(_globalized_pages(result_json, batch.first_page))
        result_md = batch_output / "result.md"
        if result_md.exists():
            markdown_parts.append(result_md.read_text(encoding="utf-8"))
        parse_log = batch_output / "parse.log"
        if parse_log.exists():
            log_parts.append(f"--- batch {index} first_page={batch.first_page} file={batch.path.name} ---\n{parse_log.read_text(encoding='utf-8')}")
    merged = {"metadata": {}, "pages": pages}
    (output_dir / "result.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_ocr_source_map(output_dir, merged)
    (output_dir / "result.md").write_text(_merged_markdown(merged, markdown_parts), encoding="utf-8")
    (output_dir / "parse.log").write_text("\n".join(log_parts).rstrip() + "\n", encoding="utf-8")
    return output_dir


def _merged_markdown(result_json: dict[str, Any], fallback_parts: list[str]) -> str:
    blocks = normalize_blocks(result_json)
    if not blocks:
        return "\n\n".join(fallback_parts).rstrip() + "\n"
    return "\n".join(render_block_markdown(block).rstrip() for block in blocks).rstrip() + "\n"


def _write_ocr_source_map(output_dir: Path, result_json: dict[str, Any]) -> None:
    blocks = normalize_blocks(result_json)
    source_map = build_source_map(blocks, {})
    (output_dir / "source_map.json").write_text(
        json.dumps(source_map, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _batch_manifest_entries(batches: list[OcrBatch], batch_output_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for index, batch in enumerate(batches, start=1):
        batch_output = batch_output_root / f"batch_{index:03d}"
        entries.append(
            {
                "index": index,
                "first_page": batch.first_page,
                "input": batch.path.name,
                "output": str(batch_output.relative_to(batch_output_root.parent)),
                "status": "succeeded" if _batch_output_complete(batch_output) else "pending",
            }
        )
    return entries


def _batch_output_complete(batch_output: Path) -> bool:
    result_json = batch_output / "result.json"
    if not result_json.exists():
        return False
    if not (batch_output / "result.md").exists():
        return False
    if not (batch_output / "parse.log").exists():
        return False
    try:
        json.loads(result_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return True


def _write_batch_manifest(output_dir: Path, options: OcrOptions, entries: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source_pdf": str(options.source_pdf),
        "batch_size": _effective_batch_size(options),
        "max_pages": options.max_pages,
        "page_range": list(options.page_range) if options.page_range else None,
        "batches": entries,
    }
    (output_dir / "batch_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _effective_batch_size(options: OcrOptions) -> int:
    if options.batch_size > 0:
        return options.batch_size
    if options.page_range:
        first_page, last_page = options.page_range
        selected_pages = last_page - first_page + 1
        if options.max_pages is not None:
            selected_pages = min(selected_pages, options.max_pages)
        return max(1, selected_pages)
    return options.batch_size


def _globalized_pages(result_json: dict[str, Any], first_page: int) -> list[dict[str, Any]]:
    if isinstance(result_json.get("pages"), list):
        raw_pages = result_json["pages"]
    else:
        raw_pages = [{"page_index": 1, "blocks": result_json.get("blocks") or []}]
    pages: list[dict[str, Any]] = []
    for local_index, raw_page in enumerate(raw_pages, start=1):
        if not isinstance(raw_page, dict):
            continue
        global_page = first_page + local_index - 1
        blocks = []
        block_index = 1
        for block in raw_page.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            normalized = dict(block)
            normalized["block_id"] = f"p{global_page:03d}_b{block_index:03d}"
            blocks.append(normalized)
            block_index += 1
        page = dict(raw_page)
        page["page_index"] = global_page
        page["blocks"] = blocks
        pages.append(page)
    return pages


def check_ocr_health(timeout: int | None = None) -> dict[str, object]:
    client = _ocr_client_from_env(timeout=timeout)
    if not hasattr(client, "check_health"):
        return {"status": "unknown", "service": "direct-ocr"}
    return client.check_health()


def _ocr_client_from_env(timeout: int | None = None) -> OcrHttpClient | OcrJobClient:
    return OcrJobClient(OcrApiConfig.from_env(timeout=timeout))
