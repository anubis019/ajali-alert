from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import async_session, init_db
from app.escalator import check_escalations, auto_resolve_old_alerts
from app.routers import alerts_router, auth_router as user_router, dashboard_router, teams_router, policies_router
from app.routers.auth_router import auth_router
from app.websocket_manager import ws_router

logger = logging.getLogger("ajali")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables + seed; Background: escalation loop."""
    await init_db()
    from app.seed import seed
    await seed()

    # Escalation background task
    async def escalation_loop():
        while True:
            try:
                async with async_session() as db:
                    escalated = await check_escalations(db)
                    auto_resolved = await auto_resolve_old_alerts(db)
                    if escalated or auto_resolved:
                        logger.info(
                            "Escalation cycle: escalated=%d auto_resolved=%d",
                            escalated, auto_resolved,
                        )
            except Exception:
                logger.exception("Escalation loop error")
            await asyncio.sleep(settings.ESCALATION_CHECK_INTERVAL)

    task = asyncio.create_task(escalation_loop())
    yield
    task.cancel()


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "🚨 **Ajali Alert System** — Kenya Emergency Response Platform\n\n"
        "Real-time emergency dispatch and response for:\n"
        "- 🚗 **Accidents** — Road traffic collisions, vehicle entrapment, pedestrian incidents\n"
        "- 🔥 **Fire** — Structural fires, vehicle fires, chemical spills, wildfire\n"
        "- 🏥 **Medical** — Cardiac events, maternity emergencies, drowning, trauma\n"
        "- 🛡️ **Security** — Armed robbery, home invasion, civil unrest, assaults\n\n"
        "Citizens report emergencies via USSD (*1233#), mobile app, SMS, or voice call.\n"
        "Dispatchers assign responders by type (Police, Ambulance, Fire Brigade, Community).\n"
        "Escalation enforces Golden Hour response targets.\n\n"
        "*Ajali* means *emergency/accident* in Swahili."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS — allow frontend and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router.router, prefix="/api/v1")
app.include_router(alerts_router.router, prefix="/api/v1")
app.include_router(dashboard_router.router, prefix="/api/v1")
app.include_router(teams_router.router, prefix="/api/v1")
app.include_router(policies_router.router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "operational",
        "system": "Ajali Alert System",
        "version": settings.APP_VERSION,
        "description": "Kenya Emergency Response Platform",
        "ussd_code": settings.USSD_CODE,
        "emergency_types": ["accident", "fire", "medical", "security"],
    }
