"""API routes for telemetry start/stop controls."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.base import get_db
from ..db.crud import session_crud, device_profile_crud
from ..services.manager import ServiceManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

# Global service manager instance
service_manager: Optional[ServiceManager] = None


class TelemetryStartRequest(BaseModel):
    """Telemetry start request model."""
    profile_id: Optional[int] = None
    session_name: Optional[str] = None


class TelemetryStartResponse(BaseModel):
    """Telemetry start response model."""
    success: bool
    session_id: int
    session_name: str
    profile_id: Optional[int] = None
    message: str


class TelemetryStopResponse(BaseModel):
    """Telemetry stop response model."""
    success: bool
    session_id: Optional[int] = None
    message: str


class TelemetryStatusResponse(BaseModel):
    """Telemetry status response model."""
    is_running: bool
    session_id: Optional[int] = None
    session_name: Optional[str] = None
    profile_id: Optional[int] = None
    start_time: Optional[str] = None
    elapsed_seconds: Optional[int] = None


def get_service_manager() -> ServiceManager:
    """Get or create service manager instance."""
    global service_manager
    if service_manager is None:
        service_manager = ServiceManager()
    return service_manager


@router.post("/start", response_model=TelemetryStartResponse)
async def start_telemetry(
    request: TelemetryStartRequest,
    db: AsyncSession = Depends(get_db)
) -> TelemetryStartResponse:
    """Start telemetry logging with a new session.
    
    Args:
        request: Start request with optional profile_id and session_name.
        db: Database session.
        
    Returns:
        TelemetryStartResponse: Session details and status.
        
    Raises:
        HTTPException: If telemetry is already running or start fails.
    """
    try:
        manager = get_service_manager()
        
        # Check if telemetry is already running
        if manager.is_running():
            raise HTTPException(
                status_code=400,
                detail="Telemetry is already running. Stop current session before starting a new one."
            )
        
        # Get default profile if none specified
        profile_id = request.profile_id
        if profile_id is None:
            default_profile = await device_profile_crud.get_default(db)
            if default_profile:
                profile_id = default_profile.id
            else:
                raise HTTPException(
                    status_code=400,
                    detail="No profile specified and no default profile found. Please create a device profile first."
                )
        
        # Create session name if not provided
        session_name = request.session_name
        if not session_name:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            session_name = f"Telemetry Session {timestamp}"
        
        # Create new session
        session = await session_crud.create(
            db=db,
            name=session_name,
            car_id=None,
            driver=None,
            track=None
        )
        
        # Start services with the session
        await manager.start_session(session.id, profile_id, db)
        
        logger.info(f"Telemetry started - Session ID: {session.id}, Profile ID: {profile_id}")
        
        return TelemetryStartResponse(
            success=True,
            session_id=session.id,
            session_name=session.name,
            profile_id=profile_id,
            message=f"Telemetry started successfully with session '{session.name}'"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting telemetry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start telemetry: {str(e)}")


@router.post("/stop", response_model=TelemetryStopResponse)
async def stop_telemetry() -> TelemetryStopResponse:
    """Stop telemetry logging and shutdown services.
    
    Returns:
        TelemetryStopResponse: Stop status and session details.
        
    Raises:
        HTTPException: If telemetry is not running or stop fails.
    """
    try:
        manager = get_service_manager()
        
        # Check if telemetry is running
        if not manager.is_running():
            raise HTTPException(
                status_code=400,
                detail="Telemetry is not currently running."
            )
        
        # Get current session ID before stopping
        current_session_id = manager.get_current_session_id()
        
        # Stop services
        await manager.stop_session()
        
        logger.info(f"Telemetry stopped - Session ID: {current_session_id}")
        
        return TelemetryStopResponse(
            success=True,
            session_id=current_session_id,
            message=f"Telemetry stopped successfully. Session {current_session_id} ended."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping telemetry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop telemetry: {str(e)}")


@router.get("/status", response_model=TelemetryStatusResponse)
async def get_telemetry_status(
    db: AsyncSession = Depends(get_db)
) -> TelemetryStatusResponse:
    """Get current telemetry status.
    
    Args:
        db: Database session.
        
    Returns:
        TelemetryStatusResponse: Current telemetry status and session details.
    """
    try:
        manager = get_service_manager()
        
        is_running = manager.is_running()
        session_id = manager.get_current_session_id() if is_running else None
        
        # Get session details if running
        session_name = None
        profile_id = None
        start_time = None
        elapsed_seconds = None
        
        if is_running and session_id:
            session = await session_crud.get_by_id(db, session_id)
            if session:
                session_name = session.name
                profile_id = getattr(session, 'profile_id', None)
                start_time = session.created_at.isoformat()
                
                # Calculate elapsed time
                if session.created_at:
                    elapsed = datetime.now(timezone.utc) - session.created_at
                    elapsed_seconds = int(elapsed.total_seconds())
        
        return TelemetryStatusResponse(
            is_running=is_running,
            session_id=session_id,
            session_name=session_name,
            profile_id=profile_id,
            start_time=start_time,
            elapsed_seconds=elapsed_seconds
        )
        
    except Exception as e:
        logger.error(f"Error getting telemetry status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get telemetry status: {str(e)}")
