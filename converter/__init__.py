from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_APP_CONVERTER = (
    _ROOT / "apps" / "converter_desktop" / "converter"
)

for package_root in (
    _ROOT / "packages" / "bookmd_core",
    _ROOT / "packages" / "source_map_core",
    _ROOT / "packages" / "translator_core",
    _ROOT / "packages" / "ocr_client",
):
    if package_root.exists():
        sys.path.insert(0, str(package_root))

if _APP_CONVERTER.exists():
    __path__.append(str(_APP_CONVERTER))
