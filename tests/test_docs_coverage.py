from pathlib import Path


def test_release_docs_cover_converter_translation_and_acceptance():
    required = {
        "README.md": ["Phase 7", "verify_release.py", "OCR_API_URL"],
        "docs/deepseek_translation.md": ["DEEPSEEK_API_KEY", "cache", "privacy"],
        "docs/windows_converter_usage.md": ["translation:", "bilingual", "cache_path", "build-from-pdf", "ocr-health", "--batch-size"],
        "docs/release_checklist.md": ["Python tests", "Android APK", "Known limitations"],
        "docs/final_acceptance.md": ["Requirement", "Evidence", "Status", "OCR HTTP API"],
        "docs/phase7.md": ["OCR_API_URL", "build-from-pdf", "No local OCR model deployment"],
    }

    for path, markers in required.items():
        text = Path(path).read_text(encoding="utf-8")
        for marker in markers:
            assert marker in text
