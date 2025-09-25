"""Session management API routes."""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.base import get_db
from ..db.crud import session_crud
from ..services.manager import service_manager
from ..utils.schemas import (
    ErrorResponse,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionStartResponse,
    SessionStopResponse,
)

router = APIRouter()


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=201,
    summary="Create a new session",
    description="Create a new telemetry data collection session.",
)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Create a new telemetry data collection session.
    
    Args:
        session_data: Session creation data.
        db: Database session dependency.
        
    Returns:
        SessionResponse: Created session information.
        
    Raises:
        HTTPException: If session creation fails.
    """
    try:
        session = await session_crud.create(
            db=db,
            name=session_data.name,
            car_id=session_data.car_id,
            driver=session_data.driver,
            track=session_data.track,
            notes=session_data.notes,
        )
        
        # Check if session is active (should be False for new sessions)
        is_active = await service_manager.is_session_active(session.id)
        
        return SessionResponse(
            id=session.id,
            name=session.name,
            car_id=session.car_id,
            driver=session.driver,
            track=session.track,
            created_utc=session.created_utc,
            notes=session.notes,
            is_active=is_active,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session: {str(e)}",
        )


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="List sessions",
    description="Get a paginated list of telemetry sessions.",
)
async def list_sessions(
    limit: int = Query(100, ge=1, le=1000, description="Number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    """Get a paginated list of telemetry sessions.
    
    Args:
        limit: Maximum number of sessions to return.
        offset: Number of sessions to skip.
        db: Database session dependency.
        
    Returns:
        SessionListResponse: Paginated list of sessions with metadata.
    """
    try:
        sessions = await session_crud.get_all(db=db, limit=limit, offset=offset)
        
        # Get active session IDs
        active_sessions = await service_manager.get_active_sessions()
        
        # Convert to response format with active status
        session_responses = []
        for session in sessions:
            is_active = session.id in active_sessions
            session_responses.append(
                SessionResponse(
                    id=session.id,
                    name=session.name,
                    car_id=session.car_id,
                    driver=session.driver,
                    track=session.track,
                    created_utc=session.created_utc,
                    notes=session.notes,
                    is_active=is_active,
                )
            )
        
        return SessionListResponse(
            sessions=session_responses,
            total=len(session_responses),  # TODO: Implement proper count query
            limit=limit,
            offset=offset,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sessions: {str(e)}",
        )


@router.post(
    "/sessions/{session_id}/start",
    response_model=SessionStartResponse,
    summary="Start session data collection",
    description="Start telemetry data collection services for a session.",
)
async def start_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
) -> SessionStartResponse:
    """Start telemetry data collection services for a session.
    
    Args:
        session_id: ID of the session to start.
        db: Database session dependency.
        
    Returns:
        SessionStartResponse: Session start status and information.
        
    Raises:
        HTTPException: If session not found or start fails.
    """
    try:
        # Verify session exists
        session = await session_crud.get_by_id(db=db, session_id=session_id)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found",
            )
        
        # Check if session is already active
        is_active = await service_manager.is_session_active(session_id)
        if is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Session {session_id} is already active",
            )
        
        # Start services
        success = await service_manager.start_session_services(session_id, db)
        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start services for session {session_id}",
            )
        
        return SessionStartResponse(
            session_id=session_id,
            status="started",
            message=f"Data collection started for session {session_id}",
            started_at=datetime.now(timezone.utc),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start session {session_id}: {str(e)}",
        )


@router.post(
    "/sessions/{session_id}/stop",
    response_model=SessionStopResponse,
    summary="Stop session data collection",
    description="Stop telemetry data collection services for a session.",
)
async def stop_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
) -> SessionStopResponse:
    """Stop telemetry data collection services for a session.
    
    Args:
        session_id: ID of the session to stop.
        db: Database session dependency.
        
    Returns:
        SessionStopResponse: Session stop status and information.
        
    Raises:
        HTTPException: If session not found or stop fails.
    """
    try:
        # Verify session exists
        session = await session_crud.get_by_id(db=db, session_id=session_id)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found",
            )
        
        # Check if session is active
        is_active = await service_manager.is_session_active(session_id)
        if not is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Session {session_id} is not active",
            )
        
        # Stop services
        success = await service_manager.stop_session_services(session_id)
        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to stop services for session {session_id}",
            )
        
        return SessionStopResponse(
            session_id=session_id,
            status="stopped",
            message=f"Data collection stopped for session {session_id}",
            stopped_at=datetime.now(timezone.utc),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop session {session_id}: {str(e)}",
        )
