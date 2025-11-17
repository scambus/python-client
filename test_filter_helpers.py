#!/usr/bin/env python3
"""
Test script for identifier type filter helpers.
"""

from scambus_client import (
    build_identifier_type_filter,
    build_combined_filter,
)


def test_build_identifier_type_filter():
    """Test building identifier type filters."""
    print("Testing build_identifier_type_filter()...")

    # Test single type for identifier streams
    result = build_identifier_type_filter("phone", data_type="identifier")
    expected = '$.type == "phone"'
    assert result == expected, f"Expected: {expected}, Got: {result}"
    print(f"  ✓ Single type (identifier): {result}")

    # Test multiple types for identifier streams
    result = build_identifier_type_filter(["phone", "email"], data_type="identifier")
    expected = '$.type == "phone" || $.type == "email"'
    assert result == expected, f"Expected: {expected}, Got: {result}"
    print(f"  ✓ Multiple types (identifier): {result}")

    # Test single type for journal entry streams
    result = build_identifier_type_filter("phone", data_type="journal_entry")
    expected = 'exists($.identifiers[*] ? (@.type == "phone"))'
    assert result == expected, f"Expected: {expected}, Got: {result}"
    print(f"  ✓ Single type (journal_entry): {result}")

    # Test multiple types for journal entry streams
    result = build_identifier_type_filter(["phone", "email"], data_type="journal_entry")
    expected = 'exists($.identifiers[*] ? (@.type == "phone" || @.type == "email"))'
    assert result == expected, f"Expected: {expected}, Got: {result}"
    print(f"  ✓ Multiple types (journal_entry): {result}")

    # Test three types
    result = build_identifier_type_filter(["phone", "email", "url"])
    expected = '$.type == "phone" || $.type == "email" || $.type == "url"'
    assert result == expected, f"Expected: {expected}, Got: {result}"
    print(f"  ✓ Three types (default): {result}")

    # Test invalid type
    try:
        build_identifier_type_filter("invalid_type")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid identifier type" in str(e)
        print(f"  ✓ Invalid type rejected: {e}")

    print("  All build_identifier_type_filter() tests passed!\n")


def test_build_combined_filter():
    """Test building combined filters."""
    print("Testing build_combined_filter()...")

    # Test identifier types only
    result = build_combined_filter(identifier_types="phone")
    expected = '$.type == "phone"'
    assert result == expected, f"Expected: {expected}, Got: {result}"
    print(f"  ✓ Identifier type only: {result}")

    # Test identifier types with confidence
    result = build_combined_filter(identifier_types="phone", min_confidence=0.8)
    expected = '$.type == "phone" && $.confidence >= 0.8'
    assert result == expected, f"Expected: {expected}, Got: {result}"
    print(f"  ✓ Type + min confidence: {result}")

    # Test multiple types with confidence range
    result = build_combined_filter(
        identifier_types=["phone", "email"],
        min_confidence=0.9,
        max_confidence=1.0
    )
    expected = '($.type == "phone" || $.type == "email") && $.confidence >= 0.9 && $.confidence <= 1.0'
    assert result == expected, f"Expected: {expected}, Got: {result}"
    print(f"  ✓ Multiple types + confidence range: {result}")

    # Test custom expression only
    result = build_combined_filter(custom_expression='$.details.platform == "whatsapp"')
    expected = '$.details.platform == "whatsapp"'
    assert result == expected, f"Expected: {expected}, Got: {result}"
    print(f"  ✓ Custom expression only: {result}")

    # Test everything combined
    result = build_combined_filter(
        identifier_types="social_media",
        min_confidence=0.85,
        custom_expression='$.details.platform == "telegram"'
    )
    expected = '$.type == "social_media" && $.confidence >= 0.85 && $.details.platform == "telegram"'
    assert result == expected, f"Expected: {expected}, Got: {result}"
    print(f"  ✓ All options combined: {result}")

    # Test no parameters (should return None)
    result = build_combined_filter()
    assert result is None, f"Expected None, Got: {result}"
    print(f"  ✓ No parameters returns None")

    # Test invalid confidence range
    try:
        build_combined_filter(min_confidence=1.5)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "must be between 0 and 1" in str(e)
        print(f"  ✓ Invalid confidence rejected: {e}")

    print("  All build_combined_filter() tests passed!\n")


def test_real_world_examples():
    """Test real-world usage examples."""
    print("Testing real-world examples...")

    # Phone numbers only
    result = build_identifier_type_filter("phone")
    print(f"  ✓ Phone numbers only:\n    {result}")

    # Contact info (phone or email)
    result = build_identifier_type_filter(["phone", "email"])
    print(f"  ✓ Contact info (phone or email):\n    {result}")

    # High confidence identifiers
    result = build_combined_filter(
        identifier_types=["phone", "email", "url"],
        min_confidence=0.9
    )
    print(f"  ✓ High confidence contact identifiers:\n    {result}")

    # WhatsApp only with high confidence
    result = build_combined_filter(
        identifier_types="social_media",
        min_confidence=0.85,
        custom_expression='$.details.platform == "whatsapp"'
    )
    print(f"  ✓ WhatsApp identifiers (high confidence):\n    {result}")

    # Financial identifiers (bank accounts or crypto wallets)
    result = build_identifier_type_filter(["bank_account", "crypto_wallet"])
    print(f"  ✓ Financial identifiers:\n    {result}")

    print("\n  All real-world examples generated successfully!\n")


if __name__ == "__main__":
    print("=" * 70)
    print("  Filter Helper Tests")
    print("=" * 70)
    print()

    test_build_identifier_type_filter()
    test_build_combined_filter()
    test_real_world_examples()

    print("=" * 70)
    print("  ✓ All tests passed!")
    print("=" * 70)
