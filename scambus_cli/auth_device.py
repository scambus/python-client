"""Device Authorization Flow for Scambus CLI.

Implements OAuth 2.0 Device Authorization Grant (RFC 8628).
More secure than local callback server - no client secrets needed.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Default config directory
CONFIG_DIR = Path.home() / ".scambus"
CONFIG_FILE = CONFIG_DIR / "config.json"


class DeviceAuthManager:
    """Manages device authorization flow authentication."""

    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/api").rstrip("/")
        self.config_dir = CONFIG_DIR
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = CONFIG_FILE

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file."""
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)
        self.config_file.chmod(0o600)

    def device_login(self) -> Optional[str]:
        """
        Perform device authorization flow.

        Returns:
            JWT token if successful, None otherwise
        """
        # Step 1: Request device code
        try:
            response = requests.post(f"{self.api_url}/api/auth/device/code", timeout=10)
            response.raise_for_status()
            device_data = response.json()
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to initiate device flow: {e}")
            return None

        device_code = device_data["device_code"]
        user_code = device_data["user_code"]
        verification_uri = device_data["verification_uri"]
        expires_in = device_data["expires_in"]
        interval = device_data["interval"]

        # Step 2: Display user code and verification URI
        console.print(
            Panel.fit(
                f"[cyan bold]Device Authorization[/cyan bold]\n\n"
                f"Go to: [link]{verification_uri}[/link]\n"
                f"Enter code: [yellow bold]{user_code}[/yellow bold]\n\n"
                f"Code expires in {expires_in // 60} minutes",
                title="🔐 Login Required",
                border_style="cyan",
            )
        )

        # Step 3: Poll for authorization
        start_time = time.time()

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            _ = progress.add_task("Waiting for authorization...", total=None)

            while time.time() - start_time < expires_in:
                try:
                    poll_response = requests.post(
                        f"{self.api_url}/api/auth/device/token",
                        json={"device_code": device_code},
                        timeout=10,
                    )

                    if poll_response.status_code == 200:
                        # Authorization complete!
                        token_data = poll_response.json()
                        access_token = token_data["access_token"]
                        refresh_token = token_data.get("refresh_token")

                        # Save tokens
                        config = self._load_config()
                        config["auth"] = {
                            "type": "device",
                            "token": access_token,
                            "refresh_token": refresh_token,
                            "expires_at": time.time() + token_data["expires_in"],
                        }
                        self._save_config(config)

                        progress.stop()
                        console.print("[green]✓[/green] Authentication successful!")
                        return access_token

                    elif poll_response.status_code == 202:
                        # Still pending
                        pass

                    elif poll_response.status_code == 400:
                        error_data = poll_response.json()
                        if error_data.get("error") == "slow_down":
                            # Increase polling interval
                            interval += 5

                    elif poll_response.status_code == 410:
                        # Expired
                        progress.stop()
                        console.print("[red]✗[/red] Code expired")
                        return None

                    elif poll_response.status_code == 404:
                        progress.stop()
                        console.print("[red]✗[/red] Invalid device code")
                        return None

                except requests.RequestException:
                    pass

                # Wait before next poll
                time.sleep(interval)

        console.print("[red]✗[/red] Authorization timeout")
        return None

    def api_key_login(self, api_key: str) -> Optional[str]:
        """
        Authenticate using API key.

        Args:
            api_key: API key from web UI

        Returns:
            JWT token if successful, None otherwise
        """
        try:
            response = requests.post(
                f"{self.api_url}/api/auth/apikey", json={"apiKey": api_key}, timeout=10
            )
            response.raise_for_status()
            token_data = response.json()
            jwt_token = token_data["token"]

            # Save token
            config = self._load_config()
            config["auth"] = {
                "type": "apikey",
                "token": jwt_token,
                "api_key": api_key,  # Store for reference
            }
            self._save_config(config)

            console.print("[green]✓[/green] API key authentication successful!")
            return jwt_token

        except requests.RequestException as e:
            console.print(f"[red]✗[/red] API key authentication failed: {e}")
            return None

    def refresh_access_token(self) -> Optional[str]:
        """
        Refresh the access token using the refresh token.

        Returns:
            New access token if successful, None otherwise
        """
        config = self._load_config()
        auth = config.get("auth", {})
        refresh_token = auth.get("refresh_token")

        if not refresh_token:
            return None

        try:
            response = requests.post(
                f"{self.api_url}/api/auth/refresh",
                json={"refresh_token": refresh_token},
                timeout=10,
            )

            if response.status_code == 200:
                token_data = response.json()
                new_access_token = token_data["access_token"]

                # Update stored access token and expiry
                auth["token"] = new_access_token
                auth["expires_at"] = time.time() + token_data["expires_in"]
                config["auth"] = auth
                self._save_config(config)

                return new_access_token
            else:
                # Refresh failed (invalid or expired refresh token)
                return None

        except requests.RequestException:
            return None

    def get_token(self) -> Optional[str]:
        """Get saved token from config, refreshing if needed."""
        config = self._load_config()
        auth = config.get("auth", {})

        token = auth.get("token")
        if not token:
            return None

        # Check expiration for device flow tokens
        if auth.get("type") == "device":
            expires_at = auth.get("expires_at", 0)

            # If token expired, try to refresh
            if time.time() > expires_at:
                new_token = self.refresh_access_token()
                if new_token:
                    return new_token
                else:
                    console.print(
                        "[yellow]⚠[/yellow] Token expired and refresh failed. Please login again."
                    )
                    return None

        return token

    def logout(self):
        """Remove saved credentials."""
        config = self._load_config()
        if "auth" in config:
            del config["auth"]
            self._save_config(config)
        console.print("[green]✓[/green] Logged out successfully")

    def get_token_info(self) -> Optional[Dict[str, Any]]:
        """
        Get detailed token information including expiry.

        Returns:
            Dict with token info or None if not authenticated
        """
        config = self._load_config()
        auth = config.get("auth", {})

        if not auth.get("token"):
            return None

        info = {
            "type": auth.get("type"),
            "has_token": bool(auth.get("token")),
            "has_refresh_token": bool(auth.get("refresh_token")),
            "expires_at": auth.get("expires_at"),
        }

        # Calculate time until expiry
        if info["expires_at"]:
            seconds_remaining = info["expires_at"] - time.time()
            info["seconds_remaining"] = max(0, seconds_remaining)
            info["is_expired"] = seconds_remaining <= 0
        else:
            info["seconds_remaining"] = None
            info["is_expired"] = None

        return info

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get current user information."""
        token = self.get_token()
        if not token:
            return None

        try:
            response = requests.get(
                f"{self.api_url}/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    def assume_automation(
        self, name_or_id: str, description: Optional[str] = None
    ) -> Optional[str]:
        """
        Assume an automation identity.

        Accepts either an automation name or UUID:
        - If UUID: Uses that automation directly
        - If name and exists: Creates new API key for existing automation
        - If name and doesn't exist: Creates new automation with API key

        Then logs in with that key, replacing the current authentication.

        Args:
            name_or_id: Automation name or UUID
            description: Optional automation description (used when creating new automation)

        Returns:
            JWT token if successful, None otherwise
        """
        # Get current token for creating the automation
        current_token = self.get_token()
        if not current_token:
            console.print(
                "[red]✗[/red] Not authenticated. Run: [cyan]scambus auth login[/cyan] first"
            )
            return None

        try:
            # Check if input looks like a UUID
            import re

            uuid_pattern = re.compile(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
            )
            is_uuid = bool(uuid_pattern.match(name_or_id))

            if is_uuid:
                # Input is a UUID - use it directly
                automation_id = name_or_id
                console.print(f"[cyan]Using automation ID:[/cyan] {automation_id}")

                # Verify it exists
                try:
                    verify_response = requests.get(
                        f"{self.api_url}/api/automations/{automation_id}",
                        headers={"Authorization": f"Bearer {current_token}"},
                        timeout=10,
                    )
                    verify_response.raise_for_status()
                    automation = verify_response.json()
                    automation_name = automation.get("name", "Unknown")
                    console.print(f"[green]✓[/green] Found automation: {automation_name}")
                except requests.RequestException:
                    console.print(f"[red]✗[/red] Automation not found: {automation_id}")
                    return None
            else:
                # Input is a name - search for it
                automation_name = name_or_id
                console.print(f"[cyan]Checking for existing automation:[/cyan] {automation_name}")
                list_response = requests.get(
                    f"{self.api_url}/api/automations",
                    headers={"Authorization": f"Bearer {current_token}"},
                    timeout=10,
                )
                list_response.raise_for_status()
                automations = list_response.json()

                # Find automation by name
                existing_automation = None
                for auto in automations:
                    if auto.get("name") == automation_name:
                        existing_automation = auto
                        break

                if existing_automation:
                    automation_id = existing_automation["id"]
                    console.print(f"[green]✓[/green] Found existing automation: {automation_id}")
                else:
                    # Create new automation if not found
                    console.print(f"[cyan]Creating new automation:[/cyan] {automation_name}")
                    automation_body = {"name": automation_name, "active": True}
                    if description:
                        automation_body["description"] = description

                    automation_response = requests.post(
                        f"{self.api_url}/api/automations",
                        headers={"Authorization": f"Bearer {current_token}"},
                        json=automation_body,
                        timeout=10,
                    )
                    automation_response.raise_for_status()
                    automation = automation_response.json()
                    automation_id = automation["id"]

                    console.print(f"[green]✓[/green] Automation created: {automation_id}")

            # Step 2: Create API key for automation
            console.print("[cyan]Generating API key...[/cyan]")

            # Get automation name for the key name
            if not is_uuid:
                key_name = f"{name_or_id} CLI Key"
            else:
                # For UUID input, fetch the automation name
                try:
                    auto_response = requests.get(
                        f"{self.api_url}/api/automations/{automation_id}",
                        headers={"Authorization": f"Bearer {current_token}"},
                        timeout=10,
                    )
                    auto_response.raise_for_status()
                    auto_data = auto_response.json()
                    key_name = f"{auto_data.get('name', 'Automation')} CLI Key"
                except:
                    key_name = "CLI Key"

            api_key_body = {"name": key_name}

            api_key_response = requests.post(
                f"{self.api_url}/api/automations/{automation_id}/api-keys",
                headers={"Authorization": f"Bearer {current_token}"},
                json=api_key_body,
                timeout=10,
            )
            api_key_response.raise_for_status()
            api_key_data = api_key_response.json()

            access_key_id = api_key_data["accessKeyId"]
            secret_access_key = api_key_data["secretAccessKey"]
            combined_key = f"{access_key_id}:{secret_access_key}"

            console.print(f"[green]✓[/green] API key created")
            console.print(
                f"\n[yellow]⚠ Save this API key - it won't be shown again:[/yellow]\n"
                f"[bold]{combined_key}[/bold]\n"
            )

            # Step 3: Login with the new API key
            console.print("[cyan]Switching to automation identity...[/cyan]")
            token = self.api_key_login(combined_key)

            if token:
                # Get automation name for display
                display_name = (
                    name_or_id
                    if not is_uuid
                    else automation_name if "automation_name" in locals() else automation_id[:8]
                )
                console.print(f"[green]✓[/green] Now operating as automation: {display_name}")
                return token
            else:
                console.print("[red]✗[/red] Failed to switch to automation identity")
                return None

        except requests.RequestException as e:
            console.print(f"[red]✗[/red] Failed to create automation: {e}")
            return None
