"""Persona management commands."""

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


def _persona_to_json(persona):
    """Convert a Persona model to a JSON-serializable dict."""
    return {
        "id": persona.id,
        "name": persona.name,
        "description": persona.description,
        "personality": persona.personality,
        "background": persona.background,
        "address_line1": persona.address_line1,
        "address_line2": persona.address_line2,
        "address_city": persona.address_city,
        "address_state": persona.address_state,
        "address_postal_code": persona.address_postal_code,
        "address_country": persona.address_country,
        "is_active": persona.is_active,
        "is_test": persona.is_test,
        "created_at": persona.created_at.isoformat() if persona.created_at else None,
        "updated_at": persona.updated_at.isoformat() if persona.updated_at else None,
        "identifiers": [
            {
                "persona_id": i.persona_id,
                "identifier_id": i.identifier_id,
                "annotation": i.annotation,
                "identifier_value": i.identifier_value,
                "identifier_type": i.identifier_type,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in persona.identifiers
        ],
        "media": [
            {
                "persona_id": m.persona_id,
                "media_id": m.media_id,
                "category": m.category,
                "notes": m.notes,
                "file_name": m.file_name,
                "mime_type": m.mime_type,
                "file_size": m.file_size,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in persona.media
        ],
    }


@click.group()
def personas():
    """Manage personas."""
    pass


@personas.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_personas(ctx, output_json):
    """List all personas.

    Examples:
        scambus personas list
        scambus personas list --json
    """
    client = ctx.obj.get_client()

    try:
        result = client.list_personas()

        if not result:
            print_info("No personas found")
            return

        if output_json:
            print_json([_persona_to_json(p) for p in result])
        else:
            table_data = [
                {
                    "ID": p.id[:8],
                    "Name": p.name or "N/A",
                    "Active": "Yes" if p.is_active else "No",
                    "Description": (p.description or "")[:50],
                    "Created": p.created_at.strftime("%Y-%m-%d") if p.created_at else "N/A",
                }
                for p in result
            ]

            print_table(table_data, title=f"Personas ({len(result)})")

    except Exception as e:
        print_error(f"Failed to list personas: {e}")
        sys.exit(1)


@personas.command()
@click.argument("persona_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def get(ctx, persona_id, output_json):
    """Get persona details.

    Examples:
        scambus personas get <persona-id>
        scambus personas get <persona-id> --json
    """
    client = ctx.obj.get_client()

    try:
        persona = client.get_persona(persona_id)

        if output_json:
            print_json(_persona_to_json(persona))
        else:
            details = {
                "ID": persona.id or "N/A",
                "Name": persona.name or "N/A",
                "Active": "Yes" if persona.is_active else "No",
                "Description": persona.description or "N/A",
                "Personality": persona.personality or "N/A",
                "Background": persona.background or "N/A",
                "Created": persona.created_at.isoformat() if persona.created_at else "N/A",
            }

            # Address fields
            addr_parts = []
            for val in [
                persona.address_line1,
                persona.address_line2,
                persona.address_city,
                persona.address_state,
                persona.address_postal_code,
                persona.address_country,
            ]:
                if val:
                    addr_parts.append(val)
            if addr_parts:
                details["Address"] = ", ".join(addr_parts)

            # Identifiers
            if persona.identifiers:
                ident_strs = []
                for ident in persona.identifiers:
                    ident_type = ident.identifier_type or "unknown"
                    ident_value = ident.identifier_value or "N/A"
                    annotation = ident.annotation or ""
                    s = f"{ident_type}: {ident_value}"
                    if annotation:
                        s += f" ({annotation})"
                    ident_strs.append(s)
                details["Identifiers"] = "\n    ".join(ident_strs)

            # Media
            if persona.media:
                media_strs = []
                for m in persona.media:
                    category = m.category or "other"
                    file_name = m.file_name or "N/A"
                    notes = m.notes or ""
                    s = f"[{category}] {file_name}"
                    if notes:
                        s += f" - {notes}"
                    media_strs.append(s)
                details["Media"] = "\n    ".join(media_strs)

            print_detail(details, title="Persona Details")

    except Exception as e:
        print_error(f"Failed to get persona: {e}")
        sys.exit(1)


@personas.command()
@click.option("--name", required=True, help="Persona name")
@click.option("--description", help="Persona description")
@click.option("--personality", help="Personality traits/style")
@click.option("--background", help="Background story")
@click.option("--address-line1", help="Street address line 1")
@click.option("--address-line2", help="Street address line 2")
@click.option("--address-city", help="City")
@click.option("--address-state", help="State or province")
@click.option("--address-postal-code", help="Postal/ZIP code")
@click.option("--address-country", help="Country")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def create(
    ctx,
    name,
    description,
    personality,
    background,
    address_line1,
    address_line2,
    address_city,
    address_state,
    address_postal_code,
    address_country,
    output_json,
):
    """Create a new persona.

    Examples:
        scambus personas create --name "John Smith"
        scambus personas create --name "Jane Doe" --description "Tech worker" --personality "Friendly"
        scambus personas create --name "Bob" --address-city "New York" --address-country "US"
    """
    client = ctx.obj.get_client()

    try:
        persona = client.create_persona(
            name=name,
            description=description or "",
            personality=personality or "",
            background=background or "",
            address_line1=address_line1 or "",
            address_line2=address_line2 or "",
            address_city=address_city or "",
            address_state=address_state or "",
            address_postal_code=address_postal_code or "",
            address_country=address_country or "",
        )

        if output_json:
            print_json(_persona_to_json(persona))
        else:
            print_success(f"Persona created: {persona.id}")
            print_detail(
                {
                    "ID": persona.id,
                    "Name": persona.name,
                    "Active": "Yes" if persona.is_active else "No",
                },
                title="Created Persona",
            )

    except Exception as e:
        print_error(f"Failed to create persona: {e}")
        sys.exit(1)


@personas.command()
@click.argument("persona_id")
@click.option("--name", help="New name")
@click.option("--description", help="New description")
@click.option("--personality", help="New personality")
@click.option("--background", help="New background")
@click.option("--active/--inactive", default=None, help="Set active status")
@click.option("--address-line1", help="Street address line 1")
@click.option("--address-line2", help="Street address line 2")
@click.option("--address-city", help="City")
@click.option("--address-state", help="State or province")
@click.option("--address-postal-code", help="Postal/ZIP code")
@click.option("--address-country", help="Country")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def update(
    ctx,
    persona_id,
    name,
    description,
    personality,
    background,
    active,
    address_line1,
    address_line2,
    address_city,
    address_state,
    address_postal_code,
    address_country,
    output_json,
):
    """Update a persona.

    Examples:
        scambus personas update <persona-id> --name "New Name"
        scambus personas update <persona-id> --inactive
        scambus personas update <persona-id> --description "Updated description" --personality "Reserved"
        scambus personas update <persona-id> --address-city "London" --address-country "UK"
    """
    client = ctx.obj.get_client()

    try:
        kwargs = {}
        if name is not None:
            kwargs["name"] = name
        if description is not None:
            kwargs["description"] = description
        if personality is not None:
            kwargs["personality"] = personality
        if background is not None:
            kwargs["background"] = background
        if active is not None:
            kwargs["is_active"] = active
        if address_line1 is not None:
            kwargs["address_line1"] = address_line1
        if address_line2 is not None:
            kwargs["address_line2"] = address_line2
        if address_city is not None:
            kwargs["address_city"] = address_city
        if address_state is not None:
            kwargs["address_state"] = address_state
        if address_postal_code is not None:
            kwargs["address_postal_code"] = address_postal_code
        if address_country is not None:
            kwargs["address_country"] = address_country

        if not kwargs:
            print_error("No updates specified")
            sys.exit(1)

        persona = client.update_persona(persona_id, **kwargs)

        if output_json:
            print_json(_persona_to_json(persona))
        else:
            print_success(f"Persona updated: {persona.id}")

    except Exception as e:
        print_error(f"Failed to update persona: {e}")
        sys.exit(1)


@personas.command()
@click.argument("persona_id")
@click.pass_context
def delete(ctx, persona_id):
    """Delete a persona.

    Examples:
        scambus personas delete <persona-id>
    """
    client = ctx.obj.get_client()

    try:
        client.delete_persona(persona_id)
        print_success(f"Persona deleted: {persona_id}")

    except Exception as e:
        print_error(f"Failed to delete persona: {e}")
        sys.exit(1)


@personas.command("add-media")
@click.argument("persona_id")
@click.argument("media_id")
@click.option(
    "--category",
    required=True,
    type=click.Choice(
        ["passport", "driving_license", "utility_bill", "selfie", "pet", "car", "house", "other"],
        case_sensitive=False,
    ),
    help="Media category",
)
@click.option("--notes", help="Notes about this media")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def add_media(ctx, persona_id, media_id, category, notes, output_json):
    """Link a media item to a persona.

    Examples:
        scambus personas add-media <persona-id> <media-id> --category selfie
        scambus personas add-media <persona-id> <media-id> --category passport --notes "Front page"
    """
    client = ctx.obj.get_client()

    try:
        link = client.add_persona_media(
            persona_id=persona_id,
            media_id=media_id,
            category=category,
            notes=notes or "",
        )

        if output_json:
            print_json(
                {
                    "persona_id": link.persona_id,
                    "media_id": link.media_id,
                    "category": link.category,
                    "notes": link.notes,
                    "created_at": link.created_at.isoformat() if link.created_at else None,
                }
            )
        else:
            print_success(f"Media {media_id[:8]} linked to persona {persona_id[:8]}")

    except Exception as e:
        print_error(f"Failed to add media to persona: {e}")
        sys.exit(1)


@personas.command("update-media")
@click.argument("persona_id")
@click.argument("media_id")
@click.option(
    "--category",
    type=click.Choice(
        ["passport", "driving_license", "utility_bill", "selfie", "pet", "car", "house", "other"],
        case_sensitive=False,
    ),
    help="New media category",
)
@click.option("--notes", help="New notes about this media")
@click.pass_context
def update_media(ctx, persona_id, media_id, category, notes):
    """Update category or notes on a persona-media link.

    Examples:
        scambus personas update-media <persona-id> <media-id> --category passport
        scambus personas update-media <persona-id> <media-id> --notes "Updated scan"
    """
    client = ctx.obj.get_client()

    if category is None and notes is None:
        print_error("No updates specified. Use --category and/or --notes.")
        sys.exit(1)

    try:
        client.update_persona_media(
            persona_id=persona_id,
            media_id=media_id,
            category=category,
            notes=notes,
        )
        print_success(f"Media {media_id[:8]} updated on persona {persona_id[:8]}")

    except Exception as e:
        print_error(f"Failed to update persona media: {e}")
        sys.exit(1)


@personas.command("remove-media")
@click.argument("persona_id")
@click.argument("media_id")
@click.pass_context
def remove_media(ctx, persona_id, media_id):
    """Unlink a media item from a persona.

    Examples:
        scambus personas remove-media <persona-id> <media-id>
    """
    client = ctx.obj.get_client()

    try:
        client.remove_persona_media(persona_id, media_id)
        print_success(f"Media {media_id[:8]} removed from persona {persona_id[:8]}")

    except Exception as e:
        print_error(f"Failed to remove media from persona: {e}")
        sys.exit(1)
