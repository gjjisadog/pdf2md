from __future__ import annotations

import zipfile
from pathlib import Path


DETERMINISTIC_ZIP_TIMESTAMP = (2024, 1, 1, 0, 0, 0)


def package_directory(source_dir: str | Path, output_path: str | Path) -> Path:
    source = Path(source_dir)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(path for path in source.rglob("*") if path.is_file()):
            archive_name = file_path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(archive_name, DETERMINISTIC_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, file_path.read_bytes())

    return output
