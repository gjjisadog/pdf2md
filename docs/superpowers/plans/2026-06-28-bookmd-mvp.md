# BookMD MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable local BookMD pipeline: sample OCR output -> validated `.bookmd` package -> Android/WebView reader skeleton.

**Architecture:** Python packages provide conversion, `.bookmd` validation, source-map generation, and translation boundaries. The desktop converter is a thin CLI orchestrator. Android uses Kotlin + WebView with local renderer assets so later reading modes can evolve without changing the package format.

**Tech Stack:** Python 3.11+, pytest, Typer or argparse, zipfile, pathlib, JSON, Kotlin Android skeleton, WebView, HTML/CSS/JS renderer assets.

---

## File Map

- Create `pyproject.toml`: Python package metadata, pytest config, console/module import paths.
- Create `README.md`: project purpose, quickstart, non-goals.
- Create `docs/*.md`: architecture, BookMD spec, converter usage, Android usage, translation, troubleshooting.
- Create `packages/bookmd_core/bookmd_core/`: BookMD manifest models, builder, validator, zip reader.
- Create `packages/source_map_core/source_map_core/`: normalized block model and source map generator/query helpers.
- Create `packages/translator_core/translator_core/`: translator interface, noop translator, cache, DeepSeek config guard.
- Create `packages/markdown_renderer/renderer/`: mobile renderer HTML/CSS/JS assets.
- Create `apps/converter_desktop/converter/`: CLI, config loading, OCR parser, chapter/Markdown generation, build orchestration.
- Create `samples/ocr_output_sample/`: fake `result.json`, `result.md`, assets, `original.pdf`.
- Create `samples/bookmd_sample/.gitkeep`: output directory placeholder.
- Create `tests/`: unit and end-to-end tests for core package behavior and CLI.
- Create `apps/reader-android/`: minimal Gradle/Kotlin Android project skeleton and WebView reader boundary.

## Task 1: Repository And Python Test Harness

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `tests/test_imports.py`

- [ ] **Step 1: Write failing import smoke test**

```python
def test_python_packages_import():
    import bookmd_core
    import source_map_core
    import translator_core

    assert bookmd_core.__name__ == "bookmd_core"
    assert source_map_core.__name__ == "source_map_core"
    assert translator_core.__name__ == "translator_core"
```

- [ ] **Step 2: Run test and confirm failure**

Run: `python -m pytest tests/test_imports.py -q`

Expected: FAIL because packages are not created yet.

- [ ] **Step 3: Add package metadata and empty package modules**

Create package roots and `__init__.py` files. Configure pytest `pythonpath` to include:

```toml
[tool.pytest.ini_options]
pythonpath = [
  "packages/bookmd_core",
  "packages/source_map_core",
  "packages/translator_core",
  "apps/converter_desktop"
]
```

- [ ] **Step 4: Run test and confirm pass**

Run: `python -m pytest tests/test_imports.py -q`

Expected: PASS.

## Task 2: Source Map Core

**Files:**
- Create: `packages/source_map_core/source_map_core/models.py`
- Create: `packages/source_map_core/source_map_core/generator.py`
- Modify: `packages/source_map_core/source_map_core/__init__.py`
- Create: `tests/test_source_map_core.py`

- [ ] **Step 1: Write failing source map tests**

```python
from source_map_core import normalize_blocks, build_source_map


def test_normalize_blocks_accepts_pages_shape():
    data = {"pages": [{"page": 1, "blocks": [{"id": "b1", "type": "paragraph", "bbox": [1, 2, 3, 4], "text": "Hello"}]}]}

    blocks = normalize_blocks(data)

    assert blocks[0].block_id == "b1"
    assert blocks[0].page == 1
    assert blocks[0].bbox == [1, 2, 3, 4]


def test_build_source_map_preserves_trace_data():
    blocks = normalize_blocks({"blocks": [{"block_id": "p001_b001", "page": 1, "type": "paragraph", "bbox": [0, 0, 10, 10], "text": "Grid inverter"}]})

    source_map = build_source_map(blocks, chapter_by_block={"p001_b001": ("ch_001", "chapters/001_intro.md")})

    assert source_map["blocks"][0]["block_id"] == "p001_b001"
    assert source_map["blocks"][0]["chapter_id"] == "ch_001"
    assert source_map["blocks"][0]["source_text"] == "Grid inverter"
```

- [ ] **Step 2: Run tests and confirm missing functions**

Run: `python -m pytest tests/test_source_map_core.py -q`

Expected: FAIL because `normalize_blocks` and `build_source_map` do not exist.

- [ ] **Step 3: Implement block normalization and source map generation**

Implement:

```python
@dataclass(frozen=True)
class OcrBlock:
    block_id: str
    page: int
    type: str
    bbox: list[float]
    text: str = ""
    level: int | None = None
    asset_path: str | None = None
    latex: str | None = None
    markdown: str | None = None
    caption: str | None = None
```

Accept both `pages[].blocks[]` and top-level `blocks[]`. Generate fallback IDs as `p{page:03d}_b{index:03d}`.

- [ ] **Step 4: Run source map tests**

Run: `python -m pytest tests/test_source_map_core.py -q`

Expected: PASS.

## Task 3: BookMD Core Validation And Packaging

**Files:**
- Create: `packages/bookmd_core/bookmd_core/validator.py`
- Create: `packages/bookmd_core/bookmd_core/packager.py`
- Modify: `packages/bookmd_core/bookmd_core/__init__.py`
- Create: `tests/test_bookmd_core.py`

- [ ] **Step 1: Write failing validation tests**

```python
import json
import zipfile

from bookmd_core import REQUIRED_FILES, validate_bookmd


def test_validate_bookmd_accepts_required_files(tmp_path):
    archive = tmp_path / "sample.bookmd"
    with zipfile.ZipFile(archive, "w") as zf:
        for name in REQUIRED_FILES:
            payload = {"chapters": []} if name == "book.json" else {}
            zf.writestr(name, json.dumps(payload))
        zf.writestr("chapters/001_intro.md", "# Intro")

    result = validate_bookmd(archive)

    assert result.valid is True
    assert result.errors == []


def test_validate_bookmd_reports_missing_manifest(tmp_path):
    archive = tmp_path / "broken.bookmd"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("source_map.json", "{}")

    result = validate_bookmd(archive)

    assert result.valid is False
    assert "book.json" in result.errors[0]
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `python -m pytest tests/test_bookmd_core.py -q`

Expected: FAIL because `bookmd_core` validation does not exist.

- [ ] **Step 3: Implement validator and packager**

Implement:

```python
REQUIRED_FILES = [
    "book.json",
    "source_map.json",
    "terms.json",
    "translation.json",
    "reading_config.json",
    "search_index.json",
]
```

`validate_bookmd(path)` returns `ValidationResult(valid: bool, errors: list[str], warnings: list[str])`.

`package_directory(source_dir, output_path)` writes deterministic zip entries.

- [ ] **Step 4: Run BookMD tests**

Run: `python -m pytest tests/test_bookmd_core.py -q`

Expected: PASS.

## Task 4: Translator Core Boundary

**Files:**
- Create: `packages/translator_core/translator_core/models.py`
- Create: `packages/translator_core/translator_core/cache.py`
- Create: `packages/translator_core/translator_core/noop.py`
- Create: `packages/translator_core/translator_core/deepseek.py`
- Modify: `packages/translator_core/translator_core/__init__.py`
- Create: `tests/test_translator_core.py`

- [ ] **Step 1: Write failing translator tests**

```python
import pytest

from translator_core import DeepSeekConfig, MissingApiKeyError, NoopTranslator, TranslationBlock


def test_noop_translator_preserves_block_alignment():
    result = NoopTranslator().translate_blocks([TranslationBlock(block_id="b1", text="Voltage source inverter")], target_lang="zh")

    assert result[0].block_id == "b1"
    assert result[0].translated_text == "Voltage source inverter"


def test_deepseek_config_requires_api_key_when_enabled(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(MissingApiKeyError):
        DeepSeekConfig.from_env()
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `python -m pytest tests/test_translator_core.py -q`

Expected: FAIL because translator modules do not exist.

- [ ] **Step 3: Implement noop translator and DeepSeek config guard**

Implement aligned dataclasses:

```python
@dataclass(frozen=True)
class TranslationBlock:
    block_id: str
    text: str

@dataclass(frozen=True)
class TranslationResult:
    block_id: str
    source_text: str
    translated_text: str
```

`DeepSeekConfig.from_env()` reads `DEEPSEEK_API_KEY`, model, timeout, retry and raises `MissingApiKeyError` when absent.

- [ ] **Step 4: Run translator tests**

Run: `python -m pytest tests/test_translator_core.py -q`

Expected: PASS.

## Task 5: Converter Markdown And Chapter Generation

**Files:**
- Create: `apps/converter_desktop/converter/markdown.py`
- Create: `apps/converter_desktop/converter/chapters.py`
- Modify: `apps/converter_desktop/converter/__init__.py`
- Create: `tests/test_converter_markdown.py`

- [ ] **Step 1: Write failing Markdown tests**

```python
from converter.chapters import build_chapters
from converter.markdown import render_block_markdown
from source_map_core import OcrBlock


def test_render_paragraph_includes_hidden_trace_comment():
    block = OcrBlock(block_id="p001_b003", page=1, type="paragraph", bbox=[72, 188, 510, 246], text="并网逆变器通常采用电流内环控制。")

    markdown = render_block_markdown(block)

    assert "<!-- block_id: p001_b003; page: 1; bbox: [72, 188, 510, 246] -->" in markdown
    assert "并网逆变器通常采用电流内环控制。" in markdown


def test_render_formula_prefers_latex():
    block = OcrBlock(block_id="eq_001", page=2, type="formula", bbox=[1, 2, 3, 4], latex="G_i(s)=K_p+\\frac{K_i}{s}")

    markdown = render_block_markdown(block)

    assert "$$" in markdown
    assert "G_i(s)" in markdown


def test_build_chapters_splits_on_headings():
    blocks = [
        OcrBlock(block_id="h1", page=1, type="heading", bbox=[], text="第一章 绪论", level=1),
        OcrBlock(block_id="p1", page=1, type="paragraph", bbox=[], text="正文"),
    ]

    chapters = build_chapters(blocks)

    assert chapters[0].chapter_id == "ch_001"
    assert chapters[0].title == "第一章 绪论"
    assert chapters[0].path == "chapters/001_chapter_1.md"
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `python -m pytest tests/test_converter_markdown.py -q`

Expected: FAIL because converter modules do not exist.

- [ ] **Step 3: Implement Markdown renderer and chapter splitter**

Implement heading, paragraph, formula, figure, table, caption, and footnote block rendering. Keep output deterministic and preserve trace comments.

- [ ] **Step 4: Run converter Markdown tests**

Run: `python -m pytest tests/test_converter_markdown.py -q`

Expected: PASS.

## Task 6: Build Orchestrator And CLI

**Files:**
- Create: `apps/converter_desktop/converter/builder.py`
- Create: `apps/converter_desktop/converter/cli.py`
- Create: `apps/converter_desktop/converter/__main__.py`
- Create: `tests/test_converter_cli.py`

- [ ] **Step 1: Write failing build test**

```python
import json
import subprocess
import sys

from bookmd_core import validate_bookmd


def test_cli_build_generates_valid_bookmd(tmp_path):
    sample = tmp_path / "ocr"
    sample.mkdir()
    (sample / "result.md").write_text("# 第一章 绪论\n\n内容", encoding="utf-8")
    (sample / "result.json").write_text(json.dumps({"blocks": [{"block_id": "h1", "page": 1, "type": "heading", "level": 1, "text": "第一章 绪论", "bbox": [0, 0, 10, 10]}, {"block_id": "p1", "page": 1, "type": "paragraph", "text": "并网逆变器", "bbox": [0, 10, 10, 20]}]}, ensure_ascii=False), encoding="utf-8")
    pdf = tmp_path / "original.pdf"
    pdf.write_bytes(b"%PDF-1.4\n% placeholder\n")
    output = tmp_path / "out.bookmd"

    completed = subprocess.run([
        sys.executable, "-m", "converter", "build",
        "--source-pdf", str(pdf),
        "--ocr-output", str(sample),
        "--output", str(output),
        "--translate", "false",
    ], check=False, text=True, capture_output=True)

    assert completed.returncode == 0, completed.stderr
    assert validate_bookmd(output).valid is True
```

- [ ] **Step 2: Run test and confirm failure**

Run: `python -m pytest tests/test_converter_cli.py -q`

Expected: FAIL because CLI does not exist.

- [ ] **Step 3: Implement `build` and `validate` commands**

Use `argparse` for minimal dependencies. Implement:

```bash
python -m converter build --source-pdf ... --ocr-output ... --output ... --translate false
python -m converter validate samples/bookmd_sample/sample.bookmd
```

Build must create a temporary staging directory, generate all required JSON files, copy assets/source PDF, package zip, and validate output.

- [ ] **Step 4: Run CLI tests**

Run: `python -m pytest tests/test_converter_cli.py -q`

Expected: PASS.

## Task 7: Sample Data And End-To-End Fixture

**Files:**
- Create: `samples/ocr_output_sample/result.json`
- Create: `samples/ocr_output_sample/result.md`
- Create: `samples/ocr_output_sample/original.pdf`
- Create: `samples/ocr_output_sample/assets/images/page_001_fig_001.svg`
- Create: `samples/ocr_output_sample/assets/formulas/page_001_formula_001.svg`
- Create: `samples/ocr_output_sample/assets/tables/page_001_table_001.svg`
- Create: `samples/bookmd_sample/.gitkeep`
- Create: `tests/test_sample_e2e.py`

- [ ] **Step 1: Write failing sample E2E test**

```python
import json
import subprocess
import sys
import zipfile


def test_sample_ocr_output_builds_bookmd(tmp_path):
    output = tmp_path / "sample.bookmd"

    completed = subprocess.run([
        sys.executable, "-m", "converter", "build",
        "--source-pdf", "samples/ocr_output_sample/original.pdf",
        "--ocr-output", "samples/ocr_output_sample",
        "--output", str(output),
        "--translate", "false",
    ], check=False, text=True, capture_output=True)

    assert completed.returncode == 0, completed.stderr
    with zipfile.ZipFile(output) as zf:
        source_map = json.loads(zf.read("source_map.json"))
        search_index = json.loads(zf.read("search_index.json"))

    assert any(item["block_id"] == "p001_b002" for item in source_map["blocks"])
    assert any("并网逆变器" in item["text"] for item in search_index["items"])
```

- [ ] **Step 2: Run test and confirm sample missing failure**

Run: `python -m pytest tests/test_sample_e2e.py -q`

Expected: FAIL because sample files do not exist yet.

- [ ] **Step 3: Add sample OCR data and tiny SVG/PDF placeholders**

Include blocks for heading, Chinese paragraph, English paragraph, formula, figure, table, caption, bbox, and asset paths.

- [ ] **Step 4: Run sample E2E test**

Run: `python -m pytest tests/test_sample_e2e.py -q`

Expected: PASS.

## Task 8: Markdown Renderer Assets

**Files:**
- Create: `packages/markdown_renderer/renderer/bookmd-renderer.html`
- Create: `packages/markdown_renderer/renderer/bookmd-renderer.css`
- Create: `packages/markdown_renderer/renderer/bookmd-renderer.js`
- Create: `tests/test_renderer_assets.py`

- [ ] **Step 1: Write failing asset existence test**

```python
from pathlib import Path


def test_renderer_assets_include_custom_block_hooks():
    root = Path("packages/markdown_renderer/renderer")

    html = (root / "bookmd-renderer.html").read_text(encoding="utf-8")
    css = (root / "bookmd-renderer.css").read_text(encoding="utf-8")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")

    assert "bookmd-content" in html
    assert ".bookmd-figure" in css
    assert "window.BookMDReader" in js
    assert "block_id" in js
```

- [ ] **Step 2: Run test and confirm failure**

Run: `python -m pytest tests/test_renderer_assets.py -q`

Expected: FAIL because renderer assets do not exist.

- [ ] **Step 3: Implement static renderer assets**

HTML provides WebView shell. CSS supports mobile typography, figure/table/formula blocks, scroll/paged mode classes, dark theme. JS exposes `window.BookMDReader.loadChapter(payload)` and block click callbacks.

- [ ] **Step 4: Run asset test**

Run: `python -m pytest tests/test_renderer_assets.py -q`

Expected: PASS.

## Task 9: Android Reader Skeleton

**Files:**
- Create: `apps/reader-android/settings.gradle.kts`
- Create: `apps/reader-android/build.gradle.kts`
- Create: `apps/reader-android/app/build.gradle.kts`
- Create: `apps/reader-android/app/src/main/AndroidManifest.xml`
- Create: `apps/reader-android/app/src/main/java/com/bookmd/reader/MainActivity.kt`
- Create: `apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt`
- Create: `apps/reader-android/app/src/main/java/com/bookmd/reader/data/SourceMapRepository.kt`
- Create: `apps/reader-android/app/src/main/assets/bookmd-renderer.html`
- Create: `tests/test_android_skeleton.py`

- [ ] **Step 1: Write failing skeleton test**

```python
from pathlib import Path


def test_android_reader_skeleton_has_webview_and_repository_boundaries():
    root = Path("apps/reader-android")

    assert (root / "settings.gradle.kts").exists()
    main = (root / "app/src/main/java/com/bookmd/reader/MainActivity.kt").read_text(encoding="utf-8")
    repo = (root / "app/src/main/java/com/bookmd/reader/data/BookRepository.kt").read_text(encoding="utf-8")

    assert "WebView" in main
    assert "BookRepository" in repo
    assert "book.json" in repo
```

- [ ] **Step 2: Run test and confirm failure**

Run: `python -m pytest tests/test_android_skeleton.py -q`

Expected: FAIL because Android files do not exist.

- [ ] **Step 3: Create minimal Android skeleton**

Add a standard Kotlin Android project skeleton with WebView enabled, repository classes for unzip/read manifest, and renderer asset placeholder copied from markdown renderer.

- [ ] **Step 4: Run skeleton test**

Run: `python -m pytest tests/test_android_skeleton.py -q`

Expected: PASS.

## Task 10: Documentation And Full Verification

**Files:**
- Create: `docs/architecture.md`
- Create: `docs/bookmd_spec.md`
- Create: `docs/windows_converter_usage.md`
- Create: `docs/android_reader_usage.md`
- Create: `docs/deepseek_translation.md`
- Create: `docs/troubleshooting.md`
- Modify: `README.md`

- [ ] **Step 1: Write or update docs with exact MVP commands**

Document:

```bash
python -m pytest
python -m converter build --source-pdf samples/ocr_output_sample/original.pdf --ocr-output samples/ocr_output_sample --output samples/bookmd_sample/sample.bookmd --translate false
python -m converter validate samples/bookmd_sample/sample.bookmd
```

- [ ] **Step 2: Run all tests**

Run: `python -m pytest`

Expected: PASS.

- [ ] **Step 3: Generate sample BookMD**

Run:

```bash
python -m converter build --source-pdf samples/ocr_output_sample/original.pdf --ocr-output samples/ocr_output_sample --output samples/bookmd_sample/sample.bookmd --translate false
```

Expected: command exits 0 and writes `samples/bookmd_sample/sample.bookmd`.

- [ ] **Step 4: Validate sample BookMD**

Run:

```bash
python -m converter validate samples/bookmd_sample/sample.bookmd
```

Expected: command exits 0 and reports valid package.

- [ ] **Step 5: Final status check**

Run: `git status --short`

Expected: only intentional files are modified or untracked.

## Self-Review

- The plan covers the MVP design: Python build/validate loop, sample data, renderer assets, Android skeleton, docs, and verification.
- The plan does not include OCR/Paddle/CUDA/cloud/account/commercial features.
- Tests are written before each production component.
- The tasks are sequential and each has an explicit verification command.
