from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.error import URLError
import zipfile

from bookmd_core import validate_bookmd
from source_map_core import normalize_blocks
from translator_core import MissingApiKeyError
from ocr_client import MissingOcrConfigError, OcrApiError

from .builder import BuildOptions, ConverterError, build_bookmd
from .config import load_config
from .ocr_pipeline import OcrOptions, check_ocr_health, run_ocr
from .quality import inspect_bookmd, render_quality_report_json, render_quality_report_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="converter")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--source-pdf", required=True)
    build_parser.add_argument("--ocr-output", required=True)
    build_parser.add_argument("--output", required=True)
    build_parser.add_argument("--translate", default="false")
    build_parser.add_argument("--target-lang", default="zh")
    build_parser.add_argument("--provider", default="noop")
    build_parser.add_argument("--config")
    build_parser.add_argument("--generate-block-assets")

    ocr_parser = subparsers.add_parser("ocr")
    ocr_parser.add_argument("--source-pdf", required=True)
    ocr_parser.add_argument("--output-dir", required=True)
    ocr_parser.add_argument("--batch-size", type=int, default=0)
    ocr_parser.add_argument("--max-pages", type=int)
    ocr_parser.add_argument("--page-range")

    ocr_health_parser = subparsers.add_parser("ocr-health")
    ocr_health_parser.add_argument("--timeout", type=int)

    build_from_pdf_parser = subparsers.add_parser("build-from-pdf")
    build_from_pdf_parser.add_argument("--source-pdf", required=True)
    build_from_pdf_parser.add_argument("--ocr-output", required=True)
    build_from_pdf_parser.add_argument("--output", required=True)
    build_from_pdf_parser.add_argument("--translate", default="false")
    build_from_pdf_parser.add_argument("--target-lang", default="zh")
    build_from_pdf_parser.add_argument("--provider", default="noop")
    build_from_pdf_parser.add_argument("--config")
    build_from_pdf_parser.add_argument("--generate-block-assets")
    build_from_pdf_parser.add_argument("--batch-size", type=int, default=0)
    build_from_pdf_parser.add_argument("--max-pages", type=int)
    build_from_pdf_parser.add_argument("--page-range")

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("bookmd")

    quality_parser = subparsers.add_parser("quality-report")
    quality_parser.add_argument("bookmd")
    quality_parser.add_argument("--format", choices=["json", "markdown"], default="markdown")

    validate_ocr_parser = subparsers.add_parser("validate-ocr")
    validate_ocr_parser.add_argument("ocr_output")

    args = parser.parse_args(argv)

    try:
        if args.command == "build":
            output = build_bookmd(
                _build_options_from_args(args)
            )
            print(f"BookMD written: {output}")
            _print_build_summary(output)
            return 0
        if args.command == "ocr":
            output_dir = run_ocr(_ocr_options_from_args(args))
            print(f"OCR output written: {output_dir}")
            return 0
        if args.command == "ocr-health":
            print(json.dumps(check_ocr_health(timeout=_positive_int_or_none(args.timeout, "--timeout")), ensure_ascii=False))
            return 0
        if args.command == "build-from-pdf":
            run_ocr(_ocr_options_from_args(args))
            output = build_bookmd(_build_options_from_args(args))
            print(f"BookMD written: {output}")
            _print_build_summary(output)
            return 0
        if args.command == "validate":
            result = validate_bookmd(Path(args.bookmd))
            if result.valid:
                print(f"Valid BookMD: {args.bookmd}")
                return 0
            for error in result.errors:
                print(f"ERROR: {error}")
            return 1
        if args.command == "quality-report":
            report = inspect_bookmd(Path(args.bookmd))
            if args.format == "json":
                print(render_quality_report_json(report))
            else:
                print(render_quality_report_markdown(report))
            return 0 if report.valid else 1
        if args.command == "validate-ocr":
            result = _validate_ocr_output(Path(args.ocr_output))
            if result["errors"]:
                for error in result["errors"]:
                    print(f"ERROR: {error}")
                return 1
            print(
                "Valid OCR output: "
                f"pages={result['pages']} "
                f"blocks={result['blocks']} "
                f"source_map_blocks={result['source_map_blocks']}"
            )
            return 0
    except URLError as exc:
        print(_format_ocr_network_error(exc))
        return 1
    except (ConverterError, MissingApiKeyError, MissingOcrConfigError, OcrApiError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}")
        return 1

    return 1


def _build_options_from_args(args: argparse.Namespace) -> BuildOptions:
    config = load_config(args.config)
    generate_block_assets = getattr(args, "generate_block_assets", None)
    if generate_block_assets is not None:
        output_config = config.setdefault("output", {})
        if isinstance(output_config, dict):
            output_config["generate_block_assets"] = _parse_bool(generate_block_assets)
    target_lang = args.target_lang
    translation = config.get("translation")
    if isinstance(translation, dict):
        target_lang = str(translation.get("default_target_lang", target_lang))

    return BuildOptions(
        source_pdf=Path(args.source_pdf),
        ocr_output=Path(args.ocr_output),
        output=Path(args.output),
        translate=_parse_bool(args.translate),
        target_lang=target_lang,
        provider=args.provider,
        config=config,
    )


def _ocr_options_from_args(args: argparse.Namespace) -> OcrOptions:
    output_dir = getattr(args, "output_dir", None) or getattr(args, "ocr_output")
    return OcrOptions(
        source_pdf=Path(args.source_pdf),
        output_dir=Path(output_dir),
        batch_size=int(getattr(args, "batch_size", 0) or 0),
        max_pages=getattr(args, "max_pages", None),
        page_range=_parse_page_range(getattr(args, "page_range", None)),
    )


def _parse_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "y"}


def _parse_page_range(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    parts = value.split("-", 1)
    if len(parts) != 2:
        raise ConverterError("--page-range must use START-END syntax")
    try:
        start = int(parts[0])
        end = int(parts[1])
    except ValueError as exc:
        raise ConverterError("--page-range START and END must be integers") from exc
    if start < 1 or end < start:
        raise ConverterError("--page-range must satisfy START >= 1 and END >= START")
    return start, end


def _positive_int_or_none(value: int | None, name: str) -> int | None:
    if value is None:
        return None
    if value < 1:
        raise ConverterError(f"{name} must be greater than 0")
    return value


def _format_ocr_network_error(exc: URLError) -> str:
    api_url = os.getenv("OCR_API_URL", "<unset>")
    key_state = "configured" if os.getenv("OCR_API_KEY") else "not configured"
    reason = getattr(exc, "reason", exc)
    return (
        f"ERROR: OCR API unreachable: {reason}. "
        f"OCR_API_URL={api_url}; OCR_API_KEY is {key_state}. "
        "Check Tailscale/network, service health, and whether the OCR service is running."
    )


def _validate_ocr_output(ocr_output: Path) -> dict[str, object]:
    errors: list[str] = []
    required_files = ["result.md", "result.json", "source_map.json", "parse.log"]
    for filename in required_files:
        if not (ocr_output / filename).exists():
            errors.append(f"{filename} does not exist")
    if errors:
        return {"errors": errors, "pages": 0, "blocks": 0, "source_map_blocks": 0}

    try:
        result_json = json.loads((ocr_output / "result.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"result.json is not valid JSON: {exc}")
        return {"errors": errors, "pages": 0, "blocks": 0, "source_map_blocks": 0}
    try:
        source_map = json.loads((ocr_output / "source_map.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"source_map.json is not valid JSON: {exc}")
        return {"errors": errors, "pages": 0, "blocks": 0, "source_map_blocks": 0}

    blocks = normalize_blocks(result_json if isinstance(result_json, dict) else {})
    source_map_blocks = source_map.get("blocks") if isinstance(source_map, dict) else None
    if not isinstance(source_map_blocks, list):
        errors.append("source_map.json must contain blocks array")
        source_map_blocks = []
    if len(source_map_blocks) != len(blocks):
        errors.append(
            f"source_map blocks count {len(source_map_blocks)} does not match OCR blocks count {len(blocks)}"
        )
    elif _source_map_signature(source_map_blocks) != _ocr_blocks_signature(blocks):
        errors.append("source_map blocks do not align with OCR blocks")

    return {
        "errors": errors,
        "pages": _ocr_page_count(result_json if isinstance(result_json, dict) else {}),
        "blocks": len(blocks),
        "source_map_blocks": len(source_map_blocks),
    }


def _ocr_page_count(result_json: dict[str, object]) -> int:
    pages = result_json.get("pages")
    if isinstance(pages, list):
        return len(pages)
    blocks = normalize_blocks(result_json)
    return len({block.page for block in blocks})


def _ocr_blocks_signature(blocks: list[object]) -> list[tuple[str, int, tuple[object, ...], str]]:
    return [
        (block.block_id, block.page, tuple(block.bbox), block.text)
        for block in blocks
    ]


def _source_map_signature(blocks: list[object]) -> list[tuple[str, int, tuple[object, ...], str]]:
    signature: list[tuple[str, int, tuple[object, ...], str]] = []
    for block in blocks:
        if not isinstance(block, dict):
            signature.append(("", 0, (), ""))
            continue
        try:
            source_page = int(block.get("source_page") or block.get("page") or 1)
        except (TypeError, ValueError):
            source_page = 0
        signature.append(
            (
                str(block.get("block_id") or ""),
                source_page,
                tuple(block.get("bbox") or []),
                str(block.get("source_text") or ""),
            )
        )
    return signature


def _print_build_summary(output: Path) -> None:
    with zipfile.ZipFile(output) as zf:
        manifest = json.loads(zf.read("book.json"))
        source_map = json.loads(zf.read("source_map.json"))
        translation = json.loads(zf.read("translation.json"))
    chapters = manifest.get("chapters") or []
    blocks = source_map.get("blocks") or []
    translated = [
        item for item in translation.get("blocks") or []
        if item.get("status") == "translated"
    ]
    print(
        "Summary: "
        f"chapters={len(chapters)} "
        f"blocks={len(blocks)} "
        f"translated={len(translated)} "
        "warnings=0"
    )
