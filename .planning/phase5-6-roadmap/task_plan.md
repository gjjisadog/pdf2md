# Phase 5 And 6 Roadmap

## Goal

Plan the remaining product work after phase four: phase five hardens the Windows converter and translation pipeline, and phase six turns the repository into a documented, verifiable personal release.

## Status

- Planning: complete
- Implementation: complete
- Verification: complete

## Phase 5 Summary

Phase five focuses on converter and translator production readiness:

- Mockable DeepSeek client.
- JSON response parsing and block alignment.
- Translation cache and resumable translation.
- Term extraction and `terms.json`.
- Bilingual Markdown output and richer `translation.json`.
- Converter diagnostics, logs, config validation, and Windows path robustness.

## Phase 6 Summary

Phase six focuses on final delivery:

- README and docs completed for converter, Android reader, release, and troubleshooting.
- Release verification script/checklist.
- Sample `.bookmd` regeneration and validation.
- Android APK build instructions and emulator/manual acceptance checklist.
- Known limitations and upgrade roadmap.

## Verification Commands

```bash
python -m pytest
python scripts/verify_release.py
python -m converter build --source-pdf samples/ocr_output_sample/original.pdf --ocr-output samples/ocr_output_sample --output /tmp/bookmd-release/sample.bookmd --translate false
python -m converter validate /tmp/bookmd-release/sample.bookmd
cd apps/reader-android
ANDROID_HOME=/tmp/bookmd-android-sdk ANDROID_SDK_ROOT=/tmp/bookmd-android-sdk JAVA_HOME=/tmp/bookmd-jdk17/Contents/Home ./gradlew assembleDebug
```

## Completion Notes

- `translator_core` now includes mockable DeepSeek translation, strict response parsing, JSONL cache storage, and deterministic terms extraction.
- Converter translation now writes translated chapters, `terms.json`, richer `translation.json`, translated source map entries, and translated search index entries.
- Release verification is covered by `scripts/verify_release.py`, `docs/release_checklist.md`, and `docs/final_acceptance.md`.
- Android debug APK build succeeded with local SDK/JDK paths.

## Risks

| Risk | Mitigation |
| --- | --- |
| Real DeepSeek calls make tests flaky or costly | Use injectable HTTP transport and mocked tests; keep live API as manual verification. |
| Translation corrupts Markdown structure | Translate block text only, preserve block IDs and custom block syntax, add alignment tests. |
| Cache format becomes hard to migrate | Use JSONL records with explicit schema version and cache key. |
| Final release accidentally commits build artifacts | Document generated artifacts and keep APK/temp outputs ignored. |
