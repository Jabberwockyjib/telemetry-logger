"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SessionBase(BaseModel):
    """Base session schema with common fields."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Session name")
    car_id: Optional[str] = Field(None, max_length=100, description="Vehicle identifier")
    driver: Optional[str] = Field(None, max_length=100, description="Driver name")
    track: Optional[str] = Field(None, max_length=100, description="Track name")
    notes: Optional[str] = Field(None, description="Optional session notes")


class SessionCreate(SessionBase):
    """Schema for creating a new session."""
    pass


class SessionResponse(SessionBase):
    """Schema for session responses."""
    
    id: int = Field(..., description="Session ID")
    created_utc: datetime = Field(..., description="Session creation timestamp")
    is_active: bool = Field(False, description="Whether the session is currently active")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class SessionListResponse(BaseModel):
    """Schema for session list responses."""
    
    sessions: List[SessionResponse] = Field(..., description="List of sessions")
    total: int = Field(..., description="Total number of sessions")
    limit: int = Field(..., description="Number of sessions per page")
    offset: int = Field(..., description="Number of sessions skipped")


class SessionStartResponse(BaseModel):
    """Schema for session start responses."""
    
    session_id: int = Field(..., description="Session ID")
    status: str = Field(..., description="Start status")
    message: str = Field(..., description="Status message")
    started_at: datetime = Field(..., description="Session start timestamp")


class SessionStopResponse(BaseModel):
    """Schema for session stop responses."""
    
    session_id: int = Field(..., description="Session ID")
    status: str = Field(..., description="Stop status")
    message: str = Field(..., description="Status message")
    stopped_at: datetime = Field(..., description="Session stop timestamp")


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
