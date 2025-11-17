"""Main CLI entry point for Scambus."""

import sys

import click
from rich.console import Console

from .auth_device import DeviceAuthManager
from .config import get_api_url

console = Console()

__version__ = "2.0.0"


class Context:
    """CLI context object."""

    def __init__(self):
        self.api_url = get_api_url()
        self.token = None
        self.client = None

    def ensure_authenticated(self):
        """Ensure user is authenticated."""
        if not self.token:
            manager = DeviceAuthManager(self.api_url)
            self.token = manager.get_token()
            if not self.token:
                console.print(
                    "[red]Error:[/red] Not authenticated. Run: [cyan]scambus auth login[/cyan]"
                )
                sys.exit(1)

    def get_client(self):
        """Get authenticated Scambus client."""
        if not self.client:
            self.ensure_authenticated()

            try:
                from scambus_client import ScambusClient

                # Ensure URL has /api suffix for the client
                api_url = self.api_url.rstrip("/")
                if not api_url.endswith("/api"):
                    api_url = f"{api_url}/api"

                self.client = ScambusClient(api_url=api_url, api_token=self.token)
            except Exception as e:
                console.print(f"[red]Failed to create client:[/red] {e}")
                sys.exit(1)

        return self.client


@click.group()
@click.version_option(version=__version__)
@click.option("--api-url", envvar="SCAMBUS_URL", help="Scambus API URL")
@click.pass_context
def cli(ctx, api_url):
    """
    🛡️  Scambus CLI - Submit scam reports and manage data streams

    Submit scam reports, search identifiers, and manage export streams.

    Environment Variables:
      SCAMBUS_URL         API URL (default: https://scambus.net)
      SCAMBUS_API_KEY     Your API key (legacy, use 'scambus auth login' instead)

    Examples:
      # Login first
      scambus auth login

      # Submit a scam detection
      scambus journal create-detection --description "Phishing email" \\
          --identifier email:scammer@example.com

      # Search for an identifier
      scambus search identifiers --query "+1234567890"

      # Create a data stream
      scambus streams create --name "Phone Scams" --filter type=phone_call
    """
    # Create context object
    if ctx.obj is None:
        ctx.obj = Context()

    if api_url:
        ctx.obj.api_url = api_url


# ============================================================================
# AUTH COMMANDS
# ============================================================================


@cli.group()
def auth():
    """Authentication commands."""
    pass


@auth.command()
@click.option("--api-key", help="API key for programmatic access")
def login(api_key):
    """Login to Scambus.

    Without --api-key: Device authorization flow (opens browser)
    With --api-key: API key authentication (for automation)
    """
    try:
        api_url = get_api_url()
        manager = DeviceAuthManager(api_url)

        if api_key:
            # API key authentication
            token = manager.api_key_login(api_key)
        else:
            # Device authorization flow
            token = manager.device_login()

        if token:
            # Show authentication status
            from datetime import timedelta

            from rich.panel import Panel

            token_info = manager.get_token_info()
            user_info = manager.get_user_info()

            status_lines = ["[green]✓ Successfully authenticated[/green]\n"]

            if user_info:
                status_lines.append(f"[bold]Name:[/bold] {user_info.get('name')}")
                status_lines.append(f"[bold]Email:[/bold] {user_info.get('email')}")
                status_lines.append(f"[bold]ID:[/bold] {user_info.get('id')}")
                status_lines.append(f"[bold]Entity Type:[/bold] {user_info.get('entityType')}")
                status_lines.append(f"[bold]Role:[/bold] {user_info.get('role')}")

            # Show token info
            if token_info:
                status_lines.append(f"\n[bold]Auth Type:[/bold] {token_info['type']}")

                if token_info["seconds_remaining"] is not None:
                    td = timedelta(seconds=int(token_info["seconds_remaining"]))
                    status_lines.append(f"[bold]Access Token:[/bold] Expires in {td}")

                if token_info["has_refresh_token"]:
                    status_lines.append("[bold]Refresh Token:[/bold] [green]Available[/green]")

            console.print(
                Panel.fit(
                    "\n".join(status_lines), title="Authentication Success", border_style="green"
                )
            )
        else:
            console.print("[red]✗[/red] Authentication failed")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Login failed: {e}")
        sys.exit(1)


@auth.command()
def logout():
    """Logout and remove stored credentials."""
    api_url = get_api_url()
    manager = DeviceAuthManager(api_url)
    manager.logout()


@auth.command()
def status():
    """Show authentication status and token validity."""
    from datetime import timedelta

    from rich.panel import Panel

    api_url = get_api_url()
    manager = DeviceAuthManager(api_url)

    token_info = manager.get_token_info()

    if not token_info:
        console.print("[yellow]⚠[/yellow] Not authenticated. Run: [cyan]scambus auth login[/cyan]")
        return

    user_info = manager.get_user_info()

    # Build status message
    status_lines = []

    if token_info["is_expired"]:
        status_lines.append("[bold]Status:[/bold] [yellow]Expired (will auto-refresh)[/yellow]")
    else:
        status_lines.append("[bold]Status:[/bold] [green]Authenticated[/green]")

    if user_info:
        status_lines.append(f"[bold]Name:[/bold] {user_info.get('name')}")
        status_lines.append(f"[bold]Email:[/bold] {user_info.get('email')}")
        status_lines.append(f"[bold]ID:[/bold] {user_info.get('id')}")
        status_lines.append(f"[bold]Entity Type:[/bold] {user_info.get('entityType')}")
        status_lines.append(f"[bold]Role:[/bold] {user_info.get('role')}")

    # Show token info
    status_lines.append(f"\n[bold]Auth Type:[/bold] {token_info['type']}")

    if token_info["seconds_remaining"] is not None:
        if token_info["is_expired"]:
            status_lines.append("[bold]Access Token:[/bold] [yellow]Expired[/yellow]")
        else:
            td = timedelta(seconds=int(token_info["seconds_remaining"]))
            status_lines.append(f"[bold]Access Token:[/bold] Expires in {td}")

    if token_info["has_refresh_token"]:
        status_lines.append("[bold]Refresh Token:[/bold] [green]Available[/green]")

    status_lines.append(f"[bold]Config:[/bold] {manager.config_file}")

    console.print(
        Panel.fit(
            "\n".join(status_lines),
            title="Authentication Status",
            border_style="cyan" if not token_info["is_expired"] else "yellow",
        )
    )


# ============================================================================
# CONFIG COMMANDS
# ============================================================================


@cli.group()
def config():
    """Configuration commands."""
    pass


@config.command()
@click.argument("url")
def set_url(url):
    """Set Scambus API URL."""
    from .config import set_api_url

    set_api_url(url)
    console.print(f"[green]✓[/green] API URL set to: {url}")


@config.command(name="show")
def show_config():
    """Show current configuration."""
    from pathlib import Path

    from rich.panel import Panel

    console.print(
        Panel.fit(
            f"[bold]API URL:[/bold] {get_api_url()}\n"
            f"[bold]Config Dir:[/bold] {Path.home() / '.scambus'}",
            title="Configuration",
            border_style="cyan",
        )
    )


# Import command groups - imported here to avoid circular imports
from .commands import cases, journal, media, profile, search, streams, tags, views  # noqa: E402

cli.add_command(journal.journal)
cli.add_command(media.media)
cli.add_command(search.search)
cli.add_command(streams.streams)
cli.add_command(cases.cases)
cli.add_command(tags.tags)
cli.add_command(profile.profile)
cli.add_command(views.views)


def main():
    """Entry point for the CLI."""
    cli(obj=None)


if __name__ == "__main__":
    main()
