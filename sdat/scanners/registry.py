"""Scanner registry — maps file extensions to scanner modules."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from .base import LanguageScanner
from .c_cpp_scanner import CCppScanner
from .go_scanner import GoScanner
from .java_scanner import JavaScanner
from .php_scanner import PhpScanner
from .python_scanner import PythonScanner
from .rust_scanner import RustScanner
from .typescript_scanner import TypeScriptScanner

# Registry of language and framework scanners.
# Phase 2 connects the authoritative PythonScanner.
# Phase 3 connects the authoritative TypeScriptScanner.
# Phase 4 enables Go, Rust, C/C++, PHP, Java, Ruby, Swift, Dart.

REGISTRY: dict[str, dict[str, Any]] = {
    "python": {
        "extensions": [".py"],
        "module": "sdat.scanners.python_scanner",
        "scanner_class": PythonScanner,
        "enabled": True,
    },
    "typescript": {
        "extensions": [".ts", ".tsx", ".js", ".jsx"],
        "module": "sdat.scanners.typescript_scanner",
        "scanner_class": TypeScriptScanner,
        "enabled": True,
    },
    "go": {
        "extensions": [".go"],
        "module": "sdat.scanners.go_scanner",
        "scanner_class": GoScanner,
        "enabled": True,
    },
    "rust": {
        "extensions": [".rs"],
        "module": "sdat.scanners.rust_scanner",
        "scanner_class": RustScanner,
        "enabled": True,
    },
    "c_cpp": {
        "extensions": [".c", ".h", ".cpp", ".cc", ".cxx", ".hpp"],
        "module": "sdat.scanners.c_cpp_scanner",
        "scanner_class": CCppScanner,
        "enabled": True,
    },
    "php": {
        "extensions": [".php"],
        "module": "sdat.scanners.php_scanner",
        "scanner_class": PhpScanner,
        "enabled": True,
    },
    "java": {
        "extensions": [".java", ".kt"],
        "module": "sdat.scanners.java_scanner",
        "scanner_class": JavaScanner,
        "enabled": True,
    },
    "ruby": {
        "extensions": [".rb"],
        "module": "sdat.scanners.ruby_scanner",
        "enabled": False,  # Phase 4
    },
    "react": {
        "extends": "typescript",
        "markers": ["react", "next", "jsx"],
        "module": "sdat.scanners.react_scanner",
        "enabled": False,  # Phase 5
    },
    "vue": {
        "extends": "typescript",
        "markers": ["vue", "nuxt"],
        "module": "sdat.scanners.vue_scanner",
        "enabled": False,  # Phase 5
    },
    "svelte": {
        "extends": "typescript",
        "markers": ["svelte"],
        "module": "sdat.scanners.svelte_scanner",
        "enabled": False,  # Phase 5
    },
    "angular": {
        "extends": "typescript",
        "markers": ["angular"],
        "module": "sdat.scanners.angular_scanner",
        "enabled": False,  # Phase 5
    },
}


def get_scanner(name: str) -> dict[str, Any] | None:
    """Return scanner config by name, or None if not registered."""
    return REGISTRY.get(name)


def get_enabled_scanners() -> list[dict[str, Any]]:
    """Return list of enabled scanner configs."""
    return [s for s in REGISTRY.values() if s.get("enabled", False)]


def list_scanners() -> list[str]:
    """Return all registered scanner names."""
    return list(REGISTRY.keys())


def extension_to_scanner(ext: str) -> str | None:
    """Map a file extension (e.g. '.py' or 'py') to its scanner name."""
    clean_ext = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
    for name, config in REGISTRY.items():
        if clean_ext in [e.lower() for e in config.get("extensions", [])]:
            return name
    return None


def get_scanner_class(name: str) -> type[LanguageScanner] | None:
    """Resolve and return scanner class by name."""
    config = REGISTRY.get(name)
    if not config:
        return None

    if "scanner_class" in config:
        return config["scanner_class"]

    mod_name = config.get("module")
    if not mod_name:
        return None

    try:
        mod = importlib.import_module(mod_name)
        # Look for conventional class name, e.g. PythonScanner, GoScanner
        cls_name = f"{name.capitalize()}Scanner"
        return getattr(mod, cls_name, None)
    except ImportError:
        return None


def get_scanner_instance(name: str) -> LanguageScanner | None:
    """Return an instantiated scanner for the given language name."""
    cls = get_scanner_class(name)
    if cls is not None:
        return cls()
    return None


def get_scanner_for_file(file_path: Path | str) -> LanguageScanner | None:
    """Look up and instantiate the appropriate scanner for a file."""
    path = Path(file_path)
    scanner_name = extension_to_scanner(path.suffix)
    if not scanner_name:
        return None

    config = REGISTRY.get(scanner_name)
    if not config or not config.get("enabled", False):
        return None

    return get_scanner_instance(scanner_name)

