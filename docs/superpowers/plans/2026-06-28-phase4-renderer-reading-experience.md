# Phase 4 Renderer And Reading Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the BookMD renderer and Android reading experience so professional Markdown content, media, source tracing, settings, and progress work from one shared renderer source.

**Architecture:** `packages/markdown_renderer/renderer` becomes the source renderer asset set. Android copies or embeds those assets into `apps/reader-android/app/src/main/assets` and passes chapter Markdown plus reading config into `window.BookMDReader`. Android owns file import, settings persistence, progress persistence, media viewer, and navigation.

**Tech Stack:** Python 3.12/pytest, JavaScript renderer assets, Kotlin Android Activity/WebView, Android SharedPreferences, Gradle 7.6.4, Android SDK 33.

---

## File Map

- Modify `packages/markdown_renderer/renderer/bookmd-renderer.html`: keep external CSS/JS references and stable root element.
- Modify `packages/markdown_renderer/renderer/bookmd-renderer.css`: add layout, language-mode, table, footnote, code, and media viewer friendly styles.
- Modify `packages/markdown_renderer/renderer/bookmd-renderer.js`: harden custom block parser, language mode filtering, search highlighting, anchors, footnotes, and progress APIs.
- Create `scripts/sync_android_renderer_assets.py`: copy package renderer assets into Android assets.
- Modify `apps/reader-android/app/src/main/assets/bookmd-renderer.html`: generated/copied renderer HTML.
- Create `apps/reader-android/app/src/main/assets/bookmd-renderer.css`: generated/copied renderer CSS.
- Create `apps/reader-android/app/src/main/assets/bookmd-renderer.js`: generated/copied renderer JS.
- Modify `apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt`: load packaged HTML, pass reading config, save/restore progress, support settings/media bridge.
- Modify `apps/reader-android/app/src/main/java/com/bookmd/reader/settings/ReaderSettings.kt`: persist settings and expose mode/theme/font/line-height.
- Create `apps/reader-android/app/src/main/java/com/bookmd/reader/SettingsActivity.kt`: simple settings screen.
- Create `apps/reader-android/app/src/main/java/com/bookmd/reader/ImageViewerActivity.kt`: full-screen local image/table viewer.
- Modify `apps/reader-android/app/src/main/java/com/bookmd/reader/web/BookMdWebBridge.kt`: route media taps to viewer and progress callbacks.
- Modify `apps/reader-android/app/src/main/java/com/bookmd/reader/data/ReadingProgressStore.kt`: save chapter path and scroll/block progress.
- Modify `apps/reader-android/app/src/main/AndroidManifest.xml`: register settings and image viewer activities.
- Modify `tests/test_renderer_assets.py`: add renderer grammar and parity assertions.
- Modify `tests/test_android_skeleton.py`: assert settings/media/progress wiring.
- Create `docs/phase4.md`: phase summary and verification record.
- Modify `README.md` and `docs/android_reader_usage.md`: update phase four usage notes.

## Task 1: Renderer Asset Parity

**Files:**
- Create: `scripts/sync_android_renderer_assets.py`
- Modify: `tests/test_renderer_assets.py`
- Modify: `apps/reader-android/app/src/main/assets/bookmd-renderer.html`
- Create: `apps/reader-android/app/src/main/assets/bookmd-renderer.css`
- Create: `apps/reader-android/app/src/main/assets/bookmd-renderer.js`

- [ ] **Step 1: Write failing parity test**

Add this test to `tests/test_renderer_assets.py`:

```python
from pathlib import Path


def test_android_renderer_assets_match_package_renderer():
    package = Path("packages/markdown_renderer/renderer")
    android = Path("apps/reader-android/app/src/main/assets")

    for name in ["bookmd-renderer.html", "bookmd-renderer.css", "bookmd-renderer.js"]:
        assert (android / name).read_text(encoding="utf-8") == (package / name).read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
python -m pytest tests/test_renderer_assets.py::test_android_renderer_assets_match_package_renderer -q
```

Expected: FAIL because Android currently has an inline renderer that differs from package assets.

- [ ] **Step 3: Add sync script**

Create `scripts/sync_android_renderer_assets.py`:

```python
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_RENDERER = ROOT / "packages/markdown_renderer/renderer"
ANDROID_ASSETS = ROOT / "apps/reader-android/app/src/main/assets"
ASSET_NAMES = ["bookmd-renderer.html", "bookmd-renderer.css", "bookmd-renderer.js"]


def main() -> None:
    ANDROID_ASSETS.mkdir(parents=True, exist_ok=True)
    for name in ASSET_NAMES:
        shutil.copyfile(PACKAGE_RENDERER / name, ANDROID_ASSETS / name)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Sync assets**

Run:

```bash
python scripts/sync_android_renderer_assets.py
```

Expected: Android assets now contain HTML/CSS/JS matching package renderer.

- [ ] **Step 5: Run parity test**

Run:

```bash
python -m pytest tests/test_renderer_assets.py::test_android_renderer_assets_match_package_renderer -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/sync_android_renderer_assets.py apps/reader-android/app/src/main/assets tests/test_renderer_assets.py
git commit -m "test: keep android renderer assets in sync"
```

## Task 2: Renderer Grammar Hardening

**Files:**
- Modify: `packages/markdown_renderer/renderer/bookmd-renderer.js`
- Modify: `packages/markdown_renderer/renderer/bookmd-renderer.css`
- Modify: `tests/test_renderer_assets.py`
- Run: `python scripts/sync_android_renderer_assets.py`

- [ ] **Step 1: Add failing static tests for supported grammar**

Add assertions to `tests/test_renderer_assets.py`:

```python
def test_renderer_supports_phase_four_markdown_features():
    js = Path("packages/markdown_renderer/renderer/bookmd-renderer.js").read_text(encoding="utf-8")
    css = Path("packages/markdown_renderer/renderer/bookmd-renderer.css").read_text(encoding="utf-8")

    assert "renderMarkdownTable" in js
    assert "renderCodeFence" in js
    assert "renderFootnote" in js
    assert "renderReferenceLink" in js
    assert "data-language-mode" in js
    assert ".bookmd-code" in css
    assert ".bookmd-footnote" in css
    assert ".bookmd-table-scroll" in css
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
python -m pytest tests/test_renderer_assets.py::test_renderer_supports_phase_four_markdown_features -q
```

Expected: FAIL until the named renderer paths exist.

- [ ] **Step 3: Implement renderer support**

Add focused renderer functions in `bookmd-renderer.js`:

```javascript
function renderCodeFence(language, lines) {
  return `<pre class="bookmd-code"><code data-language="${escapeHtml(language)}">${escapeHtml(lines.join("\n"))}</code></pre>`;
}

function renderMarkdownTable(lines) {
  const rows = lines.map((line) => line.split("|").slice(1, -1).map((cell) => cell.trim()));
  const header = rows[0] || [];
  const body = rows.slice(2);
  const th = header.map((cell) => `<th>${escapeHtml(cell)}</th>`).join("");
  const trs = body.map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("");
  return `<div class="bookmd-table-scroll"><table><thead><tr>${th}</tr></thead><tbody>${trs}</tbody></table></div>`;
}

function renderFootnote(id, text) {
  return `<aside class="bookmd-footnote" id="fn-${escapeHtml(id)}">${escapeHtml(text)}</aside>`;
}

function renderReferenceLink(label, href) {
  return `<a class="bookmd-reference" href="${escapeHtml(href)}">${escapeHtml(label)}</a>`;
}
```

Wire these functions into `renderMarkdown(markdown)` while preserving existing trace comments and `data-block-id`.

- [ ] **Step 4: Add CSS**

Add styles:

```css
.bookmd-table-scroll {
  overflow-x: auto;
  margin: 1rem 0;
}

.bookmd-table-scroll table {
  border-collapse: collapse;
  min-width: 100%;
}

.bookmd-table-scroll th,
.bookmd-table-scroll td {
  border: 1px solid var(--bookmd-rule);
  padding: 0.45rem 0.6rem;
}

.bookmd-code {
  overflow-x: auto;
  padding: 0.75rem;
  border: 1px solid var(--bookmd-rule);
  background: color-mix(in srgb, var(--bookmd-bg), var(--bookmd-text) 6%);
}
```

- [ ] **Step 5: Sync Android renderer assets**

Run:

```bash
python scripts/sync_android_renderer_assets.py
```

- [ ] **Step 6: Run renderer tests**

Run:

```bash
python -m pytest tests/test_renderer_assets.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/markdown_renderer/renderer apps/reader-android/app/src/main/assets tests/test_renderer_assets.py
git commit -m "feat: harden bookmd renderer grammar"
```

## Task 3: Reading Config And Settings

**Files:**
- Modify: `apps/reader-android/app/src/main/java/com/bookmd/reader/settings/ReaderSettings.kt`
- Create: `apps/reader-android/app/src/main/java/com/bookmd/reader/SettingsActivity.kt`
- Modify: `apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt`
- Modify: `apps/reader-android/app/src/main/AndroidManifest.xml`
- Modify: `tests/test_android_skeleton.py`

- [ ] **Step 1: Add failing Android wiring test**

Add to `tests/test_android_skeleton.py`:

```python
def test_android_reader_has_settings_screen_and_modes():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    manifest = Path("apps/reader-android/app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    settings = (root / "settings/ReaderSettings.kt").read_text(encoding="utf-8")
    reader = (root / "ReaderActivity.kt").read_text(encoding="utf-8")

    assert "SettingsActivity" in manifest
    assert (root / "SettingsActivity.kt").exists()
    assert "fontSize" in settings
    assert "lineHeight" in settings
    assert "theme" in settings
    assert "layout" in settings
    assert "languageMode" in settings
    assert "reading_config.json" in reader
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
python -m pytest tests/test_android_skeleton.py::test_android_reader_has_settings_screen_and_modes -q
```

Expected: FAIL until settings screen and config loading are added.

- [ ] **Step 3: Implement persisted settings model**

Update `ReaderSettings.kt` to read/write SharedPreferences:

```kotlin
data class ReaderSettings(
    val fontSize: Int = 18,
    val lineHeight: Double = 1.75,
    val theme: String = "light",
    val layout: String = "paged",
    val languageMode: String = "zh",
)
```

Add companion/load/save methods using keys `font_size`, `line_height`, `theme`, `layout`, `language_mode`.

- [ ] **Step 4: Load defaults from BookMD config**

In `ReaderActivity.kt`, read `File(bookDir, "reading_config.json")` and merge defaults with persisted settings before building the payload config.

- [ ] **Step 5: Add simple SettingsActivity**

Implement a minimal vertical layout with controls for font size, line height, theme, layout, and language mode. Keep controls simple for phase four: buttons or text rows that cycle values are acceptable.

- [ ] **Step 6: Register activity**

Add `SettingsActivity` to `AndroidManifest.xml`.

- [ ] **Step 7: Run tests and build**

Run:

```bash
python -m pytest tests/test_android_skeleton.py -q
cd apps/reader-android
ANDROID_HOME=/tmp/bookmd-android-sdk ANDROID_SDK_ROOT=/tmp/bookmd-android-sdk ./gradlew --no-daemon assembleDebug
```

Expected: tests PASS and Android build SUCCESSFUL.

- [ ] **Step 8: Commit**

```bash
git add apps/reader-android/app/src/main/java/com/bookmd/reader apps/reader-android/app/src/main/AndroidManifest.xml tests/test_android_skeleton.py
git commit -m "feat: add android reader settings modes"
```

## Task 4: Media Viewer Bridge

**Files:**
- Create: `apps/reader-android/app/src/main/java/com/bookmd/reader/ImageViewerActivity.kt`
- Modify: `apps/reader-android/app/src/main/java/com/bookmd/reader/web/BookMdWebBridge.kt`
- Modify: `apps/reader-android/app/src/main/AndroidManifest.xml`
- Modify: `tests/test_android_skeleton.py`

- [ ] **Step 1: Add failing wiring test**

Add:

```python
def test_android_reader_has_image_viewer_for_media_taps():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    manifest = Path("apps/reader-android/app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    bridge = (root / "web/BookMdWebBridge.kt").read_text(encoding="utf-8")

    assert "ImageViewerActivity" in manifest
    assert (root / "ImageViewerActivity.kt").exists()
    assert "onImageSelected" in bridge
    assert "EXTRA_MEDIA_URI" in bridge or "media_uri" in bridge
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python -m pytest tests/test_android_skeleton.py::test_android_reader_has_image_viewer_for_media_taps -q
```

Expected: FAIL until viewer exists.

- [ ] **Step 3: Implement ImageViewerActivity**

Create a full-screen `ImageView` that loads a `file://` URI from intent extra `media_uri`, uses `adjustViewBounds = true`, and dark background.

- [ ] **Step 4: Wire bridge**

In `BookMdWebBridge.onImageSelected(src: String?)`, launch `ImageViewerActivity` with `media_uri`.

- [ ] **Step 5: Run tests and emulator smoke path**

Run:

```bash
python -m pytest tests/test_android_skeleton.py -q
cd apps/reader-android
ANDROID_HOME=/tmp/bookmd-android-sdk ANDROID_SDK_ROOT=/tmp/bookmd-android-sdk ./gradlew --no-daemon assembleDebug
```

Then install on emulator and tap a figure/table image.

- [ ] **Step 6: Commit**

```bash
git add apps/reader-android/app/src/main/java/com/bookmd/reader apps/reader-android/app/src/main/AndroidManifest.xml tests/test_android_skeleton.py
git commit -m "feat: open bookmd media fullscreen"
```

## Task 5: Reading Progress

**Files:**
- Modify: `packages/markdown_renderer/renderer/bookmd-renderer.js`
- Modify: `apps/reader-android/app/src/main/java/com/bookmd/reader/data/ReadingProgressStore.kt`
- Modify: `apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt`
- Modify: `tests/test_android_skeleton.py`

- [ ] **Step 1: Add failing tests**

Add static assertions:

```python
def test_android_reader_persists_reading_progress():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    progress = (root / "data/ReadingProgressStore.kt").read_text(encoding="utf-8")
    reader = (root / "ReaderActivity.kt").read_text(encoding="utf-8")
    js = Path("packages/markdown_renderer/renderer/bookmd-renderer.js").read_text(encoding="utf-8")

    assert "saveProgress" in progress
    assert "readProgress" in progress
    assert "currentProgress" in js
    assert "restoreProgress" in js
    assert "ReadingProgressStore" in reader
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python -m pytest tests/test_android_skeleton.py::test_android_reader_persists_reading_progress -q
```

Expected: FAIL until APIs exist.

- [ ] **Step 3: Add renderer progress APIs**

Implement in `bookmd-renderer.js`:

```javascript
function currentProgress() {
  return {
    scroll_y: window.scrollY || 0,
    block_id: nearestVisibleBlockId(),
  };
}

function restoreProgress(progress) {
  if (progress && progress.block_id && jumpToBlock(progress.block_id)) return true;
  if (progress && Number.isFinite(progress.scroll_y)) {
    window.scrollTo(0, progress.scroll_y);
    return true;
  }
  return false;
}
```

Export both on `window.BookMDReader`.

- [ ] **Step 4: Persist in Android**

Store progress key as `bookDir.name + ":" + chapterPath`. Save on pause via `evaluateJavascript("window.BookMDReader.currentProgress()")`, parse JSON, persist chapter path, block ID, and scroll Y. Restore after chapter load by calling `restoreProgress`.

- [ ] **Step 5: Sync assets and verify**

Run:

```bash
python scripts/sync_android_renderer_assets.py
python -m pytest
cd apps/reader-android
ANDROID_HOME=/tmp/bookmd-android-sdk ANDROID_SDK_ROOT=/tmp/bookmd-android-sdk ./gradlew --no-daemon assembleDebug
```

Expected: tests PASS and build SUCCESSFUL.

- [ ] **Step 6: Commit**

```bash
git add packages/markdown_renderer/renderer apps/reader-android/app/src/main/assets apps/reader-android/app/src/main/java/com/bookmd/reader tests/test_android_skeleton.py
git commit -m "feat: persist android reading progress"
```

## Task 6: Documentation And Final Verification

**Files:**
- Modify: `docs/phase4.md`
- Modify: `README.md`
- Modify: `docs/android_reader_usage.md`
- Modify: `docs/troubleshooting.md`

- [ ] **Step 1: Update docs**

Document:
- renderer asset sync command
- supported renderer blocks
- Android settings behavior
- emulator verification flow
- known limitation: no PDF bbox screenshot yet

- [ ] **Step 2: Run full verification**

Run:

```bash
python -m pytest
rm -rf /tmp/bookmd-phase4 && mkdir -p /tmp/bookmd-phase4
python -m converter build --source-pdf samples/ocr_output_sample/original.pdf --ocr-output samples/ocr_output_sample --output /tmp/bookmd-phase4/sample.bookmd --translate false
python -m converter validate /tmp/bookmd-phase4/sample.bookmd
cd apps/reader-android
ANDROID_HOME=/tmp/bookmd-android-sdk ANDROID_SDK_ROOT=/tmp/bookmd-android-sdk ./gradlew --no-daemon assembleDebug
```

Expected:
- pytest reports all tests passed
- converter writes `/tmp/bookmd-phase4/sample.bookmd`
- validator reports valid BookMD
- Gradle reports BUILD SUCCESSFUL

- [ ] **Step 3: Emulator acceptance**

Install APK, import or inject sample `.bookmd`, then verify:
- shelf opens
- TOC opens
- reader renders figure/formula/table
- settings change font/theme/layout/language mode
- image/table tap opens full-screen viewer
- search jumps to a result
- source-map dialog still shows page/type/bbox/text
- progress restores after closing and reopening reader

- [ ] **Step 4: Commit**

```bash
git add README.md docs
git commit -m "docs: record phase four renderer reading verification"
```

## Final Acceptance Checklist

- [ ] Android renderer assets match package renderer assets.
- [ ] Renderer tests cover custom blocks, media, tables, search, language mode, and progress APIs.
- [ ] Python tests pass.
- [ ] Sample `.bookmd` builds and validates.
- [ ] Android debug APK builds.
- [ ] Emulator verifies reading settings, media viewer, search jump, source-map dialog, and progress restore.

