"""
German Rental Contract Review API
Main application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.dependencies import get_db
from core.logging import setup_logging, get_logger
from database.connection import create_tables
from routers.legal_kb import router as legal_kb_router
from routers.contracts import router as contracts_router

# Setup centralized logging
setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
)


@app.on_event("startup")
async def startup_event():
    """Create database tables on startup."""
    logger.info("Starting up %s", settings.APP_TITLE)
    create_tables()
    logger.info("Database tables initialized")


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
