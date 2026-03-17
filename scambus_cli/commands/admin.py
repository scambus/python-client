"""Admin commands for special domain rules and URL consolidation."""

import sys
import time

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


@click.group()
def admin():
    """Admin operations (requires system admin permission)."""
    pass


# ── Special Domain Rules ──────────────────────────────────────────────


@admin.group("domain-rules")
def domain_rules():
    """Manage special domain rules for URL consolidation."""
    pass


@domain_rules.command("list")
@click.option(
    "--category",
    type=click.Choice(["shortener", "pastebin", "archive", "cloud_storage", "custom"]),
    help="Filter by category",
)
@click.option("--active/--inactive", default=None, help="Filter by active status")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_rules(ctx, category, active, output_json):
    """List special domain rules.

    Examples:
        scambus admin domain-rules list
        scambus admin domain-rules list --category shortener
        scambus admin domain-rules list --active
    """
    client = ctx.obj.get_client()

    try:
        rules = client.list_special_domain_rules(category=category, active=active)

        if not rules:
            print_info("No rules found")
            return

        if output_json:
            print_json([
                {
                    "id": r.id,
                    "domain": r.domain,
                    "category": r.category,
                    "path_depth": r.path_depth,
                    "strip_query": r.strip_query,
                    "strip_fragment": r.strip_fragment,
                    "is_active": r.is_active,
                    "is_default": r.is_default,
                }
                for r in rules
            ])
        else:
            table_data = [
                {
                    "Domain": r.domain,
                    "Category": r.category,
                    "Depth": str(r.path_depth),
                    "StripQ": "Yes" if r.strip_query else "No",
                    "StripF": "Yes" if r.strip_fragment else "No",
                    "Active": "Yes" if r.is_active else "No",
                    "Default": "Yes" if r.is_default else "No",
                }
                for r in rules
            ]
            print_table(table_data, title=f"Special Domain Rules ({len(rules)})")

    except Exception as e:
        print_error(f"Failed to list rules: {e}")
        sys.exit(1)


@domain_rules.command("create")
@click.option("--domain", required=True, help="Domain name (e.g. bit.ly)")
@click.option(
    "--category",
    required=True,
    type=click.Choice(["shortener", "pastebin", "archive", "cloud_storage", "custom"]),
    help="Rule category",
)
@click.option("--path-depth", type=int, default=1, help="Path segments to preserve (0-10)")
@click.option("--no-strip-query", is_flag=True, help="Keep query parameters")
@click.option("--no-strip-fragment", is_flag=True, help="Keep fragment")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def create_rule(ctx, domain, category, path_depth, no_strip_query, no_strip_fragment, output_json):
    """Create a new special domain rule.

    Examples:
        scambus admin domain-rules create --domain t.co --category shortener
        scambus admin domain-rules create --domain pastebin.com --category pastebin --path-depth 1
    """
    client = ctx.obj.get_client()

    try:
        rule = client.create_special_domain_rule(
            domain=domain,
            category=category,
            path_depth=path_depth,
            strip_query=not no_strip_query,
            strip_fragment=not no_strip_fragment,
        )

        if output_json:
            print_json({
                "id": rule.id,
                "domain": rule.domain,
                "category": rule.category,
                "path_depth": rule.path_depth,
                "is_active": rule.is_active,
            })
        else:
            print_success(f"Rule created for: {rule.domain}")
            print_detail({
                "ID": rule.id,
                "Domain": rule.domain,
                "Category": rule.category,
                "Path Depth": str(rule.path_depth),
                "Strip Query": "Yes" if rule.strip_query else "No",
                "Strip Fragment": "Yes" if rule.strip_fragment else "No",
            }, title="Created Rule")

    except Exception as e:
        print_error(f"Failed to create rule: {e}")
        sys.exit(1)


@domain_rules.command("update")
@click.argument("rule_id")
@click.option("--domain", help="New domain name")
@click.option(
    "--category",
    type=click.Choice(["shortener", "pastebin", "archive", "cloud_storage", "custom"]),
    help="New category",
)
@click.option("--path-depth", type=int, help="New path depth (0-10)")
@click.option("--strip-query/--no-strip-query", default=None, help="Strip query parameters")
@click.option("--strip-fragment/--no-strip-fragment", default=None, help="Strip fragment")
@click.option("--active/--inactive", "is_active", default=None, help="Active status")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def update_rule(ctx, rule_id, domain, category, path_depth, strip_query, strip_fragment, is_active, output_json):
    """Update a special domain rule.

    Examples:
        scambus admin domain-rules update abc-123 --inactive
        scambus admin domain-rules update abc-123 --path-depth 2
    """
    client = ctx.obj.get_client()

    try:
        rule = client.update_special_domain_rule(
            rule_id=rule_id,
            domain=domain,
            category=category,
            path_depth=path_depth,
            strip_query=strip_query,
            strip_fragment=strip_fragment,
            is_active=is_active,
        )

        if output_json:
            print_json({
                "id": rule.id,
                "domain": rule.domain,
                "category": rule.category,
                "is_active": rule.is_active,
            })
        else:
            print_success(f"Rule updated: {rule.domain}")

    except Exception as e:
        print_error(f"Failed to update rule: {e}")
        sys.exit(1)


@domain_rules.command("delete")
@click.argument("rule_id")
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.pass_context
def delete_rule(ctx, rule_id, yes):
    """Delete a special domain rule (default rules cannot be deleted).

    Examples:
        scambus admin domain-rules delete abc-123
        scambus admin domain-rules delete abc-123 --yes
    """
    if not yes:
        click.confirm(f"Are you sure you want to delete rule {rule_id}?", abort=True)

    client = ctx.obj.get_client()

    try:
        client.delete_special_domain_rule(rule_id)
        print_success(f"Rule deleted: {rule_id}")

    except Exception as e:
        print_error(f"Failed to delete rule: {e}")
        sys.exit(1)


# ── URL Consolidation ─────────────────────────────────────────────────


@admin.group("url-consolidation")
def url_consolidation():
    """Manage URL identifier consolidation."""
    pass


@url_consolidation.command("start")
@click.option("--wait", is_flag=True, help="Wait for consolidation to complete")
@click.option("--poll-interval", type=float, default=5.0, help="Polling interval in seconds (with --wait)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def start_consolidation(ctx, wait, poll_interval, output_json):
    """Start URL consolidation background job.

    Examples:
        scambus admin url-consolidation start
        scambus admin url-consolidation start --wait
    """
    client = ctx.obj.get_client()

    try:
        status = client.start_url_consolidation()

        if not wait:
            if output_json:
                print_json({
                    "status": status.status,
                    "total_groups": status.total_groups,
                })
            else:
                print_success(f"Consolidation started (status: {status.status})")
                if status.total_groups:
                    print_info(f"Total groups to process: {status.total_groups}")
                print_info("Use 'scambus admin url-consolidation status' to check progress")
            return

        # Wait mode: poll until done
        print_info("Waiting for consolidation to complete...")
        while status.is_running:
            if status.total_groups and status.processed_groups is not None:
                pct = (status.processed_groups / status.total_groups * 100) if status.total_groups > 0 else 0
                print_info(
                    f"Progress: {status.processed_groups}/{status.total_groups} "
                    f"({pct:.0f}%) - merged: {status.merged}, skipped: {status.skipped}"
                )
            time.sleep(poll_interval)
            status = client.get_url_consolidation_status()

        if output_json:
            print_json({
                "status": status.status,
                "total_groups": status.total_groups,
                "processed_groups": status.processed_groups,
                "merged": status.merged,
                "skipped": status.skipped,
                "errors": status.errors,
            })
        elif status.is_completed:
            print_success("Consolidation completed")
            print_detail({
                "Groups": str(status.total_groups or 0),
                "Processed": str(status.processed_groups or 0),
                "Merged": str(status.merged or 0),
                "Skipped": str(status.skipped or 0),
                "Errors": str(status.errors or 0),
            }, title="Results")
        elif status.is_failed:
            print_error(f"Consolidation failed: {status.last_error}")
        else:
            print_warning(f"Consolidation ended with status: {status.status}")

    except Exception as e:
        print_error(f"Failed to start consolidation: {e}")
        sys.exit(1)


@url_consolidation.command("status")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def consolidation_status(ctx, output_json):
    """Check URL consolidation job status.

    Examples:
        scambus admin url-consolidation status
    """
    client = ctx.obj.get_client()

    try:
        status = client.get_url_consolidation_status()

        if output_json:
            print_json({
                "status": status.status,
                "started_at": status.started_at,
                "completed_at": status.completed_at,
                "total_groups": status.total_groups,
                "processed_groups": status.processed_groups,
                "merged": status.merged,
                "skipped": status.skipped,
                "errors": status.errors,
                "last_error": status.last_error,
            })
        else:
            details = {"Status": status.status}
            if status.started_at:
                details["Started"] = status.started_at
            if status.completed_at:
                details["Completed"] = status.completed_at
            if status.status != "idle":
                details["Total Groups"] = str(status.total_groups)
                details["Processed"] = str(status.processed_groups)
                details["Merged"] = str(status.merged)
                details["Skipped"] = str(status.skipped)
                if status.errors > 0:
                    details["Errors"] = str(status.errors)
            if status.last_error:
                details["Last Error"] = status.last_error
            print_detail(details, title="URL Consolidation Status")

    except Exception as e:
        print_error(f"Failed to get status: {e}")
        sys.exit(1)


@url_consolidation.command("cancel")
@click.pass_context
def cancel_consolidation(ctx):
    """Cancel a running URL consolidation job.

    Examples:
        scambus admin url-consolidation cancel
    """
    client = ctx.obj.get_client()

    try:
        result = client.cancel_url_consolidation()
        message = result.get("message", "Cancellation requested")
        print_success(message)

    except Exception as e:
        print_error(f"Failed to cancel consolidation: {e}")
        sys.exit(1)
