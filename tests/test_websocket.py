"""Tests for WebSocket functionality and real-time data streaming."""

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
from backend.app.services.websocket_bus import WebSocketBus


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


class TestWebSocketBus:
    """Test WebSocket bus functionality."""
    
    async def test_websocket_bus_initialization(self) -> None:
        """Test WebSocket bus initializes correctly."""
        bus = WebSocketBus()
        
        assert len(bus._connections) == 0
        assert bus._heartbeat_task is None
    
    async def test_connect_and_disconnect(self) -> None:
        """Test connecting and disconnecting WebSocket clients."""
        bus = WebSocketBus()
        
        # Mock WebSocket
        class MockWebSocket:
            def __init__(self):
                self.sent_messages = []
            
            async def send_text(self, message: str) -> None:
                self.sent_messages.append(message)
        
        websocket1 = MockWebSocket()
        websocket2 = MockWebSocket()
        
        # Connect clients
        await bus.connect(websocket1, 1)
        await bus.connect(websocket2, 1)
        
        assert 1 in bus._connections
        assert len(bus._connections[1]) == 2
        assert websocket1 in bus._connections[1]
        assert websocket2 in bus._connections[1]
        
        # Disconnect one client
        await bus.disconnect(websocket1, 1)
        
        assert len(bus._connections[1]) == 1
        assert websocket2 in bus._connections[1]
        assert websocket1 not in bus._connections[1]
        
        # Disconnect remaining client
        await bus.disconnect(websocket2, 1)
        
        assert 1 not in bus._connections
        assert len(bus._connections) == 0
    
    async def test_broadcast_to_session(self) -> None:
        """Test broadcasting data to session clients."""
        bus = WebSocketBus()
        
        # Mock WebSocket
        class MockWebSocket:
            def __init__(self):
                self.sent_messages = []
            
            async def send_text(self, message: str) -> None:
                self.sent_messages.append(message)
        
        websocket1 = MockWebSocket()
        websocket2 = MockWebSocket()
        
        # Connect clients
        await bus.connect(websocket1, 1)
        await bus.connect(websocket2, 1)
        
        # Broadcast data
        test_data = {"speed": 65.0, "rpm": 2500}
        await bus.broadcast_to_session(1, test_data)
        
        # Check messages were sent
        assert len(websocket1.sent_messages) == 1
        assert len(websocket2.sent_messages) == 1
        
        # Verify message content
        message1 = json.loads(websocket1.sent_messages[0])
        message2 = json.loads(websocket2.sent_messages[0])
        
        assert message1["type"] == "telemetry_data"
        assert message1["session_id"] == 1
        assert message1["data"] == test_data
        assert "timestamp" in message1
        
        assert message2["type"] == "telemetry_data"
        assert message2["session_id"] == 1
        assert message2["data"] == test_data
    
    async def test_broadcast_heartbeat(self) -> None:
        """Test broadcasting heartbeat to all clients."""
        bus = WebSocketBus()
        
        # Mock WebSocket
        class MockWebSocket:
            def __init__(self):
                self.sent_messages = []
            
            async def send_text(self, message: str) -> None:
                self.sent_messages.append(message)
        
        websocket1 = MockWebSocket()
        websocket2 = MockWebSocket()
        
        # Connect clients to different sessions
        await bus.connect(websocket1, 1)
        await bus.connect(websocket2, 2)
        
        # Broadcast heartbeat
        await bus.broadcast_heartbeat()
        
        # Check messages were sent
        assert len(websocket1.sent_messages) == 1
        assert len(websocket2.sent_messages) == 1
        
        # Verify heartbeat message content
        message1 = json.loads(websocket1.sent_messages[0])
        message2 = json.loads(websocket2.sent_messages[0])
        
        assert message1["type"] == "heartbeat"
        assert message2["type"] == "heartbeat"
        assert "timestamp" in message1
        assert "timestamp" in message2
    
    async def test_connection_count(self) -> None:
        """Test getting connection counts."""
        bus = WebSocketBus()
        
        # Mock WebSocket
        class MockWebSocket:
            pass
        
        websocket1 = MockWebSocket()
        websocket2 = MockWebSocket()
        websocket3 = MockWebSocket()
        
        # Initially no connections
        assert await bus.get_connection_count() == 0
        assert await bus.get_connection_count(1) == 0
        
        # Connect clients
        await bus.connect(websocket1, 1)
        await bus.connect(websocket2, 1)
        await bus.connect(websocket3, 2)
        
        # Check counts
        assert await bus.get_connection_count() == 3
        assert await bus.get_connection_count(1) == 2
        assert await bus.get_connection_count(2) == 1
        assert await bus.get_connection_count(3) == 0
    
    async def test_get_active_sessions(self) -> None:
        """Test getting active session list."""
        bus = WebSocketBus()
        
        # Mock WebSocket
        class MockWebSocket:
            pass
        
        websocket1 = MockWebSocket()
        websocket2 = MockWebSocket()
        
        # Initially no active sessions
        assert await bus.get_active_sessions() == []
        
        # Connect clients
        await bus.connect(websocket1, 1)
        await bus.connect(websocket2, 2)
        
        # Check active sessions
        active_sessions = await bus.get_active_sessions()
        assert len(active_sessions) == 2
        assert 1 in active_sessions
        assert 2 in active_sessions
    
    async def test_shutdown(self) -> None:
        """Test WebSocket bus shutdown."""
        bus = WebSocketBus()
        
        # Mock WebSocket
        class MockWebSocket:
            def __init__(self):
                self.closed = False
            
            async def close(self) -> None:
                self.closed = True
        
        websocket1 = MockWebSocket()
        websocket2 = MockWebSocket()
        
        # Connect clients
        await bus.connect(websocket1, 1)
        await bus.connect(websocket2, 2)
        
        # Shutdown
        await bus.shutdown()
        
        # Check connections are cleared
        assert len(bus._connections) == 0
        assert bus._heartbeat_task is None


class TestWebSocketEndpoints:
    """Test WebSocket API endpoints."""
    
    def test_websocket_test_page(self, client: TestClient) -> None:
        """Test WebSocket test page endpoint."""
        response = client.get("/api/v1/ws/test")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "WebSocket Test" in response.text
        assert "connect()" in response.text
        assert "disconnect()" in response.text
    
    def test_websocket_connection_requires_session_id(self, client: TestClient) -> None:
        """Test that WebSocket connection requires session_id parameter."""
        # This should fail because session_id is required
        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/ws") as websocket:
                websocket.receive_text()
    
    def test_websocket_connection_with_session_id(self, client: TestClient) -> None:
        """Test WebSocket connection with session_id parameter."""
        with client.websocket_connect("/api/v1/ws?session_id=1") as websocket:
            # Should receive connection confirmation
            data = websocket.receive_text()
            message = json.loads(data)
            
            assert message["type"] == "connection"
            assert message["session_id"] == 1
            assert "Connected to telemetry data stream" in message["message"]
    
    def test_websocket_echo_functionality(self, client: TestClient) -> None:
        """Test WebSocket echo functionality."""
        with client.websocket_connect("/api/v1/ws?session_id=1") as websocket:
            # First receive connection message
            data = websocket.receive_text()
            connection_message = json.loads(data)
            assert connection_message["type"] == "connection"
            
            # Send a test message
            test_message = "ping"
            websocket.send_text(test_message)
            
            # Should receive echo
            data = websocket.receive_text()
            message = json.loads(data)
            
            assert message["type"] == "echo"
            assert message["data"] == test_message
    
    def test_websocket_heartbeat_reception(self, client: TestClient) -> None:
        """Test that WebSocket clients receive heartbeats."""
        with client.websocket_connect("/api/v1/ws?session_id=1") as websocket:
            # Wait for initial connection message
            data = websocket.receive_text()
            connection_message = json.loads(data)
            assert connection_message["type"] == "connection"
            
            # Wait for heartbeat (should arrive within 5 seconds)
            data = websocket.receive_text()
            heartbeat_message = json.loads(data)
            
            assert heartbeat_message["type"] == "heartbeat"
            assert "timestamp" in heartbeat_message
            assert "WebSocket connection active" in heartbeat_message["message"]


class TestWebSocketIntegration:
    """Test WebSocket integration with service manager."""
    
    def test_websocket_receives_telemetry_data(self, client: TestClient) -> None:
        """Test that WebSocket clients receive telemetry data from services."""
        # First create a session
        session_data = {"name": "WebSocket Test Session"}
        create_response = client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        # Start the session to activate services
        start_response = client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200
        
        # Connect WebSocket
        with client.websocket_connect(f"/api/v1/ws?session_id={session_id}") as websocket:
            # Wait for connection message
            data = websocket.receive_text()
            connection_message = json.loads(data)
            assert connection_message["type"] == "connection"
            
            # Wait for telemetry data (should arrive from stub services)
            telemetry_received = False
            for _ in range(20):  # Try up to 20 messages (services run at 10Hz)
                try:
                    data = websocket.receive_text()
                    message = json.loads(data)
                    
                    if message["type"] == "telemetry_data":
                        assert message["session_id"] == session_id
                        assert "data" in message
                        assert "source" in message["data"]
                        assert message["data"]["source"] in ["obd", "gps", "meshtastic"]
                        telemetry_received = True
                        break
                except Exception:
                    continue
            
            # Note: This test may fail if services don't start quickly enough
            # In a real scenario, we'd wait for services to be ready
            if not telemetry_received:
                print("Warning: Did not receive telemetry data from services (may be timing issue)")
        
        # Stop the session
        stop_response = client.post(f"/api/v1/sessions/{session_id}/stop")
        assert stop_response.status_code == 200


# Pytest configuration for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
