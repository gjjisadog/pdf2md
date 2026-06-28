from __future__ import annotations

import zipfile
from pathlib import Path


def package_directory(source_dir: str | Path, output_path: str | Path) -> Path:
    source = Path(source_dir)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(path for path in source.rglob("*") if path.is_file()):
            zf.write(file_path, file_path.relative_to(source).as_posix())

    return output
