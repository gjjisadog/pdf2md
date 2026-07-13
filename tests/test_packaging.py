from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _project_table() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def test_pyproject_declares_installable_build_and_runtime_dependencies():
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert payload["build-system"]["build-backend"] == "setuptools.build_meta"
    project = payload["project"]
    assert project["requires-python"] == ">=3.11"
    dependencies = {item.split("[", 1)[0].split(">", 1)[0].split("=", 1)[0].lower() for item in project["dependencies"]}
    assert {"pypdf", "pypdfium2", "pillow", "jsonschema"} <= dependencies


def test_pyproject_exposes_bookmd_console_script_and_dev_dependencies():
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = payload["project"]

    assert project["scripts"]["bookmd"] == "converter.cli:main"
    optional = project["optional-dependencies"]["dev"]
    assert any(item.startswith("pytest") for item in optional)
    assert any(item.startswith("build") for item in optional)
