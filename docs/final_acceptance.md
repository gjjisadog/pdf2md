# Final Acceptance

| Requirement | Evidence | Status |
| --- | --- | --- |
| Build `.bookmd` from OCR output | `python -m converter build --source-pdf samples/ocr_output_sample/original.pdf --ocr-output samples/ocr_output_sample --output ... --translate false` | Verified by release script |
| Validate `.bookmd` structure | `python -m converter validate ...` | Verified by release script |
| Preserve source map and search index | `tests/test_sample_e2e.py` | Verified |
| DeepSeek client is mockable | `tests/test_translator_core.py` fake transport | Verified |
| Translation cache avoids duplicate provider calls | `tests/test_converter_translation.py` | Verified |
| Terms and translation payloads are generated | `tests/test_converter_translation.py` | Verified |
| Android APK builds | `./gradlew assembleDebug` | Verified when Android SDK/JDK are installed |
| Android import/shelf/TOC/reader/search/source map/settings/media/progress | `docs/release_checklist.md` manual pass steps | Manual |
| OCR/Paddle local deployment | Out of scope for MVP | Known limitation |
| Commercial installer/app store package | Out of scope for MVP | Known limitation |
