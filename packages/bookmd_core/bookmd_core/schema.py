from __future__ import annotations

import json
from importlib import resources
from typing import Any


SCHEMA_NAMES = {
    "book",
    "source_map",
    "search_index",
    "terms",
    "translation",
    "reading_config",
}


def load_schema(name: str, version: str = "1.0") -> dict[str, Any]:
    if name not in SCHEMA_NAMES:
        raise ValueError(f"Unknown BookMD schema: {name}")
    if version != "1.0":
        raise ValueError(f"Unknown BookMD schema version: {version}")
    resource = resources.files("schemas.bookmd.v1").joinpath(f"{name}.schema.json")
    try:
        return json.loads(resource.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"BookMD schema file is missing: {name}") from exc
