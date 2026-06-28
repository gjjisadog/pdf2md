from pathlib import Path


def test_release_docs_cover_converter_translation_and_acceptance():
    required = {
        "README.md": ["Phase 6", "verify_release.py", "Android"],
        "docs/deepseek_translation.md": ["DEEPSEEK_API_KEY", "cache", "privacy"],
        "docs/windows_converter_usage.md": ["translation:", "bilingual", "cache_path"],
        "docs/release_checklist.md": ["Python tests", "Android APK", "Known limitations"],
        "docs/final_acceptance.md": ["Requirement", "Evidence", "Status"],
    }

    for path, markers in required.items():
        text = Path(path).read_text(encoding="utf-8")
        for marker in markers:
            assert marker in text
