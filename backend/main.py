"""
Main entry point for the BBAC Simulator FastAPI application.
Configures the app, registers routers, sets up CORS, and manages the lifecycle
of background tasks (Telemetry Generator and Analytics Engine).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from config import settings
from database.connection import init_db, close_db, AsyncSessionLocal
from database.models import User
from api.routes import dashboard, users, logs, policies, simulation
from api.routes.auth import router as auth_router
from api.routes.user_actions import router as user_actions_router
from api import websocket as websocket_module
from modules.telemetry.generator import generator
from modules.analytics.engine import analytics_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def seed_initial_users() -> None:
    """
    Ensures the two hardcoded accounts (admin + user) exist as real User
    records in the database so user_actions routes can look them up by
    username from the JWT token.

    Called after init_db() so tables are guaranteed to exist.
    Uses INSERT-if-not-exists logic — safe to call on every startup.
    """
    async with AsyncSessionLocal() as session:
        # Admin account
        result = await session.execute(
            select(User).where(User.username == settings.ADMIN_USERNAME)
        )
        if not result.scalar_one_or_none():
            session.add(User(
                username=settings.ADMIN_USERNAME,
                email="admin@bbac-simulator.local",
                role="admin",
            ))
            logger.info("Seeded admin user: %s", settings.ADMIN_USERNAME)

        # Regular user account
        result = await session.execute(
            select(User).where(User.username == settings.USER_USERNAME)
        )
        if not result.scalar_one_or_none():
            session.add(User(
                username=settings.USER_USERNAME,
                email="user@bbac-simulator.local",
                role="user",
            ))
            logger.info("Seeded regular user: %s", settings.USER_USERNAME)

        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan — runs once at startup and once at shutdown.
    """
    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------
    logger.info("Starting BBAC Simulator Backend...")

    # 1. Create all tables if they don't exist yet (idempotent)
    await init_db()
    logger.info("Database tables verified/created.")

    # 2. Seed the two hardcoded user accounts AFTER tables exist
    try:
        await seed_initial_users()
        logger.info("Initial users verified/seeded.")
    except Exception:
        logger.exception("Failed to seed initial users — check DB connection.")

    # 3. Wire the pipeline together
    #    Without these two lines: logs are never scored and nothing is
    #    ever broadcast to the dashboard WebSocket stream.
    generator.set_on_log_created(analytics_engine.process_log)
    analytics_engine.set_broadcast_callback(websocket_module.manager.broadcast)
    logger.info("Generator -> Analytics Engine -> WebSocket pipeline wired.")

    # 4. Pre-train the ML model on any existing historical data
    await analytics_engine.initialize()

    # Note: generator and analytics_engine are NOT auto-started here.
    # The admin controls both via POST /api/simulation/start from the dashboard.

    yield

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    logger.info("Shutting down BBAC Simulator Backend...")
    generator.stop()
    analytics_engine.stop()
    await close_db()
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="BBAC Simulator API",
    description="Behavioral-Based Access Control Simulator Backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

# Auth — must be registered first so /api/auth/login is available before
# any protected route is called
app.include_router(auth_router,         prefix="/api")
app.include_router(user_actions_router, prefix="/api")

# Existing routes
app.include_router(dashboard.router,    prefix="/api")
app.include_router(users.router,        prefix="/api")
app.include_router(logs.router,         prefix="/api")
app.include_router(policies.router,     prefix="/api")
app.include_router(simulation.router,   prefix="/api")

# WebSocket — defined in api/websocket.py as /ws/stream
# Not redefined here; the router keeps connect/disconnect/receive
# logic in exactly one place with correct async handling.
app.include_router(websocket_module.router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint for uptime monitoring."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "generator_running": generator.is_running,
        "analytics_running": analytics_engine.is_running,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )