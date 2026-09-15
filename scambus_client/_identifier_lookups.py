"""Identifier lookup builders shared by the sync and async clients."""

import json
import re
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

_DELTACHAT_FINGERPRINT = re.compile(r"^[0-9A-F]{40}$")
_DELTACHAT_QR_SCHEME = "openpgp4fpr:"
_DELTACHAT_INVITE_HOST = "i.delta.chat"


def normalize_deltachat_fingerprint(value: str) -> str:
    """Return the bare uppercase OpenPGP fingerprint from a fingerprint, an
    ``https://i.delta.chat/#...`` invite link or an ``OPENPGP4FPR:`` QR payload."""
    rest = value.strip()
    if rest.lower().startswith(_DELTACHAT_QR_SCHEME):
        rest = rest[len(_DELTACHAT_QR_SCHEME) :]
    else:
        parsed = urlparse(rest if "://" in rest else "https://" + rest)
        if (parsed.hostname or "").lower() == _DELTACHAT_INVITE_HOST:
            rest = unquote(parsed.fragment)
    rest = re.split(r"[&#]", rest, maxsplit=1)[0]
    bare = re.sub(r"[\s:-]", "", rest).upper()
    if not _DELTACHAT_FINGERPRINT.match(bare):
        raise ValueError("Delta Chat fingerprint must be 40 hexadecimal characters")
    return bare


def deltachat_lookup(
    fingerprint: str,
    display_name: Optional[str] = None,
    confidence: Optional[float] = None,
) -> Dict[str, Any]:
    """Build a ``social_media`` identifier lookup for a Delta Chat account."""
    data: Dict[str, Any] = {
        "platform": "deltachat",
        "handle": normalize_deltachat_fingerprint(fingerprint),
    }
    if display_name:
        data["displayName"] = display_name

    result: Dict[str, Any] = {"type": "social_media", "value": json.dumps(data)}
    if confidence is not None:
        result["confidence"] = confidence
    return result
