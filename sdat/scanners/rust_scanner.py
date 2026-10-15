"""Rust scanner for SDAT — conforms to LanguageScanner protocol."""

from __future__ import annotations

from .rust import (
    RustScanner,
    _scan_rust_evidence,
    _scan_rust_file,
    discover_rust_files,
    scan_rust_project,
    scan_rust_project_evidence,
)

__all__ = [
    "RustScanner",
    "_scan_rust_evidence",
    "_scan_rust_file",
    "discover_rust_files",
    "scan_rust_project",
    "scan_rust_project_evidence",
]
