"""Journal entry commands."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from scambus_cli.utils import (
    print_detail,
    print_error,
    print_info,
    print_json,
    print_success,
    print_table,
    print_warning,
)


def now_iso():
    """Return current time in ISO 8601 format with timezone."""
    return datetime.now(timezone.utc).isoformat()


def parse_time_or_relative(time_str):
    """
    Parse a time string that can be either:
    - ISO 8601 format (e.g., "2025-10-27T10:00:00Z")
    - Relative time (e.g., "-15m", "+2h", "-1d")

    Relative time format:
    - Must start with + or -
    - Followed by a number
    - Followed by a unit: s (seconds), m (minutes), h (hours), d (days)

    Examples:
        "-15m"  -> 15 minutes ago
        "+2h"   -> 2 hours from now
        "-1d"   -> 1 day ago
        "now"   -> current time

    Returns:
        datetime object in UTC

    Raises:
        ValueError: If the format is invalid
    """
    import re
    from datetime import timedelta

    if not time_str:
        return None

    time_str = time_str.strip()

    # Special case: "now"
    if time_str.lower() == "now":
        return datetime.now(timezone.utc)

    # Check if it's a relative time (starts with + or -)
    relative_pattern = r'^([+-])(\d+)([smhd])$'
    match = re.match(relative_pattern, time_str)

    if match:
        sign, amount, unit = match.groups()
        amount = int(amount)

        # Calculate timedelta based on unit
        if unit == 's':
            delta = timedelta(seconds=amount)
        elif unit == 'm':
            delta = timedelta(minutes=amount)
        elif unit == 'h':
            delta = timedelta(hours=amount)
        elif unit == 'd':
            delta = timedelta(days=amount)
        else:
            raise ValueError(f"Invalid time unit: {unit}. Use s, m, h, or d.")

        # Apply sign
        if sign == '-':
            return datetime.now(timezone.utc) - delta
        else:
            return datetime.now(timezone.utc) + delta

    # Try to parse as ISO 8601
    try:
        from dateutil import parser as date_parser
        parsed = date_parser.isoparse(time_str)
        # Ensure it has timezone info
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (ValueError, ImportError) as e:
        raise ValueError(
            f"Invalid time format: {time_str}. "
            f"Use ISO 8601 format (e.g., '2025-10-27T10:00:00Z') "
            f"or relative time (e.g., '-15m', '+2h', '-1d')"
        ) from e


def upload_media_file(client, file_path, notes=None):
    """Helper to upload a media file."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Use the client's upload_media method instead of _request
    media = client.upload_media(file_path, notes=notes)
    # Return dict format for compatibility with existing code
    # Note: existing code expects 'filename' but Media object has 'file_name'
    return {
        "id": media.id,
        "filename": media.file_name,
        "type": media.type,
        "mimeType": media.mime_type,
        "fileSize": media.file_size,
        "notes": media.notes,
    }


@click.group()
def journal():
    """Manage journal entries."""
    pass


@journal.command("list")
@click.option("--type", "entry_type", help="Filter by type")
@click.option("--page", default=1)
@click.option("--limit", default=20)
@click.option("--json", "output_json", is_flag=True)
@click.pass_context
def list_entries(ctx, entry_type, page, limit, output_json):
    """List journal entries."""
    client = ctx.obj.get_client()

    try:
        entries = client.list_journal_entries(entry_type=entry_type, page=page, limit=limit)

        if output_json:
            print_json([e.to_dict() for e in entries])
        else:
            table_data = [
                {
                    "ID": e.id,
                    "Type": e.entry_type,
                    "Description": (e.description or "")[:50],
                    "Created": e.created_at.strftime("%Y-%m-%d") if e.created_at else "N/A",
                }
                for e in entries
            ]

            print_table(table_data, title=f"Journal Entries (Page {page})")

    except Exception as e:
        print_error(f"Failed to list journal entries: {e}")
        sys.exit(1)


@journal.command()
@click.argument("entry_id")
@click.option("--json", "output_json", is_flag=True)
@click.pass_context
def get(ctx, entry_id, output_json):
    """Get journal entry details."""
    client = ctx.obj.get_client()

    try:
        entry = client.get_journal_entry(entry_id)

        if output_json:
            print_json(entry.to_dict())
        else:
            print_detail(entry.to_dict(), title=f"Journal Entry: {entry.entry_type}")

    except Exception as e:
        print_error(f"Failed to get journal entry: {e}")
        sys.exit(1)


@journal.command()
@click.option("--search", help="Full-text search in description")
@click.option("--type", "entry_type", help="Filter by type (phone_call, email, etc.)")
@click.option(
    "--direction",
    help="Call/message direction (inbound/outbound) - shortcut for --detail direction=X",
)
@click.option("--platform", help="Platform (pstn, voip, etc.) - shortcut for --detail platform=X")
@click.option(
    "--detail",
    multiple=True,
    help="JSONB detail filter in format key=value (e.g., direction=inbound)",
)
@click.option("--min-confidence", type=float, help="Minimum confidence score (0.0-1.0)")
@click.option("--max-confidence", type=float, help="Maximum confidence score (0.0-1.0)")
@click.option("--after", help="Performed after date (ISO format: 2025-01-01T00:00:00Z)")
@click.option("--before", help="Performed before date (ISO format)")
@click.option("--order-by", default="performed_at", help="Sort column (default: performed_at)")
@click.option("--order-desc/--order-asc", default=True, help="Sort order (default: descending)")
@click.option("--limit", type=int, help="Max results to fetch (fetches in pages of 100)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--with-identifiers", is_flag=True, help="Include related identifiers")
@click.option("--with-evidence", is_flag=True, help="Include related evidence")
@click.pass_context
def query(
    ctx,
    search,
    entry_type,
    direction,
    platform,
    detail,
    min_confidence,
    max_confidence,
    after,
    before,
    order_by,
    order_desc,
    limit,
    output_json,
    with_identifiers,
    with_evidence,
):
    """
    Query journal entries with advanced filtering.

    Results are fetched in pages of 100 until limit is reached or no more results.

    Examples:
        # Search for "spam" in recent entries
        scambus journal query --search spam --limit 50

        # Find all inbound phone calls
        scambus journal query --type phone_call --direction inbound

        # Query by multiple JSONB details
        scambus journal query --detail direction=inbound --detail platform=pstn

        # Time range query with confidence filter
        scambus journal query --after 2025-01-01T00:00:00Z --min-confidence 0.7

        # Export everything to JSON
        scambus journal query --json > results.json
    """
    client = ctx.obj.get_client()

    try:
        # Build details dict from --detail options and shortcuts
        details = {}
        if direction:
            details["direction"] = direction
        if platform:
            details["platform"] = platform
        for d in detail:
            if "=" in d:
                key, value = d.split("=", 1)
                details[key] = value

        # Fetch results (paginated)
        all_entries = []
        cursor = None
        fetched = 0
        max_to_fetch = limit if limit else float("inf")

        while fetched < max_to_fetch:
            result = client.query_journal_entries(
                search_query=search,
                entry_type=entry_type,
                min_confidence=min_confidence,
                max_confidence=max_confidence,
                performed_after=after,
                performed_before=before,
                details=details if details else None,
                order_by=order_by,
                order_desc=order_desc,
                cursor=cursor,
                include_identifiers=with_identifiers,
                include_evidence=with_evidence,
            )

            all_entries.extend(result["data"])
            fetched += result["count"]

            if not result["hasMore"]:
                break

            cursor = result["nextCursor"]

            # Stop if we've reached the limit
            if limit and fetched >= limit:
                all_entries = all_entries[:limit]
                break

        if output_json:
            # Output as JSON array
            print_json(
                [
                    {
                        "id": e.id,
                        "type": e.type,
                        "description": e.description,
                        "performed_at": e.performed_at.isoformat() if e.performed_at else None,
                        "details": e.details,
                        "identifiers": (
                            [
                                {"id": i.id, "type": i.type, "displayValue": i.display_value}
                                for i in (e.identifiers or [])
                            ]
                            if with_identifiers
                            else None
                        ),
                        "evidence": (
                            [{"id": ev.id, "type": ev.type} for ev in (e.evidence or [])]
                            if with_evidence
                            else None
                        ),
                    }
                    for e in all_entries
                ]
            )
        else:
            # Pretty table output
            if not all_entries:
                print_warning("No entries found matching criteria")
                return

            table_data = [
                {
                    "ID": e.id[:8],
                    "Type": e.type or "N/A",
                    "Description": (e.description or "")[:60],
                    "Performed": (
                        e.performed_at.strftime("%Y-%m-%d %H:%M") if e.performed_at else "N/A"
                    ),
                    "Identifiers": len(e.identifiers) if e.identifiers else 0,
                }
                for e in all_entries
            ]

            print_table(table_data, title=f"Query Results ({len(all_entries)} entries)")

            if cursor and fetched >= (limit or float("inf")):
                print_info(f"Showing first {len(all_entries)} results (use --limit to fetch more)")

    except Exception as e:
        print_error(f"Query failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


# ============================================================================
# CREATE COMMANDS
# ============================================================================


@journal.command()
@click.option("--description", required=True, help="Entry description")
@click.option(
    "--identifier",
    multiple=True,
    help="Identifier in format type:value (e.g., email:user@example.com, phone:+1234567890)",
)
@click.option(
    "--our-identifier",
    multiple=True,
    help="Our identifier in format type:value (e.g., phone:+15551234567)",
)
@click.option(
    "--confidence",
    type=float,
    default=1.0,
    help="Confidence level for identifiers (0.0-1.0, default: 1.0)",
)
@click.option("--attach", multiple=True, type=click.Path(exists=True), help="Attach file(s)")
@click.option("--case-id", help="Case ID to link to")
@click.option(
    "--originator-type",
    type=click.Choice(["user", "automation"]),
    help="Originator type for creating entry on behalf of another entity",
)
@click.option(
    "--originator-identifier",
    help="Originator identifier (email/clerk_user_id for user, name for automation)",
)
@click.option(
    "--create-originator",
    is_flag=True,
    help="Create originator if it doesn't exist",
)
@click.pass_context
def create_note(ctx, description, identifier, our_identifier, confidence, attach, case_id, originator_type, originator_identifier, create_originator):
    """Create a note entry."""
    client = ctx.obj.get_client()

    try:
        # Upload attachments if provided
        media_ids = []
        if attach:
            for file_path in attach:
                print(f"Uploading {file_path}...")
                media = upload_media_file(
                    client, file_path, notes=f"Attachment for note: {description}"
                )
                media_ids.append(media["id"])
                print_success(f"Uploaded: {media['filename']}")

        data = {"type": "note", "description": description, "performed_at": now_iso()}

        # Add identifier lookups if provided
        if identifier:
            identifiers = []
            for ident in identifier:
                if ":" not in ident:
                    print_error(
                        f"Invalid identifier format: {ident}. Use type:value (e.g., email:user@example.com)"
                    )
                    sys.exit(1)
                ident_type, ident_value = ident.split(":", 1)
                identifiers.append(
                    {"type": ident_type, "value": ident_value, "confidence": confidence}
                )
            data["identifier_lookups"] = identifiers

        # Add our identifier lookups if provided
        if our_identifier:
            our_identifiers = []
            for ident in our_identifier:
                if ":" not in ident:
                    print_error(
                        f"Invalid our identifier format: {ident}. Use type:value (e.g., phone:+15551234567)"
                    )
                    sys.exit(1)
                ident_type, ident_value = ident.split(":", 1)
                our_identifiers.append(
                    {"type": ident_type, "value": ident_value, "confidence": confidence}
                )
            data["our_identifier_lookups"] = our_identifiers

        # Add evidence if media uploaded
        if media_ids:
            data["evidence"] = {
                "type": "document",
                "description": f"Attachments for note: {description}",
                "source": "CLI Upload",
                "collected_at": now_iso(),
                "media_ids": media_ids,
            }

        if case_id:
            data["case_id"] = case_id

        # Add originator lookup if provided
        if originator_type or originator_identifier:
            # Validation: both must be provided together
            if not originator_type or not originator_identifier:
                print_error(
                    "Both --originator-type and --originator-identifier must be provided together"
                )
                sys.exit(1)

            data["originator_lookup"] = {
                "type": originator_type,
                "identifier": originator_identifier,
                "create_if_not_exists": create_originator,
            }

        entry = client._request("POST", "/journal-entries", json_data=data)
        print_success(f"Note created: {entry['id']}")
        print_detail(entry, title="Created Entry")

    except Exception as e:
        print_error(f"Failed to create note: {e}")
        sys.exit(1)


@journal.command()
@click.option("--description", default="", help="Call description (optional)")
@click.option(
    "--direction", required=True, type=click.Choice(["inbound", "outbound"]), help="Call direction"
)
@click.option(
    "--platform",
    default="pstn",
    type=click.Choice(
        ["facebook", "signal", "telegram", "facetime", "skype", "wechat", "whatsapp", "pstn"]
    ),
    help="Call platform (default: pstn)",
)
@click.option("--duration", type=int, help="Duration in seconds (optional, for backwards compat)")
@click.option("--start-time", help="Call start time (ISO 8601 or relative like '-15m', defaults to now)")
@click.option("--end-time", help="Call end time (ISO 8601 or relative like '-5m', defaults to now)")
@click.option("--in-progress", is_flag=True, help="Mark call as in-progress (no end time)")
@click.option("--phone", help="Phone number identifier")
@click.option(
    "--identifier",
    multiple=True,
    help="Additional identifier in format type:value (e.g., email:user@example.com)",
)
@click.option(
    "--our-identifier",
    multiple=True,
    help="Our identifier in format type:value (e.g., phone:+15551234567)",
)
@click.option(
    "--confidence",
    type=float,
    default=1.0,
    help="Confidence level for identifiers (0.0-1.0, default: 1.0)",
)
@click.option("--recording", type=click.Path(exists=True), help="Phone call recording file")
@click.option("--transcript", type=click.Path(exists=True), help="Call transcript file")
@click.option(
    "--attach", multiple=True, type=click.Path(exists=True), help="Additional attachments"
)
@click.option("--case-id", help="Case ID to link to")
@click.option(
    "--originator-type",
    type=click.Choice(["user", "automation"]),
    help="Originator type for creating entry on behalf of another entity",
)
@click.option(
    "--originator-identifier",
    help="Originator identifier (email/clerk_user_id for user, name for automation)",
)
@click.option(
    "--create-originator",
    is_flag=True,
    help="Create originator if it doesn't exist",
)
@click.option("--json", "output_json", is_flag=True, help="Output JSON")
@click.pass_context
def create_phone_call(
    ctx,
    description,
    direction,
    duration,
    start_time,
    end_time,
    in_progress,
    phone,
    identifier,
    our_identifier,
    confidence,
    recording,
    transcript,
    attach,
    case_id,
    originator_type,
    originator_identifier,
    create_originator,
    platform,
    output_json,
):
    """Create a phone call entry."""
    client = ctx.obj.get_client()

    try:
        # Upload media files
        media_ids = []

        if recording:
            click.echo(f"Uploading recording: {recording}...", err=True)
            media = upload_media_file(
                client, recording, notes=f"Phone call recording: {description}"
            )
            media_ids.append(media["id"])
            click.echo(
                click.style(f"✓ Uploaded recording: {media['filename']}", fg="green"), err=True
            )

        if transcript:
            click.echo(f"Uploading transcript: {transcript}...", err=True)
            media = upload_media_file(
                client, transcript, notes=f"Phone call transcript: {description}"
            )
            media_ids.append(media["id"])
            click.echo(
                click.style(f"✓ Uploaded transcript: {media['filename']}", fg="green"), err=True
            )

        if attach:
            for file_path in attach:
                click.echo(f"Uploading {file_path}...", err=True)
                media = upload_media_file(
                    client, file_path, notes=f"Attachment for call: {description}"
                )
                media_ids.append(media["id"])
                click.echo(click.style(f"✓ Uploaded: {media['filename']}", fg="green"), err=True)

        # Parse and validate time parameters
        from datetime import timedelta

        # Validation: cannot specify both in_progress and end_time/duration
        if in_progress and (end_time or duration):
            print_error("Cannot specify --end-time or --duration with --in-progress")
            sys.exit(1)

        # Parse start_time
        if start_time:
            try:
                parsed_start = parse_time_or_relative(start_time)
            except ValueError as e:
                print_error(str(e))
                sys.exit(1)
        else:
            parsed_start = datetime.now(timezone.utc)

        # Parse end_time (if not in-progress)
        parsed_end = None
        if not in_progress:
            if end_time:
                try:
                    parsed_end = parse_time_or_relative(end_time)
                except ValueError as e:
                    print_error(str(e))
                    sys.exit(1)
            elif duration:
                # Backwards compatibility: calculate from duration
                parsed_end = parsed_start + timedelta(seconds=duration)
            else:
                # Default: end time is now
                parsed_end = datetime.now(timezone.utc)

        # Build data dictionary
        data = {
            "type": "phone_call",
            "description": description,
            "performed_at": parsed_start.isoformat(),
            "start_time": parsed_start.isoformat(),
            "details": {"direction": direction, "platform": platform},
        }

        # Only add end_time if not in-progress
        if not in_progress and parsed_end:
            data["end_time"] = parsed_end.isoformat()

        # Mark as in-progress if flag set
        if in_progress:
            data["in_progress"] = True

        # Add identifier lookups if provided
        identifiers = []
        if phone:
            # Inbound calls: phone is "from", outbound calls: phone is "to"
            label = "from" if direction == "inbound" else "to"
            identifiers.append(
                {"type": "phone", "value": phone, "confidence": confidence, "label": label}
            )
        if identifier:
            for ident in identifier:
                if ":" not in ident:
                    print_error(
                        f"Invalid identifier format: {ident}. Use type:value (e.g., email:user@example.com)"
                    )
                    sys.exit(1)
                ident_type, ident_value = ident.split(":", 1)
                identifiers.append(
                    {"type": ident_type, "value": ident_value, "confidence": confidence}
                )
        if identifiers:
            data["identifier_lookups"] = identifiers

        # Add our identifier lookups if provided
        if our_identifier:
            our_identifiers = []
            for ident in our_identifier:
                if ":" not in ident:
                    print_error(
                        f"Invalid our identifier format: {ident}. Use type:value (e.g., phone:+15551234567)"
                    )
                    sys.exit(1)
                ident_type, ident_value = ident.split(":", 1)
                our_identifiers.append(
                    {"type": ident_type, "value": ident_value, "confidence": confidence}
                )
            data["ourIdentifierLookups"] = our_identifiers

        # Add evidence if media uploaded
        if media_ids:
            data["evidence"] = {
                "type": "recording",
                "description": f"Recording and evidence for call: {description}",
                "source": "Phone Call",
                "collected_at": now_iso(),
                "media_ids": media_ids,
            }

        if case_id:
            data["case_id"] = case_id

        # Add originator lookup if provided
        if originator_type or originator_identifier:
            # Validation: both must be provided together
            if not originator_type or not originator_identifier:
                print_error(
                    "Both --originator-type and --originator-identifier must be provided together"
                )
                sys.exit(1)

            data["originator_lookup"] = {
                "type": originator_type,
                "identifier": originator_identifier,
                "create_if_not_exists": create_originator,
            }

        entry = client._request("POST", "/journal-entries", json_data=data)

        if output_json:
            print_json(entry)
        else:
            print_success(f"Phone call entry created: {entry['id']}")
            print_detail(entry, title="Created Entry")

    except Exception as e:
        print_error(f"Failed to create phone call entry: {e}")
        sys.exit(1)


@journal.command()
@click.option("--description", required=True, help="Email description")
@click.option(
    "--direction", required=True, type=click.Choice(["inbound", "outbound"]), help="Email direction"
)
@click.option("--subject", required=True, help="Email subject")
@click.option("--from-email", help="From email address")
@click.option("--to-email", help="To email address")
@click.option(
    "--identifier",
    multiple=True,
    help="Additional identifier in format type:value (e.g., phone:+1234567890)",
)
@click.option(
    "--confidence",
    type=float,
    default=1.0,
    help="Confidence level for identifiers (0.0-1.0, default: 1.0)",
)
@click.option("--body", help="Email body")
@click.option(
    "--screenshot", multiple=True, type=click.Path(exists=True), help="Email screenshot(s)"
)
@click.option("--eml-file", type=click.Path(exists=True), help="Raw .eml file")
@click.option(
    "--attach", multiple=True, type=click.Path(exists=True), help="Additional attachments"
)
@click.option("--case-id", help="Case ID to link to")
@click.option(
    "--originator-type",
    type=click.Choice(["user", "automation"]),
    help="Originator type for creating entry on behalf of another entity",
)
@click.option(
    "--originator-identifier",
    help="Originator identifier (email/clerk_user_id for user, name for automation)",
)
@click.option(
    "--create-originator",
    is_flag=True,
    help="Create originator if it doesn't exist",
)
@click.pass_context
def create_email(
    ctx,
    description,
    direction,
    subject,
    from_email,
    to_email,
    identifier,
    confidence,
    body,
    screenshot,
    eml_file,
    attach,
    case_id,
    originator_type,
    originator_identifier,
    create_originator,
):
    """Create an email entry."""
    client = ctx.obj.get_client()

    try:
        # Upload media files
        media_ids = []

        if screenshot:
            for ss_path in screenshot:
                print(f"Uploading screenshot: {ss_path}...")
                media = upload_media_file(client, ss_path, notes=f"Email screenshot: {subject}")
                media_ids.append(media["id"])
                print_success(f"Uploaded screenshot: {media['filename']}")

        if eml_file:
            print(f"Uploading .eml file: {eml_file}...")
            media = upload_media_file(client, eml_file, notes=f"Email source file: {subject}")
            media_ids.append(media["id"])
            print_success(f"Uploaded .eml: {media['filename']}")

        if attach:
            for file_path in attach:
                print(f"Uploading {file_path}...")
                media = upload_media_file(
                    client, file_path, notes=f"Attachment for email: {subject}"
                )
                media_ids.append(media["id"])
                print_success(f"Uploaded: {media['filename']}")

        data = {
            "type": "email",
            "description": description,
            "performed_at": now_iso(),
            "details": {"direction": direction, "subject": subject, "sentAt": now_iso()},
        }

        if body:
            data["details"]["body"] = body

        # Add identifier lookups
        identifiers = []
        if from_email:
            # Inbound emails: from_email is "from", outbound emails: from_email is "to"
            label = "from" if direction == "inbound" else "to"
            identifiers.append(
                {"type": "email", "value": from_email, "confidence": confidence, "label": label}
            )
        if to_email and to_email != from_email:
            # Inbound emails: to_email is "to", outbound emails: to_email is "from"
            label = "to" if direction == "inbound" else "from"
            identifiers.append(
                {"type": "email", "value": to_email, "confidence": confidence, "label": label}
            )
        if identifier:
            for ident in identifier:
                if ":" not in ident:
                    print_error(
                        f"Invalid identifier format: {ident}. Use type:value (e.g., phone:+1234567890)"
                    )
                    sys.exit(1)
                ident_type, ident_value = ident.split(":", 1)
                identifiers.append(
                    {"type": ident_type, "value": ident_value, "confidence": confidence}
                )
        if identifiers:
            data["identifier_lookups"] = identifiers

        # Add evidence if media uploaded
        if media_ids:
            data["evidence"] = {
                "type": "screenshot",
                "description": f"Screenshots and attachments for email: {subject}",
                "source": "Email Communication",
                "collected_at": now_iso(),
                "media_ids": media_ids,
            }

        if case_id:
            data["case_id"] = case_id

        # Add originator lookup if provided
        if originator_type or originator_identifier:
            # Validation: both must be provided together
            if not originator_type or not originator_identifier:
                print_error(
                    "Both --originator-type and --originator-identifier must be provided together"
                )
                sys.exit(1)

            data["originator_lookup"] = {
                "type": originator_type,
                "identifier": originator_identifier,
                "create_if_not_exists": create_originator,
            }

        entry = client._request("POST", "/journal-entries", json_data=data)
        print_success(f"Email entry created: {entry['id']}")
        print_detail(entry, title="Created Entry")

    except Exception as e:
        print_error(f"Failed to create email entry: {e}")
        sys.exit(1)


@journal.command()
@click.option("--description", required=True, help="Conversation description")
@click.option("--platform", required=True, help="Platform (SMS, WhatsApp, Telegram, etc.)")
@click.option("--phone", help="Phone number identifier")
@click.option(
    "--identifier",
    multiple=True,
    help="Additional identifier in format type:value (e.g., email:user@example.com)",
)
@click.option(
    "--confidence",
    type=float,
    default=1.0,
    help="Confidence level for identifiers (0.0-1.0, default: 1.0)",
)
@click.option(
    "--screenshot", multiple=True, type=click.Path(exists=True), help="Conversation screenshot(s)"
)
@click.option(
    "--attach", multiple=True, type=click.Path(exists=True), help="Additional attachments"
)
@click.option("--case-id", help="Case ID to link to")
@click.option(
    "--originator-type",
    type=click.Choice(["user", "automation"]),
    help="Originator type for creating entry on behalf of another entity",
)
@click.option(
    "--originator-identifier",
    help="Originator identifier (email/clerk_user_id for user, name for automation)",
)
@click.option(
    "--create-originator",
    is_flag=True,
    help="Create originator if it doesn't exist",
)
@click.pass_context
def create_text_conversation(
    ctx, description, platform, phone, identifier, confidence, screenshot, attach, case_id, originator_type, originator_identifier, create_originator
):
    """Create a text conversation entry."""
    client = ctx.obj.get_client()

    try:
        # Upload media files
        media_ids = []

        if screenshot:
            for ss_path in screenshot:
                print(f"Uploading screenshot: {ss_path}...")
                media = upload_media_file(
                    client, ss_path, notes=f"Text conversation screenshot on {platform}"
                )
                media_ids.append(media["id"])
                print_success(f"Uploaded screenshot: {media['filename']}")

        if attach:
            for file_path in attach:
                print(f"Uploading {file_path}...")
                media = upload_media_file(
                    client, file_path, notes=f"Attachment for {platform} conversation"
                )
                media_ids.append(media["id"])
                print_success(f"Uploaded: {media['filename']}")

        # For completed text conversations, start and end at the same time
        conversation_time = now_iso()

        data = {
            "type": "text_conversation",
            "description": description,
            "performed_at": conversation_time,
            "start_time": conversation_time,
            "end_time": conversation_time,
            "details": {"platform": platform},
        }

        # Add identifier lookups
        identifiers = []
        if phone:
            identifiers.append({"type": "phone", "value": phone, "confidence": confidence})
        if identifier:
            for ident in identifier:
                if ":" not in ident:
                    print_error(
                        f"Invalid identifier format: {ident}. Use type:value (e.g., email:user@example.com)"
                    )
                    sys.exit(1)
                ident_type, ident_value = ident.split(":", 1)
                identifiers.append(
                    {"type": ident_type, "value": ident_value, "confidence": confidence}
                )
        if identifiers:
            data["identifier_lookups"] = identifiers

        # Add evidence if media uploaded
        if media_ids:
            data["evidence"] = {
                "type": "screenshot",
                "description": f"Screenshots for {platform} conversation: {description}",
                "source": f"{platform} Communication",
                "collected_at": now_iso(),
                "media_ids": media_ids,
            }

        if case_id:
            data["case_id"] = case_id

        # Add originator lookup if provided
        if originator_type or originator_identifier:
            # Validation: both must be provided together
            if not originator_type or not originator_identifier:
                print_error(
                    "Both --originator-type and --originator-identifier must be provided together"
                )
                sys.exit(1)

            data["originator_lookup"] = {
                "type": originator_type,
                "identifier": originator_identifier,
                "create_if_not_exists": create_originator,
            }

        entry = client._request("POST", "/journal-entries", json_data=data)
        print_success(f"Text conversation entry created: {entry['id']}")
        print_detail(entry, title="Created Entry")

    except Exception as e:
        print_error(f"Failed to create text conversation entry: {e}")
        sys.exit(1)


@journal.command()
@click.option("--description", required=True, help="Detection description")
@click.option("--category", required=True, help="Detection category (phishing, fraud, etc.)")
@click.option(
    "--confidence", type=float, default=0.0, help="Detection confidence (0.0-1.0, default: 0.0)"
)
@click.option("--identifiers", help="JSON array of identifiers")
@click.option(
    "--screenshot", multiple=True, type=click.Path(exists=True), help="Detection screenshot(s)"
)
@click.option(
    "--attach", multiple=True, type=click.Path(exists=True), help="Additional evidence files"
)
@click.option("--case-id", help="Case ID to link to")
@click.option(
    "--originator-type",
    type=click.Choice(["user", "automation"]),
    help="Originator type for creating entry on behalf of another entity",
)
@click.option(
    "--originator-identifier",
    help="Originator identifier (email/clerk_user_id for user, name for automation)",
)
@click.option(
    "--create-originator",
    is_flag=True,
    help="Create originator if it doesn't exist",
)
@click.pass_context
def create_detection(
    ctx, description, category, confidence, identifiers, screenshot, attach, case_id, originator_type, originator_identifier, create_originator
):
    """Create a detection entry."""
    client = ctx.obj.get_client()

    try:
        # Upload media files
        media_ids = []

        if screenshot:
            for ss_path in screenshot:
                print(f"Uploading screenshot: {ss_path}...")
                media = upload_media_file(
                    client, ss_path, notes=f"Detection screenshot: {description}"
                )
                media_ids.append(media["id"])
                print_success(f"Uploaded screenshot: {media['filename']}")

        if attach:
            for file_path in attach:
                print(f"Uploading {file_path}...")
                media = upload_media_file(
                    client, file_path, notes=f"Detection evidence: {description}"
                )
                media_ids.append(media["id"])
                print_success(f"Uploaded: {media['filename']}")

        data = {
            "type": "detection",
            "description": description,
            "performed_at": now_iso(),
            "details": {"category": category, "confidence": confidence},
        }

        if identifiers:
            try:
                data["identifierLookups"] = json.loads(identifiers)
            except json.JSONDecodeError:
                print_error("Invalid JSON for identifiers")
                sys.exit(1)

        # Add evidence if media uploaded
        if media_ids:
            data["evidence"] = {
                "type": "screenshot",
                "description": f"Evidence for {category} detection: {description}",
                "source": "Automated Detection",
                "collected_at": now_iso(),
                "media_ids": media_ids,
            }

        if case_id:
            data["case_id"] = case_id

        # Add originator lookup if provided
        if originator_type or originator_identifier:
            # Validation: both must be provided together
            if not originator_type or not originator_identifier:
                print_error(
                    "Both --originator-type and --originator-identifier must be provided together"
                )
                sys.exit(1)

            data["originator_lookup"] = {
                "type": originator_type,
                "identifier": originator_identifier,
                "create_if_not_exists": create_originator,
            }

        entry = client._request("POST", "/journal-entries", json_data=data)
        print_success(f"Detection entry created: {entry['id']}")
        print_detail(entry, title="Created Entry")

    except Exception as e:
        print_error(f"Failed to create detection entry: {e}")
        sys.exit(1)


@journal.command()
@click.argument("entry_id")
@click.option(
    "--end-time",
    help="Activity end time (ISO 8601 or relative like '-5m', defaults to now)",
)
@click.option(
    "--reason",
    default="manual",
    help="Completion reason (default: manual)",
)
@click.option("--description", help="Optional description for the completion entry")
@click.option("--json", "output_json", is_flag=True, help="Output JSON")
@click.pass_context
def complete(ctx, entry_id, end_time, reason, description, output_json):
    """
    Complete an in-progress activity.

    Marks a journal entry as complete by creating an activity_complete child entry.
    The parent entry must have a start_time and no end_time.

    Examples:
        # Complete an activity now
        scambus journal complete abc123

        # Complete with specific end time
        scambus journal complete abc123 --end-time "-5m"

        # Complete with custom reason
        scambus journal complete abc123 --reason "timeout"
    """
    client = ctx.obj.get_client()

    try:
        # Parse end_time if provided
        parsed_end = None
        if end_time:
            try:
                parsed_end = parse_time_or_relative(end_time)
            except ValueError as e:
                print_error(str(e))
                sys.exit(1)

        # Call the client's complete_activity method
        completion_entry = client.complete_activity(
            parent_entry=entry_id,
            end_time=parsed_end,
            completion_reason=reason,
            description=description,
        )

        if output_json:
            print_json({
                "id": completion_entry.id,
                "type": completion_entry.type,
                "description": completion_entry.description,
                "performed_at": completion_entry.performed_at.isoformat() if completion_entry.performed_at else None,
                "parent_journal_entry_id": completion_entry.parent_journal_entry_id,
                "details": completion_entry.details,
            })
        else:
            print_success(f"Activity completed: {entry_id}")
            print_detail({
                "completion_id": completion_entry.id,
                "parent_id": entry_id,
                "completion_reason": reason,
                "completed_at": completion_entry.performed_at.isoformat() if completion_entry.performed_at else None,
            }, title="Activity Completed")

    except Exception as e:
        print_error(f"Failed to complete activity: {e}")
        sys.exit(1)
