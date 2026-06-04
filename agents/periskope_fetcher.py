"""
Agent 4: Periskope Fetcher
Fetches messages from Periskope API.
Used for two purposes:
  1. Reply detection — check if a lead has replied to any message
  2. Campaign analytics — fetch sent messages across all chats

API Reference: https://docs.periskope.app/api-reference/chat
Endpoints:
  GET /chats/{chat_id}/messages   → Messages for one contact (reply detection)
  GET /chats/messages             → All messages across all chats (analytics)
"""

import requests
from typing import Dict, Any, List, Optional, Tuple
from agents.base_agent import BaseAgent
from config.settings import settings
from config.constants import (
    GET_CHAT_MESSAGES_ENDPOINT,
    LIST_ALL_MESSAGES_ENDPOINT,
    REQUEST_TIMEOUT_SECONDS,
    ACK_STATUS,
)


class PeriskopeFetcher(BaseAgent):
    """
    Fetches messages from Periskope.

    Key insight from Periskope API docs:
    - Each message object has a `from_me` boolean field.
    - from_me = True  → outgoing message (YOU sent it)
    - from_me = False → incoming message (LEAD replied)
    - This is how we detect replies without any extra API call.
    """

    def __init__(self):
        super().__init__("PeriskopeFetcher")

    # -----------------------------------------------------------------------
    # Reply Detection (used by campaign scheduler)
    # -----------------------------------------------------------------------

    def check_for_reply(self, phone_number: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a specific contact has sent any incoming message.

        Args:
            phone_number: e.g. "+919876543210" or "919876543210"

        Returns:
            (has_replied: bool, replied_at: Optional[str])
        """
        chat_id = self._format_chat_id(phone_number)
        url = GET_CHAT_MESSAGES_ENDPOINT.replace("{chat_id}", chat_id)

        try:
            response = requests.get(
                url,
                headers=settings.get_auth_headers(),
                params={"limit": 20, "offset": 0},  # Only need recent messages
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

            if response.status_code == 404:
                # No conversation exists yet — no reply
                return False, None

            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])

                # Look for any message where from_me = False (lead replied)
                for msg in messages:
                    if msg.get("from_me") is False:
                        replied_at = msg.get("timestamp", self.get_timestamp())
                        self.log_info(f"Reply detected from {phone_number} at {replied_at}")
                        return True, replied_at

                return False, None

            elif response.status_code == 401:
                self.log_error("Auth failed checking replies. Check PERISKOPE_API_KEY.")
                return False, None

            else:
                self.log_warning(f"Unexpected status {response.status_code} checking {phone_number}")
                return False, None

        except requests.exceptions.Timeout:
            self.log_warning(f"Timeout checking {phone_number}. Assuming no reply.")
            return False, None
        except Exception as e:
            self.log_error(f"Error checking reply for {phone_number}: {e}")
            return False, None

    # -----------------------------------------------------------------------
    # Fetch All Messages (analytics / campaign review)
    # -----------------------------------------------------------------------

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch all messages across chats for analytics.

        Input:
        {
            "limit": 50,        # optional, default 50, max 2000
            "offset": 0,        # optional, for pagination
            "start_time": "2026-01-01",  # optional filter
            "end_time": "2026-01-31",    # optional filter
        }

        Output:
        {
            "success": True,
            "messages": [
                {
                    "unique_id": "3EB0...",
                    "chat_id": "919876543210@c.us",
                    "body": "Hi Rohan...",
                    "from_me": True,
                    "timestamp": "2026-01-20T10:30:00+00:00",
                    "status": "delivered",
                    "sender_phone": "918527184400@c.us"
                }
            ],
            "count": 50,
            "from": 1,
            "to": 50
        }
        """
        limit = min(input_data.get("limit", 50), 2000)
        offset = input_data.get("offset", 0)
        start_time = input_data.get("start_time")
        end_time = input_data.get("end_time")

        params = {"limit": limit, "offset": offset}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        try:
            response = requests.get(
                LIST_ALL_MESSAGES_ENDPOINT,
                headers=settings.get_auth_headers(),
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

            if response.status_code == 200:
                data = response.json()
                raw_messages = data.get("messages", [])
                parsed = [self._parse_message(m) for m in raw_messages]

                return {
                    "success": True,
                    "messages": parsed,
                    "count": data.get("count", len(parsed)),
                    "from": data.get("from", offset + 1),
                    "to": data.get("to", offset + len(parsed)),
                }

            elif response.status_code == 401:
                self.raise_error("AuthError", "Invalid API key", input_data)
            elif response.status_code == 422:
                detail = response.json().get("message", "Validation error")
                self.raise_error("ValidationError", detail, input_data)
            else:
                self.raise_error("APIError", f"HTTP {response.status_code}", input_data)

        except requests.exceptions.RequestException as e:
            self.raise_error("RequestError", str(e), input_data)

    def _parse_message(self, raw: Dict) -> Dict[str, Any]:
        """Extract relevant fields from raw Periskope message object."""
        ack = str(raw.get("ack", "0"))
        return {
            "unique_id": raw.get("unique_id"),
            "chat_id": raw.get("chat_id"),
            "body": raw.get("body"),
            "from_me": raw.get("from_me", False),
            "timestamp": raw.get("timestamp"),
            "status": ACK_STATUS.get(ack, "unknown"),
            "sender_phone": raw.get("sender_phone"),
            "message_type": raw.get("message_type"),
            "has_media": raw.get("has_media"),
        }

    def _format_chat_id(self, phone: str) -> str:
        """Convert phone to Periskope chat_id format: 919876543210@c.us"""
        cleaned = phone.replace("+", "").replace(" ", "").replace("-", "")
        if not cleaned.endswith("@c.us"):
            cleaned = f"{cleaned}@c.us"
        return cleaned
