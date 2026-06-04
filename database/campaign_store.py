"""
Persistence layer — Supabase (PostgreSQL).
All function signatures are identical to the old JSON version so nothing
else in the codebase needs to change.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from database.supabase_client import db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Campaign CRUD
# ─────────────────────────────────────────────────────────────────────────────

def create_campaign(
    name: str,
    messages: Dict[str, str],
    delay_days: int = 1,
    delay_hours: int = 0,
    delay_minutes: int = 0,
    description: str = "",
    created_by: str = "team",
) -> Dict[str, Any]:
    row = {
        "id":            str(uuid.uuid4()),
        "name":          name,
        "description":   description,
        "messages":      {
            "step_1": messages.get("step_1", ""),
            "step_2": messages.get("step_2", ""),
            "step_3": messages.get("step_3", ""),
        },
        "delay_days":    delay_days,
        "delay_hours":   delay_hours,
        "delay_minutes": delay_minutes,
        "status":        "draft",
        "created_by":    created_by,
        "stats":         {"total": 0, "sent": 0, "replied": 0, "completed": 0},
    }
    res = db().table("campaigns").insert(row).execute()
    return res.data[0]


def get_campaign(campaign_id: str) -> Optional[Dict[str, Any]]:
    res = db().table("campaigns").select("*").eq("id", campaign_id).execute()
    return res.data[0] if res.data else None


def list_campaigns() -> List[Dict[str, Any]]:
    res = db().table("campaigns").select("*").order("created_at", desc=True).execute()
    return res.data or []


def update_campaign(campaign_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    updates["updated_at"] = _now()
    res = db().table("campaigns").update(updates).eq("id", campaign_id).execute()
    return res.data[0] if res.data else None


def update_campaign_stats(campaign_id: str):
    contacts = get_contacts_for_campaign(campaign_id)
    stats = {
        "total":     len(contacts),
        "sent":      sum(1 for c in contacts if c.get("messages_sent")),
        "replied":   sum(1 for c in contacts if c["status"] == "replied"),
        "completed": sum(1 for c in contacts if c["status"] == "completed"),
    }
    db().table("campaigns").update({"stats": stats, "updated_at": _now()}).eq("id", campaign_id).execute()


# ─────────────────────────────────────────────────────────────────────────────
# Contact CRUD
# ─────────────────────────────────────────────────────────────────────────────

def add_contacts_to_campaign(
    campaign_id: str,
    contacts: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    # Fetch existing phones to skip duplicates
    existing = get_contacts_for_campaign(campaign_id)
    existing_phones = {c["phone_number"] for c in existing}

    rows = []
    for row in contacts:
        phone = row.get("phone_number", "").strip()
        if not phone or phone in existing_phones:
            continue
        rows.append({
            "id":              str(uuid.uuid4()),
            "campaign_id":     campaign_id,
            "phone_number":    phone,
            "first_name":      row.get("first_name", "there").strip(),
            "company":         row.get("company", "").strip(),
            "current_step":    1,
            "status":          "active",
            "next_message_at": _now(),
            "messages_sent":   [],
            "replied_at":      None,
            "reply_body":      None,
        })
        existing_phones.add(phone)

    if rows:
        res = db().table("contacts").insert(rows).execute()
        added = res.data or []
        update_campaign_stats(campaign_id)
        return added
    return []


def get_contacts_for_campaign(campaign_id: str) -> List[Dict[str, Any]]:
    res = (
        db().table("contacts")
        .select("*")
        .eq("campaign_id", campaign_id)
        .order("created_at")
        .execute()
    )
    return res.data or []


def get_contact(contact_id: str) -> Optional[Dict[str, Any]]:
    res = db().table("contacts").select("*").eq("id", contact_id).execute()
    return res.data[0] if res.data else None


def update_contact(contact_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    updates["updated_at"] = _now()
    res = db().table("contacts").update(updates).eq("id", contact_id).execute()
    return res.data[0] if res.data else None


def get_active_contacts_due(campaign_id: str) -> List[Dict[str, Any]]:
    """Contacts that are active, not past step 3, and whose next_message_at has passed."""
    now = _now()
    res = (
        db().table("contacts")
        .select("*")
        .eq("campaign_id", campaign_id)
        .eq("status", "active")
        .lte("next_message_at", now)
        .lte("current_step", 3)
        .execute()
    )
    return res.data or []
