"""
Agent: CampaignManager
Handles creation, retrieval, and updates of outbound campaigns.
"""

from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from database.campaign_store import (
    create_campaign,
    get_campaign,
    list_campaigns,
    update_campaign,
    add_contacts_to_campaign,
    get_contacts_for_campaign,
)


class CampaignManager(BaseAgent):
    def __init__(self):
        super().__init__("CampaignManager")

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action")

        if action == "create":
            return self._create(input_data)
        elif action == "get":
            return self._get(input_data)
        elif action == "list":
            return self._list()
        elif action == "update":
            return self._update(input_data)
        elif action == "add_contacts":
            return self._add_contacts(input_data)
        elif action == "get_contacts":
            return self._get_contacts(input_data)
        else:
            self.raise_error("ValidationError", f"Unknown action: {action}", input_data)

    # ── Create ──────────────────────────────────────────────────────────────

    def _create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        name = data.get("name", "").strip()
        if not name:
            self.raise_error("ValidationError", "Campaign name is required", data)

        messages = data.get("messages", {})
        if not messages.get("step_1"):
            self.raise_error("ValidationError", "At least step_1 message is required", data)

        campaign = create_campaign(
            name=name,
            messages=messages,
            delay_days=int(data.get("delay_days", 1)),
            delay_hours=int(data.get("delay_hours", 0)),
            delay_minutes=int(data.get("delay_minutes", 0)),
            description=data.get("description", ""),
            created_by=data.get("created_by", "team"),
        )
        self.log_info(f"Campaign created: {campaign['id']} — '{name}'")
        return {"success": True, "campaign": campaign}

    # ── Get ─────────────────────────────────────────────────────────────────

    def _get(self, data: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = data.get("campaign_id", "")
        campaign = get_campaign(campaign_id)
        if not campaign:
            self.raise_error("NotFound", f"Campaign {campaign_id} not found", data)
        return {"success": True, "campaign": campaign}

    # ── List ─────────────────────────────────────────────────────────────────

    def _list(self) -> Dict[str, Any]:
        campaigns = list_campaigns()
        return {"success": True, "campaigns": campaigns, "count": len(campaigns)}

    # ── Update ───────────────────────────────────────────────────────────────

    def _update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = data.get("campaign_id", "")
        allowed_fields = {"name", "description", "messages", "delay_days", "delay_hours", "delay_minutes", "status"}
        updates = {k: v for k, v in data.items() if k in allowed_fields}

        if not updates:
            self.raise_error("ValidationError", "No valid fields to update", data)

        campaign = update_campaign(campaign_id, updates)
        if not campaign:
            self.raise_error("NotFound", f"Campaign {campaign_id} not found", data)

        self.log_info(f"Campaign updated: {campaign_id}")
        return {"success": True, "campaign": campaign}

    # ── Add Contacts ─────────────────────────────────────────────────────────

    def _add_contacts(self, data: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = data.get("campaign_id", "")
        contacts = data.get("contacts", [])   # list of {phone_number, first_name, company}

        if not get_campaign(campaign_id):
            self.raise_error("NotFound", f"Campaign {campaign_id} not found", data)
        if not contacts:
            self.raise_error("ValidationError", "contacts list is empty", data)

        added = add_contacts_to_campaign(campaign_id, contacts)
        self.log_info(f"Added {len(added)} contacts to campaign {campaign_id}")
        return {
            "success": True,
            "campaign_id": campaign_id,
            "added": len(added),
            "skipped": len(contacts) - len(added),
            "contacts": added,
        }

    # ── Get Contacts ──────────────────────────────────────────────────────────

    def _get_contacts(self, data: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = data.get("campaign_id", "")
        contacts = get_contacts_for_campaign(campaign_id)
        return {
            "success": True,
            "campaign_id": campaign_id,
            "contacts": contacts,
            "count": len(contacts),
        }
