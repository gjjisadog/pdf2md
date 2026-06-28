# Phase 6 Release And Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a repeatable local release flow and complete user-facing documentation for the personal BookMD MVP.

**Architecture:** Keep generated artifacts out of git. Add a Python release verification script that checks converter, package validation, renderer parity, tests, and Android build when toolchains are present. Documentation records exact commands, acceptance evidence, limitations, and future roadmap.

**Tech Stack:** Python 3.12, pytest, zipfile, pathlib, subprocess, Gradle wrapper, Android SDK when available.

**Execution status:** Completed on 2026-06-28. Verified with `python -m pytest`, `python scripts/verify_release.py`, and Android `assembleDebug` using local SDK/JDK paths.

---

## Task 1: Release Verification Script

**Files:**
- Create: `scripts/verify_release.py`
- Create: `tests/test_release_script.py`
- Modify: `docs/phase6.md`

- [ ] **Step 1: Write failing script existence test**

```python
from pathlib import Path


def test_release_verification_script_documents_required_checks():
    script = Path("scripts/verify_release.py")
    text = script.read_text(encoding="utf-8")

    assert "python -m pytest" in text
    assert "converter build" in text
    assert "converter validate" in text
    assert "assembleDebug" in text
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python -m pytest tests/test_release_script.py -q
```

Expected: FAIL because the script does not exist.

- [ ] **Step 3: Implement script**

Implement a Python script that:
- runs pytest
- builds `/tmp/bookmd-release/sample.bookmd`
- validates it
- checks renderer asset parity
- runs Android build only when `ANDROID_HOME` exists
- prints a clear summary

- [ ] **Step 4: Run script test and script**

Run:

```bash
python -m pytest tests/test_release_script.py -q
python scripts/verify_release.py
```

Expected: PASS on Python checks; Android build is either run or explicitly skipped with a message.

- [ ] **Step 5: Commit**

```bash
git add scripts/verify_release.py tests/test_release_script.py docs/phase6.md
git commit -m "feat: add release verification script"
```

## Task 2: Documentation Completion

**Files:**
- Modify: `README.md`
- Modify: `docs/windows_converter_usage.md`
- Modify: `docs/deepseek_translation.md`
- Modify: `docs/android_reader_usage.md`
- Modify: `docs/troubleshooting.md`
- Create: `docs/release_checklist.md`

- [ ] **Step 1: Add docs coverage test**

Add a test that checks required docs exist and mention:
- converter build
- converter validate
- DeepSeek env vars
- Android APK path
- release verification script
- no OCR deployment

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python -m pytest tests/test_docs_coverage.py -q
```

Expected: FAIL until docs are complete.

- [ ] **Step 3: Update docs**

Complete user-facing docs with copy-pasteable commands and privacy notes.

- [ ] **Step 4: Run docs test**

Run:

```bash
python -m pytest tests/test_docs_coverage.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md docs tests/test_docs_coverage.py
git commit -m "docs: complete release documentation"
```

## Task 3: Final Acceptance Matrix

**Files:**
- Create: `docs/final_acceptance.md`
- Modify: `docs/phase6.md`

- [ ] **Step 1: Write acceptance matrix**

Create a matrix with columns:
- requirement
- status
- verification command or manual check
- notes/limitations

Cover:
- converter
- `.bookmd`
- translation
- renderer
- Android reader
- search
- source map
- progress
- media viewing
- docs

- [ ] **Step 2: Validate no unsupported feature is implied**

Run:

```bash
rg -n "OCR|cloud|sync|account|payment|PDF region screenshot" README.md docs
```

Expected: Docs clearly mark these as non-goals or future work.

- [ ] **Step 3: Commit**

```bash
git add docs/final_acceptance.md docs/phase6.md
git commit -m "docs: add final acceptance matrix"
```

## Task 4: Final Verification And Handoff

**Files:**
- Modify: `docs/phase6.md`
- Modify: `.planning/phase5-6-roadmap/progress.md`

- [ ] **Step 1: Run full release verification**

Run:

```bash
python scripts/verify_release.py
```

Expected: PASS or Android skipped only when SDK env is absent.

- [ ] **Step 2: Run Android build when SDK is present**

Run:

```bash
cd apps/reader-android
ANDROID_HOME=/tmp/bookmd-android-sdk ANDROID_SDK_ROOT=/tmp/bookmd-android-sdk ./gradlew --no-daemon assembleDebug
```

Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Record final results**

Update `docs/phase6.md` with:
- test results
- sample build path
- APK path
- emulator/manual checks completed
- known limitations

- [ ] **Step 4: Commit**

```bash
git add docs/phase6.md .planning/phase5-6-roadmap/progress.md
git commit -m "docs: record final release verification"
```
