"""Search commands."""

import sys

import click

from scambus_cli.utils import print_error, print_info, print_json, print_table


@click.group()
def search():
    """Search identifiers and cases."""
    pass


@search.command()
@click.option("--query", required=True, help="Search query (REQUIRED)")
@click.option(
    "--type",
    "identifier_type",
    help="Filter by identifier type (optional). Available types: email, phone, bank_account, crypto_wallet, social_media, zelle",
)
@click.option("--limit", type=int, default=20, help="Maximum results to return (default: 20)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON format")
@click.pass_context
def identifiers(ctx, query, identifier_type, limit, output_json):
    """Search for identifiers by query string.

    \b
    Required Options:
      --query        Text to search for (phone numbers, emails, usernames, etc.)

    \b
    Optional Filters:
      --type         Filter by identifier type (default: all types)
                     Available types: email, phone, bank_account, crypto_wallet,
                                     social_media, zelle
      --limit        Maximum number of results (default: 20)
      --json         Output results in JSON format

    \b
    Examples:
      # Search for a phone number
      scambus search identifiers --query "+1234567890"

      # Search for email addresses containing "scammer"
      scambus search identifiers --query "scammer" --type email

      # Search bank accounts with more results
      scambus search identifiers --query "Bank of America" --type bank_account --limit 50

      # Get raw JSON output
      scambus search identifiers --query "crypto" --type crypto_wallet --json
    """
    client = ctx.obj.get_client()

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
