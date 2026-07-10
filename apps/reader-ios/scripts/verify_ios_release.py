#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
SAMPLE = REPO / "tmp" / "real_book_full_clean_toc.bookmd"
PROJECT = ROOT / "BookMDReader.xcodeproj"
SCHEME = "BookMDReader"


def run(
    command: list[str],
    *,
    timeout: int = 120,
    allow_failure: bool = False,
    echo_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(command))
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if echo_output and result.stdout:
        print(result.stdout, end="")
    if echo_output and result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0 and not allow_failure:
        raise subprocess.CalledProcessError(result.returncode, command)
    return result


def xcode_failure_summary(output: str) -> str:
    if "IDESimulatorFoundation" in output and "DVTDownloads" in output:
        return (
            "Xcode is installed but its simulator/private framework content is inconsistent. "
            "IDESimulatorFoundation cannot load because /Library/Developer/PrivateFrameworks/"
            "DVTDownloads.framework is missing a symbol required by this Xcode build."
        )
    if "A required plugin failed to load" in output:
        return "xcodebuild cannot load a required Xcode plug-in."
    if "timed out" in output.lower():
        return "xcodebuild timed out before it could inspect the project."
    return "xcodebuild failed before the iOS reader could be built or tested."


def verify_xcode_available(*, allow_xcode_blocked: bool) -> bool:
    try:
        version = run(["xcodebuild", "-version"], timeout=15, allow_failure=True)
    except subprocess.TimeoutExpired:
        message = "xcodebuild -version timed out"
        if allow_xcode_blocked:
            print(f"[xcode-blocked] {message}")
            return False
        raise RuntimeError(message)

    if version.returncode != 0:
        message = version.stderr or version.stdout or "xcodebuild -version failed"
        if allow_xcode_blocked:
            print(f"[xcode-blocked] {message}")
            return False
        raise RuntimeError(message)

    try:
        listing = run(
            ["xcodebuild", "-list", "-project", str(PROJECT)],
            timeout=20,
            allow_failure=True,
            echo_output=False,
        )
    except subprocess.TimeoutExpired:
        message = "xcodebuild -list timed out"
        if allow_xcode_blocked:
            print(f"[xcode-blocked] {message}")
            return False
        raise RuntimeError(message)

    if listing.returncode != 0:
        combined = (listing.stdout or "") + (listing.stderr or "")
        summary = xcode_failure_summary(combined)
        if allow_xcode_blocked:
            print(f"[xcode-blocked] {summary}")
            return False
        print(combined, file=sys.stderr)
        raise RuntimeError(summary)

    return True


def resolve_destination(destination: str) -> str:
    if destination != "auto":
        return destination

    try:
        result = run(["xcrun", "simctl", "list", "devices", "available", "-j"], timeout=30, echo_output=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "xcrun simctl timed out while listing available simulators. "
            "Repair the local Xcode simulator installation, then rerun verify_ios_release.py."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "xcrun simctl failed while listing available simulators. "
            "Repair the local Xcode simulator installation, then rerun verify_ios_release.py."
        ) from exc

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "xcrun simctl returned non-JSON output while listing available simulators. "
            "Repair the local Xcode simulator installation, then rerun verify_ios_release.py."
        ) from exc
    candidates: list[tuple[str, str]] = []
    fallback_ipads: list[tuple[str, str]] = []
    for devices in data.get("devices", {}).values():
        for device in devices:
            name = device.get("name", "")
            udid = device.get("udid", "")
            if not name or not udid:
                continue
            if "iPad mini" in name:
                candidates.append((name, udid))
            elif name.startswith("iPad"):
                fallback_ipads.append((name, udid))

    if candidates:
        name, udid = candidates[0]
        destination = f"platform=iOS Simulator,id={udid}"
        print(f"Using iPad mini simulator: {name} ({udid})")
        return destination

    if fallback_ipads:
        names = ", ".join(name for name, _ in fallback_ipads[:5])
        raise RuntimeError(
            "No available iPad mini simulator was found. "
            f"Available iPad simulators include: {names}. "
            "Install an iPad mini simulator runtime or pass --destination explicitly."
        )

    raise RuntimeError("No available iPad simulator was found. Install an iPad mini simulator runtime.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the iPadOS BookMD reader release path.")
    parser.add_argument(
        "--allow-xcode-blocked",
        action="store_true",
        help="Exit 0 after static verification if the local Xcode installation is blocked.",
    )
    parser.add_argument(
        "--destination",
        default="auto",
        help="xcodebuild destination for simulator tests; default auto-selects an available iPad mini.",
    )
    args = parser.parse_args()

    run(["xcodegen", "generate"], timeout=60)
    run(["python3", "scripts/verify_ios_static.py"], timeout=180)
    run(["python3", "scripts/verify_ios_core.py", "--compile-only"], timeout=180)

    if not SAMPLE.exists():
        raise SystemExit(f"missing real sample: {SAMPLE}")

    xcode_ready = verify_xcode_available(allow_xcode_blocked=args.allow_xcode_blocked)
    if not xcode_ready:
        print("Static iOS reader verification passed; build/test is blocked by local Xcode.")
        print("See docs/ios_xcode_repair.md for the non-destructive repair and runtime acceptance path.")
        return 0 if args.allow_xcode_blocked else 2

    env = os.environ.copy()
    env["BOOKMD_REAL_SAMPLE"] = str(SAMPLE)
    destination = resolve_destination(args.destination)
    command = [
        "xcodebuild",
        "test",
        "-project",
        str(PROJECT),
        "-scheme",
        SCHEME,
        "-destination",
        destination,
    ]
    print("+ " + " ".join(command))
    result = subprocess.run(command, cwd=ROOT, env=env, text=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
