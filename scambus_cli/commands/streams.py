"""Export stream commands."""

import json
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
def streams():
    """Manage export streams."""
    pass


@streams.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_streams(ctx, output_json):
    """List your export streams.

    Examples:
        scambus streams list
        scambus streams list --json
    """
    client = ctx.obj.get_client()

    try:
        streams = client.list_streams()

        if not streams:
            print_info("No streams found")
            return

        if output_json:
            print_json(
                [
                    {
                        "id": s.id,
                        "name": s.name,
                        "state": s.state,
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                    }
                    for s in streams
                ]
            )
        else:
            table_data = [
                {
                    "ID": s.id[:8],
                    "Name": s.name,
                    "State": s.state,
                    "Created": s.created_at.strftime("%Y-%m-%d") if s.created_at else "N/A",
                }
                for s in streams
            ]

            print_table(table_data, title=f"Export Streams ({len(streams)})")

    except Exception as e:
        print_error(f"Failed to list streams: {e}")
        sys.exit(1)


@streams.command()
@click.argument("stream_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def get(ctx, stream_id, output_json):
    """Get stream details.

    Examples:
        scambus streams get <stream-id>
    """
    client = ctx.obj.get_client()

    try:
        stream = client.get_stream(stream_id)

        if output_json:
            print_json(
                {
                    "id": stream.id,
                    "name": stream.name,
                    "state": stream.state,
                    "filters": stream.filters,
                    "created_at": stream.created_at.isoformat() if stream.created_at else None,
                }
            )
        else:
            print_detail(
                {
                    "ID": stream.id,
                    "Name": stream.name,
                    "State": stream.state,
                    "Filters": json.dumps(stream.filters, indent=2) if stream.filters else "None",
                    "Created": stream.created_at.isoformat() if stream.created_at else "N/A",
                },
                title="Stream Details",
            )

    except Exception as e:
        print_error(f"Failed to get stream: {e}")
        sys.exit(1)


@streams.command()
@click.option("--name", required=True, help="Stream name")
@click.option(
    "--data-type",
    type=click.Choice(["journal_entry", "identifier"], case_sensitive=False),
    default="journal_entry",
    help="Stream data type (default: journal_entry)",
)
@click.option(
    "--identifier-type",
    "identifier_types",
    multiple=True,
    help="Identifier types to filter (can be specified multiple times, e.g., --identifier-type phone --identifier-type email)",
)
@click.option(
    "--min-confidence",
    type=float,
    default=0.0,
    help="Minimum confidence score (0.0-1.0, default: 0.0)",
)
@click.option(
    "--max-confidence",
    type=float,
    default=1.0,
    help="Maximum confidence score (0.0-1.0, default: 1.0)",
)
@click.option(
    "--backfill",
    is_flag=True,
    help="Trigger backfill after creating stream (for identifier streams)",
)
@click.option(
    "--backfill-from-date",
    help="Only backfill from this date (ISO format, e.g., 2025-01-01T00:00:00Z)",
)
@click.option(
    "--filter-expression",
    help="JSONPath filter expression for advanced filtering",
)
@click.option(
    "--retention-days",
    type=int,
    help="Days to retain data (default: 30)",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def create(
    ctx,
    name,
    data_type,
    identifier_types,
    min_confidence,
    max_confidence,
    backfill,
    backfill_from_date,
    filter_expression,
    retention_days,
    output_json,
):
    """Create a new export stream.

    Examples:
        # Create journal entry stream
        scambus streams create --name "Phone Scams" --data-type journal_entry --min-confidence 0.9

        # Create identifier stream
        scambus streams create --name "High-Confidence Phones" \\
            --data-type identifier \\
            --identifier-type phone \\
            --min-confidence 0.8

        # Create identifier stream with backfill
        scambus streams create --name "Recent Emails" \\
            --data-type identifier \\
            --identifier-type email \\
            --backfill \\
            --backfill-from-date 2025-01-01T00:00:00Z
    """
    client = ctx.obj.get_client()

    try:
        # Validate confidence range
        if min_confidence < 0.0 or min_confidence > 1.0:
            print_error("min-confidence must be between 0.0 and 1.0")
            sys.exit(1)
        if max_confidence < 0.0 or max_confidence > 1.0:
            print_error("max-confidence must be between 0.0 and 1.0")
            sys.exit(1)
        if min_confidence > max_confidence:
            print_error("min-confidence cannot be greater than max-confidence")
            sys.exit(1)

        stream = client.create_stream(
            name=name,
            data_type=data_type,
            identifier_types=list(identifier_types) if identifier_types else None,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            backfill_historical=backfill,
            backfill_from_date=backfill_from_date,
            filter_expression=filter_expression,
            retention_days=retention_days,
        )

        if output_json:
            print_json(
                {
                    "id": stream.id,
                    "name": stream.name,
                    "data_type": stream.data_type,
                    "state": stream.state,
                }
            )
        else:
            print_success(f"Stream created: {stream.id}")
            details = {
                "ID": stream.id,
                "Name": stream.name,
                "Data Type": stream.data_type,
                "State": stream.state,
            }
            if identifier_types:
                details["Identifier Types"] = ", ".join(identifier_types)
            if min_confidence > 0.0 or max_confidence < 1.0:
                details["Confidence Range"] = f"{min_confidence}-{max_confidence}"
            if backfill:
                details["Backfill"] = "Triggered"
                if backfill_from_date:
                    details["Backfill From"] = backfill_from_date

            print_detail(details, title="Created Stream")

    except Exception as e:
        print_error(f"Failed to create stream: {e}")
        sys.exit(1)


@streams.command()
@click.argument("stream_id")
@click.option("--limit", type=int, default=10, help="Number of events to consume")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def consume(ctx, stream_id, limit, output_json):
    """Consume events from a stream.

    Automatically detects and formats both journal entry and identifier messages.

    Examples:
        scambus streams consume <stream-id>
        scambus streams consume <stream-id> --limit 100
    """
    client = ctx.obj.get_client()

    try:
        result = client.consume_stream(stream_id, limit=limit)
        messages = result.get("messages", [])

        if not messages:
            print_info("No messages available")
            return

        if output_json:
            print_json(messages)
        else:
            print_success(f"Consumed {len(messages)} messages")
            next_cursor = result.get("nextCursor")
            if next_cursor:
                print_info(f"Next cursor: {next_cursor}")

            for i, msg in enumerate(messages, 1):
                # Detect message type by checking for identifier-specific fields
                is_identifier = "identifierId" in msg or "identifier_id" in msg

                if is_identifier:
                    _format_identifier_message(i, msg)
                else:
                    _format_journal_entry_message(i, msg)

    except Exception as e:
        print_error(f"Failed to consume stream: {e}")
        sys.exit(1)


def _format_identifier_message(index: int, msg: dict):
    """Format an identifier stream message for display."""
    print(f"\n--- Message {index} (Identifier) ---")

    # Get identifier fields (support both camelCase and snake_case)
    identifier_id = msg.get("identifierId") or msg.get("identifier_id", "N/A")
    identifier_type = msg.get("type", "unknown")
    display_value = msg.get("displayValue") or msg.get("display_value", "N/A")
    confidence = msg.get("confidence", 0.0)
    published_at = msg.get("publishedAt") or msg.get("published_at", "N/A")

    print(f"Identifier ID: {identifier_id}")
    print(f"Type: {identifier_type}")
    print(f"Value: {display_value}")
    print(f"Confidence: {confidence:.3f}")
    print(f"Published: {published_at}")

    # Show tags if present
    tags = msg.get("tags", [])
    if tags:
        tag_names = [t.get("name", t.get("id", "unknown")) for t in tags]
        print(f"Tags: {', '.join(tag_names)}")

    # Show triggering journal entry if present
    triggering_je = msg.get("triggeringJournalEntry") or msg.get("triggering_journal_entry")
    if triggering_je:
        je_type = triggering_je.get("type", "unknown")
        je_id = triggering_je.get("id", "N/A")
        performed_at = triggering_je.get("performedAt") or triggering_je.get("performed_at", "N/A")
        print(f"Triggered by: {je_type} ({je_id[:8]}...) at {performed_at}")


def _format_journal_entry_message(index: int, msg: dict):
    """Format a journal entry stream message for display."""
    print(f"\n--- Message {index} (Journal Entry) ---")

    je_id = msg.get("id", "N/A")
    je_type = msg.get("type", "unknown")
    description = msg.get("description", "")
    performed_at = msg.get("performedAt") or msg.get("performed_at", "N/A")

    print(f"Journal Entry ID: {je_id}")
    print(f"Type: {je_type}")
    if description:
        print(f"Description: {description}")
    print(f"Performed: {performed_at}")

    # Show identifiers if present
    identifiers = msg.get("identifiers", [])
    if identifiers:
        print(f"Identifiers ({len(identifiers)}):")
        for ident in identifiers[:5]:  # Show first 5
            ident_type = ident.get("type", "unknown")
            ident_value = ident.get("displayValue") or ident.get("display_value", "N/A")
            ident_conf = ident.get("confidence", 0.0)
            print(f"  - {ident_type}: {ident_value} (confidence: {ident_conf:.3f})")
        if len(identifiers) > 5:
            print(f"  ... and {len(identifiers) - 5} more")


@streams.command()
@click.argument("stream_id")
@click.option(
    "--ignore-checkpoint",
    is_flag=True,
    help="Rebuild last 24 hours instead of using checkpoint",
)
@click.option(
    "--no-clear",
    is_flag=True,
    help="Don't clear stream before rebuilding (default: clear stream)",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def recover(ctx, stream_id, ignore_checkpoint, no_clear, output_json):
    """Trigger recovery/rebuild for a stream.

    This command rebuilds a stream from publish history, useful after Redis data loss
    or corruption. By default, it clears the stream and rebuilds from the last
    consumed checkpoint.

    Examples:
        # Standard checkpoint-based recovery
        scambus streams recover <stream-id>

        # Full 24-hour rebuild
        scambus streams recover <stream-id> --ignore-checkpoint

        # Gap-fill without clearing existing data
        scambus streams recover <stream-id> --no-clear
    """
    client = ctx.obj.get_client()

    try:
        result = client.recover_stream(
            stream_id=stream_id,
            ignore_checkpoint=ignore_checkpoint,
            clear_stream=not no_clear,
        )

        if output_json:
            print_json(result)
        else:
            print_success(f"Recovery triggered for stream: {stream_id}")
            print_info(f"Status: {result.get('status', 'unknown')}")
            if result.get("message"):
                print_info(f"Message: {result['message']}")

    except Exception as e:
        print_error(f"Failed to trigger recovery: {e}")
        sys.exit(1)


@streams.command()
@click.argument("stream_id")
@click.option(
    "--from-date",
    required=True,
    help="Only backfill from this date (ISO format, e.g., 2025-01-01T00:00:00Z)",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def backfill(ctx, stream_id, from_date, output_json):
    """Trigger backfill for an identifier stream.

    This command backfills historical identifier states into an identifier stream.
    Only works for identifier-type streams.

    Examples:
        # Backfill all identifiers from Jan 1, 2025
        scambus streams backfill <stream-id> --from-date 2025-01-01T00:00:00Z

        # Backfill from 7 days ago
        scambus streams backfill <stream-id> --from-date 2025-01-25T00:00:00Z
    """
    client = ctx.obj.get_client()

    try:
        result = client.backfill_stream(stream_id=stream_id, from_date=from_date)

        if output_json:
            print_json(result)
        else:
            print_success(f"Backfill triggered for stream: {stream_id}")
            print_info(f"From date: {from_date}")
            if result.get("status"):
                print_info(f"Status: {result['status']}")
            if result.get("message"):
                print_info(f"Message: {result['message']}")

    except Exception as e:
        print_error(f"Failed to trigger backfill: {e}")
        sys.exit(1)


@streams.command("recovery-status")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def recovery_status(ctx, output_json):
    """View recent recovery history for all streams.

    Shows recovery operations across all streams, including status,
    timing, and any errors.

    Examples:
        scambus streams recovery-status
        scambus streams recovery-status --json
    """
    client = ctx.obj.get_client()

    try:
        status = client.get_recovery_status()
        logs = status.get("logs", [])

        if not logs:
            print_info("No recovery history found")
            return

        if output_json:
            print_json(logs)
        else:
            print_success(f"Recovery History ({len(logs)} operations)")
            for log in logs:
                print(f"\n--- {log.get('streamName', 'Unknown Stream')} ---")
                print(f"Stream ID: {log.get('streamId', 'N/A')}")
                print(f"Started: {log.get('startedAt', 'N/A')}")
                print(f"Completed: {log.get('completedAt', 'In Progress')}")
                if log.get("error"):
                    print(f"Error: {log['error']}")
                if log.get("recordsReplayed") is not None:
                    print(f"Records Replayed: {log['recordsReplayed']}")

    except Exception as e:
        print_error(f"Failed to get recovery status: {e}")
        sys.exit(1)


@streams.command("recovery-info")
@click.argument("stream_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def recovery_info(ctx, stream_id, output_json):
    """Get recovery information for a specific stream.

    Shows current recovery state, checkpoints, and replay progress.

    Examples:
        scambus streams recovery-info <stream-id>
        scambus streams recovery-info <stream-id> --json
    """
    client = ctx.obj.get_client()

    try:
        info = client.get_stream_recovery_info(stream_id)

        if output_json:
            print_json(info)
        else:
            print_detail(
                {
                    "Is Rebuilding": info.get("isRebuilding", False),
                    "Last Consumed Journal Entry": info.get("lastConsumedJournalEntry", "None"),
                    "Last Consumed Identifier": info.get("lastConsumedIdentifier", "None"),
                    "Journal Entries to Replay": info.get("journalEntriesToReplay", "N/A"),
                    "Identifiers to Replay": info.get("identifiersToReplay", "N/A"),
                },
                title="Stream Recovery Info",
            )

    except Exception as e:
        print_error(f"Failed to get recovery info: {e}")
        sys.exit(1)


@streams.command()
@click.argument("stream_id")
@click.pass_context
def delete(ctx, stream_id):
    """Delete a stream.

    Examples:
        scambus streams delete <stream-id>
    """
    client = ctx.obj.get_client()

    try:
        client.delete_stream(stream_id)
        print_success(f"Stream deleted: {stream_id}")

    except Exception as e:
        print_error(f"Failed to delete stream: {e}")
        sys.exit(1)
