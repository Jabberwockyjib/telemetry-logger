"""CRUD operations for database models."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Frame, Session, Signal


class SessionCRUD:
    """CRUD operations for Session model."""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        name: str,
        car_id: Optional[str] = None,
        driver: Optional[str] = None,
        track: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Session:
        """Create a new session.
        
        Args:
            db: Database session.
            name: Session name.
            car_id: Vehicle identifier.
            driver: Driver name.
            track: Track name.
            notes: Optional notes.
            
        Returns:
            Session: Created session instance.
        """
        session = Session(
            name=name,
            car_id=car_id,
            driver=driver,
            track=track,
            created_utc=datetime.now(timezone.utc),
            notes=notes,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session
    
    @staticmethod
    async def get_by_id(db: AsyncSession, session_id: int) -> Optional[Session]:
        """Get session by ID.
        
        Args:
            db: Database session.
            session_id: Session ID.
            
        Returns:
            Optional[Session]: Session instance or None.
        """
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all(db: AsyncSession, limit: int = 100, offset: int = 0) -> List[Session]:
        """Get all sessions with pagination.
        
        Args:
            db: Database session.
            limit: Maximum number of sessions to return.
            offset: Number of sessions to skip.
            
        Returns:
            List[Session]: List of session instances.
        """
        result = await db.execute(
            select(Session)
            .order_by(Session.created_utc.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()


class SignalCRUD:
    """CRUD operations for Signal model."""
    
    @staticmethod
    async def create_batch(
        db: AsyncSession,
        signals: List[Dict[str, Any]],
    ) -> List[Signal]:
        """Create multiple signals in a batch operation.
        
        Args:
            db: Database session.
            signals: List of signal data dictionaries.
            
        Returns:
            List[Signal]: List of created signal instances.
        """
        signal_objects = [
            Signal(
                session_id=signal["session_id"],
                source=signal["source"],
                channel=signal["channel"],
                ts_utc=signal["ts_utc"],
                ts_mono_ns=signal["ts_mono_ns"],
                value_num=signal.get("value_num"),
                value_text=signal.get("value_text"),
                unit=signal.get("unit"),
                quality=signal.get("quality"),
            )
            for signal in signals
        ]
        
        db.add_all(signal_objects)
        await db.commit()
        
        # Refresh all objects to get their IDs
        for signal in signal_objects:
            await db.refresh(signal)
        
        return signal_objects
    
    @staticmethod
    async def get_by_session(
        db: AsyncSession,
        session_id: int,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Signal]:
        """Get signals by session ID.
        
        Args:
            db: Database session.
            session_id: Session ID.
            limit: Maximum number of signals to return.
            offset: Number of signals to skip.
            
        Returns:
            List[Signal]: List of signal instances.
        """
        result = await db.execute(
            select(Signal)
            .where(Signal.session_id == session_id)
            .order_by(Signal.ts_mono_ns)
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_by_source_channel(
        db: AsyncSession,
        session_id: int,
        source: str,
        channel: str,
        limit: int = 1000,
    ) -> List[Signal]:
        """Get signals by source and channel.
        
        Args:
            db: Database session.
            session_id: Session ID.
            source: Signal source.
            channel: Signal channel.
            limit: Maximum number of signals to return.
            
        Returns:
            List[Signal]: List of signal instances.
        """
        result = await db.execute(
            select(Signal)
            .where(
                Signal.session_id == session_id,
                Signal.source == source,
                Signal.channel == channel,
            )
            .order_by(Signal.ts_mono_ns)
            .limit(limit)
        )
        return result.scalars().all()


class FrameCRUD:
    """CRUD operations for Frame model."""
    
    @staticmethod
    async def create_batch(
        db: AsyncSession,
        frames: List[Dict[str, Any]],
    ) -> List[Frame]:
        """Create multiple frames in a batch operation.
        
        Args:
            db: Database session.
            frames: List of frame data dictionaries.
            
        Returns:
            List[Frame]: List of created frame instances.
        """
        frame_objects = [
            Frame(
                session_id=frame["session_id"],
                ts_utc=frame["ts_utc"],
                ts_mono_ns=frame["ts_mono_ns"],
                payload_json=frame["payload_json"],
            )
            for frame in frames
        ]
        
        db.add_all(frame_objects)
        await db.commit()
        
        # Refresh all objects to get their IDs
        for frame in frame_objects:
            await db.refresh(frame)
        
        return frame_objects
    
    @staticmethod
    async def get_by_session(
        db: AsyncSession,
        session_id: int,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Frame]:
        """Get frames by session ID.
        
        Args:
            db: Database session.
            session_id: Session ID.
            limit: Maximum number of frames to return.
            offset: Number of frames to skip.
            
        Returns:
            List[Frame]: List of frame instances.
        """
        result = await db.execute(
            select(Frame)
            .where(Frame.session_id == session_id)
            .order_by(Frame.ts_mono_ns)
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()


# Convenience instances
session_crud = SessionCRUD()
signal_crud = SignalCRUD()
frame_crud = FrameCRUD()
