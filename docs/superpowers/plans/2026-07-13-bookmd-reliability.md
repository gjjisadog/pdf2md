# BookMD Reliability And Cross-Platform Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repository installable in clean environments, validate BookMD 1.0 packages strictly while preserving legacy 0.1 readers, and generate cover/complex-block assets on Windows, macOS, and Linux without system PDF utilities.

**Architecture:** Keep `bookmd_core` as the format authority, add JSON Schema plus cross-file validation, and expose a compatibility-aware `validate_bookmd(path, strict=False)` API. Add a small `converter.pdf_backend` implemented with pypdfium2, Pillow, and pypdf; route OCR batch splitting and asset generation through it while preserving existing test injection hooks. Add GitHub Actions jobs for package installation, the Python test matrix, and a required Windows real-PDF visual smoke.

**Tech Stack:** Python >=3.11, setuptools, pytest, jsonschema, pypdf, pypdfium2, Pillow, GitHub Actions, existing Kotlin/Swift static verifiers.

## Current status (2026-07-14)

- Tasks 1–5 are implemented and locally verified: installable sdist/wheel, BookMD 1.0 schemas and fixtures, strict validator, portable PDFium/Pillow backend, failure diagnostics, and Android/iOS version gates.
- Task 6 is implemented in `.github/workflows/python-ci.yml`; commit `36d8d03` triggers the 3×2 Python matrix plus the Windows real-visual job. Gitea run 3 currently reports all seven jobs as `pending / Waiting to run` because no matching runner has claimed them.
- Task 7 local evidence is complete (`356 passed`, isolated wheel install, sample strict build/validation). Remote Windows execution remains the only unverified acceptance item.

## Global Constraints

- New packages write `format_version: "1.0"`; missing format version and `version: "0.1"` remain readable through a legacy profile with warnings.
- Unknown BookMD major versions fail strict validation; known minor extensions warn and continue.
- No CI job calls a live OCR or translation provider.
- Cover and complex visual assets remain first-class reading content; OCR cleanup must not change block IDs or source pages.
- The portable backend must not require `swift`, `pdftoppm`, or `sips` on the host.
- Existing renderer syntax, chapter path conventions, and source-map field names remain compatible.

---

### Task 1: Make the Python distribution installable

**Files:** `pyproject.toml`, `tests/test_packaging.py`, `README.md`.

**Interfaces:** The wheel exposes `converter`, `bookmd_core`, `source_map_core`, `translator_core`, and `ocr_client`; the console script is `bookmd = converter.cli:main`.

- [ ] Write tests that assert the metadata declares Python >=3.11, runtime dependencies `pypdf`, `pypdfium2`, `Pillow`, and `jsonschema`, plus the `bookmd` entry point.
- [ ] Run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_packaging.py -q`; it must fail before metadata changes.
- [ ] Configure setuptools build metadata and package discovery for `apps/converter_desktop` and all `packages/*` roots. Add runtime and `dev` optional dependencies and the console script without removing current pytest paths.
- [ ] Run `python -m pip install -e '.[dev]'`, `python -m build`, install `dist/*.whl` into a fresh virtual environment, and run `bookmd --help` without `PYTHONPATH`.
- [ ] Document editable install, wheel build, and installed CLI usage in README.
- [ ] Commit with `git add pyproject.toml tests/test_packaging.py README.md && git commit -m "build: make BookMD converter installable"`.

### Task 2: Add BookMD 1.0 schemas and compatibility fixtures

**Files:** `schemas/bookmd/v1/*.schema.json`, `tests/fixtures/bookmd/{legacy_v0_1,valid_v1,invalid_v1}/`, `packages/bookmd_core/bookmd_core/schema.py`, `tests/test_bookmd_schema.py`, `tests/test_bookmd_compatibility.py`.

**Interfaces:** `load_schema(name: str, version: str = "1.0") -> dict[str, Any]`; tests package fixture directories at runtime instead of committing generated archives.

- [ ] Add failing tests named `test_valid_v1_fixture_passes_strict_validation`, `test_legacy_v01_fixture_passes_with_migration_warning`, `test_invalid_v1_fixture_reports_unsafe_and_dangling_references`, and `test_schema_loader_rejects_unknown_schema_name`.
- [ ] Run the focused schema tests and confirm they fail because the schemas and loader do not exist.
- [ ] Define schemas for `book.json`, `source_map.json`, `search_index.json`, `terms.json`, `translation.json`, and `reading_config.json`. Require `format_version: "1.0"` for v1, non-empty IDs, positive source pages, four-number bboxes, and valid relative POSIX paths.
- [ ] Add representative legacy, valid v1, and invalid v1 fixture directories. The valid fixture must include one chapter, one block, one search item, one translation item, one term, and one referenced asset.
- [ ] Implement package-relative schema loading and a fixture zipper helper.
- [ ] Run the focused tests and confirm valid v1 passes, legacy v0.1 passes with a warning, and invalid v1 reports the member or block ID.
- [ ] Commit with `git add schemas tests/fixtures tests/test_bookmd_schema.py tests/test_bookmd_compatibility.py packages/bookmd_core/bookmd_core/schema.py && git commit -m "feat: define BookMD 1.0 schemas and fixtures"`.

### Task 3: Implement strict BookMD validation

**Files:** `packages/bookmd_core/bookmd_core/validator.py`, `packages/bookmd_core/bookmd_core/references.py`, `packages/bookmd_core/bookmd_core/__init__.py`, `apps/converter_desktop/converter/cli.py`, `apps/converter_desktop/converter/quality.py`, `tests/test_bookmd_validator_strict.py`, `tests/test_bookmd_core.py`.

**Interfaces:** `validate_bookmd(path: str | Path, *, strict: bool = False) -> ValidationResult`; compatibility mode is the default library behavior, strict mode is used by CLI, release, and quality reports.

- [ ] Add failing tests for duplicate ZIP entries, absolute and parent paths, unknown major versions, duplicate block IDs, dangling search/translation references, missing assets, invalid bboxes, and extraction-size limits.
- [ ] Implement ZIP safety checks before reading members: duplicate names, absolute paths, `..` traversal, symlinks, entry-count limits, and total declared uncompressed-size limits.
- [ ] Implement version-aware JSON Schema validation. Missing `format_version` or `version == "0.1"` selects legacy profile; `1.x` selects v1; unknown major fails strict validation.
- [ ] Implement cross-file checks for chapter IDs/paths/orders, source-map uniqueness and geometry, search and translation references, terms shape, and Markdown/HTML assets inside the archive `assets/` root.
- [ ] Make `validate` and `quality-report` call strict mode while retaining the existing `ValidationResult` fields and stable `ERROR:`/`WARNING:` prefixes.
- [ ] Run the focused validator and quality tests, then commit with `git add packages/bookmd_core apps/converter_desktop/converter tests && git commit -m "feat: strictly validate BookMD packages"`.

### Task 4: Add the portable PDFium/Pillow backend

**Files:** `apps/converter_desktop/converter/pdf_backend.py`, `apps/converter_desktop/converter/builder.py`, `apps/converter_desktop/converter/ocr_pipeline.py`, `tests/test_pdf_backend.py`, `tests/test_converter_asset_generation.py`, `tests/test_converter_ocr_cli.py`.

**Interfaces:** `PdfBackend.page_count`, `split_pages`, `render_page`, and `crop_region`; `get_pdf_backend() -> PdfBackend` returns the wheel-backed implementation.

- [ ] Add a test helper using pypdf to generate a valid two-page PDF with a known page size and colored content stream; the real backend, not fake renderer callbacks, must consume it.
- [ ] Add failing tests for page count, split output, rendered PNG dimensions, bbox crop output, invalid bbox rejection, and page-render reuse. Assert the crop contains non-white pixels from the known colored region.
- [ ] Implement PDFium page rendering with pypdfium2 and PNG encoding with Pillow. Convert failures to errors containing PDF path and page number.
- [ ] Implement Pillow cropping with current bbox scaling and margin rules, rejecting non-finite and non-positive boxes.
- [ ] Route cover generation, generated block assets, and OCR batch splitting through the backend. Preserve the existing injected renderer/cropper arguments for unit tests and page caching per build.
- [ ] Track requested-asset failures by block ID/page and expose them as quality warnings instead of silently falling back.
- [ ] Run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_pdf_backend.py tests/test_converter_asset_generation.py tests/test_converter_ocr_cli.py -q`, then commit with `git add apps/converter_desktop/converter tests && git commit -m "feat: use portable PDFium visual asset backend"`.

### Task 5: Emit and consume BookMD 1.0 metadata

**Files:** `apps/converter_desktop/converter/builder.py`, Android BookModels/BookRepository, iOS BookModels/BookMDArchive, converter and reader tests.

- [ ] Add failing tests asserting new builds write `format_version == "1.0"`, legacy fixtures import, and unknown major versions produce readable import errors.
- [ ] Add `format_version` to builder manifests without changing block IDs, chapter paths, source-map fields, search item structure, or renderer custom blocks.
- [ ] Add Android and Swift parsing gates: absent value means legacy, major 1 is supported, unknown majors are rejected without a crash.
- [ ] Run converter tests, `tests/test_android_skeleton.py`, and `python3 apps/reader-ios/scripts/verify_ios_static.py`.
- [ ] Commit with `git add apps/converter_desktop/converter apps/reader-android apps/reader-ios tests && git commit -m "feat: emit and consume BookMD 1.0 metadata"`.

### Task 6: Add GitHub Actions package and Windows visual gates

**Files:** `.github/workflows/ci.yml`, optionally `.github/workflows/windows-visual.yml`, `README.md`, `tests/test_ci_contract.py`.

- [ ] Add workflow contract tests asserting Ubuntu, Windows, and macOS runners; Python 3.11; wheel build/install; pytest; and the real visual test command, with no OCR or DeepSeek secrets.
- [ ] Add a Python matrix job using checkout, setup-python, pip cache, `pip install -e '.[dev]'`, and the full test suite.
- [ ] Add a package job that builds sdist/wheel, installs the wheel into a fresh environment, runs `bookmd --help`, builds the sample package, and validates it strictly.
- [ ] Add a required Windows job running the real PDFium/Pillow backend tests and the sample asset-generation test without relying on `tmp/` artifacts.
- [ ] Run workflow contract tests and all local package commands. Verify the Windows job through the remote Actions result.
- [ ] Commit with `git add .github README.md tests/test_ci_contract.py && git commit -m "ci: verify clean installs and Windows visual assets"`.

### Task 7: Record final acceptance evidence

**Files:** `docs/final_acceptance.md`, `docs/release_checklist.md`, `docs/phase9.md`.

- [ ] Run the full suite, wheel build, benchmark runner, strict validation, and quality report.
- [ ] Install the generated wheel into a new environment, run `bookmd --help`, build the sample, and validate it in strict mode.
- [ ] Record CI run evidence, package-install status, Windows visual output, and explicit live-provider/platform limitations.
- [ ] Run `git diff --check` and `git status --short --branch`.
- [ ] Commit with `git add docs/final_acceptance.md docs/release_checklist.md docs/phase9.md && git commit -m "docs: record BookMD reliability acceptance"`.
