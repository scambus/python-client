"""Search commands."""

import sys

import click

from scambus_cli.utils import print_error, print_info, print_json, print_table


@click.group()
def search():
    """Search identifiers and cases."""
    pass


@search.command()
@click.option("--query", help="Search query for existing identifiers (use without --follow)")
@click.option(
    "--type",
    "identifier_type",
    help="Filter by identifier type (optional). Available types: email, phone, bank_account, crypto_wallet, social_media, zelle",
)
@click.option("--limit", type=int, default=20, help="Maximum results to return (default: 20, only for search)")
@click.option("--min-confidence", type=float, default=0.0, help="Minimum confidence (0.0-1.0, only for --follow)")
@click.option("--follow", "-f", is_flag=True, help="Follow mode: create temporary stream and watch for new identifiers in real-time")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON format")
@click.pass_context
def identifiers(ctx, query, identifier_type, limit, min_confidence, follow, output_json):
    """Search for identifiers or follow new ones in real-time.

    \b
    Search Mode (without --follow):
      --query        Text to search for (phone numbers, emails, usernames, etc.) [REQUIRED]
      --type         Filter by identifier type
      --limit        Maximum number of results (default: 20)

    \b
    Follow Mode (with --follow):
      --type         Identifier type to follow [REQUIRED with --follow]
      --min-confidence  Minimum confidence threshold (default: 0.0)

    \b
    Examples:
      # Search for existing identifiers
      scambus search identifiers --query "+1234567890"
      scambus search identifiers --query "scammer" --type email

      # Follow new phone numbers in real-time
      scambus search identifiers --type phone --follow

      # Follow high-confidence emails
      scambus search identifiers --type email --min-confidence 0.8 --follow

      # Follow with JSON output
      scambus search identifiers --type phone --follow --json
    """
    client = ctx.obj.get_client()

    # Follow mode: create temporary stream and watch for new identifiers
    if follow:
        if not identifier_type:
            print_error("--type is required when using --follow")
            sys.exit(1)

        import asyncio
        from scambus_client.websocket_client import ScambusWebSocketClient
        from scambus_cli.config import get_api_url
        from scambus_cli.auth_device import DeviceAuthManager

        stream_id = None

        try:
            # Create temporary stream
            print_info(f"Creating temporary stream for {identifier_type} identifiers...")

            stream = client.create_temporary_stream(
                data_type="identifier",
                identifier_types=[identifier_type],
                min_confidence=min_confidence
            )
            stream_id = stream.id

            print_info(f"Temporary stream created: {stream_id}")
            print_info(f"Stream will be cleaned up after 1 hour of inactivity")
            print_info(f"Watching for new {identifier_type} identifiers (Ctrl+C to stop)...\n")

            # Get API URL and authentication
            api_url = get_api_url()
            manager = DeviceAuthManager(api_url)
            token = manager.get_token()

            # Create WebSocket client
            ws_client = ScambusWebSocketClient(api_url=api_url, api_token=token)

            message_count = 0

            # Define message handler
            def handle_message(message):
                nonlocal message_count
                message_count += 1

                if output_json:
                    print_json(message)
                else:
                    # Format identifier message
                    from scambus_cli.commands.streams import _format_identifier_message
                    _format_identifier_message(message_count, message)

            # Define error handler
            def handle_error(error):
                print_error(f"WebSocket error: {error}")

            # Run WebSocket client
            asyncio.run(ws_client.listen_stream(
                stream_id=stream_id,
                on_message=handle_message,
                on_error=handle_error,
                cursor="$"  # Start from now (only new messages)
            ))

        except KeyboardInterrupt:
            print_info(f"\n\nStopped following. Received {message_count} identifiers.")
        except Exception as e:
            print_error(f"Failed to follow identifiers: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            # Clean up temporary stream
            if stream_id:
                try:
                    print_info(f"Deleting temporary stream {stream_id}...")
                    client.delete_stream(stream_id)
                    print_info("Temporary stream deleted")
                except Exception as e:
                    print_error(f"Failed to delete temporary stream: {e}")

        return

    # Search mode: search existing identifiers
    if not query:
        print_error("--query is required when not using --follow")
        sys.exit(1)

    try:
        # Convert single type to list if provided
        types = [identifier_type] if identifier_type else None

        results = client.search_identifiers(
            query=query, types=types, limit=limit
        )

        if not results:
            print_info("No identifiers found")
            return

        if output_json:
            print_json(
                [
                    {
                        "id": r.id,
                        "type": r.type,
                        "display_value": r.display_value,
                        "confidence": r.confidence,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                    for r in results
                ]
            )
        else:
            table_data = [
                {
                    "ID": r.id[:8],
                    "Type": r.type,
                    "Value": r.display_value,
                    "Confidence": f"{r.confidence:.2f}" if r.confidence is not None else "N/A",
                }
                for r in results
            ]

            print_table(table_data, title=f"Identifier Search Results ({len(results)})")

    except Exception as e:
        print_error(f"Search failed: {e}")
        sys.exit(1)


@search.command()
@click.option("--query", required=True, help="Search query (REQUIRED)")
@click.option(
    "--status",
    help="Filter by case status (optional). Available statuses: open, closed, investigating",
)
@click.option("--limit", type=int, default=20, help="Maximum results to return (default: 20)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON format")
@click.pass_context
def cases(ctx, query, status, limit, output_json):
    """Search for investigation cases by query string.

    \b
    Required Options:
      --query        Text to search for (case titles, descriptions, etc.)

    \b
    Optional Filters:
      --status       Filter by case status (default: all statuses)
                     Available statuses: open, closed, investigating
      --limit        Maximum number of results (default: 20)
      --json         Output results in JSON format

    \b
    Examples:
      # Search all cases for "phishing"
      scambus search cases --query "phishing"

      # Search only open cases
      scambus search cases --query "Bank of America" --status open

      # Get more results in JSON format
      scambus search cases --query "fraud" --limit 100 --json
    """
    client = ctx.obj.get_client()

    try:
        results = client.search_cases(query=query, status=status, limit=limit)

        if not results:
            print_info("No cases found")
            return

        if output_json:
            print_json(
                [
                    {
                        "id": c.id,
                        "title": c.title,
                        "status": c.status,
                        "created_at": c.created_at.isoformat() if c.created_at else None,
                    }
                    for c in results
                ]
            )
        else:
            table_data = [
                {
                    "ID": c.id[:8],
                    "Title": c.title,
                    "Status": c.status or "N/A",
                    "Created": c.created_at.strftime("%Y-%m-%d") if c.created_at else "N/A",
                }
                for c in results
            ]

            print_table(table_data, title=f"Case Search Results ({len(results)})")

    except Exception as e:
        print_error(f"Search failed: {e}")
        sys.exit(1)
