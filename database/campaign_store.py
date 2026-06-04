"""
Persistence layer — uses Supabase when credentials are configured,
falls back to local JSON files otherwise.
Same function signatures either way.
"""

import json, uuid, os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from database.supabase_client import db

# ── JSON file paths (fallback) ────────────────────────────────────────────────
_DATA_DIR       = os.path.join(os.path.dirname(__file__), "..", "data")
_CAMPAIGNS_FILE = os.path.join(_DATA_DIR, "campaigns.json")
_CONTACTS_FILE  = os.path.join(_DATA_DIR, "contacts.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _use_supabase() -> bool:
    return db() is not None


# ── JSON helpers ──────────────────────────────────────────────────────────────

def _load(path, default):
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(path, data):
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ═════════════════════════════════════════════════════════════════════════════
# Campaign CRUD
# ═════════════════════════════════════════════════════════════════════════════

def create_campaign(name, messages, delay_days=1, delay_hours=0,
                    delay_minutes=0, description="", created_by="team"):
    row = {
        "id":            str(uuid.uuid4()),
        "name":          name,
        "description":   description,
        "messages":      {"step_1": messages.get("step_1",""),
                          "step_2": messages.get("step_2",""),
                          "step_3": messages.get("step_3","")},
        "delay_days":    delay_days,
        "delay_hours":   delay_hours,
        "delay_minutes": delay_minutes,
        "status":        "draft",
        "created_by":    created_by,
        "created_at":    _now(),
        "updated_at":    _now(),
        "stats":         {"total":0,"sent":0,"replied":0,"completed":0},
    }
    if _use_supabase():
        res = db().table("campaigns").insert(row).execute()
        return res.data[0]
    else:
        campaigns = _load(_CAMPAIGNS_FILE, {})
        campaigns[row["id"]] = row
        _save(_CAMPAIGNS_FILE, campaigns)
        return row


def get_campaign(campaign_id: str) -> Optional[Dict]:
    if _use_supabase():
        res = db().table("campaigns").select("*").eq("id", campaign_id).execute()
        return res.data[0] if res.data else None
    else:
        return _load(_CAMPAIGNS_FILE, {}).get(campaign_id)


def list_campaigns() -> List[Dict]:
    if _use_supabase():
        res = db().table("campaigns").select("*").order("created_at", desc=True).execute()
        return res.data or []
    else:
        campaigns = _load(_CAMPAIGNS_FILE, {})
        return sorted(campaigns.values(), key=lambda c: c["created_at"], reverse=True)


def update_campaign(campaign_id: str, updates: Dict) -> Optional[Dict]:
    updates["updated_at"] = _now()
    if _use_supabase():
        res = db().table("campaigns").update(updates).eq("id", campaign_id).execute()
        return res.data[0] if res.data else None
    else:
        campaigns = _load(_CAMPAIGNS_FILE, {})
        if campaign_id not in campaigns:
            return None
        campaigns[campaign_id].update(updates)
        _save(_CAMPAIGNS_FILE, campaigns)
        return campaigns[campaign_id]


def update_campaign_stats(campaign_id: str):
    contacts = get_contacts_for_campaign(campaign_id)
    stats = {
        "total":     len(contacts),
        "sent":      sum(1 for c in contacts if c.get("messages_sent")),
        "replied":   sum(1 for c in contacts if c["status"] == "replied"),
        "completed": sum(1 for c in contacts if c["status"] == "completed"),
    }
    if _use_supabase():
        db().table("campaigns").update({"stats": stats, "updated_at": _now()}).eq("id", campaign_id).execute()
    else:
        campaigns = _load(_CAMPAIGNS_FILE, {})
        if campaign_id in campaigns:
            campaigns[campaign_id]["stats"] = stats
            campaigns[campaign_id]["updated_at"] = _now()
            _save(_CAMPAIGNS_FILE, campaigns)


# ═════════════════════════════════════════════════════════════════════════════
# Contact CRUD
# ═════════════════════════════════════════════════════════════════════════════

def add_contacts_to_campaign(campaign_id: str, contacts: List[Dict]) -> List[Dict]:
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
            "created_at":      _now(),
            "updated_at":      _now(),
        })
        existing_phones.add(phone)

    if not rows:
        return []

    if _use_supabase():
        res = db().table("contacts").insert(rows).execute()
        added = res.data or []
    else:
        all_contacts = _load(_CONTACTS_FILE, [])
        all_contacts.extend(rows)
        _save(_CONTACTS_FILE, all_contacts)
        added = rows

    update_campaign_stats(campaign_id)
    return added


def get_contacts_for_campaign(campaign_id: str) -> List[Dict]:
    if _use_supabase():
        res = db().table("contacts").select("*").eq("campaign_id", campaign_id).order("created_at").execute()
        return res.data or []
    else:
        return [c for c in _load(_CONTACTS_FILE, []) if c["campaign_id"] == campaign_id]


def get_contact(contact_id: str) -> Optional[Dict]:
    if _use_supabase():
        res = db().table("contacts").select("*").eq("id", contact_id).execute()
        return res.data[0] if res.data else None
    else:
        return next((c for c in _load(_CONTACTS_FILE, []) if c["id"] == contact_id), None)


def update_contact(contact_id: str, updates: Dict) -> Optional[Dict]:
    updates["updated_at"] = _now()
    if _use_supabase():
        res = db().table("contacts").update(updates).eq("id", contact_id).execute()
        return res.data[0] if res.data else None
    else:
        all_contacts = _load(_CONTACTS_FILE, [])
        for i, c in enumerate(all_contacts):
            if c["id"] == contact_id:
                all_contacts[i].update(updates)
                _save(_CONTACTS_FILE, all_contacts)
                return all_contacts[i]
        return None


def get_active_contacts_due(campaign_id: str) -> List[Dict]:
    now = _now()
    if _use_supabase():
        res = (db().table("contacts").select("*")
               .eq("campaign_id", campaign_id)
               .eq("status", "active")
               .lte("next_message_at", now)
               .lte("current_step", 3)
               .execute())
        return res.data or []
    else:
        contacts = get_contacts_for_campaign(campaign_id)
        return [
            c for c in contacts
            if c["status"] == "active"
            and c.get("next_message_at", "") <= now
            and c.get("current_step", 1) <= 3
        ]
