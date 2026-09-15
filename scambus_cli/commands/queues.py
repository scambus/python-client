"""Queue commands for human and bot operators."""

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
def queues():
    """Manage and consume work queues."""
    pass


def _dt(value):
    return value.isoformat() if value else None


def _queue_to_dict(queue):
    return {
        "id": queue.id,
        "name": queue.name,
        "description": queue.description,
        "priority_mode": queue.priority_mode,
        "auto_populate": queue.auto_populate,
        "actor_cluster_id": queue.actor_cluster_id,
        "redis_stream_key": queue.redis_stream_key,
        "stream_version": queue.stream_version,
        "is_active": queue.is_active,
        "created_at": _dt(queue.created_at),
        "updated_at": _dt(queue.updated_at),
    }


def _item_to_dict(item):
    return {
        "id": item.id,
        "queue_id": item.queue_id,
        "cluster_id": item.cluster_id,
        "representative_id": item.representative_id,
        "representative_value": item.representative_value,
        "representative_type": item.representative_type,
        "state": item.state,
        "priority": item.priority,
        "contact_count": item.contact_count,
        "claimed_by": item.claimed_by,
        "claimed_at": _dt(item.claimed_at),
        "last_contacted_at": _dt(item.last_contacted_at),
        "next_contact_after": _dt(item.next_contact_after),
        "actor_cluster_id": item.actor_cluster_id,
        "funnel_entry_id": item.funnel_entry_id,
        "created_at": _dt(item.created_at),
        "updated_at": _dt(item.updated_at),
    }


def _event_to_dict(event):
    return {
        "id": event.id,
        "queue_item_id": event.queue_item_id,
        "queue_id": event.queue_id,
        "previous_queue_id": event.previous_queue_id,
        "target_queue_id": event.target_queue_id,
        "event": event.event,
        "state": event.state,
        "stream_version": event.stream_version,
        "metadata": event.metadata,
        "occurred_at": _dt(event.occurred_at),
        "queue_name": event.queue_name,
        "previous_queue_name": event.previous_queue_name,
        "target_queue_name": event.target_queue_name,
    }


def _stream_message_to_dict(message):
    return {
        "cursor": message.cursor,
        "event": message.event,
        "queue_id": message.queue_id,
        "previous_queue_id": message.previous_queue_id,
        "target_queue_id": message.target_queue_id,
        "queue_item_id": message.queue_item_id,
        "cluster_id": message.cluster_id,
        "representative_id": message.representative_id,
        "representative_type": message.representative_type,
        "representative_value": message.representative_value,
        "state": message.state,
        "priority": message.priority,
        "contact_count": message.contact_count,
        "stream_version": message.stream_version,
        "occurred_at": _dt(message.occurred_at),
        "metadata": message.metadata,
    }


@queues.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_queues(ctx, output_json):
    """List queues."""
    client = ctx.obj.get_client()
    try:
        queue_list = client.list_queues()
        if not queue_list:
            print_info("No queues found")
            return
        if output_json:
            print_json([_queue_to_dict(q) for q in queue_list])
        else:
            print_table(
                [
                    {
                        "ID": q.id[:8],
                        "Name": q.name,
                        "Mode": q.priority_mode,
                        "Active": "Yes" if q.is_active else "No",
                        "Stream": q.redis_stream_key or "N/A",
                    }
                    for q in queue_list
                ],
                title=f"Queues ({len(queue_list)})",
            )
    except Exception as e:
        print_error(f"Failed to list queues: {e}")
        sys.exit(1)


@queues.command()
@click.argument("queue_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def get(ctx, queue_id, output_json):
    """Get queue details."""
    client = ctx.obj.get_client()
    try:
        queue = client.get_queue(queue_id)
        data = _queue_to_dict(queue)
        if output_json:
            print_json(data)
        else:
            print_detail(data, title="Queue Details")
    except Exception as e:
        print_error(f"Failed to get queue: {e}")
        sys.exit(1)


@queues.command()
@click.option("--name", required=True, help="Queue name")
@click.option("--description", help="Queue description")
@click.option("--filter-json", help="Filter criteria JSON")
@click.option("--cadence-days", type=int, help="Cadence in days")
@click.option("--cooldown-hours", type=int, help="Cooldown in hours")
@click.option("--max-contacts-per-cluster", type=int, help="Maximum contacts per cluster")
@click.option("--rotation-enabled/--rotation-disabled", default=None, help="Set actor rotation")
@click.option(
    "--priority-mode",
    type=click.Choice(["fifo", "oldest_contact", "highest_confidence"]),
    help="Queue priority mode",
)
@click.option("--auto-populate/--manual", default=None, help="Set automatic population")
@click.option("--actor-cluster-id", help="Actor cluster ID")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def create(
    ctx,
    name,
    description,
    filter_json,
    cadence_days,
    cooldown_hours,
    max_contacts_per_cluster,
    rotation_enabled,
    priority_mode,
    auto_populate,
    actor_cluster_id,
    output_json,
):
    """Create a queue."""
    client = ctx.obj.get_client()
    try:
        filter_criteria = json.loads(filter_json) if filter_json else None
        queue = client.create_queue(
            name=name,
            description=description,
            filter_criteria=filter_criteria,
            cadence_days=cadence_days,
            cooldown_hours=cooldown_hours,
            max_contacts_per_cluster=max_contacts_per_cluster,
            rotation_enabled=rotation_enabled,
            priority_mode=priority_mode,
            auto_populate=auto_populate,
            actor_cluster_id=actor_cluster_id,
        )
        data = _queue_to_dict(queue)
        if output_json:
            print_json(data)
        else:
            print_success(f"Queue created: {queue.id}")
            print_detail(data, title="Created Queue")
    except json.JSONDecodeError as e:
        print_error(f"Invalid --filter-json: {e}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Failed to create queue: {e}")
        sys.exit(1)


@queues.command()
@click.argument("queue_id")
@click.option("--name", help="Queue name")
@click.option("--description", help="Queue description")
@click.option("--filter-json", help="Filter criteria JSON")
@click.option("--cadence-days", type=int, help="Cadence in days")
@click.option("--cooldown-hours", type=int, help="Cooldown in hours")
@click.option("--max-contacts-per-cluster", type=int, help="Maximum contacts per cluster")
@click.option("--rotation-enabled/--rotation-disabled", default=None, help="Set actor rotation")
@click.option(
    "--priority-mode",
    type=click.Choice(["fifo", "oldest_contact", "highest_confidence"]),
    help="Queue priority mode",
)
@click.option("--auto-populate/--manual", default=None, help="Set automatic population")
@click.option("--actor-cluster-id", help="Actor cluster ID")
@click.option("--active/--inactive", default=None, help="Set active state")
@click.pass_context
def update(
    ctx,
    queue_id,
    name,
    description,
    filter_json,
    cadence_days,
    cooldown_hours,
    max_contacts_per_cluster,
    rotation_enabled,
    priority_mode,
    auto_populate,
    actor_cluster_id,
    active,
):
    """Update a queue."""
    client = ctx.obj.get_client()
    try:
        updates = {}
        for key, value in {
            "name": name,
            "description": description,
            "cadence_days": cadence_days,
            "cooldown_hours": cooldown_hours,
            "max_contacts_per_cluster": max_contacts_per_cluster,
            "rotation_enabled": rotation_enabled,
            "priority_mode": priority_mode,
            "auto_populate": auto_populate,
            "actor_cluster_id": actor_cluster_id,
            "is_active": active,
        }.items():
            if value is not None:
                updates[key] = value
        if filter_json:
            updates["filter_criteria"] = json.loads(filter_json)
        if not updates:
            print_error("No updates specified")
            sys.exit(1)
        queue = client.update_queue(queue_id, **updates)
        print_success(f"Queue updated: {queue.id}")
    except json.JSONDecodeError as e:
        print_error(f"Invalid --filter-json: {e}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Failed to update queue: {e}")
        sys.exit(1)


@queues.command()
@click.argument("queue_id")
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.pass_context
def delete(ctx, queue_id, yes):
    """Delete a queue."""
    client = ctx.obj.get_client()
    try:
        if not yes and not click.confirm(f"Delete queue {queue_id}?"):
            return
        client.delete_queue(queue_id)
        print_success(f"Queue deleted: {queue_id}")
    except Exception as e:
        print_error(f"Failed to delete queue: {e}")
        sys.exit(1)


@queues.command()
@click.argument("queue_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def stats(ctx, queue_id, output_json):
    """Show queue state counts."""
    client = ctx.obj.get_client()
    try:
        result = client.get_queue_stats(queue_id)
        data = result.__dict__
        if output_json:
            print_json(data)
        else:
            print_detail(data, title="Queue Stats")
    except Exception as e:
        print_error(f"Failed to get queue stats: {e}")
        sys.exit(1)


@queues.command()
@click.argument("queue_id")
@click.option("--state", help="Filter by state")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def items(ctx, queue_id, state, output_json):
    """List queue items."""
    client = ctx.obj.get_client()
    try:
        item_list = client.list_queue_items(queue_id, state=state)
        if not item_list:
            print_info("No queue items found")
            return
        if output_json:
            print_json([_item_to_dict(i) for i in item_list])
        else:
            print_table(
                [
                    {
                        "ID": i.id[:8],
                        "State": i.state,
                        "Priority": i.priority,
                        "Representative": i.representative_value or i.representative_id[:8],
                        "Contacts": i.contact_count,
                    }
                    for i in item_list
                ],
                title=f"Queue Items ({len(item_list)})",
            )
    except Exception as e:
        print_error(f"Failed to list queue items: {e}")
        sys.exit(1)


@queues.command()
@click.argument("queue_id")
@click.option("--cursor", default="0", help="Redis stream cursor")
@click.option("--limit", type=int, help="Maximum messages")
@click.option("--block-ms", type=int, help="Block duration in milliseconds")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def stream(ctx, queue_id, cursor, limit, block_ms, output_json):
    """Read queue Redis stream messages."""
    client = ctx.obj.get_client()
    try:
        result = client.read_queue_stream(queue_id, cursor=cursor, limit=limit, block_ms=block_ms)
        data = {
            "stream_key": result.stream_key,
            "cursor": result.cursor,
            "claim_endpoint": result.claim_endpoint,
            "source_of_truth": result.source_of_truth,
            "messages": [_stream_message_to_dict(m) for m in result.messages],
        }
        if output_json:
            print_json(data)
        elif not result.messages:
            print_info(f"No messages; cursor={result.cursor}")
        else:
            print_table(
                [
                    {
                        "Cursor": m.cursor,
                        "Event": m.event,
                        "Item": m.queue_item_id[:8],
                        "State": m.state,
                        "Priority": m.priority,
                    }
                    for m in result.messages
                ],
                title=f"Queue Stream ({len(result.messages)})",
            )
            print_info(f"Next cursor: {result.cursor}")
    except Exception as e:
        print_error(f"Failed to read queue stream: {e}")
        sys.exit(1)


@queues.command()
@click.argument("queue_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def claim(ctx, queue_id, output_json):
    """Claim the next queue item."""
    client = ctx.obj.get_client()
    try:
        item = client.claim_queue_item(queue_id)
        if item is None:
            print_info("No items available to claim")
            return
        data = _item_to_dict(item)
        if output_json:
            print_json(data)
        else:
            print_detail(data, title="Claimed Queue Item")
    except Exception as e:
        print_error(f"Failed to claim queue item: {e}")
        sys.exit(1)


@queues.command()
@click.argument("queue_id")
@click.argument("item_id")
@click.pass_context
def release(ctx, queue_id, item_id):
    """Release a claimed queue item."""
    client = ctx.obj.get_client()
    try:
        result = client.release_queue_item(queue_id, item_id)
        print_success(f"Item released: {result.get('state')}")
    except Exception as e:
        print_error(f"Failed to release queue item: {e}")
        sys.exit(1)


@queues.command()
@click.argument("queue_id")
@click.argument("item_id")
@click.option("--contact-identifier-id", help="Contact identifier ID")
@click.option("--journal-entry-id", help="Journal entry ID")
@click.option("--notes", help="Contact notes")
@click.pass_context
def contact(ctx, queue_id, item_id, contact_identifier_id, journal_entry_id, notes):
    """Record contact for a claimed queue item."""
    client = ctx.obj.get_client()
    try:
        result = client.record_queue_contact(
            queue_id,
            item_id,
            contact_identifier_id=contact_identifier_id,
            journal_entry_id=journal_entry_id,
            notes=notes,
        )
        print_success(f"Contact recorded: {result.get('state')}")
    except Exception as e:
        print_error(f"Failed to record queue contact: {e}")
        sys.exit(1)


@queues.command()
@click.argument("queue_id")
@click.argument("item_id")
@click.option("--reason", help="Reason")
@click.option("--outcome", help="Outcome")
@click.option("--note", help="Note")
@click.pass_context
def complete(ctx, queue_id, item_id, reason, outcome, note):
    """Complete a queue item."""
    client = ctx.obj.get_client()
    try:
        result = client.complete_queue_item(
            queue_id, item_id, reason=reason, outcome=outcome, note=note
        )
        print_success(f"Item completed: {result.get('state')}")
    except Exception as e:
        print_error(f"Failed to complete queue item: {e}")
        sys.exit(1)


@queues.command()
@click.argument("queue_id")
@click.argument("item_id")
@click.option("--reason", help="Reason")
@click.option("--outcome", help="Outcome")
@click.option("--note", help="Note")
@click.pass_context
def drop(ctx, queue_id, item_id, reason, outcome, note):
    """Drop a queue item from active work."""
    client = ctx.obj.get_client()
    try:
        result = client.drop_queue_item(
            queue_id, item_id, reason=reason, outcome=outcome, note=note
        )
        print_success(f"Item dropped: {result.get('state')}")
    except Exception as e:
        print_error(f"Failed to drop queue item: {e}")
        sys.exit(1)


@queues.command()
@click.argument("queue_id")
@click.argument("item_id")
@click.option("--target-queue-id", required=True, help="Target queue ID")
@click.option("--reason", help="Reason")
@click.option("--outcome", help="Outcome")
@click.option("--note", help="Note")
@click.pass_context
def move(ctx, queue_id, item_id, target_queue_id, reason, outcome, note):
    """Move a queue item to another queue."""
    client = ctx.obj.get_client()
    try:
        result = client.move_queue_item(
            queue_id,
            item_id,
            target_queue_id,
            reason=reason,
            outcome=outcome,
            note=note,
        )
        print_success(f"Item moved to queue: {result.get('queue_id')}")
    except Exception as e:
        print_error(f"Failed to move queue item: {e}")
        sys.exit(1)


@queues.command()
@click.argument("queue_id")
@click.argument("item_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def events(ctx, queue_id, item_id, output_json):
    """Show queue item lifecycle events."""
    client = ctx.obj.get_client()
    try:
        event_list = client.get_queue_item_events(queue_id, item_id)
        if output_json:
            print_json([_event_to_dict(e) for e in event_list])
        elif not event_list:
            print_info("No queue item events found")
        else:
            print_table(
                [
                    {
                        "Event": e.event,
                        "State": e.state,
                        "Version": e.stream_version,
                        "At": _dt(e.occurred_at) or "N/A",
                    }
                    for e in event_list
                ],
                title=f"Queue Events ({len(event_list)})",
            )
    except Exception as e:
        print_error(f"Failed to get queue events: {e}")
        sys.exit(1)


@queues.command()
@click.argument("queue_id")
@click.argument("item_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def history(ctx, queue_id, item_id, output_json):
    """Show queue item contact history."""
    client = ctx.obj.get_client()
    try:
        logs = client.get_queue_item_history(queue_id, item_id)
        data = [
            {
                "id": log.id,
                "contacted_by": log.contacted_by,
                "contact_identifier_id": log.contact_identifier_id,
                "journal_entry_id": log.journal_entry_id,
                "outcome": log.outcome,
                "contacted_at": _dt(log.contacted_at),
                "notes": log.notes,
            }
            for log in logs
        ]
        if output_json:
            print_json(data)
        elif not logs:
            print_info("No contact history found")
        else:
            print_table(data, title=f"Queue Contact History ({len(logs)})")
    except Exception as e:
        print_error(f"Failed to get queue history: {e}")
        sys.exit(1)


@queues.command()
@click.argument("queue_id")
@click.argument("item_id")
@click.option(
    "--role", type=click.Choice(["target", "actor"]), default="target", help="Cluster role"
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def cluster(ctx, queue_id, item_id, role, output_json):
    """Show identifiers in a queue item's target or actor cluster."""
    client = ctx.obj.get_client()
    try:
        identifiers = client.get_queue_item_cluster_identifiers(queue_id, item_id, role=role)
        data = [identifier.__dict__ for identifier in identifiers]
        if output_json:
            print_json(data)
        elif not identifiers:
            print_info("No identifiers found")
        else:
            print_table(
                [
                    {
                        "ID": ident.id[:8],
                        "Type": ident.type,
                        "Value": ident.value,
                        "Ours": "Yes" if ident.is_ours else "No",
                        "Confidence": ident.confidence if ident.confidence is not None else "N/A",
                    }
                    for ident in identifiers
                ],
                title=f"Queue Cluster Identifiers ({role})",
            )
    except Exception as e:
        print_error(f"Failed to get queue cluster identifiers: {e}")
        sys.exit(1)
