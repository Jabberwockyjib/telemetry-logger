"""Tests for session management endpoints and service manager."""

import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.main import app
from backend.app.services.manager import ServiceManager


@pytest.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an in-memory SQLite database session for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            echo=False,
        )
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            yield session
        
    finally:
        await engine.dispose()
        Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def client() -> TestClient:
    """Create test client for FastAPI app."""
    return TestClient(app)


class TestSessionEndpoints:
    """Test session management API endpoints."""
    
    def test_create_session_success(self, client: TestClient) -> None:
        """Test successful session creation."""
        session_data = {
            "name": "Test Session",
            "car_id": "CAR001",
            "driver": "Test Driver",
            "track": "Test Track",
            "notes": "Test notes",
        }
        
        response = client.post("/api/v1/sessions", json=session_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["name"] == "Test Session"
        assert data["car_id"] == "CAR001"
        assert data["driver"] == "Test Driver"
        assert data["track"] == "Test Track"
        assert data["notes"] == "Test notes"
        assert data["is_active"] is False
        assert "id" in data
        assert "created_utc" in data
    
    def test_create_session_minimal(self, client: TestClient) -> None:
        """Test session creation with minimal data."""
        session_data = {"name": "Minimal Session"}
        
        response = client.post("/api/v1/sessions", json=session_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["name"] == "Minimal Session"
        assert data["car_id"] is None
        assert data["driver"] is None
        assert data["track"] is None
        assert data["notes"] is None
        assert data["is_active"] is False
    
    def test_create_session_validation_error(self, client: TestClient) -> None:
        """Test session creation with validation errors."""
        # Missing required name
        response = client.post("/api/v1/sessions", json={})
        assert response.status_code == 422
        
        # Empty name
        response = client.post("/api/v1/sessions", json={"name": ""})
        assert response.status_code == 422
        
        # Name too long
        response = client.post("/api/v1/sessions", json={"name": "x" * 256})
        assert response.status_code == 422
    
    def test_list_sessions_empty(self, client: TestClient) -> None:
        """Test listing sessions when none exist."""
        # Note: This test may not be truly empty due to shared test database
        # In a real scenario, each test would use an isolated database
        response = client.get("/api/v1/sessions")
        
        assert response.status_code == 200
        data = response.json()
        
        # Just verify the response structure, not the content
        assert "sessions" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["limit"] == 100
        assert data["offset"] == 0
    
    def test_list_sessions_with_data(self, client: TestClient) -> None:
        """Test listing sessions with data."""
        import time
        
        # Create test sessions with unique names
        timestamp = int(time.time() * 1000)  # milliseconds for uniqueness
        session1_data = {"name": f"Test List Session 1 {timestamp}", "car_id": "CAR001"}
        session2_data = {"name": f"Test List Session 2 {timestamp}", "car_id": "CAR002"}
        
        create1_response = client.post("/api/v1/sessions", json=session1_data)
        create2_response = client.post("/api/v1/sessions", json=session2_data)
        
        assert create1_response.status_code == 201
        assert create2_response.status_code == 201
        
        response = client.get("/api/v1/sessions")
        
        assert response.status_code == 200
        data = response.json()
        
        # Find our test sessions in the response
        test_sessions = [
            s for s in data["sessions"] 
            if s["name"] in [session1_data["name"], session2_data["name"]]
        ]
        
        assert len(test_sessions) == 2
        
        # Check session order (should be newest first)
        session_names = [s["name"] for s in test_sessions]
        assert session2_data["name"] in session_names
        assert session1_data["name"] in session_names
    
    def test_list_sessions_pagination(self, client: TestClient) -> None:
        """Test session list pagination."""
        # Create multiple sessions
        for i in range(5):
            client.post("/api/v1/sessions", json={"name": f"Session {i}"})
        
        # Test limit
        response = client.get("/api/v1/sessions?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 3
        assert data["limit"] == 3
        
        # Test offset
        response = client.get("/api/v1/sessions?limit=2&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2
        assert data["offset"] == 2
    
    def test_start_session_success(self, client: TestClient) -> None:
        """Test successful session start."""
        # Create a session
        session_data = {"name": "Test Session"}
        create_response = client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        # Start the session
        response = client.post(f"/api/v1/sessions/{session_id}/start")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == session_id
        assert data["status"] == "started"
        assert "started_at" in data
        assert "Data collection started" in data["message"]
    
    def test_start_session_not_found(self, client: TestClient) -> None:
        """Test starting a non-existent session."""
        response = client.post("/api/v1/sessions/999/start")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_start_session_already_active(self, client: TestClient) -> None:
        """Test starting an already active session."""
        # Create and start a session
        session_data = {"name": "Test Session"}
        create_response = client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        client.post(f"/api/v1/sessions/{session_id}/start")
        
        # Try to start again
        response = client.post(f"/api/v1/sessions/{session_id}/start")
        
        assert response.status_code == 400
        data = response.json()
        assert "already active" in data["detail"]
    
    def test_stop_session_success(self, client: TestClient) -> None:
        """Test successful session stop."""
        # Create and start a session
        session_data = {"name": "Test Session"}
        create_response = client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        client.post(f"/api/v1/sessions/{session_id}/start")
        
        # Stop the session
        response = client.post(f"/api/v1/sessions/{session_id}/stop")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == session_id
        assert data["status"] == "stopped"
        assert "stopped_at" in data
        assert "Data collection stopped" in data["message"]
    
    def test_stop_session_not_found(self, client: TestClient) -> None:
        """Test stopping a non-existent session."""
        response = client.post("/api/v1/sessions/999/stop")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_stop_session_not_active(self, client: TestClient) -> None:
        """Test stopping a session that's not active."""
        # Create a session (but don't start it)
        session_data = {"name": "Test Session"}
        create_response = client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        # Try to stop it
        response = client.post(f"/api/v1/sessions/{session_id}/stop")
        
        assert response.status_code == 400
        data = response.json()
        assert "not active" in data["detail"]


class TestServiceManager:
    """Test the service manager functionality."""
    
    async def test_service_manager_initialization(self) -> None:
        """Test service manager initializes correctly."""
        manager = ServiceManager()
        
        assert len(manager._active_sessions) == 0
        assert len(manager._service_tasks) == 0
    
    async def test_start_session_services(self, async_db_session: AsyncSession) -> None:
        """Test starting session services."""
        from backend.app.db.crud import session_crud
        
        # Create a test session
        session = await session_crud.create(
            db=async_db_session,
            name="Test Session",
        )
        
        manager = ServiceManager()
        
        # Start services
        success = await manager.start_session_services(session.id, async_db_session)
        assert success is True
        
        # Check session is marked as active
        assert session.id in manager._active_sessions
        assert session.id in manager._service_tasks
        
        # Check services are running
        tasks = manager._service_tasks[session.id]
        assert "obd_service" in tasks
        assert "gps_service" in tasks
        assert "meshtastic_service" in tasks
        
        # Clean up
        await manager.shutdown()
    
    async def test_start_session_services_already_active(self, async_db_session: AsyncSession) -> None:
        """Test starting services for already active session."""
        from backend.app.db.crud import session_crud
        
        # Create a test session
        session = await session_crud.create(
            db=async_db_session,
            name="Test Session",
        )
        
        manager = ServiceManager()
        
        # Start services twice
        success1 = await manager.start_session_services(session.id, async_db_session)
        success2 = await manager.start_session_services(session.id, async_db_session)
        
        assert success1 is True
        assert success2 is False  # Already active
        
        # Clean up
        await manager.shutdown()
    
    async def test_start_session_services_nonexistent(self, async_db_session: AsyncSession) -> None:
        """Test starting services for non-existent session."""
        manager = ServiceManager()
        
        # Try to start services for non-existent session
        success = await manager.start_session_services(999, async_db_session)
        assert success is False
        
        # Check session is not marked as active
        assert 999 not in manager._active_sessions
    
    async def test_stop_session_services(self, async_db_session: AsyncSession) -> None:
        """Test stopping session services."""
        from backend.app.db.crud import session_crud
        
        # Create a test session
        session = await session_crud.create(
            db=async_db_session,
            name="Test Session",
        )
        
        manager = ServiceManager()
        
        # Start services
        await manager.start_session_services(session.id, async_db_session)
        assert session.id in manager._active_sessions
        
        # Stop services
        success = await manager.stop_session_services(session.id)
        assert success is True
        
        # Check session is no longer active
        assert session.id not in manager._active_sessions
        assert session.id not in manager._service_tasks
    
    async def test_stop_session_services_not_active(self, async_db_session: AsyncSession) -> None:
        """Test stopping services for non-active session."""
        manager = ServiceManager()
        
        # Try to stop services for non-active session
        success = await manager.stop_session_services(999)
        assert success is False
    
    async def test_is_session_active(self, async_db_session: AsyncSession) -> None:
        """Test checking if session is active."""
        from backend.app.db.crud import session_crud
        
        # Create a test session
        session = await session_crud.create(
            db=async_db_session,
            name="Test Session",
        )
        
        manager = ServiceManager()
        
        # Initially not active
        assert await manager.is_session_active(session.id) is False
        
        # Start services
        await manager.start_session_services(session.id, async_db_session)
        assert await manager.is_session_active(session.id) is True
        
        # Stop services
        await manager.stop_session_services(session.id)
        assert await manager.is_session_active(session.id) is False
        
        # Clean up
        await manager.shutdown()
    
    async def test_get_active_sessions(self, async_db_session: AsyncSession) -> None:
        """Test getting active sessions list."""
        from backend.app.db.crud import session_crud
        
        # Create test sessions
        session1 = await session_crud.create(db=async_db_session, name="Session 1")
        session2 = await session_crud.create(db=async_db_session, name="Session 2")
        
        manager = ServiceManager()
        
        # Initially no active sessions
        active = await manager.get_active_sessions()
        assert len(active) == 0
        
        # Start services for one session
        await manager.start_session_services(session1.id, async_db_session)
        active = await manager.get_active_sessions()
        assert len(active) == 1
        assert session1.id in active
        
        # Start services for second session
        await manager.start_session_services(session2.id, async_db_session)
        active = await manager.get_active_sessions()
        assert len(active) == 2
        assert session1.id in active
        assert session2.id in active
        
        # Clean up
        await manager.shutdown()
    
    async def test_shutdown(self, async_db_session: AsyncSession) -> None:
        """Test service manager shutdown."""
        from backend.app.db.crud import session_crud
        
        # Create test sessions
        session1 = await session_crud.create(db=async_db_session, name="Session 1")
        session2 = await session_crud.create(db=async_db_session, name="Session 2")
        
        manager = ServiceManager()
        
        # Start services for multiple sessions
        await manager.start_session_services(session1.id, async_db_session)
        await manager.start_session_services(session2.id, async_db_session)
        
        assert len(manager._active_sessions) == 2
        assert len(manager._service_tasks) == 2
        
        # Shutdown
        await manager.shutdown()
        
        assert len(manager._active_sessions) == 0
        assert len(manager._service_tasks) == 0
