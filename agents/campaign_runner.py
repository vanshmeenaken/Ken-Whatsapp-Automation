"""
CampaignRunner — handles building and sending a single step message for one contact.
The full sequence orchestration (sleeps, step loop) lives in utils/campaign_tasks.py.
"""

from datetime import datetime, timezone
from typing import Dict, Any
from agents.base_agent import BaseAgent
from agents.message_builder import MessageBuilder
from agents.periskope_sender import PeriskopeSender
from agents.sequence_scheduler import SequenceScheduler
from database.campaign_store import update_contact, update_campaign_stats


class CampaignRunner(BaseAgent):
    def __init__(self):
        super().__init__("CampaignRunner")
        self.builder   = MessageBuilder()
        self.sender    = PeriskopeSender()
        self.scheduler = SequenceScheduler()

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Not used directly anymore — sequence is driven by campaign_tasks.py
        return {"success": True}

    def _send_step(self, campaign: Dict[str, Any], contact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Personalise and send the correct step message for one contact.
        Called by the async sequence task via asyncio.to_thread().
        """
        step     = contact["current_step"]
        phone    = contact["phone_number"]
        template = self.scheduler.get_step_message(campaign, step)
        delay          = campaign.get("delay_days", 0)
        delay_hours    = campaign.get("delay_hours", 0)
        delay_minutes  = campaign.get("delay_minutes", 0)

        if not template:
            self._advance_contact(contact, step, delay, delay_hours, delay_minutes, unique_id=None)
            return {"success": True, "phone": phone, "step": step, "skipped": True}

        # Personalise
        try:
            built   = self.builder.run({
                "template":  template,
                "variables": {
                    "first_name": contact.get("first_name", "there"),
                    "company":    contact.get("company", ""),
                },
            })
            message = built["personalized_message"]
        except Exception:
            message = template

        # Send
        result = self.sender.run({"phone_number": phone, "message": message})

        if result["success"]:
            self._advance_contact(
                contact, step, delay, delay_hours, delay_minutes,
                unique_id=result.get("unique_id")
            )
            self.log_info(f"Step {step} sent to {phone}")
        else:
            self.log_error(f"Step {step} failed for {phone}: {result.get('error')}")

        return result

    def _advance_contact(
        self,
        contact: Dict[str, Any],
        step: int,
        delay_days: int = 0,
        delay_hours: int = 0,
        delay_minutes: int = 0,
        unique_id: str = None,
    ):
        messages_sent = list(contact.get("messages_sent", []))
        if unique_id:
            messages_sent.append({
                "step":      step,
                "sent_at":   datetime.now(timezone.utc).isoformat(),
                "unique_id": unique_id,
            })

        next_step  = step + 1
        new_status = "completed" if next_step > 3 else "active"

        update_contact(contact["id"], {
            "current_step":  next_step,
            "messages_sent": messages_sent,
            "status":        new_status,
        })
        update_campaign_stats(contact["campaign_id"])
