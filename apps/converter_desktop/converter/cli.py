from __future__ import annotations

import argparse
from pathlib import Path

from bookmd_core import validate_bookmd
from translator_core import MissingApiKeyError

from .builder import BuildOptions, ConverterError, build_bookmd


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

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("bookmd")

    args = parser.parse_args(argv)

    try:
        if args.command == "build":
            output = build_bookmd(
                BuildOptions(
                    source_pdf=Path(args.source_pdf),
                    ocr_output=Path(args.ocr_output),
                    output=Path(args.output),
                    translate=_parse_bool(args.translate),
                    target_lang=args.target_lang,
                    provider=args.provider,
                )
            )
            print(f"BookMD written: {output}")
            return 0
        if args.command == "validate":
            result = validate_bookmd(Path(args.bookmd))
            if result.valid:
                print(f"Valid BookMD: {args.bookmd}")
                return 0
            for error in result.errors:
                print(f"ERROR: {error}")
            return 1
    except (ConverterError, MissingApiKeyError) as exc:
        print(f"ERROR: {exc}")
        return 1

    return 1


def _parse_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "y"}
