.PHONY: help audit scan rebuild-kb-index test lint format clean

SDAT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
TARGET ?= ../
CONFIG := config/sdat.config.yaml
OUTPUT_DIR := docs/audit
PYTHON := python3

help:
	@echo "SDAT — System Design Audit Tool"
	@echo ""
	@echo "Usage:"
	@echo "  make audit TARGET=../       Run full audit (scan + render)"
	@echo "  make scan TARGET=../        Scan only (no AI audit)"
	@echo "  make rebuild-kb-index       Regenerate INDEX.yaml from concepts/"
	@echo "  make test                   Run all tests"
	@echo "  make lint                   Run ruff linter"
	@echo "  make format                 Run ruff formatter"
	@echo "  make clean                  Remove .sdat-cache/ and reports"

audit:
	$(PYTHON) -m sdat.cli audit $(TARGET) --config $(CONFIG) --output-dir $(OUTPUT_DIR)

scan:
	@echo "Scan mode: scanning only (Phase 0 stub — no signals emitted yet)"
	$(PYTHON) -m sdat.cli audit $(TARGET) --config $(CONFIG) --output-dir $(OUTPUT_DIR)

rebuild-kb-index:
	@echo "Rebuilding knowledge base index..."
	$(PYTHON) -c "from sdat.kb import rebuild_index; rebuild_index()"

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check sdat/ tests/

format:
	$(PYTHON) -m ruff format sdat/ tests/

clean:
	rm -rf .sdat-cache/ docs/audit/*.md
