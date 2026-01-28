"""Plex Dashboard API - Main FastAPI Application."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.database import async_session_maker, init_db, init_db_settings
from app.routers import auth, content, info, library, settings, sync, whitelist

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize database on startup."""
    await init_db_settings()  # Configure WAL mode before creating tables
    await init_db()
    yield


app = FastAPI(
    title="Plex Dashboard API",
    description="API for managing Plex/Jellyfin media server content",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://mediajanitor.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(content.router)
app.include_router(info.router)
app.include_router(library.router)
app.include_router(settings.router)
app.include_router(sync.router)
app.include_router(whitelist.router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Plex Dashboard API", "status": "running"}


async def check_database_health() -> tuple[bool, str]:
    """Check database connectivity by executing a simple query.

    Returns:
        Tuple of (is_healthy, status_message)
    """
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        return (True, "ok")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return (False, f"error: {e!s}")


async def check_redis_health() -> tuple[bool, str]:
    """Check Redis connectivity by sending a PING command.

    Returns:
        Tuple of (is_healthy, status_message)
    """
    app_settings = get_settings()
    redis_url = app_settings.redis_url

    if not redis_url:
        return (True, "not configured")

    try:
        client = aioredis.from_url(redis_url, socket_connect_timeout=5)  # type: ignore[no-untyped-call]
        try:
            await client.ping()
            return (True, "ok")
        finally:
            await client.aclose()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return (False, f"error: {e!s}")


@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint with dependency verification.

    Checks connectivity to:
    - Database (executes SELECT 1)
    - Redis (sends PING if configured)

    Returns 200 if all dependencies are healthy, 503 otherwise.
    """
    dependencies: dict[str, Any] = {}
    is_healthy = True

    # Check database
    db_healthy, db_status = await check_database_health()
    dependencies["database"] = db_status
    if not db_healthy:
        is_healthy = False

    # Check Redis
    redis_healthy, redis_status = await check_redis_health()
    dependencies["redis"] = redis_status
    if not redis_healthy:
        is_healthy = False

    response_data = {
        "status": "healthy" if is_healthy else "unhealthy",
        "dependencies": dependencies,
    }

    status_code = 200 if is_healthy else 503
    return JSONResponse(content=response_data, status_code=status_code)


@app.get("/api/hello")
async def hello() -> dict[str, str]:
    """Hello World endpoint - US-0.1."""
    return {"message": "Hello World again"}
