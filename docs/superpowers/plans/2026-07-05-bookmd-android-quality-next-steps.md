# BookMD Android Quality Next Steps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the remaining BookMD quality and Android reader verification work needed before using the converter/reader as a dependable personal technical-book workflow.

**Architecture:** Keep BookMD quality measurement in the converter layer, Android runtime verification in `scripts/verify_android_reader.py`, and acceptance evidence in docs. Do not mix OCR service deployment or translation-provider integration into this plan; those are separate workstreams.

**Tech Stack:** Python 3.12, pytest, BookMD zip format, Android Gradle project, ADB device smoke tests, existing converter quality-report command.

---

## File Structure

- Create: `docs/bookmd_benchmarks.json`
  - Owns benchmark sample metadata, expected artifact paths, document type, and readiness state.
- Create: `scripts/run_bookmd_benchmarks.py`
  - Reads benchmark metadata, runs `inspect_bookmd` on ready `.bookmd` artifacts, records missing samples as pending, and writes a JSON summary.
- Create: `tests/test_bookmd_benchmarks.py`
  - Verifies benchmark metadata parsing, pending-sample behavior, quality-report aggregation, and strict failure mode.
- Modify: `docs/phase9.md`
  - Updates P2 benchmark status and the remaining Android visual-asset runtime gate.
- Modify: `docs/final_acceptance.md`
  - Adds benchmark report evidence and distinguishes static verification from device verification.
- Modify: `docs/android_reader_usage.md`
  - Adds the exact visual-asset smoke command and expected device prerequisites.
- Modify: `docs/release_checklist.md`
  - Makes benchmark report and Android visual-asset smoke explicit release gates.

## P0 Task 1: Run Real Android Visual-Asset Device Smoke

**Purpose:** Prove that the generated `assets/generated/...` figure/formula/table images are actually reachable and zoomable in the Android reader, not only packaged correctly.

- [x] **Step 1: Confirm device connectivity**

Run:

```bash
ANDROID_HOME=/opt/homebrew/share/android-commandlinetools \
ANDROID_SDK_ROOT=/opt/homebrew/share/android-commandlinetools \
PATH=/opt/homebrew/share/android-commandlinetools/platform-tools:$PATH \
adb devices
```

Expected: at least one row ending with `device`.

- [x] **Step 2: Run the existing full Android visual-asset smoke**

Run:

```bash
ANDROID_HOME=/opt/homebrew/share/android-commandlinetools \
ANDROID_SDK_ROOT=/opt/homebrew/share/android-commandlinetools \
PATH=/opt/homebrew/share/android-commandlinetools/platform-tools:$PATH \
PYTHONDONTWRITEBYTECODE=1 \
python scripts/verify_android_reader.py \
  --device-smoke \
  --bookmd tmp/real_book_full_clean_text_visual.bookmd \
  --verify-visual-asset \
  --search-term DC-DC \
  --artifacts-dir tmp/android_reader_verify_visual_asset
```

Expected: script exits `0`, opens `ImageViewerActivity`, exposes a WebView, returns to `ReaderActivity`, and still passes source-map/PDF-page trace.

- [x] **Step 3: Record the result**

Update `docs/final_acceptance.md` Android visual-asset row from “device execution pending” to “device verified” only if Step 2 passes. If it fails, keep the row pending and record the artifact directory path plus the exact failing assertion.

## P0 Task 2: Add Multi-Book Benchmark Harness

**Purpose:** Make quality trends measurable across more than the current DC-DC book.

- [x] **Step 1: Write failing benchmark tests**

Create `tests/test_bookmd_benchmarks.py` with tests for:

```python
def test_benchmark_runner_reports_ready_and_pending_samples(tmp_path):
    ...

def test_benchmark_runner_fails_strict_mode_when_ready_sample_is_missing(tmp_path):
    ...
```

Expected behavior:

- A ready sample with an existing `.bookmd` returns `status="measured"` and includes quality metrics.
- A pending or missing sample returns `status="pending"` or `status="missing"` without failing default mode.
- `--require-ready` returns non-zero when a ready sample path is missing.

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 \
python -m pytest tests/test_bookmd_benchmarks.py -q
```

Expected: fails because the runner does not exist yet.

- [x] **Step 2: Add benchmark metadata**

Create `docs/bookmd_benchmarks.json` with these entries:

```json
{
  "schema": "bookmd_benchmark_manifest_v1",
  "samples": [
    {
      "id": "dc_dc_textbook",
      "label": "DC-DC converter textbook",
      "document_type": "power_electronics_textbook",
      "status": "ready",
      "bookmd": "tmp/real_book_full_clean_text_visual.bookmd",
      "notes": "Real technical-book sample with cover, formulas, figures, source map, and generated visual assets."
    },
    {
      "id": "scanned_low_quality",
      "label": "Scanned low-quality PDF",
      "document_type": "scanned_low_quality_pdf",
      "status": "pending",
      "bookmd": "tmp/benchmarks/scanned_low_quality.bookmd",
      "notes": "Add after selecting a representative scanned document."
    },
    {
      "id": "formula_paper",
      "label": "Formula-heavy paper",
      "document_type": "formula_heavy_paper",
      "status": "pending",
      "bookmd": "tmp/benchmarks/formula_paper.bookmd",
      "notes": "Add after selecting a paper with dense equations."
    },
    {
      "id": "table_manual",
      "label": "Table-heavy manual",
      "document_type": "table_heavy_manual",
      "status": "pending",
      "bookmd": "tmp/benchmarks/table_manual.bookmd",
      "notes": "Add after selecting a manual or datasheet with dense tables."
    }
  ]
}
```

- [x] **Step 3: Implement benchmark runner**

Create `scripts/run_bookmd_benchmarks.py` with:

- CLI args: `--manifest`, `--output`, `--require-ready`.
- Default manifest: `docs/bookmd_benchmarks.json`.
- Default output: `tmp/bookmd_benchmark_report.json`.
- Import `inspect_bookmd` from `apps/converter_desktop/converter/quality.py`.
- Output schema: `bookmd_benchmark_report_v1`.
- Per-sample fields: `id`, `label`, `document_type`, `status`, `bookmd`, `valid`, `chapter_count`, `search_item_count`, `source_map_block_count`, `has_cover`, `asset_count`, `referenced_asset_count`, `warnings`, `errors`.
- Exit code `0` by default even when pending samples exist.
- Exit code `1` with `--require-ready` when any `status="ready"` sample is missing or invalid.

- [x] **Step 4: Verify benchmark tests pass**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 \
python -m pytest tests/test_bookmd_benchmarks.py -q
```

Expected: all benchmark tests pass.

- [x] **Step 5: Run the real benchmark report**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python scripts/run_bookmd_benchmarks.py \
  --manifest docs/bookmd_benchmarks.json \
  --output tmp/bookmd_benchmark_report.json
```

Expected: `dc_dc_textbook` is measured; the other three samples are pending until source PDFs are selected and converted.

## P1 Task 3: Promote Benchmark Evidence Into Acceptance Docs

**Purpose:** Keep the project state clear after every benchmark run.

- [x] **Step 1: Update `docs/phase9.md`**

Record that the benchmark harness exists, one real sample is ready, and three document-type slots remain pending source selection.

- [x] **Step 2: Update `docs/final_acceptance.md`**

Add a row for:

```text
BookMD multi-book benchmark harness | python scripts/run_bookmd_benchmarks.py --manifest docs/bookmd_benchmarks.json --output tmp/bookmd_benchmark_report.json | Harness verified; corpus expansion pending
```

- [x] **Step 3: Update `docs/release_checklist.md`**

Add release gate:

```bash
python scripts/run_bookmd_benchmarks.py --manifest docs/bookmd_benchmarks.json --output tmp/bookmd_benchmark_report.json
python -m converter quality-report tmp/real_book_full_clean_text_visual.bookmd --format json
```

## P1 Task 4: Define Reader Performance Thresholds

**Purpose:** Turn the existing Android performance baseline into a regression gate.

- [x] **Step 1: Add static threshold documentation**

In `docs/android_reader_usage.md`, document current observed baseline from `tmp/android_reader_verify_final/performance_baseline.json`:

- open-to-reader: about 4.2 seconds
- progress restore: about 6.5 seconds
- settings round trip: about 6.8 seconds
- search flow: about 12.1 seconds
- source trace: about 4.3 seconds

- [x] **Step 2: Add planned enforcement thresholds**

Use conservative initial thresholds:

- open-to-reader: warn above 8 seconds
- progress restore: warn above 10 seconds
- settings round trip: warn above 10 seconds
- search flow: warn above 18 seconds
- source trace: warn above 8 seconds

- [x] **Step 3: Defer hard failure**

Do not fail the release script on performance thresholds yet. Record warnings only until benchmark data includes at least three book types.

## P2 Task 5: Add Second And Third Benchmark Books

**Purpose:** Move from single-book confidence to representative confidence.

- [x] **Step 1: Select source PDFs**

Choose one scanned/low-quality PDF and one formula-heavy paper that can be processed through the existing OCR API without committing source PDFs to the repository.

- [x] **Step 2: Convert in small OCR batches**

Do not upload whole books to OCR. Use existing split/batch workflow, then build `.bookmd` with visual assets enabled.

- [x] **Step 3: Update `docs/bookmd_benchmarks.json`**

Change selected samples from `status="pending"` to `status="ready"` and point `bookmd` to the generated `tmp/benchmarks/*.bookmd`.

- [x] **Step 4: Re-run benchmark report**

Run:

```bash
python scripts/run_bookmd_benchmarks.py \
  --manifest docs/bookmd_benchmarks.json \
  --output tmp/bookmd_benchmark_report.json \
  --require-ready
```

Expected: all ready samples are valid, have cover visuals, have search/source-map coverage, and record asset counts appropriate to their document type.

## P3 Task 6: Final Personal Workflow Command

**Purpose:** Reduce daily use to a predictable sequence once benchmark coverage is sufficient.

- [x] **Step 1: Document the command sequence**

In `docs/release_checklist.md`, keep the final personal gate as:

```bash
python -m converter build --source-pdf <source.pdf> --ocr-output <ocr-output-dir> --output <book.bookmd> --translate false --generate-block-assets true
python -m converter validate <book.bookmd>
python -m converter quality-report <book.bookmd> --format json
python scripts/verify_android_reader.py --device-smoke --bookmd <book.bookmd> --verify-visual-asset --search-term <known-term>
```

- [x] **Step 2: Add manual review checklist**

Manual review before phone import:

- Cover appears as first visual content.
- TOC/chapter list is usable.
- Formula/figure/table pages preserve original visual information.
- Search finds known technical terms.
- Source-map jump opens the correct PDF page.
- Reading progress restores after app restart.

## Final Verification

Run after implementation:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 python -m pytest -q
PYTHONDONTWRITEBYTECODE=1 python scripts/run_bookmd_benchmarks.py --manifest docs/bookmd_benchmarks.json --output tmp/bookmd_benchmark_report.json
PYTHONDONTWRITEBYTECODE=1 python -m converter quality-report tmp/real_book_full_clean_text_visual.bookmd --format json
ANDROID_HOME=/opt/homebrew/share/android-commandlinetools ANDROID_SDK_ROOT=/opt/homebrew/share/android-commandlinetools PATH=/opt/homebrew/share/android-commandlinetools/platform-tools:$PATH PYTHONDONTWRITEBYTECODE=1 python scripts/verify_android_reader.py --device-smoke --bookmd tmp/real_book_full_clean_text_visual.bookmd --verify-visual-asset --search-term DC-DC --artifacts-dir tmp/android_reader_verify_visual_asset
```

If no Android device/emulator is connected, record `adb devices` output and keep the device visual-asset gate pending.

## Completion Criteria

- Android real visual-asset smoke passes on a connected device/emulator.
- Benchmark harness exists and produces `tmp/bookmd_benchmark_report.json`.
- At least three representative `.bookmd` samples are measured.
- `docs/final_acceptance.md` separates verified facts from pending device or corpus work.
- The final personal workflow is documented as a short, repeatable command sequence.
