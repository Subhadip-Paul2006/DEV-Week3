#!/usr/bin/env bash
# SDAT run script — wraps the Python CLI with environment-friendly defaults.
# Usage: ./run.sh audit [TARGET]  (defaults to parent directory)

set -euo pipefail

# Resolve repo root
SDAT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SDAT_DIR"

# Pick Python
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    if command -v python >/dev/null 2>&1; then
        PYTHON=python
    else
        echo "ERROR: Python not found. Install Python 3.10+ and retry." >&2
        exit 1
    fi
fi

# Dispatch subcommand
case "${1:-audit}" in
    audit)
        TARGET="${2:-../}"
        "$PYTHON" -m sdat.cli audit "$TARGET" \
            --config "config/sdat.config.yaml" \
            --output-dir "docs/audit"
        ;;
    scan)
        TARGET="${2:-../}"
        "$PYTHON" -m sdat.cli audit "$TARGET" \
            --config "config/sdat.config.yaml" \
            --output-dir "docs/audit"
        ;;
    rebuild-kb-index)
        "$PYTHON" -c "from sdat.kb import rebuild_index; rebuild_index()"
        ;;
    test)
        shift
        "$PYTHON" -m pytest tests/ "$@"
        ;;
    *)
        echo "Usage: $0 {audit|scan|rebuild-kb-index|test} [TARGET]" >&2
        exit 1
        ;;
esac
