"""FastAPI application factory for the AgentTrace Collector."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.middleware.logging import RequestLoggingMiddleware
from app.routes import agents, drift, health, spans, stats, traces

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan -- initialize database on startup."""
    await init_db()
    logger.info("AgentTrace Collector started")
    yield
    logger.info("AgentTrace Collector shutting down")


app = FastAPI(
    title="AgentTrace Collector",
    description="Receives and stores AI agent trace events",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Register routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(spans.router, prefix="/api/v1")
app.include_router(traces.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(drift.router, prefix="/api/v1")
