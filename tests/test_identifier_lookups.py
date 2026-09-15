"""Unit tests for the shared identifier lookup builders."""

import json

import pytest

from scambus_client import AsyncScambusClient
from scambus_client._identifier_lookups import (
    deltachat_lookup,
    normalize_deltachat_fingerprint,
)

FPR = "8D2A4F1C0B3E5A7D9C1F2E3B4A5C6D7E8F9A0B1C"
GROUPED = "8D2A 4F1C 0B3E 5A7D 9C1F 2E3B 4A5C 6D7E 8F9A 0B1C"
INVITE = (
    "https://i.delta.chat/#8d2a4f1c0b3e5a7d9c1f2e3b4a5c6d7e8f9a0b1c"
    "&a=scammer%40nine.testrun.org&n=Support&i=AbCdEf&s=GhIjKl"
)


class TestNormalizeDeltaChatFingerprint:
    @pytest.mark.parametrize(
        "value",
        [
            FPR,
            FPR.lower(),
            GROUPED,
            "8D2A:4F1C:0B3E:5A7D:9C1F:2E3B:4A5C:6D7E:8F9A:0B1C",
            INVITE,
            "i.delta.chat/#" + FPR + "&a=scammer%40nine.testrun.org",
            f"OPENPGP4FPR:{FPR}#a=scammer%40nine.testrun.org&n=Support&i=AbCdEf&s=GhIjKl",
        ],
    )
    def test_accepts_every_form(self, value):
        assert normalize_deltachat_fingerprint(value) == FPR

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "8D2A4F1C",
            FPR + "AB",
            "G" + FPR[1:],
            "@" + FPR,
            "scammer@nine.testrun.org",
            "https://i.delta.chat/",
            "https://i.delta.chat/#not-a-fingerprint&a=x",
        ],
    )
    def test_rejects_invalid_input(self, value):
        with pytest.raises(ValueError, match="40 hexadecimal"):
            normalize_deltachat_fingerprint(value)


class TestDeltaChatLookup:
    def test_builds_social_media_lookup(self):
        lookup = deltachat_lookup(INVITE, display_name="Support", confidence=0.85)

        assert lookup["type"] == "social_media"
        assert lookup["confidence"] == 0.85
        assert json.loads(lookup["value"]) == {
            "platform": "deltachat",
            "handle": FPR,
            "displayName": "Support",
        }

    def test_omits_optional_fields(self):
        lookup = deltachat_lookup(GROUPED)

        assert "confidence" not in lookup
        assert json.loads(lookup["value"]) == {"platform": "deltachat", "handle": FPR}

    def test_sync_client_helper(self, client):
        lookup = client.create_deltachat_identifier(FPR.lower(), confidence=0.9)

        assert lookup == deltachat_lookup(FPR, confidence=0.9)

    def test_async_client_helper(self, mock_api_url, mock_api_key):
        async_client = AsyncScambusClient(api_url=mock_api_url, api_token=mock_api_key)

        lookup = async_client.create_deltachat_identifier(GROUPED, display_name="Support")

        assert lookup == deltachat_lookup(FPR, display_name="Support")
