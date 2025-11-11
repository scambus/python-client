#!/usr/bin/env python3
"""
Example: Working with In-Progress Activities

This example demonstrates how to use the new in-progress activity features:
- Starting activities without an end time
- Completing activities later
- Using the convenient .complete() method
- Working with phone calls and text conversations

Breaking Changes (v2.0.0):
- PhoneCallDetails no longer has start_time/end_time fields
- TextConversationDetails no longer has start_time/end_time fields
- Times are now managed at the top level of journal entries
"""

import os
from datetime import datetime, timedelta
from scambus_client import ScambusClient, PhoneCallDetails

# Initialize client
client = ScambusClient(
    base_url=os.environ.get("SCAMBUS_URL", "http://localhost:3000"),
    api_key=os.environ.get("SCAMBUS_API_KEY"),
)


def example_1_basic_in_progress_activity():
    """Example 1: Create a basic in-progress activity"""
    print("\n=== Example 1: Basic In-Progress Activity ===")

    # Start an activity without knowing when it will end
    activity = client.create_journal_entry(
        entry_type="phone_call",
        description="Customer support call with Jane Doe",
        start_time=datetime.now(),
        in_progress=True,  # This will omit end_time from the request
    )

    print(f"✓ Started activity: {activity.id}")
    print(f"  Start time: {activity.start_time}")
    print(f"  End time: {activity.end_time}")  # Will be None
    print(f"  In progress: {activity.end_time is None}")

    return activity


def example_2_complete_with_method(activity):
    """Example 2: Complete an activity using the .complete() method"""
    print("\n=== Example 2: Complete Activity with .complete() ===")

    # Complete the activity - this is the elegant way!
    completion = activity.complete()

    print(f"✓ Activity completed: {completion.id}")
    print(f"  Type: {completion.type}")
    print(f"  Description: {completion.description}")
    print(f"  Details: {completion.details}")


def example_3_complete_with_custom_time():
    """Example 3: Complete an activity with custom end time"""
    print("\n=== Example 3: Complete with Custom End Time ===")

    # Start an activity 2 hours ago
    start = datetime.now() - timedelta(hours=2)
    activity = client.create_journal_entry(
        entry_type="research",
        description="Investigating suspicious email pattern",
        start_time=start,
        in_progress=True,
    )

    print(f"✓ Started activity: {activity.id}")
    print(f"  Started: {activity.start_time}")

    # Complete it with a specific end time (1 hour later)
    end = start + timedelta(hours=1)
    completion = activity.complete(
        end_time=end,
        description="Research completed - pattern identified",
    )

    print(f"✓ Activity completed: {completion.id}")
    print(f"  Duration: {completion.details.get('durationSeconds')} seconds")


def example_4_instant_completion():
    """Example 4: Activities that complete instantly"""
    print("\n=== Example 4: Instant Completion (start_time defaults to end_time) ===")

    # When you provide start_time but not end_time and not in_progress,
    # end_time automatically defaults to start_time (instant completion)
    note = client.create_journal_entry(
        entry_type="note",
        description="Quick observation about the case",
        start_time=datetime.now(),
        # No end_time and no in_progress means instant completion
    )

    print(f"✓ Created note: {note.id}")
    print(f"  Start time: {note.start_time}")
    print(f"  End time: {note.end_time}")
    print(f"  Instant: {note.start_time == note.end_time}")


def example_5_phone_call_workflow():
    """Example 5: Complete phone call workflow"""
    print("\n=== Example 5: Phone Call Workflow ===")

    # Start a phone call
    call = client.create_phone_call(
        description="Outbound call to verify account",
        direction="outbound",
        start_time=datetime.now(),
        identifiers=["phone:+15551234567"],
        in_progress=True,
    )

    print(f"✓ Phone call started: {call.id}")
    print(f"  Direction: {call.details.get('direction')}")
    print(f"  In progress: {call.end_time is None}")

    # Later... complete the call
    print("\n  [Call in progress...]")
    print("  [30 seconds later...]")

    completion = call.complete(
        description="Call completed - account verified successfully",
    )

    print(f"\n✓ Phone call completed: {completion.id}")
    print(f"  Duration: {completion.details.get('durationSeconds')} seconds")
    print(f"  Reason: {completion.details.get('completionReason')}")


def example_6_text_conversation_workflow():
    """Example 6: Text conversation workflow"""
    print("\n=== Example 6: Text Conversation Workflow ===")

    # Start a text conversation
    conversation = client.create_text_conversation(
        description="SMS exchange with reported scammer",
        platform="sms",
        start_time=datetime.now(),
        identifiers=["phone:+15559876543"],
        in_progress=True,
    )

    print(f"✓ Text conversation started: {conversation.id}")
    print(f"  Platform: {conversation.details.get('platform')}")

    # Complete with custom reason
    completion = conversation.complete(
        completion_reason="timeout_6h",
        description="Conversation auto-completed after 6 hours",
    )

    print(f"✓ Conversation completed: {completion.id}")
    print(f"  Reason: {completion.details.get('completionReason')}")


def example_7_complete_by_id():
    """Example 7: Complete an activity by ID"""
    print("\n=== Example 7: Complete Activity by ID ===")

    # Start an activity
    activity = client.create_journal_entry(
        entry_type="analysis",
        description="Analyzing transaction patterns",
        start_time=datetime.now(),
        in_progress=True,
    )

    print(f"✓ Analysis started: {activity.id}")

    # Later, you can complete it using just the ID
    completion = client.complete_activity(
        parent_entry=activity.id,  # Can pass ID as string
        description="Analysis completed",
    )

    print(f"✓ Analysis completed: {completion.id}")


def example_8_get_in_progress_activities():
    """Example 8: Query for in-progress activities"""
    print("\n=== Example 8: Get In-Progress Activities ===")

    # Create a few in-progress activities
    activities = []
    for i in range(3):
        activity = client.create_journal_entry(
            entry_type="observation",
            description=f"Ongoing observation #{i+1}",
            start_time=datetime.now(),
            in_progress=True,
        )
        activities.append(activity)
        print(f"✓ Started activity: {activity.id}")

    # Query for all in-progress activities
    # Note: Users can query manually using the API if needed
    print(f"\n  Total in-progress activities created: {len(activities)}")

    # Complete one of them
    if activities:
        print(f"\n  Completing first activity...")
        activities[0].complete()
        print(f"✓ Completed: {activities[0].id}")


if __name__ == "__main__":
    print("=" * 60)
    print("In-Progress Activities Example")
    print("=" * 60)

    try:
        # Run all examples
        activity = example_1_basic_in_progress_activity()
        example_2_complete_with_method(activity)
        example_3_complete_with_custom_time()
        example_4_instant_completion()
        example_5_phone_call_workflow()
        example_6_text_conversation_workflow()
        example_7_complete_by_id()
        example_8_get_in_progress_activities()

        print("\n" + "=" * 60)
        print("✓ All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
