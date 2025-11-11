"""Utility functions for CLI output."""

import json

from rich.console import Console
from rich.table import Table

console = Console()


def print_success(message):
    """Print success message."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message):
    """Print error message."""
    console.print(f"[red]✗ Error:[/red] {message}")


def print_info(message):
    """Print info message."""
    console.print(f"[blue]ℹ[/blue] {message}")


def print_warning(message):
    """Print warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_table(data, title=None):
    """Print data as a table."""
    if not data:
        print_info("No data to display")
        return

    table = Table(title=title)

    # Add columns from first row
    if data:
        for key in data[0].keys():
            table.add_column(str(key))

        # Add rows
        for row in data:
            table.add_row(*[str(v) for v in row.values()])

    console.print(table)


def print_detail(data, title=None):
    """Print detailed data."""
    if title:
        console.print(f"\n[bold]{title}[/bold]")

    for key, value in data.items():
        if isinstance(value, (dict, list)):
            console.print(f"  [cyan]{key}:[/cyan]")
            console.print(f"    {json.dumps(value, indent=2)}")
        else:
            console.print(f"  [cyan]{key}:[/cyan] {value}")


def print_json(data):
    """Print data as JSON."""
    console.print_json(data=data)
