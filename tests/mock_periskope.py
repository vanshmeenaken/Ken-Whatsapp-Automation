"""
Mock Periskope API Responses for Testing
Use these to test agents without calling the real Periskope API.
"""


def mock_send_success(phone: str, message: str) -> dict:
    """Simulate a successful Periskope send response."""
    return {
        "status": "queued",
        "unique_id": f"3EB0{hash(phone) % 9999999:07X}",
        "queue_id": f"mock-{abs(hash(phone)):010d}",
        "queue_position": 0,
        "track_by": {
            "unique_id": f"GET /messages/3EB0{hash(phone) % 9999999:07X}/status"
        }
    }


def mock_send_auth_failure() -> dict:
    """Simulate a 401 auth failure from Periskope."""
    return {"code": 401, "message": "Unauthorized"}


def mock_chat_messages_with_reply(phone: str) -> dict:
    """Simulate chat messages where the lead HAS replied (from_me=False)."""
    return {
        "count": 2,
        "from": 1,
        "to": 2,
        "messages": [
            {
                "from_me": False,   # ← INCOMING (lead replied)
                "body": "Thanks, I'm interested!",
                "timestamp": "2026-01-18T14:30:00+00:00",
                "sender_phone": f"{phone.replace('+', '')}@c.us",
                "unique_id": "REPLY123",
                "ack": "0",
            },
            {
                "from_me": True,   # ← OUTGOING (our message)
                "body": "Hi Rohan, quick question...",
                "timestamp": "2026-01-15T10:00:00+00:00",
                "sender_phone": "919876543210@c.us",
                "unique_id": "SENT123",
                "ack": "4",
            }
        ]
    }


def mock_chat_messages_no_reply(phone: str) -> dict:
    """Simulate chat messages where the lead has NOT replied (all from_me=True)."""
    return {
        "count": 1,
        "from": 1,
        "to": 1,
        "messages": [
            {
                "from_me": True,   # ← OUTGOING only, no reply
                "body": "Hi Rohan, quick question...",
                "timestamp": "2026-01-15T10:00:00+00:00",
                "sender_phone": "919876543210@c.us",
                "unique_id": "SENT123",
                "ack": "4",
            }
        ]
    }
