"""Init command for bmad-assist CLI.

Initializes a project for bmad-assist usage.
"""

from pathlib import Path

import typer

from bmad_assist.cli_utils import (
    EXIT_ERROR,
    _error,
    _success,
    console,
)


def init_command(
    project: str = typer.Option(
        ".",
        "--project",
        "-p",
        help="Path to project directory to initialize",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be done without making changes",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing configuration if present",
    ),
) -> None:
    """Initialize a project for bmad-assist.

    Sets up the project with required configuration:
    - Creates .bmad-assist/ directory for state and cache
    - Adds required patterns to .gitignore to prevent committing artifacts

    This command is idempotent - safe to run multiple times.

    Examples:
        bmad-assist init                    # Initialize current directory
        bmad-assist init -p ./my-project    # Initialize specific project
        bmad-assist init --dry-run          # Preview changes without applying

    """
    from bmad_assist.git import check_gitignore, setup_gitignore

    project_path = Path(project).resolve()

    if not project_path.exists():
        _error(f"Project directory does not exist: {project_path}")
        raise typer.Exit(code=EXIT_ERROR)

    if not project_path.is_dir():
        _error(f"Path is not a directory: {project_path}")
        raise typer.Exit(code=EXIT_ERROR)

    console.print(f"[bold]Initializing bmad-assist in:[/bold] {project_path}")
    console.print()

    changes_made = False

    # 1. Create .bmad-assist directory
    bmad_dir = project_path / ".bmad-assist"
    cache_dir = bmad_dir / "cache"

    if not bmad_dir.exists():
        if dry_run:
            console.print(f"  [dim]Would create:[/dim] {bmad_dir}/")
            changes_made = True
        else:
            bmad_dir.mkdir(parents=True, exist_ok=True)
            cache_dir.mkdir(exist_ok=True)
            console.print(f"  [green]Created:[/green] {bmad_dir}/")
            changes_made = True
    else:
        console.print(f"  [dim]Already exists:[/dim] {bmad_dir}/")
        # Ensure cache subdir exists
        if not cache_dir.exists() and not dry_run:
            cache_dir.mkdir(exist_ok=True)

    # 2. Setup .gitignore
    all_present, missing = check_gitignore(project_path)

    if all_present:
        console.print("  [dim].gitignore:[/dim] All bmad-assist patterns present")
    else:
        changed, message = setup_gitignore(project_path, dry_run=dry_run)
        if changed:
            if dry_run:
                console.print(f"  [dim]Would update .gitignore:[/dim] {message}")
            else:
                console.print(f"  [green].gitignore:[/green] {message}")
            changes_made = True
        else:
            console.print(f"  [yellow].gitignore:[/yellow] {message}")

    # Summary
    console.print()
    if dry_run:
        if changes_made:
            console.print(
                "[yellow]Dry run - no changes made. Run without --dry-run to apply.[/yellow]"
            )
        else:
            console.print("[green]Project already initialized - no changes needed.[/green]")
    else:
        if changes_made:
            _success("Project initialized successfully")
        else:
            console.print("[green]Project already initialized - no changes needed.[/green]")
