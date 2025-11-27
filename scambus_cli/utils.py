"""Utility functions for CLI output."""

import json

from rich.console import Console
from rich.table import Table

# Console for data output (stdout) - for actual results/data
console_data = Console()

# Console for status/info/error messages (stderr) - for user feedback
console_status = Console(stderr=True)


def print_success(message):
    """Print success message to stderr."""
    console_status.print(f"[green]✓[/green] {message}")


def print_error(message):
    """Print error message to stderr."""
    console_status.print(f"[red]✗ Error:[/red] {message}")


def print_info(message):
    """Print info message to stderr."""
    console_status.print(f"[blue]ℹ[/blue] {message}")


def print_warning(message):
    """Print warning message to stderr."""
    console_status.print(f"[yellow]⚠[/yellow] {message}")


def print_table(data, title=None):
    """Print data as a table to stdout."""
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

    console_data.print(table)


def print_detail(data, title=None):
    """Print detailed data to stdout."""
    if title:
        console_data.print(f"\n[bold]{title}[/bold]")

    for key, value in data.items():
        if isinstance(value, (dict, list)):
            console_data.print(f"  [cyan]{key}:[/cyan]")
            console_data.print(f"    {json.dumps(value, indent=2)}")
        else:
            console_data.print(f"  [cyan]{key}:[/cyan] {value}")


def print_json(data):
    """Print data as JSON to stdout."""
    console_data.print_json(data=data)
