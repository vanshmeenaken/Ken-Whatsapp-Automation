"""
Periskope WhatsApp Automation - FastAPI Application
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config.settings import settings
from api.routes import router as api_router
from api.campaign_routes import router as campaign_router

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Periskope WhatsApp Automation Starting")
    logger.info("=" * 60)
    logger.info(f"Environment : {settings.API_ENV}")
    settings.validate()
    os.makedirs("./data", exist_ok=True)

    # Re-launch async tasks for any campaigns that were active before restart
    from database.campaign_store import list_campaigns
    from utils.campaign_tasks import start_campaign_task
    active = [c for c in list_campaigns() if c["status"] == "active"]
    for campaign in active:
        await start_campaign_task(campaign["id"])
        logger.info(f"Resumed campaign task: '{campaign['name']}'")

    logger.info("Startup complete. Server ready.")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Periskope WhatsApp Automation",
    description="Send WhatsApp messages at scale via Periskope API",
    version="2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api", tags=["Messages"])
app.include_router(campaign_router, prefix="/api")

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", tags=["Dashboard"])
async def dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/api/health", tags=["Health"])
async def health():
    from utils.campaign_tasks import running_campaigns
    return {
        "status": "ok",
        "version": "2.0",
        "environment": settings.API_ENV,
        "periskope_configured": bool(settings.PERISKOPE_API_KEY and settings.PERISKOPE_ORG_PHONE),
        "active_campaign_tasks": running_campaigns(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=settings.API_ENV == "development",
    )
