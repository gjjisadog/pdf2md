from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any


def read_book_manifest(path: str | Path) -> dict[str, Any]:
    with zipfile.ZipFile(Path(path)) as zf:
        return json.loads(zf.read("book.json").decode("utf-8"))


def read_json_file(path: str | Path, name: str) -> dict[str, Any]:
    with zipfile.ZipFile(Path(path)) as zf:
        return json.loads(zf.read(name).decode("utf-8"))


def read_text_file(path: str | Path, name: str) -> str:
    with zipfile.ZipFile(Path(path)) as zf:
        return zf.read(name).decode("utf-8")
