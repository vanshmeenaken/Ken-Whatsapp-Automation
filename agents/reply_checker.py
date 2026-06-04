"""
Agent: ReplyChecker
Checks all active contacts in a campaign for incoming replies.
If a reply is found, marks the contact as 'replied' and stops their automation.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
from agents.base_agent import BaseAgent
from agents.periskope_fetcher import PeriskopeFetcher
from database.campaign_store import (
    get_contacts_for_campaign,
    update_contact,
    update_campaign_stats,
)


class ReplyChecker(BaseAgent):
    def __init__(self):
        super().__init__("ReplyChecker")
        self.fetcher = PeriskopeFetcher()

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Checks every active contact in a campaign for replies.
        Stops automation and tags the contact if a reply is detected.

        Input:  { "campaign_id": "..." }
        Output: { "checked": N, "replied": [...], "still_active": [...] }
        """
        campaign_id = input_data.get("campaign_id", "")
        if not campaign_id:
            self.raise_error("ValidationError", "campaign_id is required", input_data)

        contacts = get_contacts_for_campaign(campaign_id)
        active = [c for c in contacts if c["status"] == "active"]

        replied_contacts = []
        still_active = []

        for contact in active:
            has_reply, reply_body, replied_at = self._check_contact(contact)
            if has_reply:
                update_contact(contact["id"], {
                    "status":     "replied",
                    "replied_at": replied_at,
                    "reply_body": reply_body,
                })
                replied_contacts.append({
                    "id":           contact["id"],
                    "phone_number": contact["phone_number"],
                    "first_name":   contact["first_name"],
                    "replied_at":   replied_at,
                    "reply_body":   reply_body,
                })
                self.log_info(
                    f"Reply detected from {contact['phone_number']} — automation stopped"
                )
            else:
                still_active.append(contact["phone_number"])

        if replied_contacts:
            update_campaign_stats(campaign_id)

        return {
            "success":      True,
            "campaign_id":  campaign_id,
            "checked":      len(active),
            "replied":      replied_contacts,
            "replied_count": len(replied_contacts),
            "still_active": still_active,
        }

    def _check_contact(self, contact: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        Returns (has_reply, reply_body, replied_at_iso).
        Uses PeriskopeFetcher to scan the chat for any incoming message.
        """
        phone = contact["phone_number"]
        try:
            has_reply, replied_at = self.fetcher.check_for_reply(phone)
            if has_reply:
                # Try to fetch the actual reply body
                body = self._get_reply_body(phone)
                replied_at_str = replied_at if replied_at else datetime.now(timezone.utc).isoformat()
                return True, body, replied_at_str
        except Exception as e:
            self.log_error(f"Reply check failed for {phone}: {e}")
        return False, "", ""

    def _get_reply_body(self, phone: str) -> str:
        """Fetch the text of the most recent incoming message from this contact."""
        try:
            result = self.fetcher.run({"limit": 20, "offset": 0})
            messages = result.get("messages", [])
            chat_id = phone.replace("+", "").replace(" ", "") + "@c.us"
            for msg in reversed(messages):
                if msg.get("chat_id") == chat_id and not msg.get("from_me", True):
                    return msg.get("body", "")
        except Exception:
            pass
        return ""
