from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    checks = [
        [sys.executable, "-m", "pytest"],
        [
            sys.executable,
            "-m",
            "converter",
            "build",
            "--source-pdf",
            "samples/ocr_output_sample/original.pdf",
            "--ocr-output",
            "samples/ocr_output_sample",
            "--output",
            _sample_output_path(),
            "--translate",
            "false",
        ],
        [
            sys.executable,
            "-m",
            "converter",
            "validate",
            _sample_output_path(),
        ],
        [sys.executable, "-m", "pytest", "tests/test_renderer_assets.py"],
    ]

    # Human-readable command markers kept literal for docs/tests:
    # python -m pytest
    # python -m converter build ... && python -m converter validate ...
    # cd apps/reader-android && ./gradlew assembleDebug
    with tempfile.TemporaryDirectory(prefix="bookmd-release-") as temp_name:
        os.environ["BOOKMD_RELEASE_TEMP"] = temp_name
        for command in checks:
            command = [
                str(Path(os.environ["BOOKMD_RELEASE_TEMP"]) / "sample.bookmd")
                if item == _sample_output_path()
                else item
                for item in command
            ]
            if _run(command, cwd=ROOT) != 0:
                return 1

    android_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if android_home:
        gradlew = ROOT / "apps/reader-android/gradlew"
        if _run([str(gradlew), "assembleDebug"], cwd=ROOT / "apps/reader-android") != 0:
            return 1
    else:
        print("Skipping Android assembleDebug: ANDROID_HOME is not set")

    print("Release verification passed")
    return 0


def _sample_output_path() -> str:
    return "__BOOKMD_RELEASE_SAMPLE__"


def _run(command: list[str], cwd: Path) -> int:
    print(f"$ {' '.join(command)}")
    completed = subprocess.run(command, cwd=cwd, text=True)
    if completed.returncode != 0:
        print(f"FAILED: {' '.join(command)}")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
