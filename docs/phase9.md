# Phase 9 Scope

Phase 9 turns the current usable BookMD MVP into a quality-focused technical-book conversion pipeline. The priority is not adding another reader shell, but making generated `.bookmd` packages consistently feel like books on phone and tablet: readable structure, trustworthy source fallback, searchable text, and preserved technical visuals.

## Current Baseline

- `tmp/real_book_full_clean_toc.bookmd` validates as a BookMD package.
- The real DC-DC sample has 18 cleaned chapters, 3474 search items, 3483 source-map blocks, and `source/original.pdf`.
- Android and iPadOS readers can import and smoke-test the real sample.
- `python -m converter quality-report tmp/real_book_full_clean_toc.bookmd --format json` records the pre-cover measurable quality baseline: valid package, 18 chapters, 0 empty chapters, 3474 search items, 3483 source-map blocks, original PDF present, 0 assets, and missing cover visual warning; the pre-1.0 artifact also emits the expected legacy migration warning.
- `tmp/real_book_full_cover.bookmd` verifies the first Phase 9 quality improvement: the package validates, contains `assets/cover/page_001.png`, starts the first chapter with `![Cover](../assets/cover/page_001.png)`, and reports `has_cover=true` with no cover/asset warnings; its legacy migration warning is expected.
- `tmp/real_book_full_visual_assets.bookmd` verifies figure/formula/table visual fallback assets on the real DC-DC sample: build time is about 60 seconds, the package validates, `quality-report` reports `asset_count=485`, `referenced_asset_count=485`, and no broken asset references, with Markdown blocks for 299 formulas, 183 figures, and 2 tables.
- The portable PDF backend is now shared by cover rendering, generated block assets, and OCR batch splitting; optional render/crop failures are recorded in `asset_generation.json` and surfaced by `quality-report` as `missing visual assets: N` warnings.
- `tmp/real_book_full_structured_visual.bookmd` verifies automatic chapter structuring plus visual assets on the real DC-DC sample: 18 chapters are produced directly from OCR blocks, title spacing glitches such as `PWMCONVERTERS`, `PARTI-FUNDAMENTALS`, and comma-joined headings are cleaned in the manifest/TOC, and `quality-report` has no quality warnings beyond the expected legacy migration warning, with 3483 source-map blocks and 3474 search items.
- `tmp/real_book_full_clean_text_visual.bookmd` verifies block-local OCR display cleanup plus visual assets on the real DC-DC sample: single-line OCR breaks are joined, soft hyphen/hyphenated line breaks are normalized, TOC entries such as `8.1Modified` and `1458.1.2Modified` are rendered as readable text, and source-map/search/asset metrics remain unchanged; only the expected legacy migration warning remains.
- `tmp/translation_pilot_fake_deepseek.bookmd` verifies the translation quality-report path on a selected real OCR sample using a fake DeepSeek-compatible translator: 3/3 blocks translated, bilingual Markdown includes `原文:`, glossary target `脉宽调制` is present, and `quality-report` shows no translation warnings beyond the expected legacy migration warning. A live DeepSeek API pilot is still pending `DEEPSEEK_API_KEY`.
- `docs/bookmd_benchmarks.json` and `scripts/run_bookmd_benchmarks.py` define the first repeatable multi-book benchmark gate. Current benchmark coverage includes the DC-DC technical textbook, a scanned/low-quality Chinese sample rebuilt as `tmp/boundary_lcl_scan_p1_6_visual.bookmd`, and a paper-style sample rebuilt as `tmp/boundary_bleu_acl2002_visual.bookmd`; the table-heavy manual slot remains pending source selection.

## Phase 9 Goals

1. Define measurable BookMD quality gates for professional PDF conversion.
2. Preserve cover, formulas, figures, tables, captions, and complex page regions as first-class visual fallback assets.
3. Improve OCR text cleanup without damaging source-map traceability.
4. Evaluate DeepSeek translation quality on real technical chapters with terminology consistency checks.
5. Create a repeatable conversion benchmark across several PDF types.

## Priority Plan

### P0: Quality Measurement And Regression Gate

- Add a `bookmd quality-report` command that inspects a `.bookmd` and emits JSON/Markdown metrics. Status: implemented as `python -m converter quality-report`.
- Metrics should include chapter count, empty/short chapters, search item count, source-map coverage, original PDF presence, cover presence, asset count, asset reference integrity, repeated OCR garbage patterns, and translation alignment coverage.
- Add pytest coverage using synthetic `.bookmd` fixtures and the real DC-DC sample when available.
- Acceptance: every future conversion has an objective quality report before reader testing.

### P0: Cover And Page-Visual Preservation

- Ensure the first visual content is the real cover page, not only OCR title text. Status: cover preservation implemented for page 1 as `assets/cover/page_001.png`.
- Add page image or region image assets for cover pages, complex formula-heavy pages, diagrams, tables, and pages with low text confidence.
- Keep OCR text layered beside or below visual fallback instead of replacing technical visuals with guessed Markdown.
- Acceptance: a generated technical book can be skimmed visually even where OCR text is imperfect.

### P1: OCR Cleanup And Chapter Structuring

- Improve heading/chapter detection so generated chapters match the real table of contents without manual cleanup. Status: implemented for the real DC-DC sample; fresh `build_chapters(normalize_blocks(result.json))` produces 18 chapters.
- Normalize obvious spacing/joining issues such as duplicated spaces, broken hyphenation, and common OCR line joins. Status: implemented for chapter/TOC titles, including `PWMCONVERTERS`, `PARTI-FUNDAMENTALS`, and comma-joined technical headings.
- Normalize obvious block-local OCR display issues in body text. Status: implemented for soft hyphen removal, hyphenated line-break joins, single-line OCR joins, section-number/title spacing such as `8.1Modified`, and TOC page-number/item joins such as `1458.1.2Modified`.
- Keep cleanup source-map-safe: block IDs and page mappings must remain stable. Status: title cleanup does not mutate OCR block IDs or source-map block records.
- Acceptance: the DC-DC sample produces the 18-chapter structure directly from pipeline rules, not post-hoc manual repair. Status: verified with `tmp/real_book_full_structured_visual.bookmd`.

### P1: Figure, Formula, Table, Caption Assets

- Detect visual blocks from OCR API output or PDF page rendering. Status: implemented for `figure`, `formula`, and `table` blocks when `--generate-block-assets true` is enabled.
- Package assets under `assets/` with stable names and Markdown references. Status: implemented as `assets/generated/page_<page>_<block_id>.png`.
- Preserve captions and link them to source-map blocks.
- Ensure Android/iPadOS render these assets with zoom-friendly behavior.
- Acceptance: asset count and referenced-asset validation are non-zero on real technical books with diagrams. Status: real DC-DC sample reports 485 assets, all referenced, with no quality warnings.

### P1: Translation Quality Pilot

- Run a controlled DeepSeek translation smoke on selected chapters only. Status: fake DeepSeek-compatible pilot completed on selected real OCR blocks; live DeepSeek call is pending `DEEPSEEK_API_KEY`.
- Build a bilingual quality report: terminology consistency, block alignment, untranslated segments, overlong translations, and Markdown breakage. Status: implemented in `quality-report` with translation provider, coverage, untranslated block IDs, glossary target gaps, Markdown risk block IDs, and overlong translation IDs.
- Maintain `terms.json` as a reviewable technical glossary, not just an artifact.
- Acceptance: one representative chapter can be read bilingually without obvious structural breakage. Status: verified with fake DeepSeek-compatible pilot; live-provider acceptance remains pending API key.

### P2: Multi-Book Benchmark Set

- Create a small benchmark corpus:
  - one power-electronics textbook,
  - one scanned/low-quality PDF,
  - one paper-heavy PDF with formulas,
  - one table-heavy manual.
- Status: benchmark manifest and runner are implemented. The power-electronics textbook slot is measured from `tmp/real_book_full_clean_text_visual.bookmd`, the scanned/low-quality slot from `tmp/boundary_lcl_scan_p1_6_visual.bookmd`, and the paper slot from `tmp/boundary_bleu_acl2002_visual.bookmd`; the table-heavy manual slot remains pending until a representative PDF is selected and converted.
- Run `python scripts/run_bookmd_benchmarks.py --manifest docs/bookmd_benchmarks.json --output tmp/bookmd_benchmark_report.json` to refresh the current report.
- Store only derived lightweight fixtures or metadata when source PDFs cannot be committed.
- Acceptance: quality trends are visible across multiple document types, not just one lucky sample.

### P2: Reader Experience Polish

- Add reader affordances for visual fallback pages: cover view, figure list, table/figure zoom entry points, and source-page jump clarity. Status: Android verification script can now smoke-test a real referenced visual asset with `--verify-visual-asset`; it selects a non-cover `assets/generated/...` reference from the `.bookmd`, opens `ImageViewerActivity` through a debug-only app-internal dispatch path, verifies the viewer WebView, returns/restores to the reader, and continues source-map smoke. Runtime execution passed on the `BookMdApi33` emulator with `tmp/real_book_full_clean_text_visual.bookmd`.
- Improve large-book performance thresholds in Android/iPadOS smoke reports.
- Acceptance: quality improvements are visible in the reader, not just inside package files. Status: script/static path and device smoke verified against `tmp/real_book_full_clean_text_visual.bookmd`, which resolves and opens `assets/generated/page_021_p021_b006.png` on the `BookMdApi33` emulator.

### P3: Packaging And Personal Workflow

- Add a single documented command for real personal conversion:
  - OCR in batches,
  - build `.bookmd`,
  - generate quality report,
  - optionally translate selected chapters,
  - validate,
  - smoke-test on Android/iPadOS.
- Add a “known conversion issues” report for manual review before importing to a phone.
- Acceptance: a non-developer future user can run the workflow with minimal command choices.

## Recommended Execution Order

1. Implement `bookmd quality-report`.
2. Add cover/page visual preservation.
3. Add figure/formula/table asset extraction.
4. Improve automatic chapter cleanup.
5. Run translation pilot on selected chapters.
6. Expand to benchmark corpus.
7. Polish reader affordances for visual assets.

## Verification Gates

Minimum gate for each phase-nine increment:

```bash
python -m pytest
python -m converter validate tmp/real_book_full_clean_toc.bookmd
python -m converter quality-report tmp/real_book_full_clean_toc.bookmd --format json
python scripts/verify_android_reader.py --device-smoke --bookmd tmp/real_book_full_clean_toc.bookmd --search-term DC-DC
cd apps/reader-ios && python3 scripts/verify_ios_release.py
```

If Android/iPadOS devices or simulators are unavailable, record the blocker explicitly and keep static package validation plus renderer tests green.

## Non-Goals

- No local OCR model deployment in this repository.
- No cloud sync, account system, public marketplace, or commercial installer.
- No destructive text cleanup that breaks source map traceability.
- No “pure Markdown at all costs” conversion for formula-heavy technical pages.

## Success Definition

Phase 9 is complete when the real DC-DC book and at least two other representative PDFs can be converted into `.bookmd` packages with:

- valid package structure,
- real cover preservation,
- measurable source-map/search coverage,
- non-zero meaningful visual assets for complex pages,
- readable cleaned chapter structure,
- documented quality report,
- Android/iPadOS smoke verification.
