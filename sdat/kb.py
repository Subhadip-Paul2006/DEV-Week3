"""Knowledge Base index builder.

Rebuilds concepts/INDEX.yaml from concept markdown files' YAML frontmatter.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

CONCEPTS_DIR = Path(__file__).parent.parent / "concepts"
INDEX_PATH = CONCEPTS_DIR / "INDEX.yaml"


def _parse_frontmatter(filepath: Path) -> dict[str, Any] | None:
    """Parse YAML frontmatter from a markdown file."""
    content = filepath.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return None
    end = content.find("---", 3)
    if end == -1:
        return None
    frontmatter_text = content[3:end].strip()
    try:
        return yaml.safe_load(frontmatter_text)
    except yaml.YAMLError:
        return None


def rebuild_index() -> None:
    """Scan concepts/ for all markdown files and rebuild INDEX.yaml."""
    entries: list[dict[str, Any]] = []

    for root, dirs, files in os.walk(CONCEPTS_DIR):
        dirs[:] = sorted(dirs)  # deterministic order
        for fname in sorted(files):
            if not fname.endswith(".md"):
                continue
            filepath = Path(root) / fname
            fm = _parse_frontmatter(filepath)
            if fm and "id" in fm:
                rel_path = filepath.relative_to(CONCEPTS_DIR)
                entry = dict(fm)
                entry["file"] = str(rel_path).replace("\\", "/")
                if "domain" not in entry:
                    parts = rel_path.parts
                    if parts and parts[0] == "core":
                        entry["domain"] = "core"
                    elif len(parts) > 1 and parts[0] == "domains":
                        entry["domain"] = parts[1]
                    elif parts and parts[0] == "cross-domain":
                        entry["domain"] = "cross_domain"
                    else:
                        entry["domain"] = "core"
                entries.append(entry)

    # Deterministic sorting by domain then concept id
    entries.sort(key=lambda e: (e.get("domain", ""), e.get("id", "")))

    index = {
        "version": _read_version(),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_concepts": len(entries),
        "domains": sorted(set(e.get("domain", "unknown") for e in entries)),
        "categories": sorted(set(e.get("category", "unknown") for e in entries)),
        "concepts": entries,
    }

    INDEX_PATH.write_text(
        yaml.dump(index, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"INDEX.yaml rebuilt: {len(entries)} concepts across {len(index['domains'])} domains and {len(index['categories'])} categories")



def _read_version() -> str:
    version_file = CONCEPTS_DIR / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


if __name__ == "__main__":
    rebuild_index()
