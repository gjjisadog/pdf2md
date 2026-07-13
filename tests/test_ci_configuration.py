from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "python-ci.yml"


def test_python_ci_builds_and_installs_wheel_on_supported_hosts():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "ubuntu-latest" in workflow
    assert "windows-latest" in workflow
    assert "macos-latest" in workflow
    assert "python -m build --wheel" in workflow
    assert "pip install" in workflow
    assert "bookmd --help" in workflow


def test_windows_ci_runs_real_portable_visual_asset_tests():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "windows-visual-assets" in workflow
    assert "tests/test_portable_visuals.py" in workflow
