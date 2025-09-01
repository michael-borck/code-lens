"""
FastAPI application entry point
"""

from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from codelens.api.routes import analysis, reports, rubrics
from codelens.core.config import settings
from codelens.db.database import init_db

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def create_app() -> FastAPI:
    """Create FastAPI application"""

    app = FastAPI(
        title=settings.app_name,
        description="Automated Code Analysis & Grading Assistant for Educators",
        version=settings.version,
        debug=settings.debug,
        openapi_url=f"{settings.api_prefix}/openapi.json" if settings.debug else None,
        docs_url=f"{settings.api_prefix}/docs" if settings.debug else None,
        redoc_url=f"{settings.api_prefix}/redoc" if settings.debug else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(
        analysis.router,
        prefix=f"{settings.api_prefix}/analyze",
        tags=["analysis"]
    )
    app.include_router(
        rubrics.router,
        prefix=f"{settings.api_prefix}/rubrics",
        tags=["rubrics"]
    )
    app.include_router(
        reports.router,
        prefix=f"{settings.api_prefix}/reports",
        tags=["reports"]
    )

    @app.on_event("startup")
    async def startup_event() -> None:
        """Initialize application on startup"""
        logger.info("Starting CodeLens application")
        await init_db()
        logger.info("Database initialized")

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """Cleanup on shutdown"""
        logger.info("Shutting down CodeLens application")

    @app.get("/health")
    async def health_check() -> dict[str, Any]:
        """Health check endpoint"""
        return {
            "status": "healthy",
            "version": settings.version,
            "app": settings.app_name
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "codelens.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_config=None,  # Use structlog configuration
    )
