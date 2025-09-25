"""Health check API routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint.
    
    Returns:
        dict[str, str]: Status response with 'ok' status.
    """
    return {"status": "ok"}
