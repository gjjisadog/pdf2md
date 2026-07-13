"""Core helpers for creating and validating BookMD packages."""

from .packager import package_directory
from .reader import read_book_manifest, read_json_file, read_text_file
from .schema import load_schema
from .validator import REQUIRED_FILES, ValidationResult, validate_bookmd
from .visuals import crop_image, render_pdf_page

__all__ = [
    "REQUIRED_FILES",
    "ValidationResult",
    "package_directory",
    "read_book_manifest",
    "read_json_file",
    "read_text_file",
    "load_schema",
    "validate_bookmd",
    "crop_image",
    "render_pdf_page",
]
