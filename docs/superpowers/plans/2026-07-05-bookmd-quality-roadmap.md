# BookMD Quality Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make professional PDF to BookMD conversion measurable, visually faithful, and repeatably good enough for long-form technical reading.

**Architecture:** Add a quality-report layer around existing `.bookmd` validation first, then improve conversion in small source-map-safe increments. Visual fallback assets become part of the package contract for complex technical pages instead of relying only on OCR text.

**Tech Stack:** Python 3.12, pytest, zipfile/json/pathlib, existing converter package, BookMD zip format, Android/iPadOS smoke verifiers.

---

## File Map

- Modify `apps/converter_desktop/converter/cli.py`: add `quality-report` CLI entry.
- Create `apps/converter_desktop/converter/quality.py`: inspect `.bookmd` packages and produce metrics.
- Modify `apps/converter_desktop/converter/builder.py`: preserve cover and visual fallback assets during build.
- Modify `apps/converter_desktop/converter/chapters.py`: improve automatic chapter/heading cleanup.
- Modify `apps/converter_desktop/converter/markdown.py`: render visual fallback blocks and captions safely.
- Modify `packages/ocr_client/ocr_client/client.py`: preserve OCR asset metadata needed by converter.
- Modify `tests/test_converter_quality.py`: add quality-report tests.
- Modify existing converter tests for cover/assets/chapter cleanup.
- Modify `docs/phase9.md` and `docs/final_acceptance.md`: record evidence as milestones complete.

## Task 1: Add BookMD Quality Report

Status: complete.

- [x] Write failing tests in `tests/test_converter_quality.py` for a valid package with original PDF, chapters, search index, source map, and assets.
- [x] Add `apps/converter_desktop/converter/quality.py` with a `BookMdQualityReport` dataclass and `inspect_bookmd(path)` function.
- [x] Add CLI command:

```bash
python -m converter quality-report path/to/book.bookmd --format json
python -m converter quality-report path/to/book.bookmd --format markdown
```

- [x] Include metrics: chapter count, empty chapter count, search item count, source-map block count, original PDF present, cover present, asset count, broken asset references, missing source pages, and warnings.
- [x] Verify:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_converter_quality.py tests/test_converter_cli.py -q
python -m converter quality-report tmp/real_book_full_clean_toc.bookmd --format json
```

## Task 2: Preserve Cover As First Visual Content

Status: complete.

- [x] Write failing tests proving generated `.bookmd` contains a cover asset or cover page reference.
- [x] Update builder pipeline to render or copy the first PDF page as a cover fallback when OCR output does not provide a cover image.
- [x] Update chapter Markdown so the first chapter starts with the cover visual before title OCR text.
- [x] Verify the cover does not break source-map/search validation.

## Task 3: Add Visual Fallback Assets For Complex Pages

Status: complete for `figure`, `formula`, and `table` OCR blocks.

- [x] Write failing tests using synthetic OCR blocks marked as figure/table/formula or low-confidence complex layout.
- [x] Package page-region or page-image assets under `assets/`.
- [x] Generate stable asset names tied to source page/block IDs.
- [x] Render Markdown references that Android/iPadOS readers can zoom.
- [x] Validate asset references during import and package validation.
- [x] Verify on the real DC-DC sample:

```bash
python -m converter build --source-pdf '/Users/wangxuwen/Library/Mobile Documents/iCloud~com~apple~iBooks/Documents/DC-DC Converter Topologies Basic to Advanced Gerry Moschopoulos Z-Library.pdf' --ocr-output tmp/real_book_full --output tmp/real_book_full_visual_assets.bookmd --translate false --generate-block-assets true
python -m converter validate tmp/real_book_full_visual_assets.bookmd
python -m converter quality-report tmp/real_book_full_visual_assets.bookmd --format json
```

Result: build time about 60 seconds; valid package; `asset_count=485`; `referenced_asset_count=485`; `broken_asset_references=[]`; 299 formula blocks, 183 figure blocks, and 2 table blocks rendered as visual fallback references.

## Task 4: Improve Chapter Structuring

Status: complete for the real DC-DC sample.

- [x] Write tests using the DC-DC table-of-contents pattern and noisy OCR headings.
- [x] Normalize repeated spacing and broken headings without changing block IDs.
- [x] Prefer real TOC/heading signals over page-by-page pseudo chapters.
- [x] Acceptance target: DC-DC sample builds to 18 meaningful chapters through rules, not manual cleanup.
- [x] Verify on the real DC-DC sample:

```bash
python -m converter build --source-pdf '/Users/wangxuwen/Library/Mobile Documents/iCloud~com~apple~iBooks/Documents/DC-DC Converter Topologies Basic to Advanced Gerry Moschopoulos Z-Library.pdf' --ocr-output tmp/real_book_full --output tmp/real_book_full_structured_visual.bookmd --translate false --generate-block-assets true
python -m converter validate tmp/real_book_full_structured_visual.bookmd
python -m converter quality-report tmp/real_book_full_structured_visual.bookmd --format json
```

Result: valid package; 18 chapters; cleaned chapter titles such as `ZERO-VOLTAGE-ZERO-CURRENT SWITCHING DC-DC FULL-BRIDGE PWM CONVERTERS`, `RESONANT CONVERTERS PART I - FUNDAMENTALS`, and `RESONANT CONVERTERS PART II - PWM CONTROLLED, QUASI-RESONANT, AND ULTRAHIGH-FREQUENCY CONVERTERS`; `source_map_block_count=3483`; `search_item_count=3474`.

## Task 5: OCR Text Cleanup

Status: complete for block-local display cleanup on the real DC-DC sample.

- [x] Add cleanup tests for duplicated spaces, soft hyphen joins, broken line joins, and obvious OCR glue words.
- [x] Keep cleanup block-local and source-map-safe.
- [x] Verify on the real DC-DC sample:

```bash
python -m converter build --source-pdf '/Users/wangxuwen/Library/Mobile Documents/iCloud~com~apple~iBooks/Documents/DC-DC Converter Topologies Basic to Advanced Gerry Moschopoulos Z-Library.pdf' --ocr-output tmp/real_book_full --output tmp/real_book_full_clean_text_visual.bookmd --translate false --generate-block-assets true
python -m converter validate tmp/real_book_full_clean_text_visual.bookmd
python -m converter quality-report tmp/real_book_full_clean_text_visual.bookmd --format json
```

Result: valid package; 18 chapters; source-map/search/asset metrics unchanged; Markdown display fixes `8.1Modified`, `8.1.1Modified`, `1458.1.2Modified`, single-line OCR breaks, soft hyphens, and hyphenated line breaks without changing OCR block IDs.
- [ ] Add quality-report warnings for suspicious cleanup-heavy pages.
- [ ] Verify no source-map block IDs are dropped.

## Task 6: Translation Quality Pilot

- [ ] Select 1-2 representative chapters from the DC-DC sample.
- [x] Run DeepSeek-compatible translation with fake transport/cache-disabled pilot on selected real OCR blocks.
- [x] Add report checks for missing translations, block alignment, glossary consistency, Markdown breakage, and overlong translations.
- [x] Keep live API tests manual; automated tests use fake transports.
- [ ] Run live DeepSeek translation with cache enabled once `DEEPSEEK_API_KEY` is available.
- [x] Verify fake DeepSeek-compatible pilot:

```bash
python -m converter validate tmp/translation_pilot_fake_deepseek.bookmd
python -m converter quality-report tmp/translation_pilot_fake_deepseek.bookmd --format json
```

Result: valid package; `translation_provider=deepseek`; `translation_block_count=3`; `translated_block_count=3`; `translation_coverage_ratio=1.0`; glossary target `脉宽调制` present; no missing glossary targets, Markdown risks, overlong translations, or quality warnings.

## Task 7: Benchmark Corpus

- [ ] Define benchmark metadata for at least three PDF types.
- [ ] Add commands to run OCR/build/quality-report per sample.
- [ ] Store quality-report outputs under `tmp/` or documented artifact paths.
- [ ] Summarize trends in `docs/final_acceptance.md`.

## Task 8: Reader Verification For Visual Assets

- [ ] Extend Android smoke to open a visual asset from the real sample when assets exist.
- [ ] Extend iPadOS smoke/static acceptance similarly.
- [ ] Verify zoom behavior and source-page fallback remain intact.

## Final Verification

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 python -m pytest -q
python -m converter validate tmp/real_book_full_clean_toc.bookmd
python -m converter quality-report tmp/real_book_full_clean_toc.bookmd --format json
ANDROID_HOME=/opt/homebrew/share/android-commandlinetools ANDROID_SDK_ROOT=/opt/homebrew/share/android-commandlinetools PATH=/opt/homebrew/share/android-commandlinetools/platform-tools:$PATH PYTHONDONTWRITEBYTECODE=1 python scripts/verify_android_reader.py --device-smoke --bookmd tmp/real_book_full_clean_toc.bookmd --search-term DC-DC
cd apps/reader-ios && python3 scripts/verify_ios_release.py
```

## Completion Criteria

- Quality report exists and is documented.
- Cover is preserved as first visual content.
- Complex technical visuals produce meaningful assets.
- Chapter structure is stable on real technical books.
- Translation pilot has measurable quality output.
- Android/iPadOS smoke tests cover the improved package.
