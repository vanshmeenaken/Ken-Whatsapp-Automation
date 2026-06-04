"""
Agent: SequenceScheduler
Determines which contacts are due for their next message step
and computes the next_message_at timestamp after a send.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from database.campaign_store import get_active_contacts_due, get_contacts_for_campaign


class SequenceScheduler(BaseAgent):
    def __init__(self):
        super().__init__("SequenceScheduler")

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: { "campaign_id": "...", "delay_days": 1 }
        Output: { "due_contacts": [...] }  — contacts ready for their next message
        """
        campaign_id = input_data.get("campaign_id", "")
        if not campaign_id:
            self.raise_error("ValidationError", "campaign_id is required", input_data)

        due = get_active_contacts_due(campaign_id)
        self.log_info(f"Campaign {campaign_id}: {len(due)} contact(s) due for messaging")
        return {"success": True, "due_contacts": due, "count": len(due)}

    def compute_next_send_time(self, delay_days: int, delay_hours: int = 0, delay_minutes: int = 0) -> str:
        """
        Returns the ISO timestamp for when the next step should be sent.
        Total wait = delay_days + delay_hours + delay_minutes.
        """
        next_at = datetime.now(timezone.utc) + timedelta(
            days=delay_days, hours=delay_hours, minutes=delay_minutes
        )
        return next_at.isoformat()

    def get_step_message(self, campaign: Dict[str, Any], step: int) -> str:
        """Return the message template for a given step (1, 2, or 3)."""
        return campaign.get("messages", {}).get(f"step_{step}", "")

    def all_steps_sent(self, contact: Dict[str, Any]) -> bool:
        """True if the contact has already received all 3 messages."""
        return contact.get("current_step", 1) > 3
