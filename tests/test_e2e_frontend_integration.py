"""End-to-end tests for frontend integration.

These tests verify the complete frontend-backend integration,
including WebSocket communication, data visualization, and user interactions.
"""

import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.db.crud import signal_crud
from backend.app.main import app
from backend.app.services.websocket_bus import websocket_bus


@pytest.fixture
async def frontend_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create database session for frontend integration tests."""
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
def frontend_client() -> TestClient:
    """Create test client for frontend integration tests."""
    return TestClient(app)


class TestFrontendBackendIntegration:
    """Test frontend-backend integration scenarios."""
    
    def test_dashboard_page_loads(self, frontend_client: TestClient) -> None:
        """Test that the main dashboard page loads correctly."""
        response = frontend_client.get("/index.html")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Cartelem Telemetry Dashboard" in response.text
        assert "session-select" in response.text
        assert "connect-btn" in response.text
    
    def test_replay_page_loads(self, frontend_client: TestClient) -> None:
        """Test that the replay page loads correctly."""
        response = frontend_client.get("/replay.html")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Cartelem Replay Dashboard" in response.text
        assert "time-scrubber" in response.text
        assert "play-pause-button" in response.text
    
    def test_static_assets_load(self, frontend_client: TestClient) -> None:
        """Test that all static assets (CSS, JS) load correctly."""
        # Test CSS
        css_response = frontend_client.get("/css/styles.css")
        assert css_response.status_code == 200
        assert "text/css" in css_response.headers["content-type"]
        
        # Test JavaScript files
        js_files = ["/js/app.js", "/js/charts.js", "/js/map.js", "/js/replay.js"]
        for js_file in js_files:
            js_response = frontend_client.get(js_file)
            assert js_response.status_code == 200
            assert "application/javascript" in js_response.headers["content-type"]
    
    async def test_dashboard_session_management_flow(self, frontend_client: TestClient, frontend_db_session: AsyncSession) -> None:
        """Test complete session management flow from frontend perspective."""
        # 1. Load dashboard
        dashboard_response = frontend_client.get("/index.html")
        assert dashboard_response.status_code == 200
        
        # 2. Create session via API (simulating frontend action)
        session_data = {"name": "Frontend Test Session", "car_id": "FE001"}
        create_response = frontend_client.post("/api/v1/sessions", json=session_data)
        assert create_response.status_code == 201
        session_id = create_response.json()["id"]
        
        # 3. Verify session appears in list
        sessions_response = frontend_client.get("/api/v1/sessions")
        assert sessions_response.status_code == 200
        sessions = sessions_response.json()["sessions"]
        session = next((s for s in sessions if s["id"] == session_id), None)
        assert session is not None
        assert session["name"] == "Frontend Test Session"
        assert session["is_active"] is False
        
        # 4. Start session (simulating frontend start button)
        start_response = frontend_client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200
        
        # 5. Verify session is active
        sessions_response = frontend_client.get("/api/v1/sessions")
        sessions = sessions_response.json()["sessions"]
        session = next((s for s in sessions if s["id"] == session_id), None)
        assert session["is_active"] is True
        
        # 6. Stop session (simulating frontend stop button)
        stop_response = frontend_client.post(f"/api/v1/sessions/{session_id}/stop")
        assert stop_response.status_code == 200
        
        # 7. Verify session is inactive
        sessions_response = frontend_client.get("/api/v1/sessions")
        sessions = sessions_response.json()["sessions"]
        session = next((s for s in sessions if s["id"] == session_id), None)
        assert session["is_active"] is False
    
    async def test_realtime_data_visualization_flow(self, frontend_client: TestClient, frontend_db_session: AsyncSession) -> None:
        """Test real-time data flow for dashboard visualization."""
        # 1. Create and start session
        session_data = {"name": "Visualization Test", "car_id": "VIZ001"}
        create_response = frontend_client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        start_response = frontend_client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200
        
        # 2. Connect WebSocket (simulating frontend connection)
        with frontend_client.websocket_connect(f"/api/v1/ws?session_id={session_id}") as websocket:
            # Wait for connection
            data = websocket.receive_text()
            connection_msg = json.loads(data)
            assert connection_msg["type"] == "connection"
            
            # 3. Simulate various data types that would be visualized
            visualization_data = [
                # GPS data for map
                {"source": "gps", "channel": "latitude", "value": 37.7749, "unit": "degrees"},
                {"source": "gps", "channel": "longitude", "value": -122.4194, "unit": "degrees"},
                {"source": "gps", "channel": "speed_kph", "value": 65.0, "unit": "kph"},
                
                # OBD data for charts
                {"source": "obd", "channel": "RPM", "value": 2500, "unit": "rpm"},
                {"source": "obd", "channel": "SPEED", "value": 65, "unit": "kph"},
                {"source": "obd", "channel": "THROTTLE_POS", "value": 45.5, "unit": "%"},
                {"source": "obd", "channel": "COOLANT_TEMP", "value": 85.0, "unit": "C"},
                
                # Engine parameters
                {"source": "obd", "channel": "ENGINE_LOAD", "value": 35.2, "unit": "%"},
                {"source": "obd", "channel": "INTAKE_TEMP", "value": 25.0, "unit": "C"},
            ]
            
            # 4. Send data and verify reception
            received_data = []
            for data_item in visualization_data:
                await websocket_bus.broadcast_to_session(session_id, data_item)
                await asyncio.sleep(0.01)
            
            # 5. Collect received messages
            for _ in range(30):  # Wait for all messages
                try:
                    data = websocket.receive_text()
                    message = json.loads(data)
                    if message["type"] == "telemetry_data":
                        received_data.append(message["data"])
                except Exception:
                    break
            
            # 6. Verify all data types were received
            sources = {d["source"] for d in received_data}
            channels = {d["channel"] for d in received_data}
            
            assert "gps" in sources
            assert "obd" in sources
            assert "latitude" in channels
            assert "longitude" in channels
            assert "RPM" in channels
            assert "SPEED" in channels
            assert "THROTTLE_POS" in channels
            assert "COOLANT_TEMP" in channels
        
        # 7. Stop session
        stop_response = frontend_client.post(f"/api/v1/sessions/{session_id}/stop")
        assert stop_response.status_code == 200
    
    async def test_replay_functionality_flow(self, frontend_client: TestClient, frontend_db_session: AsyncSession) -> None:
        """Test replay functionality with historical data."""
        # 1. Create session and add historical data
        session_data = {"name": "Replay Test", "car_id": "REP001"}
        create_response = frontend_client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        # 2. Add historical signals (simulating completed session)
        historical_signals = []
        base_time = datetime.now(timezone.utc)
        
        for i in range(10):
            signal_data = {
                "session_id": session_id,
                "source": "gps",
                "channel": "latitude",
                "ts_utc": base_time.replace(microsecond=i * 100000),
                "ts_mono_ns": 1000000000 + (i * 1000000),
                "value_num": 37.7749 + (i * 0.001),
                "unit": "degrees",
                "quality": "good"
            }
            historical_signals.append(signal_data)
        
        # Insert signals into database
        signals = await signal_crud.create_batch(frontend_db_session, historical_signals)
        assert len(signals) == 10
        
        # 3. Load replay page
        replay_response = frontend_client.get("/replay.html")
        assert replay_response.status_code == 200
        
        # 4. Verify session appears in replay dropdown
        sessions_response = frontend_client.get("/api/v1/sessions")
        sessions = sessions_response.json()["sessions"]
        session = next((s for s in sessions if s["id"] == session_id), None)
        assert session is not None
        
        # 5. Test signals retrieval for replay
        signals_response = frontend_client.get(f"/api/v1/sessions/{session_id}/signals")
        assert signals_response.status_code == 200
        signals_data = signals_response.json()
        assert len(signals_data) == 10
        
        # 6. Verify signal data structure for replay
        for signal in signals_data:
            assert "id" in signal
            assert "session_id" in signal
            assert "source" in signal
            assert "channel" in signal
            assert "ts_utc" in signal
            assert "value_num" in signal
            assert "unit" in signal
        
        # 7. Test export functionality from replay
        export_response = frontend_client.get(f"/api/v1/export/sessions/{session_id}/signals.csv")
        assert export_response.status_code == 200
        assert "text/csv" in export_response.headers["content-type"]
        
        # Verify CSV contains our data
        csv_content = export_response.text
        assert "latitude" in csv_content
        assert "37.7749" in csv_content  # First value
    
    async def test_error_handling_in_frontend_flow(self, frontend_client: TestClient) -> None:
        """Test error handling scenarios in frontend integration."""
        # 1. Test invalid session operations
        invalid_start = frontend_client.post("/api/v1/sessions/99999/start")
        assert invalid_start.status_code == 404
        
        invalid_stop = frontend_client.post("/api/v1/sessions/99999/stop")
        assert invalid_stop.status_code == 404
        
        # 2. Test WebSocket connection without session
        with pytest.raises(Exception):
            with frontend_client.websocket_connect("/api/v1/ws") as websocket:
                websocket.receive_text()
        
        # 3. Test WebSocket with invalid session
        with frontend_client.websocket_connect("/api/v1/ws?session_id=99999") as websocket:
            # Should connect but receive no meaningful data
            data = websocket.receive_text()
            connection_msg = json.loads(data)
            assert connection_msg["type"] == "connection"
        
        # 4. Test export with non-existent session
        export_response = frontend_client.get("/api/v1/export/sessions/99999/signals.csv")
        assert export_response.status_code == 404
        
        # 5. Test malformed session creation
        malformed_session = frontend_client.post("/api/v1/sessions", json={"invalid": "data"})
        assert malformed_session.status_code == 422  # Validation error


class TestFrontendPerformance:
    """Test frontend performance and responsiveness."""
    
    async def test_dashboard_load_performance(self, frontend_client: TestClient) -> None:
        """Test dashboard page load performance."""
        import time
        
        # Measure page load time
        start_time = time.time()
        response = frontend_client.get("/index.html")
        load_time = time.time() - start_time
        
        assert response.status_code == 200
        assert load_time < 1.0, f"Dashboard load time too slow: {load_time:.2f}s"
    
    async def test_api_response_times(self, frontend_client: TestClient) -> None:
        """Test API response times for frontend operations."""
        import time
        
        # Test sessions list response time
        start_time = time.time()
        response = frontend_client.get("/api/v1/sessions")
        response_time = time.time() - start_time
        
        assert response.status_code == 200
        assert response_time < 0.5, f"Sessions API too slow: {response_time:.2f}s"
        
        # Test session creation response time
        start_time = time.time()
        session_data = {"name": "Performance Test", "car_id": "PERF001"}
        response = frontend_client.post("/api/v1/sessions", json=session_data)
        response_time = time.time() - start_time
        
        assert response.status_code == 201
        assert response_time < 0.5, f"Session creation too slow: {response_time:.2f}s"
    
    async def test_websocket_connection_performance(self, frontend_client: TestClient) -> None:
        """Test WebSocket connection establishment performance."""
        import time
        
        # Create session first
        session_data = {"name": "WS Performance Test", "car_id": "WSPERF001"}
        create_response = frontend_client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        # Measure WebSocket connection time
        start_time = time.time()
        with frontend_client.websocket_connect(f"/api/v1/ws?session_id={session_id}") as websocket:
            # Wait for connection confirmation
            data = websocket.receive_text()
            connection_time = time.time() - start_time
            
            assert connection_time < 1.0, f"WebSocket connection too slow: {connection_time:.2f}s"
            
            connection_msg = json.loads(data)
            assert connection_msg["type"] == "connection"
