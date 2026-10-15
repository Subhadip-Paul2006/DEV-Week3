"""C and C++ scanner for SDAT — conforms to LanguageScanner protocol."""

from __future__ import annotations

from .c_cpp import (
    CCppScanner,
    _scan_c_cpp_evidence,
    _scan_c_cpp_file,
    discover_c_cpp_files,
    scan_c_cpp_project,
    scan_c_cpp_project_evidence,
)

__all__ = [
    "CCppScanner",
    "_scan_c_cpp_evidence",
    "_scan_c_cpp_file",
    "discover_c_cpp_files",
    "scan_c_cpp_project",
    "scan_c_cpp_project_evidence",
]
