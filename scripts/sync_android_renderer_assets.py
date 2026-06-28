from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_RENDERER = ROOT / "packages/markdown_renderer/renderer"
ANDROID_ASSETS = ROOT / "apps/reader-android/app/src/main/assets"
ASSET_NAMES = ["bookmd-renderer.html", "bookmd-renderer.css", "bookmd-renderer.js"]


def main() -> None:
    ANDROID_ASSETS.mkdir(parents=True, exist_ok=True)
    for name in ASSET_NAMES:
        shutil.copyfile(PACKAGE_RENDERER / name, ANDROID_ASSETS / name)


if __name__ == "__main__":
    main()
