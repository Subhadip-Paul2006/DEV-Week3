"""Validated runtime configuration loaded from the user's YAML file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SDATConfig:
    source_path: Path
    scanners: tuple[str, ...] = ("python", "typescript", "go", "rust", "c_cpp", "php", "java")
    max_files_per_scan: int = 50_000
    file_size_limit_mb: int = 5
    exclude_paths: tuple[str, ...] = ()
    timeout_seconds: float = 30.0
    agent_timeout_seconds: float = 30.0
    max_workers: int = 4
    context_budget_tokens: int = 4_000
    max_output_tokens: int = 2_048
    ai_provider: str = "none"
    ai_model: str | None = None
    max_ai_retries: int = 1
    project_type: str = "backend"
    foundation_agents: tuple[str, ...] = ("F-01",)
    domain_agents: tuple[str, ...] = ("D-01", "D-21")
    research_enabled: bool = False
    agent_map: dict[str, Any] = field(default_factory=dict)

    def to_ai_config(self, model_override: str | None = None):
        """Resolve credentials from the environment and limits from YAML."""
        from dataclasses import replace

        from sdat.ai.config import AIConfig

        env = dict(os.environ)
        if self.ai_provider != "none" and not env.get("SDAT_AI_PROVIDER"):
            env["SDAT_AI_PROVIDER"] = self.ai_provider
        selected_model = model_override or self.ai_model
        if selected_model:
            env["SDAT_AI_MODEL"] = selected_model
        resolved = AIConfig.from_env(env)
        return replace(
            resolved,
            timeout_seconds=self.timeout_seconds,
            context_budget_tokens=self.context_budget_tokens,
            max_tokens=self.max_output_tokens,
            max_retries=self.max_ai_retries,
        )


def load_config(path: str | Path) -> SDATConfig:
    """Load and validate SDAT runtime settings from YAML."""
    config_path = Path(path).resolve()
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ValueError(f"Could not read config file '{config_path}': {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("SDAT config root must be a YAML mapping")

    scanners = _mapping(raw, "scanners")
    auditor = _mapping(raw, "auditor")
    agents = _mapping(raw, "agents")
    foundation = _mapping(agents, "foundation")
    domain = _mapping(agents, "domain")
    research = _mapping(raw, "research")
    paths = _mapping(raw, "paths")

    scanner_names = _string_list(scanners.get("enabled"), "scanners.enabled")
    if scanner_names is None:
        scanner_names = ["python", "typescript", "go", "rust", "c_cpp", "php", "java"]
    foundation_ids = _string_list(foundation.get("enabled"), "agents.foundation.enabled")
    domain_ids = _string_list(domain.get("enabled"), "agents.domain.enabled")
    if foundation_ids is None:
        foundation_ids = ["F-01"]
    if domain_ids is None:
        domain_ids = ["D-01", "D-21"]
    excludes = _string_list(scanners.get("exclude_paths"), "scanners.exclude_paths") or []
    excludes += _string_list(paths.get("exclude"), "paths.exclude") or []

    timeout = _positive_number(auditor.get("timeout_seconds", 30), "auditor.timeout_seconds")
    max_workers = _positive_int(agents.get("max_concurrent_agents", 4), "agents.max_concurrent_agents")
    agent_timeout = _positive_number(agents.get("timeout_seconds", 30), "agents.timeout_seconds")
    context_budget = _positive_int(auditor.get("context_budget_tokens", 4_000), "auditor.context_budget_tokens")
    output_tokens = _positive_int(auditor.get("max_output_tokens", 2_048), "auditor.max_output_tokens")
    max_retries = _nonnegative_int(auditor.get("max_retries", 1), "auditor.max_retries")
    max_files = _positive_int(scanners.get("max_files_per_scan", 50_000), "scanners.max_files_per_scan")
    size_limit = _positive_int(scanners.get("file_size_limit_mb", 5), "scanners.file_size_limit_mb")

    map_path_value = raw.get("agent_map")
    if not isinstance(map_path_value, str):
        if map_path_value is not None:
            raise ValueError("agent_map must be a path string")
    map_path = (
        (config_path.parent / map_path_value).resolve()
        if map_path_value
        else Path(__file__).resolve().parent.parent / "config" / "swarm_agent_map.yaml"
    )
    agent_map: dict[str, Any] = {}
    try:
        loaded_map = yaml.safe_load(map_path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ValueError(f"Could not read agent map '{map_path}': {exc}") from exc
    if not isinstance(loaded_map, dict):
        raise ValueError("Agent map root must be a YAML mapping")
    agent_map = loaded_map
    for tier, selected in (("foundation", foundation_ids), ("domain", domain_ids)):
        tier_config = agent_map.get(tier, {})
        entries = tier_config.get("agents", []) if isinstance(tier_config, dict) else []
        known_ids = {entry.get("id") for entry in entries if isinstance(entry, dict)}
        unknown = sorted(set(selected) - known_ids)
        if unknown:
            raise ValueError(f"Configured {tier} agent IDs are absent from the agent map: {', '.join(unknown)}")

    return SDATConfig(
        source_path=config_path,
        scanners=tuple(scanner_names),
        max_files_per_scan=max_files,
        file_size_limit_mb=size_limit,
        exclude_paths=tuple(dict.fromkeys(excludes)),
        timeout_seconds=timeout,
        agent_timeout_seconds=agent_timeout,
        max_workers=max_workers,
        context_budget_tokens=context_budget,
        max_output_tokens=output_tokens,
        ai_provider=_string(auditor.get("provider", "none"), "auditor.provider").lower(),
        ai_model=_optional_string(auditor.get("model"), "auditor.model"),
        max_ai_retries=max_retries,
        project_type=_string(raw.get("project_type", "backend"), "project_type").lower(),
        foundation_agents=tuple(foundation_ids or []),
        domain_agents=tuple(domain_ids or []),
        research_enabled=bool(research.get("enabled", False)),
        agent_map=agent_map,
    )


def _mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a YAML mapping")
    return value


def _string_list(value: Any, name: str) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{name} must be a list of non-empty strings")
    return value


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _string(value, name)


def _positive_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{name} must be a positive number")
    return float(value)


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value
