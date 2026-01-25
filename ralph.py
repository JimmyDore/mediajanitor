#!/usr/bin/env python3
"""
Ralph - Autonomous development assistant

Subcommands:
  once              Single iteration (human-in-the-loop)
  run <iterations>  Autonomous loop with retry logic
  qa [SKILLS...]    Run QA skills only

Task commands (recommended):
  task ralph:once              # Single iteration (no QA)
  task ralph:run -- 20         # 20 iterations + QA at end (default)
  task ralph:run:qa-first -- 5 # QA first, then 5 iterations, QA at end
  task ralph:qa                # All QA skills only
  task ralph:qa:quick          # Quick security check only
  task ralph:dry-run -- 5      # Preview 5 iterations

Note: `ralph run` always runs QA at the end by default. Use --qa=none to skip.

Direct usage (alternative):
  uv run --with typer --with rich python ralph.py once
  uv run --with typer --with rich python ralph.py run 10
  uv run --with typer --with rich python ralph.py run --qa-first 5
  uv run --with typer --with rich python ralph.py qa
  uv run --with typer --with rich python ralph.py qa security ux
  uv run --with typer --with rich python ralph.py run --dry-run 10
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Configuration
QA_SKILLS = [
    "qa-security",
    "qa-api-contracts",
    "qa-test-coverage",
    "qa-performance",
    "qa-architecture",
    "qa-ux",
    "qa-accessibility",
    "qa-documentation",
    "qa-infra",
]
RETRY_WAIT_SECONDS = 60
DEFAULT_LOG_FILE = "ralph-output.log"
RALPH_PROMPT = "@prompt.md"

app = typer.Typer(
    name="ralph",
    help="Ralph - Autonomous development assistant",
    no_args_is_help=True,
)
console = Console()


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class RunSummary:
    """Track and display run statistics."""

    start_time: datetime
    end_time: datetime | None = None
    iterations_completed: int = 0
    stories_completed: int = 0
    initial_remaining: int = 0
    final_remaining: int = 0
    errors: list[str] = field(default_factory=list)

    def print_summary(self) -> None:
        """Print formatted summary using Rich."""
        self.end_time = self.end_time or datetime.now()
        elapsed = self.end_time - self.start_time
        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        table = Table(title="Run Summary", show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Started", self.start_time.strftime("%Y-%m-%d %H:%M:%S"))
        table.add_row("Finished", self.end_time.strftime("%Y-%m-%d %H:%M:%S"))
        table.add_row("Duration", f"{hours}h {minutes}m {seconds}s")
        table.add_row("Iterations", str(self.iterations_completed))
        table.add_row(
            "Stories completed",
            str(self.initial_remaining - self.final_remaining),
        )
        table.add_row("Stories remaining", str(self.final_remaining))

        if self.errors:
            table.add_row("Errors", str(len(self.errors)), style="red")

        console.print()
        console.print(Panel(table, border_style="blue"))

        if self.errors:
            console.print("\n[red]Errors encountered:[/red]")
            for error in self.errors:
                console.print(f"  - {error}")


# =============================================================================
# Pre-flight Checks
# =============================================================================


def preflight_checks() -> list[str]:
    """Return list of errors, empty if all good."""
    errors = []

    if not Path("prompt.md").exists():
        errors.append("prompt.md not found")

    if not Path("prd.json").exists():
        errors.append("prd.json not found")
    else:
        try:
            json.loads(Path("prd.json").read_text())
        except json.JSONDecodeError as e:
            errors.append(f"prd.json is invalid JSON: {e}")

    return errors


def run_preflight_checks(exit_on_error: bool = True) -> bool:
    """Run pre-flight checks and optionally exit on error."""
    errors = preflight_checks()
    if errors:
        console.print("[red]Pre-flight checks failed:[/red]")
        for error in errors:
            console.print(f"  [red]✗[/red] {error}")
        if exit_on_error:
            raise typer.Exit(1)
        return False

    console.print("[green]✓[/green] Pre-flight checks passed")
    return True


# =============================================================================
# Core Functions
# =============================================================================


def section_header(title: str) -> None:
    """Print a section header using Rich."""
    console.print()
    console.print(Panel(title, style="bold cyan", expand=False))
    console.print()


def check_prd_completion() -> int:
    """Return number of remaining stories (passes=false)."""
    try:
        prd = json.loads(Path("prd.json").read_text())
        remaining = sum(1 for story in prd.get("userStories", []) if not story.get("passes", False))
        return remaining
    except (json.JSONDecodeError, FileNotFoundError):
        return 999


def run_claude(prompt: str, streaming: bool = False, log_file: str | None = None, skip_permissions: bool = False) -> subprocess.CompletedProcess:
    """Run claude command and return result.

    Streams output in real-time (like shell's tee) while also writing to log file.
    """
    if skip_permissions:
        cmd = ["claude", "--dangerously-skip-permissions"]
    else:
        cmd = ["claude", "--permission-mode", "acceptEdits"]

    if streaming:
        cmd.extend(["--output-format", "stream-json", "--verbose"])
    else:
        cmd.extend(["--output-format", "text", "--verbose"])

    cmd.extend(["-p", prompt])

    # Set up environment - add IS_SANDBOX=1 for skip_permissions to work as root
    env = None
    if skip_permissions:
        env = os.environ.copy()
        env["IS_SANDBOX"] = "1"

    # Use Popen for real-time streaming (like shell's tee)
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Merge stderr into stdout
        text=True,
        bufsize=1,  # Line buffered
        env=env,
    )

    stdout_lines: list[str] = []
    log_handle = open(log_file, "a") if log_file else None

    try:
        for line in iter(process.stdout.readline, ""):
            stdout_lines.append(line)

            # Write to log file
            if log_handle:
                log_handle.write(line)
                log_handle.flush()

            # Print to console
            if streaming:
                # Parse stream-json format and extract assistant text
                try:
                    data = json.loads(line.strip())
                    if data.get("type") == "assistant" and data.get("message", {}).get("content"):
                        for content in data["message"]["content"]:
                            if content.get("type") == "text" and content.get("text"):
                                text = content["text"]
                                console.print(text, end="")
                                # Add newline after sentences for readability
                                if text.rstrip().endswith((".", "!", "?", ":")):
                                    console.print()
                except json.JSONDecodeError:
                    pass
            else:
                # Text output - print as-is
                console.print(line, end="")

        process.wait()
    finally:
        if log_handle:
            log_handle.close()

    # Return CompletedProcess-like object for compatibility
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=process.returncode,
        stdout="".join(stdout_lines),
        stderr="",
    )


def run_with_retry(prompt: str, streaming: bool = False, log_file: str | None = None, skip_permissions: bool = False) -> None:
    """Run claude command with retry logic for rate limits."""
    while True:
        result = run_claude(prompt, streaming=streaming, log_file=log_file, skip_permissions=skip_permissions)

        if result.returncode == 0:
            break

        output = (result.stdout or "") + (result.stderr or "")
        rate_limit_keywords = [
            "credit",
            "rate limit",
            "quota",
            "limit reached",
            "too many requests",
            "overloaded",
        ]

        if any(keyword in output.lower() for keyword in rate_limit_keywords):
            console.print(f"\n[yellow]Credit/rate limit detected. Waiting {RETRY_WAIT_SECONDS}s...[/yellow]")
        else:
            console.print(f"\n[yellow]Claude failed (exit {result.returncode}). Waiting {RETRY_WAIT_SECONDS}s...[/yellow]")

        time.sleep(RETRY_WAIT_SECONDS)
        console.print("[cyan]Retrying...[/cyan]")


def run_qa_skill(skill: str, log_file: str | None = None) -> None:
    """Run a single QA skill."""
    section_header(f"QA: {skill}")
    run_with_retry(f"Use /{skill} skill to review the application", streaming=True, log_file=log_file)


def validate_qa_skills(skills: list[str]) -> list[str]:
    """Validate QA skill names. Returns list of invalid skills."""
    invalid = [s for s in skills if s not in QA_SKILLS and f"qa-{s}" not in QA_SKILLS]
    return invalid


def normalize_qa_skill(skill: str) -> str:
    """Normalize skill name (add qa- prefix if needed)."""
    if skill in QA_SKILLS:
        return skill
    if f"qa-{skill}" in QA_SKILLS:
        return f"qa-{skill}"
    return skill


# =============================================================================
# Commands
# =============================================================================


@app.command()
def once(
    skip_permissions: Annotated[bool, typer.Option("--skip-permissions", help="Use --dangerously-skip-permissions for Claude")] = False,
) -> None:
    """Run a single Ralph iteration (human-in-the-loop mode).

    This is the simplest mode - it runs Claude once with the Ralph prompt
    and exits. You watch what Claude does, then run again when ready.
    """
    run_preflight_checks()
    console.print("[cyan]Starting single Ralph iteration...[/cyan]")
    
    # Set up environment - add IS_SANDBOX=1 for skip_permissions to work as root
    env = None
    if skip_permissions:
        env = os.environ.copy()
        env["IS_SANDBOX"] = "1"
        subprocess.run(["claude", "--dangerously-skip-permissions", RALPH_PROMPT], env=env)
    else:
        subprocess.run(["claude", "--permission-mode", "acceptEdits", RALPH_PROMPT])


@app.command()
def run(
    iterations: Annotated[int, typer.Argument(help="Number of iterations to run")],
    qa_first: Annotated[bool, typer.Option("--qa-first", "-q", help="Run QA skills before starting iterations")] = False,
    qa: Annotated[str | None, typer.Option("--qa", help="Comma-separated QA skills to run, or 'none' to skip")] = None,
    log_file: Annotated[str, typer.Option("--log-file", "-l", help="Output log file path")] = DEFAULT_LOG_FILE,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be executed without running")] = False,
    skip_permissions: Annotated[bool, typer.Option("--skip-permissions", help="Use --dangerously-skip-permissions for Claude (for sandboxed environments)")] = False,
) -> None:
    """Run Ralph autonomous loop for multiple iterations.

    Runs the Ralph prompt repeatedly, with retry logic for rate limits.
    Automatically stops if all PRD stories are completed.

    By default, runs all QA skills at the END of iterations.
    Use --qa-first to also run QA before iterations.
    Use --qa=none to skip QA entirely.

    Examples:
        ralph run 10              # 10 iterations + QA at end
        ralph run -q 5            # QA first, 5 iterations, QA at end
        ralph run --qa=none 5     # 5 iterations, no QA
        ralph run --dry-run 10    # Preview what would happen
    """
    # Parse QA skills
    qa_skills: list[str] = []
    if qa is None:
        qa_skills = QA_SKILLS.copy()
    elif qa.lower() == "none":
        qa_skills = []
    else:
        qa_skills = [normalize_qa_skill(s.strip()) for s in qa.split(",")]
        invalid = validate_qa_skills(qa_skills)
        if invalid:
            console.print(f"[red]Error: Unknown QA skills: {', '.join(invalid)}[/red]")
            console.print("Available skills:")
            for skill in QA_SKILLS:
                console.print(f"  - {skill}")
            raise typer.Exit(1)

    # Dry run mode
    if dry_run:
        console.print("[bold cyan][DRY RUN][/bold cyan] Preview of execution plan:\n")

        errors = preflight_checks()
        if errors:
            console.print("[red]Pre-flight checks: FAILED[/red]")
            for error in errors:
                console.print(f"  [red]✗[/red] {error}")
        else:
            console.print("[green]Pre-flight checks: ✓ All passed[/green]")

        console.print(f"\n[cyan]Iterations:[/cyan] {iterations}")
        console.print(f"[cyan]QA first:[/cyan] {'Yes' if qa_first else 'No'}")

        if qa_skills:
            console.print(f"[cyan]QA skills:[/cyan] {', '.join(qa_skills)}")
        else:
            console.print("[cyan]QA skills:[/cyan] Disabled")

        console.print(f"[cyan]Log file:[/cyan] {log_file}")

        remaining = check_prd_completion()
        console.print(f"\n[cyan]Current PRD status:[/cyan] {remaining} stories remaining")
        return

    # Actual execution
    run_preflight_checks()

    summary = RunSummary(start_time=datetime.now())
    summary.initial_remaining = check_prd_completion()

    console.print(f"[bold cyan]Starting AFK Ralph with {iterations} iterations...[/bold cyan]")
    if qa_first:
        console.print("  (with initial QA review)")
    if not qa_skills:
        console.print("  (QA skills disabled)")
    elif len(qa_skills) < len(QA_SKILLS):
        console.print(f"  (QA skills: {', '.join(qa_skills)})")
    console.print("=" * 50)

    # Initial QA if requested
    if qa_first and qa_skills:
        section_header("Initial QA Review")
        console.print(f"Running {len(qa_skills)} QA skills: {', '.join(qa_skills)}\n")
        for skill in qa_skills:
            run_qa_skill(skill, log_file=log_file)

    # Main development loop
    for i in range(1, iterations + 1):
        section_header(f"Iteration {i} of {iterations}")
        run_with_retry(RALPH_PROMPT, streaming=True, log_file=log_file, skip_permissions=skip_permissions)
        summary.iterations_completed = i

        remaining = check_prd_completion()
        summary.final_remaining = remaining

        if remaining == 0:
            console.print()
            console.print("=" * 50)
            console.print(f"[bold green]PRD complete after {i} iterations! (0 stories remaining)[/bold green]")
            console.print("=" * 50)
            break
        else:
            console.print(f"\n[cyan]{remaining} stories remaining...[/cyan]")

    # Final QA review
    if qa_skills:
        section_header("Final QA Review")
        console.print(f"Running {len(qa_skills)} QA skills: {', '.join(qa_skills)}\n")
        for skill in qa_skills:
            run_qa_skill(skill, log_file=log_file)

    summary.end_time = datetime.now()
    summary.final_remaining = check_prd_completion()
    summary.print_summary()

    console.print()
    console.print("=" * 50)
    console.print("[bold green]Completed. Check progress.txt for status.[/bold green]")
    console.print("=" * 50)


@app.command()
def qa(
    skills: Annotated[list[str] | None, typer.Argument(help="QA skills to run (omit for all)")] = None,
    log_file: Annotated[str, typer.Option("--log-file", "-l", help="Output log file path")] = DEFAULT_LOG_FILE,
) -> None:
    """Run QA skills only.

    Without arguments, runs all QA skills. You can specify specific skills
    by name (with or without 'qa-' prefix).

    Examples:
        ralph qa                    # Run all QA skills
        ralph qa security ux        # Run qa-security and qa-ux
        ralph qa qa-security        # Also works with full names
    """
    run_preflight_checks()

    if not skills:
        skills_to_run = QA_SKILLS.copy()
    else:
        skills_to_run = [normalize_qa_skill(s) for s in skills]
        invalid = validate_qa_skills(skills_to_run)
        if invalid:
            console.print(f"[red]Error: Unknown QA skills: {', '.join(invalid)}[/red]")
            console.print("\nAvailable skills:")
            for skill in QA_SKILLS:
                console.print(f"  - {skill}")
            raise typer.Exit(1)

    section_header("QA Review")
    console.print(f"Running {len(skills_to_run)} QA skills: {', '.join(skills_to_run)}\n")

    for skill in skills_to_run:
        run_qa_skill(skill, log_file=log_file)

    console.print()
    console.print("[bold green]QA review complete.[/bold green]")


@app.command("list-qa")
def list_qa() -> None:
    """List all available QA skills."""
    console.print("[bold cyan]Available QA skills:[/bold cyan]\n")
    for skill in QA_SKILLS:
        # Remove qa- prefix for display
        short_name = skill.replace("qa-", "")
        console.print(f"  [green]{skill}[/green] (or just '{short_name}')")


if __name__ == "__main__":
    app()
