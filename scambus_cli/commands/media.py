"""Media upload commands."""

import sys
from pathlib import Path

import click

from scambus_cli.utils import print_detail, print_error, print_json, print_success


@click.group()
def media():
    """Manage media uploads."""
    pass


@media.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--notes", help="Notes about the media file")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def upload(ctx, file_path, notes, output_json):
    """Upload a media file.

    Examples:
        scambus media upload screenshot.png --notes "Phishing site screenshot"
        scambus media upload recording.mp3 --notes "Scam call recording"
    """
    client = ctx.obj.get_client()

    try:
        file_path = Path(file_path)
        media = client.upload_media(file_path, notes=notes)

        if output_json:
            print_json(
                {
                    "id": media.id,
                    "file_name": media.file_name,
                    "type": media.type,
                    "mime_type": media.mime_type,
                    "file_size": media.file_size,
                    "notes": media.notes,
                }
            )
        else:
            print_success(f"Media uploaded: {media.id}")
            print_detail(
                {
                    "ID": media.id,
                    "Filename": media.file_name,
                    "Type": media.type,
                    "MIME Type": media.mime_type,
                    "Size": f"{media.file_size} bytes",
                    "Notes": media.notes or "N/A",
                },
                title="Uploaded Media",
            )

    except Exception as e:
        print_error(f"Failed to upload media: {e}")
        sys.exit(1)
