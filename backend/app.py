"""
German Rental Contract Review API
Main application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.dependencies import get_db
from core.exceptions import AppException
from core.logging import setup_logging, get_logger
from database.connection import create_tables
from fastapi import Request
from fastapi.responses import JSONResponse
from routers.legal_kb import router as legal_kb_router
from routers.contracts import router as contracts_router

from services.llm_judge import close_xai_async_client
from core.auth import close_polar_client

# Setup centralized logging
setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Modern FastAPI lifespan handler.
    """
    logger.info("Starting up %s", settings.APP_TITLE)

    auto_create = str(getattr(settings, "AUTO_CREATE_TABLES", "")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if auto_create:
        logger.warning(
            "AUTO_CREATE_TABLES is enabled — using legacy Base.metadata.create_all() path. "
            "This is a development escape hatch. Prefer running Alembic migrations instead."
        )
        create_tables()
        logger.info("Database tables initialized via create_all (legacy path)")
    else:
        logger.info(
            "AUTO_CREATE_TABLES is not set — assuming database schema was already "
            "initialized by Alembic migrations (docker-entrypoint.sh)."
        )

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down — closing shared async HTTP clients...")
    await close_xai_async_client()
    await close_polar_client()


app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)


# Public health endpoint (used by docker-compose healthcheck and orchestrators)
@app.get("/health", tags=["system"])
async def health_check():
    """Simple health check — does not require authentication."""
    return {
        "status": "healthy",
        "app": settings.APP_TITLE,
        "version": settings.APP_VERSION,
    }


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Return proper HTTP status for our custom exceptions (including auth errors from dependencies)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


# Include routers
app.include_router(legal_kb_router)
app.include_router(contracts_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)
