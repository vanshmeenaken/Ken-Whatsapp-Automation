"""
Campaign task registry.
Tracks one asyncio.Task per campaign — the long-running sequence coroutine.
"""

import asyncio
import random
import logging
from typing import Dict

logger = logging.getLogger("CampaignTasks")

# campaign_id → asyncio.Task
_tasks: Dict[str, asyncio.Task] = {}


# ── Public API ────────────────────────────────────────────────────────────────

async def start_campaign_task(campaign_id: str):
    """
    Launch (or re-launch) the sequence task for a campaign.
    Cancels any existing task first to avoid double-sends.
    """
    cancel_campaign_task(campaign_id)
    coro = _sequence(campaign_id)
    task = asyncio.create_task(coro, name=f"campaign-{campaign_id}")
    _tasks[campaign_id] = task
    logger.info(f"Task started for campaign {campaign_id}")
    return task


def cancel_campaign_task(campaign_id: str):
    """Cancel a running sequence task (used on Pause)."""
    task = _tasks.get(campaign_id)
    if task and not task.done():
        task.cancel()
        logger.info(f"Task cancelled for campaign {campaign_id}")


def is_running(campaign_id: str) -> bool:
    task = _tasks.get(campaign_id)
    return bool(task and not task.done())


def running_campaigns() -> list:
    return [cid for cid, t in _tasks.items() if not t.done()]


# ── Sequence coroutine ────────────────────────────────────────────────────────

async def _sequence(campaign_id: str):
    """
    Full 3-step campaign sequence.

    For each step:
      1. Check all active contacts for replies → stop automation for those who replied
      2. Send the step message to each active contact
         with a random 5–6 minute gap between each lead
      3. After all leads for this step are messaged, sleep the campaign delay
         (e.g. 1 day) before moving to the next step

    The inter-lead gap (5-6 min) and inter-step delay are real asyncio sleeps —
    no external scheduler involved.
    """
    from database.campaign_store import (
        get_campaign, get_contacts_for_campaign, update_campaign
    )
    from agents.reply_checker import ReplyChecker
    from agents.campaign_runner import CampaignRunner

    checker = ReplyChecker()
    runner  = CampaignRunner()

    try:
        # Find the lowest step any active contact still needs — skip already-done steps
        all_contacts = get_contacts_for_campaign(campaign_id)
        active_contacts = [c for c in all_contacts if c["status"] == "active"]
        start_step = min((c["current_step"] for c in active_contacts), default=1)

        for step in range(start_step, 4):

            # ── Fetch campaign (status may have changed) ──────────────────
            campaign = get_campaign(campaign_id)
            if not campaign or campaign["status"] != "active":
                logger.info(f"[{campaign_id}] Not active at step {step} — stopping")
                return

            # ── Check for replies before sending ─────────────────────────
            try:
                checker.run({"campaign_id": campaign_id})
            except Exception as e:
                logger.error(f"[{campaign_id}] Reply check error: {e}")

            # ── Get contacts due for this step ────────────────────────────
            contacts = [
                c for c in get_contacts_for_campaign(campaign_id)
                if c["status"] == "active" and c["current_step"] == step
            ]

            logger.info(
                f"[{campaign_id}] Step {step}: {len(contacts)} contact(s) to message"
            )

            # ── Send to each contact with 5–6 min random gap between leads ─
            for i, contact in enumerate(contacts):

                # Re-check campaign not paused mid-send
                campaign = get_campaign(campaign_id)
                if not campaign or campaign["status"] != "active":
                    logger.info(f"[{campaign_id}] Campaign paused mid-step {step}")
                    return

                # Send (sync call, run in thread so we don't block event loop)
                try:
                    await asyncio.to_thread(runner._send_step, campaign, contact)
                except Exception as e:
                    logger.error(
                        f"[{campaign_id}] Send failed for {contact['phone_number']}: {e}"
                    )

                # 5–6 min random gap before the NEXT lead (skip after last one)
                if i < len(contacts) - 1:
                    gap = random.uniform(300, 360)
                    logger.info(
                        f"[{campaign_id}] Waiting {gap:.0f}s before next lead "
                        f"({i + 2}/{len(contacts)})"
                    )
                    await asyncio.sleep(gap)

            # ── Wait campaign delay before the next step ──────────────────
            # Only sleep if we actually sent messages in this step.
            # During the wait, check for replies every 15 minutes so the
            # dashboard reflects incoming replies in near-real-time.
            if step < 3 and contacts:
                campaign = get_campaign(campaign_id)
                delay_secs = (
                    campaign.get("delay_days", 0) * 86400
                    + campaign.get("delay_hours", 0) * 3600
                    + campaign.get("delay_minutes", 0) * 60
                )
                if delay_secs > 0:
                    logger.info(
                        f"[{campaign_id}] Step {step} done. "
                        f"Waiting {delay_secs}s before step {step + 1} "
                        f"(reply check every 15 min)"
                    )
                    REPLY_CHECK_INTERVAL = 120  # check every 2 minutes
                    elapsed = 0
                    while elapsed < delay_secs:
                        chunk = min(REPLY_CHECK_INTERVAL, delay_secs - elapsed)
                        await asyncio.sleep(chunk)
                        elapsed += chunk

                        # Check for replies mid-wait
                        campaign = get_campaign(campaign_id)
                        if not campaign or campaign["status"] != "active":
                            logger.info(f"[{campaign_id}] Campaign paused during wait")
                            return
                        try:
                            result = checker.run({"campaign_id": campaign_id})
                            if result.get("replied_count", 0) > 0:
                                logger.info(
                                    f"[{campaign_id}] {result['replied_count']} new reply/replies detected mid-wait"
                                )
                        except Exception as e:
                            logger.error(f"[{campaign_id}] Mid-wait reply check error: {e}")

        # ── All 3 steps complete ──────────────────────────────────────────
        update_campaign(campaign_id, {"status": "completed"})
        logger.info(f"[{campaign_id}] All steps completed — campaign marked done")

    except asyncio.CancelledError:
        logger.info(f"[{campaign_id}] Task cancelled (campaign paused/stopped)")
    except Exception as e:
        logger.error(f"[{campaign_id}] Unexpected error in sequence: {e}")
