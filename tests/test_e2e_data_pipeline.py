"""End-to-end tests for complete data pipeline scenarios.

These tests verify specific data flow scenarios from sensor input
through processing, storage, and output formats.
"""

import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, List, Dict, Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.db.crud import signal_crud, session_crud
from backend.app.main import app
from backend.app.services.websocket_bus import websocket_bus
from backend.app.utils.packing import pack_telemetry_data, unpack_telemetry_data


@pytest.fixture
async def pipeline_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create database session for pipeline tests."""
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
def pipeline_client() -> TestClient:
    """Create test client for pipeline tests."""
    return TestClient(app)


class TestGPSDataPipeline:
    """Test complete GPS data pipeline from NMEA to export."""
    
    async def test_nmea_to_websocket_pipeline(self, pipeline_client: TestClient, pipeline_db_session: AsyncSession) -> None:
        """Test GPS NMEA data flow: NMEA → GPS Service → WebSocket → Client."""
        # 1. Create and start session
        session_data = {"name": "GPS Pipeline Test", "car_id": "GPS001"}
        create_response = pipeline_client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        start_response = pipeline_client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200
        
        # 2. Connect WebSocket client
        with pipeline_client.websocket_connect(f"/api/v1/ws?session_id={session_id}") as websocket:
            # Wait for connection
            data = websocket.receive_text()
            connection_msg = json.loads(data)
            assert connection_msg["type"] == "connection"
            
            # 3. Simulate NMEA sentence processing
            nmea_sentences = [
                "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47",
                "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A",
                "$GPVTG,054.7,T,034.4,M,005.5,N,010.2,K*48"
            ]
            
            # 4. Process NMEA sentences and broadcast results
            for sentence in nmea_sentences:
                # Simulate GPS service processing
                if sentence.startswith("$GPGGA"):
                    # Extract GGA data
                    parts = sentence.split(",")
                    if len(parts) >= 15:
                        lat_deg = float(parts[2][:2]) + float(parts[2][2:]) / 60.0
                        lon_deg = float(parts[4][:3]) + float(parts[4][3:]) / 60.0
                        altitude = float(parts[9]) if parts[9] else 0.0
                        
                        # Broadcast GPS data
                        gps_data = {
                            "source": "gps",
                            "channel": "latitude",
                            "value": lat_deg,
                            "unit": "degrees"
                        }
                        await websocket_bus.broadcast_to_session(session_id, gps_data)
                        
                        gps_data["channel"] = "longitude"
                        gps_data["value"] = lon_deg
                        await websocket_bus.broadcast_to_session(session_id, gps_data)
                        
                        gps_data["channel"] = "altitude"
                        gps_data["value"] = altitude
                        gps_data["unit"] = "meters"
                        await websocket_bus.broadcast_to_session(session_id, gps_data)
            
            # 5. Collect received GPS data
            gps_messages = []
            for _ in range(20):
                try:
                    data = websocket.receive_text()
                    message = json.loads(data)
                    if message["type"] == "telemetry_data" and message["data"]["source"] == "gps":
                        gps_messages.append(message["data"])
                except Exception:
                    break
            
            # 6. Verify GPS data was received
            assert len(gps_messages) > 0
            channels = {msg["channel"] for msg in gps_messages}
            assert "latitude" in channels
            assert "longitude" in channels
            assert "altitude" in channels
        
        # 7. Stop session
        stop_response = pipeline_client.post(f"/api/v1/sessions/{session_id}/stop")
        assert stop_response.status_code == 200
    
    async def test_gps_data_storage_and_retrieval(self, pipeline_client: TestClient, pipeline_db_session: AsyncSession) -> None:
        """Test GPS data storage and retrieval pipeline."""
        # 1. Create session
        session_data = {"name": "GPS Storage Test", "car_id": "GPS002"}
        create_response = pipeline_client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        # 2. Simulate GPS data collection and storage
        gps_signals = [
            {
                "session_id": session_id,
                "source": "gps",
                "channel": "latitude",
                "ts_utc": datetime.now(timezone.utc),
                "ts_mono_ns": 1000000000,
                "value_num": 37.7749,
                "unit": "degrees",
                "quality": "good"
            },
            {
                "session_id": session_id,
                "source": "gps",
                "channel": "longitude",
                "ts_utc": datetime.now(timezone.utc),
                "ts_mono_ns": 1000000001,
                "value_num": -122.4194,
                "unit": "degrees",
                "quality": "good"
            },
            {
                "session_id": session_id,
                "source": "gps",
                "channel": "speed_kph",
                "ts_utc": datetime.now(timezone.utc),
                "ts_mono_ns": 1000000002,
                "value_num": 65.0,
                "unit": "kph",
                "quality": "good"
            }
        ]
        
        # 3. Store GPS signals
        signals = await signal_crud.create_batch(pipeline_db_session, gps_signals)
        assert len(signals) == 3
        
        # 4. Retrieve GPS signals via API
        signals_response = pipeline_client.get(f"/api/v1/sessions/{session_id}/signals")
        assert signals_response.status_code == 200
        retrieved_signals = signals_response.json()
        
        # 5. Verify GPS data integrity
        gps_signals_retrieved = [s for s in retrieved_signals if s["source"] == "gps"]
        assert len(gps_signals_retrieved) == 3
        
        # Verify specific GPS channels
        channels = {s["channel"] for s in gps_signals_retrieved}
        assert "latitude" in channels
        assert "longitude" in channels
        assert "speed_kph" in channels
        
        # 6. Test GPS data export
        export_response = pipeline_client.get(f"/api/v1/export/sessions/{session_id}/signals.csv")
        assert export_response.status_code == 200
        
        csv_content = export_response.text
        assert "latitude" in csv_content
        assert "longitude" in csv_content
        assert "speed_kph" in csv_content
        assert "37.7749" in csv_content
        assert "-122.4194" in csv_content


class TestOBDDataPipeline:
    """Test complete OBD data pipeline from PID reading to export."""
    
    async def test_obd_pid_to_websocket_pipeline(self, pipeline_client: TestClient, pipeline_db_session: AsyncSession) -> None:
        """Test OBD PID data flow: PID Request → OBD Service → WebSocket → Client."""
        # 1. Create and start session
        session_data = {"name": "OBD Pipeline Test", "car_id": "OBD001"}
        create_response = pipeline_client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        start_response = pipeline_client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200
        
        # 2. Connect WebSocket client
        with pipeline_client.websocket_connect(f"/api/v1/ws?session_id={session_id}") as websocket:
            # Wait for connection
            data = websocket.receive_text()
            connection_msg = json.loads(data)
            assert connection_msg["type"] == "connection"
            
            # 3. Simulate OBD PID readings
            obd_pids = [
                {"pid": "SPEED", "value": 65.0, "unit": "kph"},
                {"pid": "RPM", "value": 2500.0, "unit": "rpm"},
                {"pid": "THROTTLE_POS", "value": 45.5, "unit": "%"},
                {"pid": "COOLANT_TEMP", "value": 85.0, "unit": "C"},
                {"pid": "ENGINE_LOAD", "value": 35.2, "unit": "%"}
            ]
            
            # 4. Process OBD PIDs and broadcast results
            for pid_data in obd_pids:
                obd_message = {
                    "source": "obd",
                    "channel": pid_data["pid"],
                    "value": pid_data["value"],
                    "unit": pid_data["unit"],
                    "quality": "good"
                }
                await websocket_bus.broadcast_to_session(session_id, obd_message)
                await asyncio.sleep(0.01)
            
            # 5. Collect received OBD data
            obd_messages = []
            for _ in range(30):
                try:
                    data = websocket.receive_text()
                    message = json.loads(data)
                    if message["type"] == "telemetry_data" and message["data"]["source"] == "obd":
                        obd_messages.append(message["data"])
                except Exception:
                    break
            
            # 6. Verify OBD data was received
            assert len(obd_messages) > 0
            channels = {msg["channel"] for msg in obd_messages}
            assert "SPEED" in channels
            assert "RPM" in channels
            assert "THROTTLE_POS" in channels
            assert "COOLANT_TEMP" in channels
            assert "ENGINE_LOAD" in channels
        
        # 7. Stop session
        stop_response = pipeline_client.post(f"/api/v1/sessions/{session_id}/stop")
        assert stop_response.status_code == 200
    
    async def test_obd_data_aggregation_and_export(self, pipeline_client: TestClient, pipeline_db_session: AsyncSession) -> None:
        """Test OBD data aggregation and export pipeline."""
        # 1. Create session
        session_data = {"name": "OBD Aggregation Test", "car_id": "OBD002"}
        create_response = pipeline_client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        # 2. Simulate OBD data collection over time
        obd_signals = []
        base_time = datetime.now(timezone.utc)
        
        # Simulate 10 seconds of OBD data at 10Hz
        for second in range(10):
            for sample in range(10):
                timestamp = base_time.replace(microsecond=(second * 1000000) + (sample * 100000))
                mono_time = 1000000000 + (second * 1000000000) + (sample * 100000000)
                
                # Vary RPM and speed over time
                rpm = 2000 + (second * 100) + (sample * 10)
                speed = 50 + (second * 2) + (sample * 0.2)
                
                obd_signals.extend([
                    {
                        "session_id": session_id,
                        "source": "obd",
                        "channel": "RPM",
                        "ts_utc": timestamp,
                        "ts_mono_ns": mono_time,
                        "value_num": float(rpm),
                        "unit": "rpm",
                        "quality": "good"
                    },
                    {
                        "session_id": session_id,
                        "source": "obd",
                        "channel": "SPEED",
                        "ts_utc": timestamp,
                        "ts_mono_ns": mono_time + 1,
                        "value_num": float(speed),
                        "unit": "kph",
                        "quality": "good"
                    }
                ])
        
        # 3. Store OBD signals
        signals = await signal_crud.create_batch(pipeline_db_session, obd_signals)
        assert len(signals) == 200  # 10 seconds * 10 samples * 2 channels
        
        # 4. Test filtered retrieval
        rpm_signals_response = pipeline_client.get(
            f"/api/v1/sessions/{session_id}/signals",
            params={"channels": ["RPM"]}
        )
        assert rpm_signals_response.status_code == 200
        rpm_signals = rpm_signals_response.json()
        assert len(rpm_signals) == 100
        assert all(s["channel"] == "RPM" for s in rpm_signals)
        
        # 5. Test time range filtering
        start_time = base_time.replace(microsecond=500000)
        end_time = base_time.replace(microsecond=1500000)
        
        time_filtered_response = pipeline_client.get(
            f"/api/v1/sessions/{session_id}/signals",
            params={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        )
        assert time_filtered_response.status_code == 200
        time_filtered_signals = time_filtered_response.json()
        assert len(time_filtered_signals) > 0
        assert len(time_filtered_signals) < 200  # Should be subset
        
        # 6. Test export with filters
        export_response = pipeline_client.get(
            f"/api/v1/export/sessions/{session_id}/signals.csv",
            params={"sources": ["obd"], "channels": ["RPM", "SPEED"]}
        )
        assert export_response.status_code == 200
        
        csv_content = export_response.text
        assert "RPM" in csv_content
        assert "SPEED" in csv_content
        assert "rpm" in csv_content
        assert "kph" in csv_content


class TestMeshtasticDataPipeline:
    """Test complete Meshtastic data pipeline from packing to transmission."""
    
    async def test_telemetry_packing_pipeline(self, pipeline_client: TestClient, pipeline_db_session: AsyncSession) -> None:
        """Test telemetry data packing and unpacking pipeline."""
        # 1. Create session
        session_data = {"name": "Meshtastic Packing Test", "car_id": "MESH001"}
        create_response = pipeline_client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        # 2. Prepare telemetry data for packing
        telemetry_data = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 100.5,
            "SPEED": 65.0,
            "RPM": 2500.0,
            "COOLANT_TEMP": 85.0
        }
        
        # 3. Test packing
        packed_data = pack_telemetry_data(telemetry_data)
        assert isinstance(packed_data, bytes)
        assert len(packed_data) > 0
        
        # 4. Test unpacking
        unpacked_data = unpack_telemetry_data(packed_data)
        assert isinstance(unpacked_data, dict)
        
        # 5. Verify data integrity
        for key, expected_value in telemetry_data.items():
            assert key in unpacked_data
            # Allow for small floating point differences due to scaling
            assert abs(unpacked_data[key] - expected_value) < 0.01
        
        # 6. Test with WebSocket broadcast (simulating Meshtastic service)
        start_response = pipeline_client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200
        
        with pipeline_client.websocket_connect(f"/api/v1/ws?session_id={session_id}") as websocket:
            # Wait for connection
            data = websocket.receive_text()
            connection_msg = json.loads(data)
            assert connection_msg["type"] == "connection"
            
            # 7. Broadcast packed telemetry data
            meshtastic_data = {
                "source": "meshtastic",
                "channel": "packed_telemetry",
                "value": len(packed_data),  # Packet size
                "unit": "bytes",
                "quality": "good",
                "packed_data": packed_data.hex()  # Hex representation
            }
            
            await websocket_bus.broadcast_to_session(session_id, meshtastic_data)
            
            # 8. Verify reception
            meshtastic_received = False
            for _ in range(10):
                try:
                    data = websocket.receive_text()
                    message = json.loads(data)
                    if message["type"] == "telemetry_data" and message["data"]["source"] == "meshtastic":
                        assert message["data"]["channel"] == "packed_telemetry"
                        assert message["data"]["value"] == len(packed_data)
                        meshtastic_received = True
                        break
                except Exception:
                    continue
            
            assert meshtastic_received, "Meshtastic data not received"
        
        # 9. Stop session
        stop_response = pipeline_client.post(f"/api/v1/sessions/{session_id}/stop")
        assert stop_response.status_code == 200


class TestCompleteDataFlowScenarios:
    """Test complete end-to-end data flow scenarios."""
    
    async def test_track_session_simulation(self, pipeline_client: TestClient, pipeline_db_session: AsyncSession) -> None:
        """Simulate a complete track session with multiple data sources."""
        # 1. Create track session
        session_data = {
            "name": "Track Day Simulation",
            "car_id": "TRACK001",
            "driver": "Test Driver",
            "track": "Test Circuit"
        }
        create_response = pipeline_client.post("/api/v1/sessions", json=session_data)
        session_id = create_response.json()["id"]
        
        # 2. Start session
        start_response = pipeline_client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200
        
        # 3. Simulate track session data collection
        track_data = []
        base_time = datetime.now(timezone.utc)
        
        # Simulate 30 seconds of track data
        for second in range(30):
            for sample in range(10):  # 10Hz sampling
                timestamp = base_time.replace(microsecond=(second * 1000000) + (sample * 100000))
                mono_time = 1000000000 + (second * 1000000000) + (sample * 100000000)
                
                # Simulate track position (circular track)
                angle = (second * 10 + sample) % 360
                lat = 37.7749 + 0.001 * (angle / 360.0)
                lon = -122.4194 + 0.001 * (angle / 360.0)
                
                # Simulate varying speed and RPM
                speed = 60 + 20 * (angle / 360.0)
                rpm = 2000 + 1000 * (angle / 360.0)
                
                track_data.extend([
                    {
                        "session_id": session_id,
                        "source": "gps",
                        "channel": "latitude",
                        "ts_utc": timestamp,
                        "ts_mono_ns": mono_time,
                        "value_num": lat,
                        "unit": "degrees",
                        "quality": "good"
                    },
                    {
                        "session_id": session_id,
                        "source": "gps",
                        "channel": "longitude",
                        "ts_utc": timestamp,
                        "ts_mono_ns": mono_time + 1,
                        "value_num": lon,
                        "unit": "degrees",
                        "quality": "good"
                    },
                    {
                        "session_id": session_id,
                        "source": "gps",
                        "channel": "speed_kph",
                        "ts_utc": timestamp,
                        "ts_mono_ns": mono_time + 2,
                        "value_num": speed,
                        "unit": "kph",
                        "quality": "good"
                    },
                    {
                        "session_id": session_id,
                        "source": "obd",
                        "channel": "RPM",
                        "ts_utc": timestamp,
                        "ts_mono_ns": mono_time + 3,
                        "value_num": rpm,
                        "unit": "rpm",
                        "quality": "good"
                    },
                    {
                        "session_id": session_id,
                        "source": "obd",
                        "channel": "SPEED",
                        "ts_utc": timestamp,
                        "ts_mono_ns": mono_time + 4,
                        "value_num": speed,
                        "unit": "kph",
                        "quality": "good"
                    }
                ])
        
        # 4. Store track session data
        signals = await signal_crud.create_batch(pipeline_db_session, track_data)
        assert len(signals) == 1500  # 30 seconds * 10 samples * 5 channels
        
        # 5. Test real-time WebSocket streaming
        with pipeline_client.websocket_connect(f"/api/v1/ws?session_id={session_id}") as websocket:
            # Wait for connection
            data = websocket.receive_text()
            connection_msg = json.loads(data)
            assert connection_msg["type"] == "connection"
            
            # Simulate real-time data streaming
            for i in range(10):
                sample_data = track_data[i * 5:(i + 1) * 5]  # 5 channels per sample
                for signal in sample_data:
                    ws_data = {
                        "source": signal["source"],
                        "channel": signal["channel"],
                        "value": signal["value_num"],
                        "unit": signal["unit"]
                    }
                    await websocket_bus.broadcast_to_session(session_id, ws_data)
                await asyncio.sleep(0.1)
            
            # Collect received messages
            received_messages = []
            for _ in range(50):
                try:
                    data = websocket.receive_text()
                    message = json.loads(data)
                    if message["type"] == "telemetry_data":
                        received_messages.append(message["data"])
                except Exception:
                    break
            
            # Verify data diversity
            sources = {msg["source"] for msg in received_messages}
            channels = {msg["channel"] for msg in received_messages}
            
            assert "gps" in sources
            assert "obd" in sources
            assert "latitude" in channels
            assert "longitude" in channels
            assert "RPM" in channels
            assert "SPEED" in channels
        
        # 6. Stop session
        stop_response = pipeline_client.post(f"/api/v1/sessions/{session_id}/stop")
        assert stop_response.status_code == 200
        
        # 7. Test complete data export
        export_response = pipeline_client.get(f"/api/v1/export/sessions/{session_id}/signals.csv")
        assert export_response.status_code == 200
        
        csv_content = export_response.text
        lines = csv_content.strip().split('\n')
        assert len(lines) == 1501  # Header + 1500 data rows
        
        # Verify CSV contains expected data
        assert "latitude" in csv_content
        assert "longitude" in csv_content
        assert "RPM" in csv_content
        assert "SPEED" in csv_content
        assert "gps" in csv_content
        assert "obd" in csv_content
        
        # 8. Test Parquet export
        parquet_response = pipeline_client.get(f"/api/v1/export/sessions/{session_id}/signals.parquet")
        assert parquet_response.status_code == 200
        assert "application/octet-stream" in parquet_response.headers["content-type"]
        
        # 9. Test filtered export
        gps_only_response = pipeline_client.get(
            f"/api/v1/export/sessions/{session_id}/signals.csv",
            params={"sources": ["gps"]}
        )
        assert gps_only_response.status_code == 200
        
        gps_csv_content = gps_only_response.text
        gps_lines = gps_csv_content.strip().split('\n')
        assert len(gps_lines) == 901  # Header + 900 GPS rows (30s * 10Hz * 3 channels)
        
        # Verify only GPS data
        assert "gps" in gps_csv_content
        assert "obd" not in gps_csv_content
