"""
Campaign API Routes
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Any
import csv, io, logging

from agents.campaign_manager import CampaignManager
from agents.reply_checker import ReplyChecker
from agents import AgentException
from utils.campaign_tasks import start_campaign_task, cancel_campaign_task, is_running

logger = logging.getLogger("api.campaigns")
router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

manager = CampaignManager()
checker = ReplyChecker()


# ─────────────────────────────────────────────────────────────────────────────
# POST /campaigns — Create
# ─────────────────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_campaign(body: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return manager.run({"action": "create", **body})
    except AgentException as e:
        raise HTTPException(status_code=400, detail=e.message)


# ─────────────────────────────────────────────────────────────────────────────
# GET /campaigns — List
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", status_code=200)
async def list_campaigns() -> Dict[str, Any]:
    try:
        return manager.run({"action": "list"})
    except AgentException as e:
        raise HTTPException(status_code=500, detail=e.message)


# ─────────────────────────────────────────────────────────────────────────────
# GET /campaigns/{id} — Detail
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{campaign_id}", status_code=200)
async def get_campaign(campaign_id: str) -> Dict[str, Any]:
    try:
        result   = manager.run({"action": "get", "campaign_id": campaign_id})
        contacts = manager.run({"action": "get_contacts", "campaign_id": campaign_id})
        result["contacts"]      = contacts["contacts"]
        result["contact_count"] = contacts["count"]
        result["task_running"]  = is_running(campaign_id)
        return result
    except AgentException as e:
        raise HTTPException(status_code=404, detail=e.message)


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /campaigns/{id} — Update
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/{campaign_id}", status_code=200)
async def update_campaign(campaign_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return manager.run({"action": "update", "campaign_id": campaign_id, **body})
    except AgentException as e:
        raise HTTPException(status_code=400, detail=e.message)


# ─────────────────────────────────────────────────────────────────────────────
# POST /campaigns/{id}/contacts — Add contacts (JSON)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{campaign_id}/contacts", status_code=200)
async def add_contacts(campaign_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return manager.run({
            "action":      "add_contacts",
            "campaign_id": campaign_id,
            "contacts":    body.get("contacts", []),
        })
    except AgentException as e:
        raise HTTPException(status_code=400, detail=e.message)


# ─────────────────────────────────────────────────────────────────────────────
# POST /campaigns/{id}/contacts/upload — Add contacts (CSV)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{campaign_id}/contacts/upload", status_code=200)
async def upload_contacts_csv(campaign_id: str, file: UploadFile = File(...)) -> Dict[str, Any]:
    try:
        content = await file.read()
        reader  = csv.DictReader(io.StringIO(content.decode("utf-8")))
        contacts = [
            {
                "phone_number": (row.get("phone_number") or "").strip(),
                "first_name":   (row.get("first_name") or "").strip(),
                "company":      (row.get("company") or "").strip(),
            }
            for row in reader
        ]
        return manager.run({
            "action":      "add_contacts",
            "campaign_id": campaign_id,
            "contacts":    contacts,
        })
    except AgentException as e:
        raise HTTPException(status_code=400, detail=e.message)


# ─────────────────────────────────────────────────────────────────────────────
# POST /campaigns/{id}/start — Activate + launch sequence task
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{campaign_id}/start", status_code=200)
async def start_campaign(campaign_id: str) -> Dict[str, Any]:
    """
    Activates the campaign and launches the async sequence task.
    Step 1 messages begin sending immediately (with 5-6 min gaps between leads).
    Steps 2 and 3 follow automatically after the configured delay.
    """
    try:
        manager.run({"action": "update", "campaign_id": campaign_id, "status": "active"})
        await start_campaign_task(campaign_id)
        return {"success": True, "message": "Campaign activated — sequence started"}
    except AgentException as e:
        raise HTTPException(status_code=400, detail=e.message)


# ─────────────────────────────────────────────────────────────────────────────
# POST /campaigns/{id}/pause — Pause + cancel sequence task
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{campaign_id}/pause", status_code=200)
async def pause_campaign(campaign_id: str) -> Dict[str, Any]:
    try:
        cancel_campaign_task(campaign_id)
        result = manager.run({"action": "update", "campaign_id": campaign_id, "status": "paused"})
        return {"success": True, "message": "Campaign paused", "campaign": result["campaign"]}
    except AgentException as e:
        raise HTTPException(status_code=400, detail=e.message)


# ─────────────────────────────────────────────────────────────────────────────
# POST /campaigns/{id}/run — Resume / re-trigger sequence task
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{campaign_id}/run", status_code=200)
async def run_campaign(campaign_id: str) -> Dict[str, Any]:
    """
    Re-launches the sequence task (e.g. after server restart).
    Safe to call even if already running — will restart cleanly.
    """
    try:
        manager.run({"action": "update", "campaign_id": campaign_id, "status": "active"})
        await start_campaign_task(campaign_id)
        return {"success": True, "message": "Campaign sequence (re)started"}
    except AgentException as e:
        raise HTTPException(status_code=500, detail=e.message)


# ─────────────────────────────────────────────────────────────────────────────
# POST /campaigns/run/all — Re-launch all active campaigns
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/run/all", status_code=200)
async def run_all_campaigns() -> Dict[str, Any]:
    from database.campaign_store import list_campaigns
    active = [c for c in list_campaigns() if c["status"] == "active"]
    for c in active:
        await start_campaign_task(c["id"])
    return {"success": True, "campaigns_started": len(active)}


# ─────────────────────────────────────────────────────────────────────────────
# POST /campaigns/{id}/check-replies
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{campaign_id}/check-replies", status_code=200)
async def check_replies(campaign_id: str) -> Dict[str, Any]:
    try:
        return checker.run({"campaign_id": campaign_id})
    except AgentException as e:
        raise HTTPException(status_code=500, detail=e.message)
