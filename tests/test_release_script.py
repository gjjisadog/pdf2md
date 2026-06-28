from pathlib import Path


def test_release_verification_script_documents_required_checks():
    script = Path("scripts/verify_release.py").read_text(encoding="utf-8")

    assert "python -m pytest" in script
    assert "converter" in script
    assert "validate" in script
    assert "assembleDebug" in script
    assert "ANDROID_HOME" in script
