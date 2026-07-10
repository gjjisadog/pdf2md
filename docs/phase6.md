# Phase 6 Scope

Phase 6 is the final release and acceptance phase for the personal BookMD MVP. It turns the working codebase into a clear, repeatable local delivery package with documentation, verification scripts, and an explicit limitations list.

## Goals

- Complete user-facing documentation:
  - README quickstart
  - Windows converter usage
  - DeepSeek translation setup
  - Android reader usage
  - troubleshooting
  - final release checklist
- Provide a one-command or near-one-command release verification path.
- Regenerate and validate the sample `.bookmd`.
- Build the Android debug APK and document where it is produced.
- Define emulator/manual acceptance steps for:
  - import/open `.bookmd`
  - shelf
  - TOC
  - reader
  - settings
  - media viewer
  - source map
  - search
  - progress restore
- Record known limitations and next-stage upgrade ideas.

## Non-Goals

- No commercial installer.
- No app store packaging.
- No cloud sync or account system.
- No real OCR deployment.
- No paid API live test as a required automated check.

## Implementation Plan

1. Release Verification Script
   - Add `scripts/verify_release.py` or equivalent shell-safe Python script.
   - Run Python tests.
   - Build and validate a temporary sample `.bookmd`.
   - Check renderer asset parity.
   - Optionally run Android `assembleDebug` when `ANDROID_HOME` is available.

2. Documentation Completion
   - Update README with phase five/six status.
   - Expand Windows converter usage with config examples.
   - Expand DeepSeek docs with env vars, cache, retry, and privacy notes.
   - Expand Android docs with install, sample import, settings, and manual test steps.
   - Add release checklist doc.

3. Sample And Artifact Policy
   - Keep generated APKs and temporary release outputs out of git.
   - Regenerate sample `.bookmd` only if deterministic and useful to commit.
   - Document exact commands to recreate artifacts locally.

4. Final Acceptance Matrix
   - Create a table mapping product requirements to verification evidence.
   - Mark unsupported items as known limitations instead of silently implying support.

5. Final Cleanup
   - Ensure `.gitignore` covers local build outputs.
   - Ensure docs do not conflict with current code.
   - Run final verification commands and record results.

## Acceptance Criteria

- `python scripts/verify_release.py` passes on a machine with Python dependencies.
- `python -m pytest` passes.
- Sample `.bookmd` builds and validates.
- Android APK builds when Android SDK/JDK are available.
- README and docs contain enough detail for the user to run converter and reader without relying on chat history.
- Final release checklist clearly states what is verified, what is manual, and what remains future work.

## Completion Record

Completed on 2026-06-28.

Implemented:

- `scripts/verify_release.py` for Python tests, sample `.bookmd` build/validate, renderer parity, and optional Android `assembleDebug`.
- `docs/release_checklist.md` and `docs/final_acceptance.md`.
- README, Windows converter, DeepSeek translation, Android reader, and troubleshooting documentation updates.

Verification:

```bash
python -m pytest
python scripts/verify_release.py
ANDROID_HOME=/tmp/bookmd-android-sdk ANDROID_SDK_ROOT=/tmp/bookmd-android-sdk JAVA_HOME=/tmp/bookmd-jdk17/Contents/Home ./gradlew assembleDebug
```

Results:

- `python -m pytest`: latest full local run passed with 106 tests.
- `python scripts/verify_release.py`: release path is covered by the release verifier and focused release-script tests.
- `python scripts/verify_android_reader.py`: Android renderer/static checks passed and debug APK build was successful.
- `ANDROID_HOME=/tmp/bookmd-android-sdk ANDROID_SDK_ROOT=/tmp/bookmd-android-sdk python scripts/verify_android_reader.py --device-smoke --bookmd tmp/real_pdf_boundary/pdfkit_assets_check/formula_svpwm_assets.bookmd --search-term SVPWM --artifacts-dir tmp/android_reader_verify`: passed on `emulator-5554`, covering shelf open, reader open, search jump, source-map dialog, and original PDF page open.
- `ANDROID_HOME=/tmp/bookmd-android-sdk ANDROID_SDK_ROOT=/tmp/bookmd-android-sdk python scripts/verify_android_reader.py --device-smoke --bookmd tmp/real_pdf_boundary/formula_svpwm/formula_svpwm.bookmd --import-via-picker --artifacts-dir tmp/android_reader_verify_picker`: passed on `emulator-5554`, covering Android DocumentsUI file-picker import before continuing through the reader/source-map/PDF-page smoke.
- `ANDROID_HOME=/tmp/bookmd-android-sdk ANDROID_SDK_ROOT=/tmp/bookmd-android-sdk python scripts/verify_android_reader.py --device-smoke --bookmd tmp/real_pdf_boundary/formula_svpwm/formula_svpwm.bookmd --verify-progress --artifacts-dir tmp/android_reader_verify_progress`: passed on `emulator-5554`, covering reading progress persistence, app force-stop, shelf reopen, and direct restore into the reader before continuing to source-map/PDF-page smoke.
- Android debug APK: BUILD SUCCESSFUL with local SDK/JDK paths.

APK path:

```text
apps/reader-android/app/build/outputs/apk/debug/app-debug.apk
```

Remaining manual acceptance remains documented in `docs/release_checklist.md` for settings and media viewer checks.
