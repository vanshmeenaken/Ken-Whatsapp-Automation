"""
FastAPI Routes — Periskope WhatsApp Automation
"""

from fastapi import APIRouter, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
import csv
import io

from agents.message_builder import MessageBuilder
from agents.recipient_validator import RecipientValidator
from agents.periskope_sender import PeriskopeSender
from agents.periskope_fetcher import PeriskopeFetcher
from agents.error_handler import ErrorHandler
from agents import AgentException
from config.settings import settings

logger = logging.getLogger("api")
router = APIRouter()

# Agent instances (shared across requests)
builder = MessageBuilder()
validator = RecipientValidator()
sender = PeriskopeSender()
fetcher = PeriskopeFetcher()
error_handler = ErrorHandler()


# ──────────────────────────────────────────────────────────────────────────────
# POST /send — Send a single WhatsApp message
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/send", status_code=200)
async def send_message(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a single WhatsApp message.

    Request body:
    {
        "phone_number": "+919876543210",
        "message": "Hi {{first_name}}, {{company}} would benefit...",
        "template_variables": {          # optional
            "first_name": "Rohan",
            "company": "Candesis"
        }
    }
    """
    phone = body.get("phone_number")
    message = body.get("message")
    variables = body.get("template_variables")

    if not phone or not message:
        raise HTTPException(status_code=400, detail="phone_number and message are required")

    try:
        # Step 1: Validate phone
        validation = validator.run({"phone_numbers": [phone], "allow_duplicates": True})
        if not validation["valid_phones"]:
            reason = validation["invalid_phones"][0]["reason"] if validation["invalid_phones"] else "Invalid phone"
            raise HTTPException(status_code=400, detail=reason)

        # Step 2: Personalize message if variables given
        if variables:
            build_result = builder.run({"template": message, "variables": variables})
            message = build_result["personalized_message"]

        # Step 3: Send via Periskope
        result = sender.run({"phone_number": phone, "message": message})

        if result["success"]:
            return {
                "success": True,
                "status": result["status"],   # "queued"
                "queue_id": result.get("queue_id"),
                "unique_id": result.get("unique_id"),
                "phone_number": phone,
                "sent_at": result.get("sent_at"),
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except AgentException as e:
        error_handler.handle(e, {"phone": phone})
        raise HTTPException(status_code=500, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# POST /batch — Send to multiple contacts from CSV
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/batch", status_code=200)
async def send_batch(
    file: UploadFile = File(...),
    message_template: str = "Hi {{first_name}}, this is a message for {{company}}."
) -> Dict[str, Any]:
    """
    Send WhatsApp messages to multiple contacts from a CSV file.

    CSV format:
    phone_number,first_name,company
    +919876543210,Rohan,Candesis
    +919123456789,Sonia,Gardner

    All contacts get the same message template with {{first_name}} and {{company}} filled.
    """
    try:
        content = await file.read()
        csv_text = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(csv_text))

        contacts = list(reader)
        if not contacts:
            raise HTTPException(status_code=400, detail="CSV is empty")

        if len(contacts) > settings.MAX_BATCH_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Batch too large ({len(contacts)}). Max is {settings.MAX_BATCH_SIZE}."
            )

        results = {"sent": 0, "failed": 0, "details": []}

        for row in contacts:
            phone = (row.get("phone_number") or "").strip()
            first_name = (row.get("first_name") or "there").strip()
            company = (row.get("company") or "your company").strip()

            if not phone:
                continue

            # Personalize
            try:
                build_result = builder.run({
                    "template": message_template,
                    "variables": {"first_name": first_name, "company": company}
                })
                personalized = build_result["personalized_message"]
            except AgentException:
                personalized = message_template

            # Send
            send_result = sender.run({"phone_number": phone, "message": personalized})

            if send_result["success"]:
                results["sent"] += 1
            else:
                results["failed"] += 1

            results["details"].append({
                "phone_number": phone,
                "first_name": first_name,
                "company": company,
                "status": send_result.get("status", "unknown"),
                "queue_id": send_result.get("queue_id"),
                "error": send_result.get("error"),
            })

        return {
            "success": True,
            "total": len(contacts),
            "sent": results["sent"],
            "failed": results["failed"],
            "results": results["details"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# GET /fetch — Fetch all sent messages (analytics)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/fetch", status_code=200)
async def fetch_messages(
    limit: int = 50,
    offset: int = 0,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch message history from Periskope for analytics.

    Params:
        limit: Max messages to return (default 50, max 2000)
        offset: Pagination offset
        start_time: Filter start date e.g. 2026-01-01
        end_time: Filter end date e.g. 2026-01-31
    """
    try:
        result = fetcher.run({
            "limit": limit,
            "offset": offset,
            "start_time": start_time,
            "end_time": end_time,
        })
        return result

    except AgentException as e:
        error_handler.handle(e)
        raise HTTPException(status_code=500, detail=e.message)


# ──────────────────────────────────────────────────────────────────────────────
# GET /check-reply/{phone} — Check if a specific contact has replied
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/check-reply/{phone_number:path}", status_code=200)
async def check_reply(phone_number: str) -> Dict[str, Any]:
    """
    Check if a contact has replied to any of your messages.
    Useful for manual testing of the reply detection logic.

    Path param: phone_number (e.g. +919876543210 or 919876543210)
    """
    has_reply, replied_at = fetcher.check_for_reply(phone_number)
    return {
        "phone_number": phone_number,
        "has_replied": has_reply,
        "replied_at": replied_at,
    }


# ──────────────────────────────────────────────────────────────────────────────
# GET /health — Health check
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/health", status_code=200)
async def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "version": "1.0",
        "environment": settings.API_ENV,
        "periskope_api_key_set": bool(settings.PERISKOPE_API_KEY),
        "periskope_org_phone_set": bool(settings.PERISKOPE_ORG_PHONE),
    }
