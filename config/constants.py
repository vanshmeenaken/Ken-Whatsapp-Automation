"""
Periskope API Constants
All endpoints and config verified from https://docs.periskope.app
"""

# ============================================================================
# PERISKOPE API — CONFIRMED FROM DOCS
# ============================================================================

BASE_URL = "https://api.periskope.app/v1"

# Send a WhatsApp message (text or media)
# POST /message/send
SEND_MESSAGE_ENDPOINT = f"{BASE_URL}/message/send"

# Get all messages across all chats (for campaign analytics)
# GET /chats/messages
LIST_ALL_MESSAGES_ENDPOINT = f"{BASE_URL}/chats/messages"

# Get messages for a specific contact/chat (for reply detection)
# GET /chats/{chat_id}/messages
GET_CHAT_MESSAGES_ENDPOINT = f"{BASE_URL}/chats/{{chat_id}}/messages"

# Get message delivery status by unique_id
# GET /message/{unique_id}/status
MESSAGE_STATUS_ENDPOINT = f"{BASE_URL}/message/{{unique_id}}/status"

# ============================================================================
# AUTHENTICATION
# Two headers required on every request:
#   Authorization: Bearer {PERISKOPE_API_KEY}
#   x-phone: {ORG_PHONE}  e.g. 919876543210 (no + or spaces)
# ============================================================================

# ============================================================================
# CHAT ID FORMAT
# 1-1 chat:  {country_code}{phone_number}@c.us  e.g. 919876543210@c.us
#            (@c.us suffix is optional — Periskope accepts without it too)
# Group chat: {group_id}@g.us
# ============================================================================

# ============================================================================
# SEND MESSAGE — REQUEST BODY
# {
#   "chat_id": "919876543210@c.us",   # required
#   "message": "Hello World",          # text body (supports WhatsApp markdown)
# }
# ============================================================================

# ============================================================================
# SEND MESSAGE — RESPONSE BODY (messages are QUEUED, not sent immediately)
# {
#   "status": "queued",
#   "unique_id": "3EB0630434929F6B94327F",
#   "queue_id": "b986ccf5-7698-...",
#   "queue_position": 0,
#   "track_by": {
#     "unique_id": "GET /messages/3EB0630434929F6B94327F/status"
#   }
# }
# ============================================================================

# ============================================================================
# GET CHAT MESSAGES — RESPONSE (reply detection uses from_me field)
# {
#   "count": 10,
#   "from": 1,
#   "to": 10,
#   "messages": [
#     {
#       "from_me": false,       # <-- FALSE means incoming reply from lead
#       "body": "Hello there",
#       "timestamp": "2025-01-23T12:05:29+00:00",
#       "sender_phone": "919537851844@c.us",
#       "unique_id": "3FEBFB04480C6E256A37",
#       ...
#     }
#   ]
# }
# ============================================================================

# ============================================================================
# RATE LIMITS (from API response headers)
# X-RateLimit-Limit: 10    (10 requests per window)
# X-RateLimit-Remaining: 9
# X-RateLimit-Reset: {unix_timestamp}
# ============================================================================

RATE_LIMIT_PER_WINDOW = 10
REQUEST_TIMEOUT_SECONDS = 15
MAX_MESSAGE_LENGTH = 4096
MAX_MESSAGES_PER_FETCH = 2000  # Periskope max limit per request

# ============================================================================
# MESSAGE STATUS CODES (from Periskope ack field)
# ack: "0" = pending
# ack: "1" = sent
# ack: "2" = received
# ack: "3" = read
# ack: "4" = delivered
# ============================================================================

ACK_STATUS = {
    "0": "pending",
    "1": "sent",
    "2": "received",
    "3": "read",
    "4": "delivered",
}
