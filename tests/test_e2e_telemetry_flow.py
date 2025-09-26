"""End-to-end tests for complete telemetry data flow.

These tests verify the complete data pipeline from data collection
through processing, storage, and real-time streaming to clients.
"""

import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.db.crud import signal_crud, session_crud
from backend.app.main import app
from backend.app.services.manager import service_manager
from backend.app.services.websocket_bus import websocket_bus


@pytest.fixture
async def e2e_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an isolated database session for E2E testing."""
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
def e2e_client() -> TestClient:
    """Create test client for E2E testing."""
    return TestClient(app)


class TestCompleteTelemetryFlow:
    """Test complete telemetry data flow from collection to consumption."""
    
    async def test_gps_to_websocket_flow(self, e2e_client: TestClient, e2e_db_session: AsyncSession) -> None:
        """Test complete GPS data flow: GPS → Service → DB → WebSocket → Client."""
        # 1. Create session
        session_data = {"name": "E2E GPS Test", "car_id": "E2E001"}
        create_response = e2e_client.post("/api/v1/sessions", json=session_data)
        assert create_response.status_code == 201
        session_id = create_response.json()["id"]
        
        # 2. Start session (activates services)
        start_response = e2e_client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200
        
        # 3. Connect WebSocket client
        with e2e_client.websocket_connect(f"/api/v1/ws?session_id={session_id}") as websocket:
            # Wait for connection confirmation
            data = websocket.receive_text()
            connection_msg = json.loads(data)
            assert connection_msg["type"] == "connection"
            
            # 4. Simulate GPS data injection
            gps_data = {
                "source": "gps",
                "channel": "latitude",
                "value": 37.7749,
                "unit": "degrees",
                "quality": "good"
            }
            
            # Inject data directly into WebSocket bus (simulating GPS service)
            await websocket_bus.broadcast_to_session(session_id, gps_data)
            
            # 5. Verify WebSocket client receives data
            telemetry_received = False
            for _ in range(10):  # Wait up to 1 second
                try:
                    data = websocket.receive_text()
                    message = json.loads(data)
                    
                    if message["type"] == "telemetry_data":
                        assert message["session_id"] == session_id
                        assert message["data"]["source"] == "gps"
                        assert message["data"]["channel"] == "latitude"
                        assert message["data"]["value"] == 37.7749
                        telemetry_received = True
                        break
                except Exception:
                    continue
            
            assert telemetry_received, "WebSocket client did not receive GPS data"
        
        # 6. Stop session
        stop_response = e2e_client.post(f"/api/v1/sessions/{session_id}/stop")
        assert stop_response.status_code == 200
    
    async def test_obd_to_database_flow(self, e2e_client: TestClient, e2e_db_session: AsyncSession) -> None:
        """Test OBD data flow: OBD → Service → Database → Export."""
        # 1. Create and start session
        session_data = {"name": "E2E OBD Test", "car_id": "E2E002"}
        create_response = e2e_client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        start_response = e2e_client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200
        
        # 2. Simulate OBD data collection
        obd_signals = [
            {
                "session_id": session_id,
                "source": "obd",
                "channel": "RPM",
                "ts_utc": datetime.now(timezone.utc),
                "ts_mono_ns": 1000000000,
                "value_num": 2500.0,
                "unit": "rpm",
                "quality": "good"
            },
            {
                "session_id": session_id,
                "source": "obd",
                "channel": "SPEED",
                "ts_utc": datetime.now(timezone.utc),
                "ts_mono_ns": 1000000001,
                "value_num": 65.0,
                "unit": "kph",
                "quality": "good"
            }
        ]
        
        # 3. Insert data into database (simulating DB writer)
        signals = await signal_crud.create_batch(e2e_db_session, obd_signals)
        assert len(signals) == 2
        
        # 4. Verify data can be retrieved via API
        signals_response = e2e_client.get(f"/api/v1/sessions/{session_id}/signals")
        assert signals_response.status_code == 200
        signals_data = signals_response.json()
        assert len(signals_data) == 2
        
        # 5. Verify data can be exported
        export_response = e2e_client.get(f"/api/v1/export/sessions/{session_id}/signals.csv")
        assert export_response.status_code == 200
        assert "text/csv" in export_response.headers["content-type"]
        
        # 6. Stop session
        stop_response = e2e_client.post(f"/api/v1/sessions/{session_id}/stop")
        assert stop_response.status_code == 200
    
    async def test_multi_source_data_flow(self, e2e_client: TestClient, e2e_db_session: AsyncSession) -> None:
        """Test multiple data sources flowing simultaneously."""
        # 1. Create and start session
        session_data = {"name": "E2E Multi-Source Test", "car_id": "E2E003"}
        create_response = e2e_client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        start_response = e2e_client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200
        
        # 2. Connect WebSocket client
        with e2e_client.websocket_connect(f"/api/v1/ws?session_id={session_id}") as websocket:
            # Wait for connection
            data = websocket.receive_text()
            connection_msg = json.loads(data)
            assert connection_msg["type"] == "connection"
            
            # 3. Simulate multiple data sources
            test_data = [
                {"source": "gps", "channel": "latitude", "value": 37.7749, "unit": "degrees"},
                {"source": "gps", "channel": "longitude", "value": -122.4194, "unit": "degrees"},
                {"source": "obd", "channel": "RPM", "value": 2500, "unit": "rpm"},
                {"source": "obd", "channel": "SPEED", "value": 65, "unit": "kph"},
                {"source": "meshtastic", "channel": "packet_count", "value": 42, "unit": "count"}
            ]
            
            # 4. Broadcast all data
            for data_item in test_data:
                await websocket_bus.broadcast_to_session(session_id, data_item)
                await asyncio.sleep(0.01)  # Small delay between messages
            
            # 5. Collect received messages
            received_messages = []
            for _ in range(20):  # Wait for all messages
                try:
                    data = websocket.receive_text()
                    message = json.loads(data)
                    if message["type"] == "telemetry_data":
                        received_messages.append(message["data"])
                except Exception:
                    break
            
            # 6. Verify all sources were received
            sources_received = {msg["source"] for msg in received_messages}
            assert "gps" in sources_received
            assert "obd" in sources_received
            assert "meshtastic" in sources_received
            
            # 7. Verify specific channels
            channels_received = {msg["channel"] for msg in received_messages}
            assert "latitude" in channels_received
            assert "longitude" in channels_received
            assert "RPM" in channels_received
            assert "SPEED" in channels_received
        
        # 8. Stop session
        stop_response = e2e_client.post(f"/api/v1/sessions/{session_id}/stop")
        assert stop_response.status_code == 200
    
    async def test_session_lifecycle_with_data_flow(self, e2e_client: TestClient, e2e_db_session: AsyncSession) -> None:
        """Test complete session lifecycle with data collection."""
        # 1. Create session
        session_data = {"name": "E2E Lifecycle Test", "car_id": "E2E004"}
        create_response = e2e_client.post("/api/v1/sessions", json=session_data)
        assert create_response.status_code == 201
        session_id = create_response.json()["id"]
        
        # 2. Verify session is inactive
        sessions_response = e2e_client.get("/api/v1/sessions")
        sessions = sessions_response.json()["sessions"]
        session = next(s for s in sessions if s["id"] == session_id)
        assert session["is_active"] is False
        
        # 3. Start session
        start_response = e2e_client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200
        
        # 4. Verify session is active
        sessions_response = e2e_client.get("/api/v1/sessions")
        sessions = sessions_response.json()["sessions"]
        session = next(s for s in sessions if s["id"] == session_id)
        assert session["is_active"] is True
        
        # 5. Collect data for a short period
        with e2e_client.websocket_connect(f"/api/v1/ws?session_id={session_id}") as websocket:
            # Wait for connection
            data = websocket.receive_text()
            connection_msg = json.loads(data)
            assert connection_msg["type"] == "connection"
            
            # Simulate data collection
            for i in range(5):
                test_data = {
                    "source": "gps",
                    "channel": "latitude",
                    "value": 37.7749 + (i * 0.001),
                    "unit": "degrees"
                }
                await websocket_bus.broadcast_to_session(session_id, test_data)
                await asyncio.sleep(0.1)
        
        # 6. Stop session
        stop_response = e2e_client.post(f"/api/v1/sessions/{session_id}/stop")
        assert stop_response.status_code == 200
        
        # 7. Verify session is inactive again
        sessions_response = e2e_client.get("/api/v1/sessions")
        sessions = sessions_response.json()["sessions"]
        session = next(s for s in sessions if s["id"] == session_id)
        assert session["is_active"] is False
    
    async def test_error_handling_in_data_flow(self, e2e_client: TestClient, e2e_db_session: AsyncSession) -> None:
        """Test error handling throughout the data flow."""
        # 1. Create session
        session_data = {"name": "E2E Error Test", "car_id": "E2E005"}
        create_response = e2e_client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        # 2. Start session
        start_response = e2e_client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200
        
        # 3. Test invalid WebSocket connection
        with pytest.raises(Exception):
            with e2e_client.websocket_connect("/api/v1/ws") as websocket:
                websocket.receive_text()
        
        # 4. Test WebSocket with invalid session
        with e2e_client.websocket_connect("/api/v1/ws?session_id=99999") as websocket:
            # Should connect but receive no data
            data = websocket.receive_text()
            connection_msg = json.loads(data)
            assert connection_msg["type"] == "connection"
        
        # 5. Test API errors
        invalid_start = e2e_client.post("/api/v1/sessions/99999/start")
        assert invalid_start.status_code == 404
        
        invalid_stop = e2e_client.post("/api/v1/sessions/99999/stop")
        assert invalid_stop.status_code == 404
        
        # 6. Test export with no data
        export_response = e2e_client.get(f"/api/v1/export/sessions/{session_id}/signals.csv")
        assert export_response.status_code == 200  # Should succeed with empty data
        
        # 7. Stop session
        stop_response = e2e_client.post(f"/api/v1/sessions/{session_id}/stop")
        assert stop_response.status_code == 200


class TestPerformanceE2E:
    """End-to-end performance tests."""
    
    async def test_high_throughput_data_flow(self, e2e_client: TestClient, e2e_db_session: AsyncSession) -> None:
        """Test system performance under high data throughput."""
        # 1. Create and start session
        session_data = {"name": "E2E Performance Test", "car_id": "E2E006"}
        create_response = e2e_client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        start_response = e2e_client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200
        
        # 2. Connect WebSocket client
        with e2e_client.websocket_connect(f"/api/v1/ws?session_id={session_id}") as websocket:
            # Wait for connection
            data = websocket.receive_text()
            connection_msg = json.loads(data)
            assert connection_msg["type"] == "connection"
            
            # 3. Send high volume of data
            start_time = asyncio.get_event_loop().time()
            message_count = 100
            
            for i in range(message_count):
                test_data = {
                    "source": "gps",
                    "channel": "latitude",
                    "value": 37.7749 + (i * 0.0001),
                    "unit": "degrees"
                }
                await websocket_bus.broadcast_to_session(session_id, test_data)
            
            # 4. Measure reception rate
            received_count = 0
            end_time = asyncio.get_event_loop().time() + 5.0  # 5 second timeout
            
            while asyncio.get_event_loop().time() < end_time and received_count < message_count:
                try:
                    data = websocket.receive_text()
                    message = json.loads(data)
                    if message["type"] == "telemetry_data":
                        received_count += 1
                except Exception:
                    break
            
            # 5. Verify performance
            duration = asyncio.get_event_loop().time() - start_time
            throughput = received_count / duration if duration > 0 else 0
            
            # Should receive at least 80% of messages within 5 seconds
            assert received_count >= message_count * 0.8, f"Only received {received_count}/{message_count} messages"
            assert throughput >= 10, f"Throughput too low: {throughput} msg/s"
        
        # 6. Stop session
        stop_response = e2e_client.post(f"/api/v1/sessions/{session_id}/stop")
        assert stop_response.status_code == 200
    
    async def test_concurrent_sessions(self, e2e_client: TestClient, e2e_db_session: AsyncSession) -> None:
        """Test multiple concurrent sessions."""
        # 1. Create multiple sessions
        session_ids = []
        for i in range(3):
            session_data = {"name": f"E2E Concurrent Test {i}", "car_id": f"E2E{i:03d}"}
            create_response = e2e_client.post("/api/v1/sessions", json=session_data)
            session_id = create_response.json()["id"]
            session_ids.append(session_id)
        
        # 2. Start all sessions
        for session_id in session_ids:
            start_response = e2e_client.post(f"/api/v1/sessions/{session_id}/start")
            assert start_response.status_code == 200
        
        # 3. Connect WebSocket clients to all sessions
        websocket_connections = []
        for session_id in session_ids:
            websocket = e2e_client.websocket_connect(f"/api/v1/ws?session_id={session_id}")
            websocket_connections.append(websocket)
        
        try:
            # 4. Send data to each session
            for i, session_id in enumerate(session_ids):
                test_data = {
                    "source": "gps",
                    "channel": "latitude",
                    "value": 37.7749 + (i * 0.1),
                    "unit": "degrees"
                }
                await websocket_bus.broadcast_to_session(session_id, test_data)
            
            # 5. Verify all sessions received data
            for i, websocket in enumerate(websocket_connections):
                with websocket as ws:
                    # Wait for connection
                    data = ws.receive_text()
                    connection_msg = json.loads(data)
                    assert connection_msg["type"] == "connection"
                    
                    # Wait for telemetry data
                    telemetry_received = False
                    for _ in range(10):
                        try:
                            data = ws.receive_text()
                            message = json.loads(data)
                            if message["type"] == "telemetry_data":
                                assert message["session_id"] == session_ids[i]
                                telemetry_received = True
                                break
                        except Exception:
                            continue
                    
                    assert telemetry_received, f"Session {session_ids[i]} did not receive data"
        
        finally:
            # 6. Stop all sessions
            for session_id in session_ids:
                stop_response = e2e_client.post(f"/api/v1/sessions/{session_id}/stop")
                assert stop_response.status_code == 200


class TestDataIntegrityE2E:
    """End-to-end data integrity tests."""
    
    async def test_data_consistency_across_components(self, e2e_client: TestClient, e2e_db_session: AsyncSession) -> None:
        """Test that data remains consistent across all system components."""
        # 1. Create and start session
        session_data = {"name": "E2E Integrity Test", "car_id": "E2E007"}
        create_response = e2e_client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        start_response = e2e_client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200
        
        # 2. Define test data with known values
        test_data = {
            "source": "gps",
            "channel": "latitude",
            "value": 37.7749123,
            "unit": "degrees",
            "quality": "good"
        }
        
        # 3. Send data through WebSocket
        with e2e_client.websocket_connect(f"/api/v1/ws?session_id={session_id}") as websocket:
            # Wait for connection
            data = websocket.receive_text()
            connection_msg = json.loads(data)
            assert connection_msg["type"] == "connection"
            
            # Send test data
            await websocket_bus.broadcast_to_session(session_id, test_data)
            
            # 4. Verify WebSocket reception
            telemetry_received = False
            for _ in range(10):
                try:
                    data = websocket.receive_text()
                    message = json.loads(data)
                    if message["type"] == "telemetry_data":
                        assert message["data"]["source"] == test_data["source"]
                        assert message["data"]["channel"] == test_data["channel"]
                        assert abs(message["data"]["value"] - test_data["value"]) < 0.0001
                        assert message["data"]["unit"] == test_data["unit"]
                        telemetry_received = True
                        break
                except Exception:
                    continue
            
            assert telemetry_received, "WebSocket did not receive consistent data"
        
        # 5. Simulate database storage
        signal_data = {
            "session_id": session_id,
            "source": test_data["source"],
            "channel": test_data["channel"],
            "ts_utc": datetime.now(timezone.utc),
            "ts_mono_ns": 1000000000,
            "value_num": test_data["value"],
            "unit": test_data["unit"],
            "quality": test_data["quality"]
        }
        
        signal = await signal_crud.create(e2e_db_session, signal_data)
        assert signal.value_num == test_data["value"]
        assert signal.source == test_data["source"]
        assert signal.channel == test_data["channel"]
        
        # 6. Verify API retrieval
        signals_response = e2e_client.get(f"/api/v1/sessions/{session_id}/signals")
        assert signals_response.status_code == 200
        signals = signals_response.json()
        
        # Find our test signal
        test_signal = next((s for s in signals if s["channel"] == test_data["channel"]), None)
        assert test_signal is not None
        assert abs(test_signal["value_num"] - test_data["value"]) < 0.0001
        assert test_signal["source"] == test_data["source"]
        assert test_signal["unit"] == test_data["unit"]
        
        # 7. Stop session
        stop_response = e2e_client.post(f"/api/v1/sessions/{session_id}/stop")
        assert stop_response.status_code == 200
