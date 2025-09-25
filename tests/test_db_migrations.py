"""Tests for database migrations and models."""

import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.db.crud import frame_crud, session_crud, signal_crud
from backend.app.db.models import Frame, Session, Signal


@pytest.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an in-memory SQLite database session for testing.
    
    Yields:
        AsyncSession: Database session for testing.
    """
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Create async engine for in-memory SQLite
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            echo=False,
        )
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session factory
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Create session
        async with async_session() as session:
            yield session
        
    finally:
        # Clean up
        await engine.dispose()
        Path(db_path).unlink(missing_ok=True)


class TestDatabaseMigrations:
    """Test database migrations and table creation."""
    
    async def test_tables_created(self, async_db_session: AsyncSession) -> None:
        """Test that all tables are created by attempting to insert data."""
        # Test sessions table
        session = await session_crud.create(
            db=async_db_session,
            name="Migration Test Session",
        )
        assert session.id is not None
        
        # Test signals table
        signals_data = [
            {
                "session_id": session.id,
                "source": "test",
                "channel": "test_channel",
                "ts_utc": datetime.now(timezone.utc),
                "ts_mono_ns": 1000000000,
                "value_num": 42.0,
                "unit": "test_unit",
            }
        ]
        signals = await signal_crud.create_batch(async_db_session, signals_data)
        assert len(signals) == 1
        assert signals[0].id is not None
        
        # Test frames table
        frames_data = [
            {
                "session_id": session.id,
                "ts_utc": datetime.now(timezone.utc),
                "ts_mono_ns": 1000000000,
                "payload_json": json.dumps({"test": "data"}),
            }
        ]
        frames = await frame_crud.create_batch(async_db_session, frames_data)
        assert len(frames) == 1
        assert frames[0].id is not None
    
    async def test_migration_applies_successfully(self, async_db_session: AsyncSession) -> None:
        """Test that migrations apply successfully by creating and querying data."""
        # Create a complete test scenario
        session = await session_crud.create(
            db=async_db_session,
            name="Migration Test",
            car_id="TEST001",
            driver="Test Driver",
            track="Test Track",
        )
        
        # Create multiple signals
        signals_data = [
            {
                "session_id": session.id,
                "source": "obd",
                "channel": f"channel_{i}",
                "ts_utc": datetime.now(timezone.utc),
                "ts_mono_ns": 1000000000 + i * 100000000,
                "value_num": float(i),
                "unit": "test",
            }
            for i in range(3)
        ]
        await signal_crud.create_batch(async_db_session, signals_data)
        
        # Create frames
        frames_data = [
            {
                "session_id": session.id,
                "ts_utc": datetime.now(timezone.utc),
                "ts_mono_ns": 1000000000 + i * 1000000000,
                "payload_json": json.dumps({"frame": i}),
            }
            for i in range(2)
        ]
        await frame_crud.create_batch(async_db_session, frames_data)
        
        # Verify data can be retrieved
        retrieved_session = await session_crud.get_by_id(async_db_session, session.id)
        assert retrieved_session is not None
        assert retrieved_session.name == "Migration Test"
        
        session_signals = await signal_crud.get_by_session(async_db_session, session.id)
        assert len(session_signals) == 3
        
        session_frames = await frame_crud.get_by_session(async_db_session, session.id)
        assert len(session_frames) == 2


class TestCRUDOperations:
    """Test CRUD operations with the database models."""
    
    async def test_session_crud(self, async_db_session: AsyncSession) -> None:
        """Test session CRUD operations."""
        # Create session
        session = await session_crud.create(
            db=async_db_session,
            name="Test Session",
            car_id="CAR001",
            driver="Test Driver",
            track="Test Track",
            notes="Test notes",
        )
        
        assert session.id is not None
        assert session.name == "Test Session"
        assert session.car_id == "CAR001"
        assert session.driver == "Test Driver"
        assert session.track == "Test Track"
        assert session.notes == "Test notes"
        assert session.created_utc is not None
        
        # Get session by ID
        retrieved_session = await session_crud.get_by_id(async_db_session, session.id)
        assert retrieved_session is not None
        assert retrieved_session.name == "Test Session"
        
        # Get all sessions
        all_sessions = await session_crud.get_all(async_db_session)
        assert len(all_sessions) == 1
        assert all_sessions[0].id == session.id
    
    async def test_signal_crud_batch(self, async_db_session: AsyncSession) -> None:
        """Test signal batch CRUD operations."""
        # Create a session first
        session = await session_crud.create(
            db=async_db_session,
            name="Signal Test Session",
        )
        
        # Create batch of signals
        now = datetime.now(timezone.utc)
        signals_data = [
            {
                "session_id": session.id,
                "source": "obd",
                "channel": "speed",
                "ts_utc": now,
                "ts_mono_ns": 1000000000 + i * 100000000,  # 1 second intervals
                "value_num": 60.0 + i * 5.0,
                "unit": "kph",
                "quality": "good",
            }
            for i in range(5)
        ]
        
        created_signals = await signal_crud.create_batch(async_db_session, signals_data)
        
        assert len(created_signals) == 5
        for i, signal in enumerate(created_signals):
            assert signal.id is not None
            assert signal.session_id == session.id
            assert signal.source == "obd"
            assert signal.channel == "speed"
            assert signal.value_num == 60.0 + i * 5.0
            assert signal.unit == "kph"
            assert signal.quality == "good"
        
        # Get signals by session
        session_signals = await signal_crud.get_by_session(async_db_session, session.id)
        assert len(session_signals) == 5
        
        # Get signals by source and channel
        speed_signals = await signal_crud.get_by_source_channel(
            async_db_session, session.id, "obd", "speed"
        )
        assert len(speed_signals) == 5
    
    async def test_frame_crud_batch(self, async_db_session: AsyncSession) -> None:
        """Test frame batch CRUD operations."""
        # Create a session first
        session = await session_crud.create(
            db=async_db_session,
            name="Frame Test Session",
        )
        
        # Create batch of frames
        now = datetime.now(timezone.utc)
        frames_data = [
            {
                "session_id": session.id,
                "ts_utc": now,
                "ts_mono_ns": 1000000000 + i * 1000000000,  # 1 second intervals
                "payload_json": json.dumps({
                    "speed": 60.0 + i * 5.0,
                    "rpm": 2000 + i * 100,
                    "throttle": 0.5 + i * 0.1,
                }),
            }
            for i in range(3)
        ]
        
        created_frames = await frame_crud.create_batch(async_db_session, frames_data)
        
        assert len(created_frames) == 3
        for i, frame in enumerate(created_frames):
            assert frame.id is not None
            assert frame.session_id == session.id
            # SQLite stores datetimes without timezone info, so compare without tzinfo
            assert frame.ts_utc.replace(tzinfo=None) == now.replace(tzinfo=None)
            
            # Verify payload can be parsed
            payload = json.loads(frame.payload_json)
            assert payload["speed"] == 60.0 + i * 5.0
            assert payload["rpm"] == 2000 + i * 100
            assert payload["throttle"] == 0.5 + i * 0.1
        
        # Get frames by session
        session_frames = await frame_crud.get_by_session(async_db_session, session.id)
        assert len(session_frames) == 3
    
    async def test_relationships(self, async_db_session: AsyncSession) -> None:
        """Test model relationships."""
        # Create session with related data
        session = await session_crud.create(
            db=async_db_session,
            name="Relationship Test Session",
        )
        
        # Create signals
        signals_data = [
            {
                "session_id": session.id,
                "source": "gps",
                "channel": "latitude",
                "ts_utc": datetime.now(timezone.utc),
                "ts_mono_ns": 1000000000,
                "value_num": 37.7749,
                "unit": "degrees",
            }
        ]
        await signal_crud.create_batch(async_db_session, signals_data)
        
        # Create frames
        frames_data = [
            {
                "session_id": session.id,
                "ts_utc": datetime.now(timezone.utc),
                "ts_mono_ns": 1000000000,
                "payload_json": json.dumps({"lat": 37.7749, "lon": -122.4194}),
            }
        ]
        await frame_crud.create_batch(async_db_session, frames_data)
        
        # Test relationships by loading session with related data
        from sqlalchemy.orm import selectinload
        
        result = await async_db_session.execute(
            select(Session)
            .options(selectinload(Session.signals), selectinload(Session.frames))
            .where(Session.id == session.id)
        )
        loaded_session = result.scalar_one()
        
        assert len(loaded_session.signals) == 1
        assert loaded_session.signals[0].source == "gps"
        assert loaded_session.signals[0].channel == "latitude"
        
        assert len(loaded_session.frames) == 1
        payload = json.loads(loaded_session.frames[0].payload_json)
        assert payload["lat"] == 37.7749
        assert payload["lon"] == -122.4194


# Pytest configuration for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
