"""JavaScript scanner shim — aliases to TypeScript scanner engine.

Since TypeScript and JavaScript share ECMAScript syntax and the Node.js / React
ecosystem, the TypeScript scanner handles .js, .jsx, .ts, and .tsx files.
This module provides aliases so that orchestrators and scanners expecting
_scan_javascript_file function seamlessly.
"""

from __future__ import annotations

from .typescript import (
    TypeScriptScanner,
    _scan_typescript_evidence,
    _scan_typescript_file,
    discover_typescript_files,
    scan_typescript_project,
    scan_typescript_project_evidence,
)

_scan_javascript_file = _scan_typescript_file
_scan_javascript_evidence = _scan_typescript_evidence
discover_javascript_files = discover_typescript_files
scan_javascript_project = scan_typescript_project
scan_javascript_project_evidence = scan_typescript_project_evidence
JavaScriptScanner = TypeScriptScanner

__all__ = [
    "JavaScriptScanner",
    "TypeScriptScanner",
    "_scan_javascript_evidence",
    "_scan_javascript_file",
    "_scan_typescript_evidence",
    "_scan_typescript_file",
    "discover_javascript_files",
    "discover_typescript_files",
    "scan_javascript_project",
    "scan_javascript_project_evidence",
    "scan_typescript_project",
    "scan_typescript_project_evidence",
]

