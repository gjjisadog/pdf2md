from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from bookmd_core import validate_bookmd
from translator_core import MissingApiKeyError
from ocr_client import MissingOcrConfigError, OcrApiError

from .builder import BuildOptions, ConverterError, build_bookmd
from .config import load_config
from .ocr_pipeline import OcrOptions, check_ocr_health, run_ocr


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

    ocr_parser = subparsers.add_parser("ocr")
    ocr_parser.add_argument("--source-pdf", required=True)
    ocr_parser.add_argument("--output-dir", required=True)
    ocr_parser.add_argument("--batch-size", type=int, default=0)
    ocr_parser.add_argument("--max-pages", type=int)

    subparsers.add_parser("ocr-health")

    build_from_pdf_parser = subparsers.add_parser("build-from-pdf")
    build_from_pdf_parser.add_argument("--source-pdf", required=True)
    build_from_pdf_parser.add_argument("--ocr-output", required=True)
    build_from_pdf_parser.add_argument("--output", required=True)
    build_from_pdf_parser.add_argument("--translate", default="false")
    build_from_pdf_parser.add_argument("--target-lang", default="zh")
    build_from_pdf_parser.add_argument("--provider", default="noop")
    build_from_pdf_parser.add_argument("--config")
    build_from_pdf_parser.add_argument("--batch-size", type=int, default=0)
    build_from_pdf_parser.add_argument("--max-pages", type=int)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("bookmd")

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
            print(json.dumps(check_ocr_health(), ensure_ascii=False))
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
    except (ConverterError, MissingApiKeyError, MissingOcrConfigError, OcrApiError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}")
        return 1

    return 1


def _build_options_from_args(args: argparse.Namespace) -> BuildOptions:
    config = load_config(args.config)
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
    )


def _parse_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "y"}


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
