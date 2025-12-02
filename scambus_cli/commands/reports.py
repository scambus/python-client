"""PDF Report generation commands."""

import sys
import time

import click

from scambus_cli.utils import (
    print_detail,
    print_error,
    print_info,
    print_json,
    print_success,
    print_warning,
)


@click.group()
def reports():
    """Generate and manage PDF reports.

    Generate court-admissible PDF reports for identifiers, journal entries,
    or entire views. Reports include proper certification, chain of custody
    documentation, and integrity verification.
    """
    pass


@reports.command("identifier")
@click.argument("identifier_id")
@click.option("--output", "-o", type=click.Path(), help="Output file path (default: auto-generated)")
@click.option("--include-journal-entries/--no-journal-entries", default=True, help="Include related journal entries")
@click.option("--include-evidence", is_flag=True, help="Include evidence files in report")
@click.option("--sign", is_flag=True, help="Digitally sign the report")
@click.option("--wait/--no-wait", default=True, help="Wait for report completion (default: wait)")
@click.option("--timeout", type=int, default=300, help="Timeout in seconds when waiting (default: 300)")
@click.option("--json", "output_json", is_flag=True, help="Output report metadata as JSON (no download)")
@click.pass_context
def report_identifier(ctx, identifier_id, output, include_journal_entries, include_evidence, sign, wait, timeout, output_json):
    """Generate a PDF report for a single identifier.

    Creates a court-admissible PDF document containing the identifier data
    with proper certification and integrity verification.

    Examples:
        scambus reports identifier abc123-uuid

        scambus reports identifier abc123-uuid -o fraud_report.pdf

        scambus reports identifier abc123-uuid --include-evidence --sign

        scambus reports identifier abc123-uuid --json
    """
    client = ctx.obj.get_client()

    try:
        print_info(f"Generating report for identifier: {identifier_id[:8]}...")

        report = client.generate_identifier_report(
            identifier_ids=[identifier_id],
            include_journal_entries=include_journal_entries,
            include_evidence=include_evidence,
            sign_report=sign,
        )

        if output_json:
            print_json(report.to_dict())
            return

        if report.is_completed:
            _download_and_save(client, report, output)
        elif report.is_failed:
            print_error(f"Report generation failed: {report.error_message}")
            sys.exit(1)
        elif wait:
            _wait_and_download(client, report, output, timeout)
        else:
            print_success(f"Report generation started: {report.id}")
            print_info(f"Status: {report.status}")
            print_info(f"Check status with: scambus reports status {report.id}")

    except Exception as e:
        print_error(f"Failed to generate report: {e}")
        sys.exit(1)


@reports.command("journal-entry")
@click.argument("entry_id")
@click.option("--output", "-o", type=click.Path(), help="Output file path (default: auto-generated)")
@click.option("--include-identifiers/--no-identifiers", default=True, help="Include related identifiers")
@click.option("--include-evidence", is_flag=True, help="Include evidence files in report")
@click.option("--include-parents", is_flag=True, help="Include parent entries in hierarchy")
@click.option("--sign", is_flag=True, help="Digitally sign the report")
@click.option("--wait/--no-wait", default=True, help="Wait for report completion (default: wait)")
@click.option("--timeout", type=int, default=300, help="Timeout in seconds when waiting (default: 300)")
@click.option("--json", "output_json", is_flag=True, help="Output report metadata as JSON (no download)")
@click.pass_context
def report_journal_entry(ctx, entry_id, output, include_identifiers, include_evidence, include_parents, sign, wait, timeout, output_json):
    """Generate a PDF report for a single journal entry.

    Creates a court-admissible PDF document containing the journal entry data
    with proper certification and integrity verification.

    Examples:
        scambus reports journal-entry abc123-uuid

        scambus reports journal-entry abc123-uuid -o investigation_report.pdf

        scambus reports journal-entry abc123-uuid --include-evidence --include-parents

        scambus reports journal-entry abc123-uuid --json
    """
    client = ctx.obj.get_client()

    try:
        print_info(f"Generating report for journal entry: {entry_id[:8]}...")

        report = client.generate_journal_entry_report(
            journal_entry_ids=[entry_id],
            include_identifiers=include_identifiers,
            include_evidence=include_evidence,
            include_parent_chain=include_parents,
            sign_report=sign,
        )

        if output_json:
            print_json(report.to_dict())
            return

        if report.is_completed:
            _download_and_save(client, report, output)
        elif report.is_failed:
            print_error(f"Report generation failed: {report.error_message}")
            sys.exit(1)
        elif wait:
            _wait_and_download(client, report, output, timeout)
        else:
            print_success(f"Report generation started: {report.id}")
            print_info(f"Status: {report.status}")
            print_info(f"Check status with: scambus reports status {report.id}")

    except Exception as e:
        print_error(f"Failed to generate report: {e}")
        sys.exit(1)


@reports.command("view")
@click.argument("view_id")
@click.option("--output", "-o", type=click.Path(), help="Output file path (default: auto-generated)")
@click.option("--include-evidence", is_flag=True, help="Include evidence files in report")
@click.option("--sign", is_flag=True, help="Digitally sign the report")
@click.option("--wait/--no-wait", default=True, help="Wait for report completion (default: wait)")
@click.option("--timeout", type=int, default=300, help="Timeout in seconds when waiting (default: 300)")
@click.option("--json", "output_json", is_flag=True, help="Output report metadata as JSON (no download)")
@click.pass_context
def report_view(ctx, view_id, output, include_evidence, sign, wait, timeout, output_json):
    """Generate a PDF report from a saved view.

    Automatically determines the report type based on the view's entity type
    (identifier or journal) and generates an appropriate report containing
    all matching items.

    VIEW_ID can be a UUID or an alias (e.g., "my-fraud-identifiers")

    Examples:
        scambus reports view my-fraud-identifiers

        scambus reports view my-fraud-identifiers -o monthly_report.pdf

        scambus reports view 123e4567-e89b-12d3-a456-426614174000 --include-evidence

        scambus reports view my-journal-entries --sign
    """
    client = ctx.obj.get_client()

    try:
        # First, get view details to show what we're reporting on
        view = client.get_view(view_id)
        print_info(f"Generating report from view: {view.name}")
        print_info(f"Entity type: {view.entity_type}")

        report = client.generate_view_report(
            view_id=view_id,
            include_evidence=include_evidence,
            sign_report=sign,
        )

        if output_json:
            print_json(report.to_dict())
            return

        if report.is_completed:
            _download_and_save(client, report, output)
        elif report.is_failed:
            print_error(f"Report generation failed: {report.error_message}")
            sys.exit(1)
        elif wait:
            _wait_and_download(client, report, output, timeout)
        else:
            print_success(f"Report generation started: {report.id}")
            print_info(f"Status: {report.status}")
            print_info(f"Check status with: scambus reports status {report.id}")

    except Exception as e:
        print_error(f"Failed to generate report: {e}")
        sys.exit(1)


@reports.command("status")
@click.argument("report_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def report_status(ctx, report_id, output_json):
    """Check the status of a report.

    Examples:
        scambus reports status abc123-uuid

        scambus reports status abc123-uuid --json
    """
    client = ctx.obj.get_client()

    try:
        report = client.get_report_status(report_id)

        if output_json:
            print_json(report.to_dict())
        else:
            details = {
                "Report ID": report.id,
                "Type": report.report_type,
                "Status": report.status,
            }

            if report.verification_code:
                details["Verification Code"] = report.verification_code
            if report.content_hash:
                details["Content Hash"] = report.content_hash[:16] + "..."
            if report.identifier_count:
                details["Identifiers"] = report.identifier_count
            if report.journal_entry_count:
                details["Journal Entries"] = report.journal_entry_count
            if report.generated_at:
                details["Generated At"] = report.generated_at.isoformat()
            if report.expires_at:
                details["Expires At"] = report.expires_at.isoformat()
            if report.error_message:
                details["Error"] = report.error_message

            print_detail(details, title="Report Status")

            if report.is_completed:
                print_success("Report is ready for download")
                print_info(f"Download with: scambus reports download {report.id}")
            elif report.is_processing:
                print_info("Report is still being generated...")
            elif report.is_failed:
                print_error("Report generation failed")

    except Exception as e:
        print_error(f"Failed to get report status: {e}")
        sys.exit(1)


@reports.command("download")
@click.argument("report_id")
@click.option("--output", "-o", type=click.Path(), help="Output file path (default: auto-generated)")
@click.pass_context
def download_report(ctx, report_id, output):
    """Download a completed report.

    Examples:
        scambus reports download abc123-uuid

        scambus reports download abc123-uuid -o my_report.pdf
    """
    client = ctx.obj.get_client()

    try:
        # First check status
        report = client.get_report_status(report_id)

        if not report.is_completed:
            if report.is_processing:
                print_error("Report is still being generated. Please wait or use --wait flag when generating.")
            elif report.is_failed:
                print_error(f"Report generation failed: {report.error_message}")
            else:
                print_error(f"Report is not ready: {report.status}")
            sys.exit(1)

        _download_and_save(client, report, output)

    except Exception as e:
        print_error(f"Failed to download report: {e}")
        sys.exit(1)


# Helper functions

def _wait_and_download(client, report, output_path, timeout):
    """Wait for report completion and download."""
    print_info("Waiting for report generation to complete...")

    start_time = time.time()
    spinner_chars = [".", "..", "...", ""]
    spinner_idx = 0

    while report.is_processing:
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            print_error(f"\nReport generation timed out after {timeout} seconds")
            print_info(f"Report ID: {report.id}")
            print_info(f"Check status with: scambus reports status {report.id}")
            sys.exit(1)

        # Show progress
        click.echo(f"\r  Processing{spinner_chars[spinner_idx]}    ", nl=False)
        spinner_idx = (spinner_idx + 1) % len(spinner_chars)

        time.sleep(2)
        report = client.get_report_status(report.id)

    click.echo("\r" + " " * 20 + "\r", nl=False)  # Clear spinner line

    if report.is_completed:
        _download_and_save(client, report, output_path)
    elif report.is_failed:
        print_error(f"Report generation failed: {report.error_message}")
        sys.exit(1)


def _download_and_save(client, report, output_path):
    """Download report and save to file."""
    if not output_path:
        # Generate default filename
        date_str = report.generated_at.strftime("%Y%m%d") if report.generated_at else "report"
        type_str = "identifiers" if report.report_type == "identifier" else "journal"
        output_path = f"scambus_{type_str}_{date_str}_{report.id[:8]}.pdf"

    print_info(f"Downloading report to: {output_path}")
    client.download_report(report.id, output_path)

    print_success(f"Report saved to: {output_path}")

    # Show report details
    details = {
        "Report ID": report.id,
    }
    if report.identifier_count:
        details["Identifiers"] = report.identifier_count
    if report.journal_entry_count:
        details["Journal Entries"] = report.journal_entry_count
    if report.expires_at:
        details["Expires At"] = report.expires_at.isoformat()

    print_detail(details, title="Report Details")

    print_info("\nThe PDF contains a digital signature for authenticity verification.")
