"""
Agent 3: Periskope Sender
Sends WhatsApp messages via Periskope API.

API Reference: https://docs.periskope.app/api-reference/message/send-message
Endpoint: POST https://api.periskope.app/v1/message/send
Auth: Authorization: Bearer {api_key}  +  x-phone: {org_phone}
"""

import time
import requests
from typing import Dict, Any
from agents.base_agent import BaseAgent
from config.settings import settings
from config.constants import (
    SEND_MESSAGE_ENDPOINT,
    REQUEST_TIMEOUT_SECONDS,
    MAX_MESSAGE_LENGTH,
)


class PeriskopeSender(BaseAgent):
    """
    Sends a single WhatsApp message via Periskope API.

    Notes from Periskope docs:
    - Messages are QUEUED (not sent immediately). Response is "queued" status.
    - The response includes a queue_id and unique_id to track delivery.
    - Periskope retries failed messages up to 3 times automatically.
    - chat_id for 1-1 chats: {country_code}{phone}@c.us  e.g. 919876543210@c.us
    - Rate limit: 10 requests per window (see X-RateLimit headers in response)
    """

    def __init__(self):
        super().__init__("PeriskopeSender")

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input:
        {
            "phone_number": "+919876543210",   # or "919876543210"
            "message": "Hi Rohan, Candesis...",
        }

        Output (success):
        {
            "success": True,
            "status": "queued",
            "queue_id": "b986ccf5-...",
            "unique_id": "3EB0630434929F6B94327F",
            "queue_position": 0,
            "phone_number": "+919876543210",
            "sent_at": "2026-01-20T10:30:00"
        }

        Output (failure):
        {
            "success": False,
            "error": "...",
            "error_code": "...",
            "phone_number": "+919876543210",
            "status": "failed"
        }
        """
        phone = input_data.get("phone_number", "")
        message = input_data.get("message", "")

        if not phone or not message:
            self.raise_error("ValidationError", "phone_number and message are required", input_data)

        if len(message) > MAX_MESSAGE_LENGTH:
            self.raise_error("ValidationError", f"Message exceeds {MAX_MESSAGE_LENGTH} chars", input_data)

        # Format chat_id: strip + and spaces, append @c.us
        chat_id = self._format_chat_id(phone)

        return self._send(chat_id, message, phone)

    def _format_chat_id(self, phone: str) -> str:
        """
        Convert phone number to Periskope chat_id format.
        Input:  +91 98765 43210  or  +919876543210  or  919876543210
        Output: 919876543210@c.us
        """
        cleaned = phone.replace("+", "").replace(" ", "").replace("-", "")
        if not cleaned.endswith("@c.us"):
            cleaned = f"{cleaned}@c.us"
        return cleaned

    def _send(self, chat_id: str, message: str, original_phone: str) -> Dict[str, Any]:
        """Make the actual POST to Periskope send endpoint."""
        headers = settings.get_auth_headers()
        payload = {
            "chat_id": chat_id,
            "message": message,
        }

        self.log_debug(f"POST {SEND_MESSAGE_ENDPOINT} → {chat_id}")

        try:
            response = requests.post(
                SEND_MESSAGE_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

            # Success: 200 OK — message queued
            if response.status_code == 200:
                data = response.json()
                self.log_info(f"Message queued for {original_phone} | queue_id={data.get('queue_id')}")
                return {
                    "success": True,
                    "status": "queued",
                    "queue_id": data.get("queue_id"),
                    "unique_id": data.get("unique_id"),
                    "queue_position": data.get("queue_position", 0),
                    "phone_number": original_phone,
                    "sent_at": self.get_timestamp(),
                }

            # Auth failure
            elif response.status_code == 401:
                return self._failed(original_phone, "Invalid API key or x-phone header", "AUTH_FAILED")

            # Bad request (invalid phone, message too long, etc.)
            elif response.status_code == 400:
                detail = response.json().get("message", response.text)
                return self._failed(original_phone, f"Bad request: {detail}", "BAD_REQUEST")

            # Validation error
            elif response.status_code == 422:
                detail = response.json().get("message", response.text)
                return self._failed(original_phone, f"Validation error: {detail}", "VALIDATION_ERROR")

            # Rate limited
            elif response.status_code == 429:
                reset_at = response.headers.get("X-RateLimit-Reset", "unknown")
                return self._failed(original_phone, f"Rate limit hit. Resets at {reset_at}", "RATE_LIMITED")

            # Server error
            elif response.status_code >= 500:
                return self._failed(original_phone, f"Periskope server error ({response.status_code})", "SERVER_ERROR")

            else:
                return self._failed(original_phone, f"HTTP {response.status_code}: {response.text}", "HTTP_ERROR")

        except requests.exceptions.Timeout:
            return self._failed(original_phone, "Request timed out", "TIMEOUT")
        except requests.exceptions.ConnectionError:
            return self._failed(original_phone, "Cannot connect to Periskope API", "CONNECTION_ERROR")
        except Exception as e:
            return self._failed(original_phone, str(e), "UNEXPECTED_ERROR")

    def _failed(self, phone: str, error: str, code: str) -> Dict[str, Any]:
        self.log_error(f"Send failed for {phone}: {error}")
        return {
            "success": False,
            "error": error,
            "error_code": code,
            "phone_number": phone,
            "status": "failed",
        }
