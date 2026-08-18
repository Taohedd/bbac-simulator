"""
Database connection management for the BBAC Simulator.
Sets up the async SQLAlchemy engine, session factory, declarative Base,
and provides the FastAPI dependency for injecting DB sessions into routes.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import settings


# ---------------------------------------------------------------------------
# Async Engine
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,   # Logs all SQL statements when DEBUG=True in .env
    future=True,
    pool_pre_ping=True,    # Verifies connections before use, drops stale ones
    pool_size=10,
    max_overflow=20,
)


# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevents lazy-load errors after commit in async context
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Declarative Base
# Import this in database/models.py to define all ORM table models.
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    All model classes in models.py must subclass this.
    """
    pass


# ---------------------------------------------------------------------------
# Lifecycle Helpers — called by main.py startup/shutdown events
# ---------------------------------------------------------------------------
async def init_db() -> None:
    """
    Creates all tables defined on Base.metadata on application startup.
    Called once in main.py's lifespan startup event.

    Note: For production use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Disposes the connection pool cleanly on application shutdown.
    Prevents asyncpg 'connection closed mid-transaction' warnings.
    Called in main.py's lifespan shutdown event.
    """
    await engine.dispose()


# ---------------------------------------------------------------------------
# FastAPI Dependency — inject into routes with Depends(get_db)
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an async database session for use in FastAPI route handlers.
    Automatically rolls back on any unhandled exception and always
    closes the session when the request completes.

    Usage:
        @router.get("/example")
        async def example_route(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()