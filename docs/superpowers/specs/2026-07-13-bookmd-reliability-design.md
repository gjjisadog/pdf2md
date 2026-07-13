# BookMD Reliability And Cross-Platform Packaging Design

## Goal

Make the converter installable in a clean environment, make `.bookmd` a versioned and strictly validated format, and make cover/figure/formula/table asset generation work on Linux, Windows, and macOS without requiring system PDF utilities.

## Scope

This design covers three connected deliverables:

1. A standard Python package and GitHub Actions CI matrix.
2. BookMD format version 1.0 schemas, strict validation, and legacy compatibility fixtures.
3. A portable PDF rendering/cropping backend used by cover and complex-block asset generation.

It does not deploy OCR models, add cloud synchronization, add a GUI, or replace the WebView reader with a native pagination engine.

## Architecture

### Package and CI boundary

`pyproject.toml` becomes the source of truth for the installable Python distribution. The wheel contains the converter application and the four local libraries. The `bookmd` console script remains equivalent to `python -m converter`.

Runtime dependencies are:

- `pypdf` for PDF page selection and splitting.
- `pypdfium2` for PDF page rendering.
- `Pillow` for image cropping and PNG encoding.
- `jsonschema` for BookMD document validation.

Development dependencies include pytest and the package build checker. No CI job calls a live OCR or translation provider.

The CI workflow has three layers:

1. A Python test matrix on Ubuntu, Windows, and macOS.
2. A package job that builds an sdist and wheel, installs the wheel into a fresh environment, invokes the installed CLI, and builds/validates the sample package.
3. A visual regression job that creates a small valid multi-page PDF at test time, runs the real PDFium/Pillow backend, verifies cover and block assets, and executes on Windows as a required job.

Android/iOS release workflows remain separate from the Python package gate. They do not become required for a Python-only pull request.

### Portable PDF backend

Add `converter.pdf_backend` with a small backend interface:

```python
class PdfBackend(Protocol):
    def page_count(self, source_pdf: Path) -> int: ...
    def split_pages(self, source_pdf: Path, first_page: int, page_count: int, output: Path) -> Path: ...
    def render_page(self, source_pdf: Path, page: int, dpi: int, output_dir: Path) -> Path | None: ...
    def crop_region(self, page_image: Path, bbox: list[float], output: Path) -> bool: ...
```

The default implementation uses pypdfium2 and Pillow. It preserves the existing coordinate normalization and asset naming rules, and keeps the injectable renderer/cropper hooks used by unit tests.

The converter calls the backend for:

- first-page cover rendering;
- figure, formula, and table block fallback assets;
- OCR batch PDF splitting.

If a requested render or crop fails, the error records the page, block ID, backend operation, and original exception. A build may continue only when asset generation is optional; the resulting quality report must warn about each missing requested asset instead of silently returning an OCR-only block.

### BookMD 1.0 contract

Add JSON Schemas under `schemas/bookmd/v1/` for:

- `book.json`;
- `source_map.json`;
- `search_index.json`;
- `terms.json`;
- `translation.json`;
- `reading_config.json`.

New packages contain `format_version: "1.0"` in `book.json`. The existing `version` field remains readable for legacy packages but is no longer the format-version authority.

The validator has two related modes:

- Compatibility mode, used by the library API by default, accepts legacy 0.1 packages and reports migration warnings.
- Strict mode, used by the CLI, release scripts, CI, and quality reports, validates the schema and all cross-file invariants.

Strict validation checks:

- valid ZIP structure, duplicate entries, safe relative paths, and bounded extraction metadata;
- required JSON files and chapter files;
- supported major format version;
- unique chapter IDs, paths, and orders;
- unique source-map block IDs with valid page/bbox data;
- search and translation references resolving to known blocks/chapters;
- Markdown and HTML asset references resolving inside `assets/`;
- no dangling or duplicate resource references;
- optional original PDF and cover warnings consistent with existing quality-report behavior.

Version policy:

- missing `format_version` or `version: "0.1"`: legacy profile, readable with warnings;
- `format_version: "1.x"`: validate known 1.0 fields and warn on unknown minor fields;
- unknown major version: strict validation fails with an actionable error.

### Compatibility fixtures

Commit small directory fixtures under `tests/fixtures/bookmd/`:

- `legacy_v0_1/`: representative current package shape;
- `valid_v1/`: complete 1.0 package with cover and one visual asset;
- `invalid_v1/`: malformed cross-file references, unsafe path, and duplicate block examples.

Tests package the directories at runtime so binary archives do not need to be committed. Python tests validate all three fixtures. Android and iOS static/core verification use the valid v1 fixture and confirm that legacy metadata remains readable.

## Error handling

Errors must identify the archive member, block ID, page, or version field that failed. Validation returns structured `errors` and `warnings`; CLI commands print stable prefixes (`ERROR:` and `WARNING:`) and return non-zero only for errors.

The converter must never fall back silently from a requested visual asset to plain OCR. Optional fallback is permitted for an individual block, but the quality report records the missing asset and its cause.

## Testing and acceptance

The implementation is test-first:

1. Add package-install and CLI smoke tests before changing package metadata.
2. Add schema and cross-file validator tests for legacy, valid v1, and invalid v1 fixtures.
3. Add real PDFium/Pillow tests for cover rendering, page reuse, bbox cropping, and generated asset references.
4. Add a Windows CI job that runs those real rendering tests and a sample `.bookmd` build.
5. Run the existing full Python suite, wheel installation smoke, benchmark runner, and strict validation.

Completion requires:

- a clean virtual environment can install the wheel and run `bookmd --help`;
- Ubuntu, Windows, and macOS Python CI jobs pass;
- the Windows visual job produces a cover and at least one generated block asset from a real PDF;
- valid v1 fixtures pass strict validation;
- legacy fixtures remain readable with warnings;
- invalid v1 fixtures fail with actionable errors;
- existing 331+ tests and sample reader checks remain green.

## Rollout and compatibility

The first implementation changes only newly built packages to format 1.0. Existing `tmp/` artifacts and committed sample packages remain readable through the legacy profile. Renderer syntax, block IDs, chapter path conventions, and source-map field names remain unchanged.

