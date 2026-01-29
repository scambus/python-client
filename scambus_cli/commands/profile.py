"""Profile and user account commands."""

import sys

import click

from scambus_cli.utils import (
    print_detail,
    print_error,
    print_info,
    print_json,
    print_success,
    print_table,
)


@click.group()
def profile():
    """Manage your profile and account."""
    pass


@profile.command()
@click.option("--unread-only", is_flag=True, help="Show only unread notifications")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def notifications(ctx, unread_only, output_json):
    """List your notifications.

    Examples:
        scambus profile notifications
        scambus profile notifications --unread-only
    """
    client = ctx.obj.get_client()

    try:
        notifs = client.list_notifications(unread_only=unread_only)

        if not notifs:
            print_info("No notifications")
            return

        if output_json:
            print_json(
                [
                    {
                        "id": n.id,
                        "message": n.notification_text,
                        "read": n.read,
                        "created_at": (
                            n.created_at.isoformat()
                            if hasattr(n, "created_at") and n.created_at
                            else None
                        ),
                    }
                    for n in notifs
                ]
            )
        else:
            table_data = [
                {
                    "ID": n.id[:8],
                    "Message": (
                        n.notification_text[:50] + "..."
                        if len(n.notification_text) > 50
                        else n.notification_text
                    ),
                    "Read": "✓" if n.read else "✗",
                    "Created": (
                        n.created_at.strftime("%Y-%m-%d %H:%M")
                        if hasattr(n, "created_at") and n.created_at
                        else "N/A"
                    ),
                }
                for n in notifs
            ]

            print_table(table_data, title=f"Notifications ({len(notifs)})")

    except Exception as e:
        print_error(f"Failed to list notifications: {e}")
        sys.exit(1)


@profile.command()
@click.argument("notification_id")
@click.pass_context
def mark_read(ctx, notification_id):
    """Mark a notification as read.

    Examples:
        scambus profile mark-read <notification-id>
    """
    client = ctx.obj.get_client()

    try:
        client.mark_notification_as_read(notification_id)
        print_success(f"Notification marked as read: {notification_id}")

    except Exception as e:
        print_error(f"Failed to mark notification as read: {e}")
        sys.exit(1)


@profile.command()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def sessions(ctx, output_json):
    """List your active sessions.

    Examples:
        scambus profile sessions
    """
    client = ctx.obj.get_client()

    try:
        session_list = client.list_sessions()

        if not session_list:
            print_info("No active sessions")
            return

        if output_json:
            print_json(
                [
                    {
                        "id": s.id,
                        "created_at": (
                            s.created_at.isoformat()
                            if hasattr(s, "created_at") and s.created_at
                            else None
                        ),
                        "last_active": (
                            s.last_active.isoformat()
                            if hasattr(s, "last_active") and s.last_active
                            else None
                        ),
                    }
                    for s in session_list
                ]
            )
        else:
            table_data = [
                {
                    "ID": s.id[:8],
                    "Created": (
                        s.created_at.strftime("%Y-%m-%d %H:%M")
                        if hasattr(s, "created_at") and s.created_at
                        else "N/A"
                    ),
                    "Last Active": (
                        s.last_active.strftime("%Y-%m-%d %H:%M")
                        if hasattr(s, "last_active") and s.last_active
                        else "N/A"
                    ),
                }
                for s in session_list
            ]

            print_table(table_data, title=f"Active Sessions ({len(session_list)})")

    except Exception as e:
        print_error(f"Failed to list sessions: {e}")
        sys.exit(1)


@profile.command()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def passkeys(ctx, output_json):
    """List your passkeys.

    Examples:
        scambus profile passkeys
    """
    client = ctx.obj.get_client()

    try:
        passkey_list = client.list_passkeys()

        if not passkey_list:
            print_info("No passkeys registered")
            return

        if output_json:
            print_json(
                [
                    {
                        "id": p.id,
                        "name": p.name,
                        "created_at": (
                            p.created_at.isoformat()
                            if hasattr(p, "created_at") and p.created_at
                            else None
                        ),
                    }
                    for p in passkey_list
                ]
            )
        else:
            table_data = [
                {
                    "ID": p.id[:8],
                    "Name": p.name,
                    "Created": (
                        p.created_at.strftime("%Y-%m-%d")
                        if hasattr(p, "created_at") and p.created_at
                        else "N/A"
                    ),
                }
                for p in passkey_list
            ]

            print_table(table_data, title=f"Passkeys ({len(passkey_list)})")

    except Exception as e:
        print_error(f"Failed to list passkeys: {e}")
        sys.exit(1)


@profile.command()
@click.option("--enable", is_flag=True, help="Enable 2FA")
@click.option("--disable", is_flag=True, help="Disable 2FA")
@click.pass_context
def twofa(ctx, enable, disable):
    """Manage two-factor authentication.

    Examples:
        scambus profile twofa --enable
        scambus profile twofa --disable
    """
    client = ctx.obj.get_client()

    try:
        if enable and disable:
            print_error("Cannot specify both --enable and --disable")
            sys.exit(1)

        if enable:
            result = client.toggle_2fa(enabled=True)
            print_success("2FA enabled")
            if result:
                print_detail(result, title="2FA Status")
        elif disable:
            result = client.toggle_2fa(enabled=False)
            print_success("2FA disabled")
        else:
            # Show status
            status = client.get_2fa_status()
            print_detail(status, title="2FA Status")

    except Exception as e:
        print_error(f"Failed to manage 2FA: {e}")
        sys.exit(1)
