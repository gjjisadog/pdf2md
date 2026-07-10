from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (
    ROOT / "apps/converter_desktop",
    ROOT / "packages/bookmd_core",
    ROOT / "packages/source_map_core",
    ROOT / "packages/translator_core",
):
    sys.path.insert(0, str(path))

from converter.quality import inspect_bookmd  # noqa: E402


DEFAULT_MANIFEST = ROOT / "docs/bookmd_benchmarks.json"
DEFAULT_OUTPUT = ROOT / "tmp/bookmd_benchmark_report.json"


def run_benchmarks(
    manifest_path: str | Path = DEFAULT_MANIFEST,
    output_path: str | Path = DEFAULT_OUTPUT,
    *,
    require_ready: bool = False,
) -> int:
    manifest_file = Path(manifest_path)
    output_file = Path(output_path)
    manifest = _read_json(manifest_file)
    samples = manifest.get("samples")
    if not isinstance(samples, list):
        samples = []

    rows = [_measure_sample(sample) for sample in samples if isinstance(sample, dict)]
    summary = _summary(rows)
    report = {
        "schema": "bookmd_benchmark_report_v1",
        "manifest": str(manifest_file),
        "samples": rows,
        "summary": summary,
    }
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    if require_ready and (summary["missing_count"] or summary["invalid_count"]):
        return 1
    return 0


def _measure_sample(sample: dict[str, Any]) -> dict[str, Any]:
    status = str(sample.get("status") or "pending")
    bookmd = str(sample.get("bookmd") or "")
    row = _base_row(sample)
    if status != "ready":
        row["status"] = "pending"
        return row

    resolved_bookmd = _resolve_path(bookmd)
    row["bookmd"] = str(resolved_bookmd)
    if not resolved_bookmd.exists():
        row["status"] = "missing"
        row["errors"] = ["ready benchmark artifact is missing"]
        return row

    quality = inspect_bookmd(resolved_bookmd)
    row.update(
        {
            "status": "measured",
            "title": quality.title,
            "valid": quality.valid,
            "chapter_count": quality.chapter_count,
            "empty_chapter_count": quality.empty_chapter_count,
            "search_item_count": quality.search_item_count,
            "source_map_block_count": quality.source_map_block_count,
            "has_original_pdf": quality.has_original_pdf,
            "has_cover": quality.has_cover,
            "asset_count": quality.asset_count,
            "referenced_asset_count": quality.referenced_asset_count,
            "warnings": quality.warnings,
            "errors": quality.errors,
        }
    )
    return row


def _base_row(sample: dict[str, Any]) -> dict[str, Any]:
    bookmd = str(sample.get("bookmd") or "")
    return {
        "id": str(sample.get("id") or ""),
        "label": str(sample.get("label") or ""),
        "document_type": str(sample.get("document_type") or ""),
        "status": "pending",
        "bookmd": str(_resolve_path(bookmd)) if bookmd else "",
        "notes": str(sample.get("notes") or ""),
        "title": "",
        "valid": None,
        "chapter_count": None,
        "empty_chapter_count": None,
        "search_item_count": None,
        "source_map_block_count": None,
        "has_original_pdf": None,
        "has_cover": None,
        "asset_count": None,
        "referenced_asset_count": None,
        "warnings": [],
        "errors": [],
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    measured = [row for row in rows if row["status"] == "measured"]
    return {
        "sample_count": len(rows),
        "measured_count": len(measured),
        "pending_count": sum(1 for row in rows if row["status"] == "pending"),
        "missing_count": sum(1 for row in rows if row["status"] == "missing"),
        "invalid_count": sum(1 for row in measured if row["valid"] is False),
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run BookMD benchmark quality reports.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args(argv)
    return run_benchmarks(args.manifest, args.output, require_ready=args.require_ready)


if __name__ == "__main__":
    raise SystemExit(main())
