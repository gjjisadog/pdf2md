from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from ocr_client import OcrApiConfig, OcrHttpClient, OcrJobClient, write_ocr_output


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


@dataclass(frozen=True)
class OcrBatch:
    path: Path
    first_page: int


def run_ocr(options: OcrOptions) -> Path:
    if not options.source_pdf.exists():
        raise FileNotFoundError(f"Source PDF does not exist: {options.source_pdf}")
    if options.batch_size > 0:
        return run_ocr_batches(options)
    client = _ocr_client_from_env()
    if hasattr(client, "parse_to_output"):
        return client.parse_to_output(options.source_pdf, options.output_dir)
    response = client.parse_pdf(options.source_pdf)
    return write_ocr_output(response, options.output_dir)


def run_ocr_batches(options: OcrOptions) -> Path:
    client = _ocr_client_from_env()
    with tempfile.TemporaryDirectory(prefix="bookmd-ocr-batches-") as temp_name:
        temp_root = Path(temp_name)
        batches = split_pdf_batches(
            options.source_pdf,
            options.batch_size,
            temp_root / "inputs",
            options.max_pages,
        )
        batch_outputs: list[tuple[OcrBatch, Path]] = []
        for index, batch in enumerate(batches, start=1):
            batch_output = temp_root / "outputs" / f"batch_{index:03d}"
            if hasattr(client, "parse_to_output"):
                client.parse_to_output(batch.path, batch_output)
            else:
                response = client.parse_pdf(batch.path)
                write_ocr_output(response, batch_output)
            batch_outputs.append((batch, batch_output))
        return merge_ocr_batch_outputs(batch_outputs, options.output_dir)


def split_pdf_batches(
    source_pdf: Path,
    batch_size: int,
    work_dir: Path,
    max_pages: int | None = None,
) -> list[OcrBatch]:
    if shutil.which("swift"):
        try:
            return _split_pdf_batches_with_pdfkit(source_pdf, batch_size, work_dir, max_pages)
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
    page_count = min(len(reader.pages), max_pages or len(reader.pages))
    for start in range(0, page_count, batch_size):
        writer = PdfWriter()
        for page in reader.pages[start : min(start + batch_size, page_count)]:
            writer.add_page(page)
        output = work_dir / f"batch_{len(batches) + 1:03d}.pdf"
        with output.open("wb") as handle:
            writer.write(handle)
        batches.append(OcrBatch(path=output, first_page=start + 1))
    return batches


def _split_pdf_batches_with_pdfkit(
    source_pdf: Path,
    batch_size: int,
    work_dir: Path,
    max_pages: int | None = None,
) -> list[OcrBatch]:
    work_dir.mkdir(parents=True, exist_ok=True)
    script = work_dir / "split_pdfkit.swift"
    script.write_text(_PDFKIT_SPLITTER_SWIFT, encoding="utf-8")
    page_count = min(_pdfkit_page_count(source_pdf, script), max_pages or 10**9)
    batches: list[OcrBatch] = []
    for first_page in range(1, page_count + 1, batch_size):
        output = work_dir / f"batch_{len(batches) + 1:03d}.pdf"
        pages_in_batch = min(batch_size, page_count - first_page + 1)
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
    (output_dir / "result.md").write_text("\n\n".join(markdown_parts).rstrip() + "\n", encoding="utf-8")
    (output_dir / "parse.log").write_text("\n".join(log_parts).rstrip() + "\n", encoding="utf-8")
    return output_dir


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


def check_ocr_health() -> dict[str, object]:
    client = _ocr_client_from_env()
    if not hasattr(client, "check_health"):
        return {"status": "unknown", "service": "direct-ocr"}
    return client.check_health()


def _ocr_client_from_env() -> OcrHttpClient | OcrJobClient:
    return OcrJobClient(OcrApiConfig.from_env())
