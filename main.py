#!/usr/bin/env python3
"""Simple runner for the FastAPI application."""

import uvicorn

from backend.app.config import settings


def main() -> None:
    """Run the FastAPI application."""
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
