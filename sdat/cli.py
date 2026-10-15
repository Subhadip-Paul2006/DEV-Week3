"""SDAT CLI Entry Point — NIRĪKṢĀ (तन्त्रविन्यास-निरीक्षा).

Production-grade developer tool CLI with Rich styling, multi-stage progress,
severity breakdown, Gemma 4 reasoning status, and actionable remediation cards.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure clean UTF-8 encoding in Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from sdat.concepts import Priority
from sdat.config import load_config
from sdat.models import DecisionStatus
from sdat.orchestrator import run_audit_pipeline


def _get_console():
    try:
        from rich.console import Console
        return Console(legacy_windows=False)
    except Exception:
        return None


def _print_brand() -> None:
    console = _get_console()
    if console:
        try:
            from rich.panel import Panel
            console.print(
                Panel(
                    "[bold cyan]निरीक्षा[/bold cyan]  [dim]•[/dim]  [bold white]तन्त्रविन्यास-निरीक्षा[/bold white]\n"
                    "[bright_blue]System Design Audit Tool[/bright_blue] — Production Architecture Auditor\n"
                    "[dim italic]Developed by shubh06[/dim italic]",
                    border_style="cyan",
                    padding=(0, 2),
                )
            )
            return
        except Exception:
            pass

    print("=" * 60)
    print("निरीक्षा • तन्त्रविन्यास-निरीक्षा")
    print("System Design Audit Tool — Production Architecture Auditor")
    print("Developed by shubh06")
    print("=" * 60)


def _render_audit_summary(res, elapsed: float, target_name: str) -> None:
    try:
        from rich.panel import Panel
        from rich.table import Table

        console = _get_console()
        if not console:
            raise RuntimeError("Rich console unavailable")

        # Count severities across missing and misconfigured findings
        crit_count = sum(1 for d in res.decisions if d.priority == Priority.CRITICAL and d.status in (DecisionStatus.MISSING, DecisionStatus.MISCONFIGURED))
        high_count = sum(1 for d in res.decisions if d.priority == Priority.HIGH and d.status in (DecisionStatus.MISSING, DecisionStatus.MISCONFIGURED))
        med_count = sum(1 for d in res.decisions if d.priority == Priority.MEDIUM and d.status in (DecisionStatus.MISSING, DecisionStatus.MISCONFIGURED))
        low_count = sum(1 for d in res.decisions if d.priority == Priority.LOW and d.status in (DecisionStatus.MISSING, DecisionStatus.MISCONFIGURED))
        info_count = sum(1 for d in res.decisions if d.priority == Priority.INFO or d.status == DecisionStatus.IMPLEMENTED)

        # AI badge
        ai_res = res.ai_enrichment
        if ai_res and ai_res.available:
            mode_text = "Live Inference" if not ai_res.is_cached else "Offline Cached Artifact"
            prov_str = f" via {ai_res.provider.title()}" if ai_res.provider not in ("none", "deterministic") else ""
            ai_badge = f"[bold green]{ai_res.model} ✓[/bold green] [dim]({mode_text}{prov_str})[/dim]"
        elif ai_res and ai_res.error:
            ai_badge = f"[yellow]AI Unavailable[/yellow] [dim]({ai_res.error})[/dim] → [bold cyan]Deterministic Mode[/bold cyan]"
        else:
            ai_badge = "[bold cyan]Deterministic Mode[/bold cyan] [dim](--no-ai active)[/dim]"

        # Summary Table
        table = Table(title="[bold green]AUDIT COMPLETE[/bold green]", border_style="green", show_header=True)
        table.add_column("Metric", style="bold white", width=26)
        table.add_column("Value", style="bold cyan")

        table.add_row("Target Project", f"[bold yellow]{target_name}[/bold yellow]")
        table.add_row("Concepts Evaluated", str(res.total_decisions))
        table.add_row("Implemented Patterns", f"[green]{res.implemented_count}[/green]")
        table.add_row("Architectural Gaps", f"[red]{res.missing_count}[/red]")
        table.add_row("Misconfigurations", f"[yellow]{res.misconfigured_count}[/yellow]")
        table.add_row("Severity: CRITICAL", f"[bold red]{crit_count}[/bold red]")
        table.add_row("Severity: HIGH", f"[red]{high_count}[/red]")
        table.add_row("Severity: MEDIUM", f"[yellow]{med_count}[/yellow]")
        table.add_row("Severity: LOW / INFO", f"[blue]{low_count}[/blue] / [dim]{info_count}[/dim]")
        table.add_row("AI Reasoning Engine", ai_badge)
        table.add_row("Audit Duration", f"{elapsed:.2f}s")
        table.add_row("Audit Reports", f"[underline cyan]{res.inventory_path or 'docs/audit'}[/underline cyan]")

        console.print()
        console.print(table)

        # Top Architectural Risk Card
        top_risk = None
        if ai_res and ai_res.remediations:
            top_risk = ai_res.remediations[0]

        if top_risk:
            ev_summary = (
                f"{top_risk.evidence[0].get('file', '')}:{top_risk.evidence[0].get('line', '')} "
                f"({top_risk.evidence[0].get('snippet', '')[:60]}...)"
                if top_risk.evidence and top_risk.evidence[0].get("file")
                else "Structural absence in repository AST facts"
            )

            ai_model_name = ai_res.model if ai_res and ai_res.model != "none" else "Rule Engine"
            reasoning = top_risk.ai_reasoning or top_risk.gemma_reasoning
            risk_text = (
                f"[bold red]Finding:[/bold red] {top_risk.finding}\n"
                f"[bold cyan]Evidence:[/bold cyan] {ev_summary}\n"
                f"[bold magenta]AI Reasoning ({ai_model_name}):[/bold magenta] {reasoning}\n"
                f"[bold green]Recommended Solution:[/bold green] {top_risk.recommended_solution}\n"
                f"[dim]See docs/audit/04-remediation.md for step-by-step implementation and validation criteria.[/dim]"
            )

            console.print()
            console.print(
                Panel(
                    risk_text,
                    title=f"[bold red]Top Architectural Risk ({top_risk.severity.upper()}): {top_risk.concept_name}[/bold red]",
                    border_style="red",
                    padding=(1, 2),
                )
            )

        console.print()
        console.print("[dim]Generated Reports:[/dim]")
        console.print("  • [green]01-inventory.md[/green]           [dim]Implemented architecture inventory[/dim]")
        console.print("  • [yellow]02-gaps.md[/yellow]                [dim]Missing foundational concepts[/dim]")
        console.print("  • [red]03-misconfigurations.md[/red]   [dim]Architecture smells and antipatterns[/dim]")
        console.print("  • [bold cyan]04-remediation.md[/bold cyan]        [dim]Actionable remediation action plans & validation[/dim]")
        console.print("  • [dim]telemetry.json[/dim]           [dim]Scanner timers & swarm telemetry[/dim]")
        console.print()
        console.print("[dim italic]Developed by shubh06 — तन्त्रविन्यास-निरीक्षा[/dim italic]")
        console.print()

    except Exception:
        # Graceful plain fallback
        print("\n" + "=" * 60)
        print("AUDIT COMPLETE")
        print("=" * 60)
        print(f"Project: {target_name}")
        print(f"Concepts evaluated: {res.total_decisions}")
        print(f"Implemented: {res.implemented_count} | Missing: {res.missing_count} | Misconfigured: {res.misconfigured_count}")
        print(f"Reports: {res.inventory_path or 'docs/audit'}")
        print("=" * 60)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sdat",
        description="निरीक्षा (तन्त्रविन्यास-निरीक्षा) — System Design Audit Tool. Developed by shubh06.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    audit_parser = subparsers.add_parser("audit", help="Run a full system-design audit on a codebase")
    audit_parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Target repository path (default: current directory)",
    )
    audit_parser.add_argument(
        "--config",
        default="config/sdat.config.yaml",
        help="Path to SDAT configuration file",
    )
    audit_parser.add_argument(
        "--output-dir",
        default="docs/audit",
        help="Directory to write audit reports into (default: docs/audit)",
    )
    audit_parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Disable AI reasoning and run purely deterministic audit",
    )
    audit_parser.add_argument(
        "--model",
        default=None,
        help="AI model identifier override (e.g. qwen/qwen3-coder:free, gemma-2-9b-it)",
    )
    audit_parser.add_argument(
        "--project-type",
        default=None,
        help="Explicit workload classification (for example backend, frontend, ml, or nlp)",
    )

    args = parser.parse_args(argv)

    if args.command == "audit":
        try:
            config = load_config(args.config)
        except ValueError as exc:
            print(f"\nERROR: Invalid SDAT config: {exc}", file=sys.stderr)
            return 2
        _print_brand()

        target_path = Path(args.target).resolve()
        target_name = target_path.name
        start_time = time.time()

        console = _get_console()
        use_rich = console is not None

        def _log_stage(step: str, desc: str) -> None:
            if use_rich and console:
                console.print(f"[bold cyan]{step}[/bold cyan] {desc}")
            else:
                print(f"{step} {desc}")

        _log_stage("[1/6]", f"Discovering project structure in '{target_name}'...")
        time.sleep(0.05)

        _log_stage("[2/6]", "Scanning source code across multi-language scanners (Python, TS, Go, Rust, C/C++, PHP, Java)...")
        time.sleep(0.05)

        _log_stage("[3/6]", "Aggregating evidence facts and cross-file correlations...")
        time.sleep(0.05)

        _log_stage("[4/6]", "Running configured foundation and workload agents...")
        time.sleep(0.05)

        if args.no_ai:
            _log_stage("[5/6]", "Skipping AI reasoning (--no-ai flag active, using deterministic remediation)...")
        else:
            selected_ai = config.to_ai_config(args.model)
            model_display = selected_ai.model or selected_ai.provider
            _log_stage("[5/6]", f"Running optional AI enrichment ({model_display}; deterministic fallback enabled)...")
        time.sleep(0.05)

        _log_stage("[6/6]", f"Generating audit reports and telemetry into '{args.output_dir}'...")

        try:
            result = run_audit_pipeline(
                target_root=args.target,
                output_dir=args.output_dir,
                project_type=args.project_type or config.project_type,
                max_workers=config.max_workers,
                agent_timeout_seconds=config.agent_timeout_seconds,
                enable_ai=not args.no_ai,
                ai_model=args.model,
                config=config,
            )
            elapsed = time.time() - start_time
            _render_audit_summary(result, elapsed, target_name)
            return 0
        except FileNotFoundError as exc:
            print(f"\nERROR: Target directory not found: {exc}", file=sys.stderr)
            return 1
        except PermissionError as exc:
            print(f"\nERROR: Permission denied: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"\nERROR: Audit execution error: {exc}", file=sys.stderr)
            return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
