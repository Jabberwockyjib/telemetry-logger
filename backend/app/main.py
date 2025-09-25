"""FastAPI app factory and main application setup."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes_health import router as health_router
from .api.routes_sessions import router as sessions_router
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.
    
    Args:
        app: FastAPI application instance.
        
    Yields:
        None: Application is running.
    """
    # Startup
    # TODO: Initialize database, services, etc.
    yield
    # Shutdown
    from .services.manager import service_manager
    await service_manager.shutdown()


def create_app() -> FastAPI:
    """Create and configure FastAPI application.
    
    Returns:
        FastAPI: Configured application instance.
    """
    app = FastAPI(
        title="Cartelem Telemetry API",
        description="Async telemetry data collection and streaming",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )
    
    # CORS middleware for development
    if settings.debug:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Mount API routes
    app.include_router(health_router, prefix="/api/v1", tags=["health"])
    app.include_router(sessions_router, prefix="/api/v1", tags=["sessions"])
    
    return app


# Create app instance
app = create_app()
