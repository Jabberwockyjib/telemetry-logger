"""Tests for GPS service and NMEA parsing."""

import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.services.gps_service import GPSService, NMEAParser


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


class TestNMEAParser:
    """Test NMEA sentence parsing functionality."""
    
    def test_parse_gga_valid(self) -> None:
        """Test parsing valid GGA sentence."""
        parser = NMEAParser()
        
        gga_sentence = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        result = parser.parse_gga(gga_sentence)
        
        assert result is not None
        assert result["sentence_type"] == "GGA"
        assert result["time"] == "123519"
        assert abs(result["latitude"] - 48.1173) < 0.0001  # 48°07.038'N
        assert abs(result["longitude"] - 11.5167) < 0.0001  # 011°31.000'E
        assert result["quality"] == 1
        assert result["satellites"] == 8
        assert result["hdop"] == 0.9
        assert result["altitude"] == 545.4
        assert result["geoid_height"] == 46.9
    
    def test_parse_gga_invalid(self) -> None:
        """Test parsing invalid GGA sentence."""
        parser = NMEAParser()
        
        invalid_sentence = "$GPGGA,invalid,data*47"
        result = parser.parse_gga(invalid_sentence)
        
        assert result is None
    
    def test_parse_rmc_valid(self) -> None:
        """Test parsing valid RMC sentence."""
        parser = NMEAParser()
        
        rmc_sentence = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        result = parser.parse_rmc(rmc_sentence)
        
        assert result is not None
        assert result["sentence_type"] == "RMC"
        assert result["time"] == "123519"
        assert result["status"] == "A"
        assert abs(result["latitude"] - 48.1173) < 0.0001
        assert abs(result["longitude"] - 11.5167) < 0.0001
        assert abs(result["speed_kph"] - 41.4848) < 0.0001  # 22.4 knots * 1.852
        assert result["course"] == 84.4
        assert result["date"] == "230394"
    
    def test_parse_rmc_invalid(self) -> None:
        """Test parsing invalid RMC sentence."""
        parser = NMEAParser()
        
        invalid_sentence = "$GPRMC,invalid,data*6A"
        result = parser.parse_rmc(invalid_sentence)
        
        assert result is None
    
    def test_parse_vtg_valid(self) -> None:
        """Test parsing valid VTG sentence."""
        parser = NMEAParser()
        
        vtg_sentence = "$GPVTG,054.7,T,034.4,M,005.5,N,010.2,K*48"
        result = parser.parse_vtg(vtg_sentence)
        
        assert result is not None
        assert result["sentence_type"] == "VTG"
        assert result["course_true"] == 54.7
        assert result["course_magnetic"] == 34.4
        assert result["speed_knots"] == 5.5
        assert result["speed_kph"] == 10.2
    
    def test_parse_vtg_invalid(self) -> None:
        """Test parsing invalid VTG sentence."""
        parser = NMEAParser()
        
        invalid_sentence = "$GPVTG,invalid,data*48"
        result = parser.parse_vtg(invalid_sentence)
        
        assert result is None
    
    def test_ddm_to_dd_conversion(self) -> None:
        """Test degrees decimal minutes to decimal degrees conversion."""
        parser = NMEAParser()
        
        # Test North latitude
        lat_n = parser._ddm_to_dd(4807.038, 'N')
        assert abs(lat_n - 48.1173) < 0.0001
        
        # Test South latitude
        lat_s = parser._ddm_to_dd(4807.038, 'S')
        assert abs(lat_s - (-48.1173)) < 0.0001
        
        # Test East longitude
        lon_e = parser._ddm_to_dd(1131.000, 'E')
        assert abs(lon_e - 11.5167) < 0.0001
        
        # Test West longitude
        lon_w = parser._ddm_to_dd(1131.000, 'W')
        assert abs(lon_w - (-11.5167)) < 0.0001


class TestGPSService:
    """Test GPS service functionality."""
    
    def test_gps_service_initialization(self) -> None:
        """Test GPS service initializes correctly."""
        service = GPSService(
            port="/dev/ttyUSB0",
            baudrate=4800,
            rate_hz=1.0,
        )
        
        assert service.port == "/dev/ttyUSB0"
        assert service.baudrate == 4800
        assert service.rate_hz == 1.0
        assert service.is_running is False
        assert service.session_id is None
        assert service.sentences_received == 0
        assert service.sentences_parsed == 0
    
    def test_get_unit_mapping(self) -> None:
        """Test GPS channel unit mapping."""
        service = GPSService()
        
        assert service._get_unit("latitude") == "degrees"
        assert service._get_unit("longitude") == "degrees"
        assert service._get_unit("altitude") == "meters"
        assert service._get_unit("speed_kph") == "kph"
        assert service._get_unit("course") == "degrees"
        assert service._get_unit("hdop") == "dimensionless"
        assert service._get_unit("satellites") == "count"
        assert service._get_unit("unknown") is None
    
    def test_get_status(self) -> None:
        """Test GPS service status reporting."""
        service = GPSService()
        
        status = service.get_status()
        
        assert "is_running" in status
        assert "port" in status
        assert "baudrate" in status
        assert "rate_hz" in status
        assert "session_id" in status
        assert "sentences_received" in status
        assert "sentences_parsed" in status
        assert "reconnect_count" in status
        assert "last_known_values" in status
        assert "serial_connected" in status
    
    @patch('serial.tools.list_ports.comports')
    def test_list_available_ports(self, mock_comports) -> None:
        """Test listing available serial ports."""
        # Mock available ports
        mock_port1 = MagicMock()
        mock_port1.device = "/dev/ttyUSB0"
        mock_port2 = MagicMock()
        mock_port2.device = "/dev/ttyUSB1"
        mock_comports.return_value = [mock_port1, mock_port2]
        
        ports = GPSService.list_available_ports()
        
        assert "/dev/ttyUSB0" in ports
        assert "/dev/ttyUSB1" in ports
        assert len(ports) == 2
    
    @patch('backend.app.services.gps_service.websocket_bus')
    async def test_handle_parsed_data(self, mock_websocket_bus) -> None:
        """Test handling parsed GPS data."""
        service = GPSService()
        service.session_id = 1
        
        # Mock websocket bus
        mock_websocket_bus.broadcast_to_session = AsyncMock()
        
        # Test data
        test_data = {
            "sentence_type": "GGA",
            "latitude": 48.1173,
            "longitude": 11.5167,
            "altitude": 545.4,
        }
        
        await service._handle_parsed_data(test_data)
        
        # Check last known values updated
        assert service.last_known_values["latitude"] == 48.1173
        assert service.last_known_values["longitude"] == 11.5167
        assert service.last_known_values["altitude"] == 545.4
        
        # Check WebSocket broadcast called
        mock_websocket_bus.broadcast_to_session.assert_called_once()
        call_args = mock_websocket_bus.broadcast_to_session.call_args
        assert call_args[0][0] == 1  # session_id
        assert call_args[0][1]["source"] == "gps"
        assert call_args[0][1]["sentence_type"] == "GGA"
    
    async def test_start_and_stop(self) -> None:
        """Test starting and stopping GPS service."""
        service = GPSService(port="/dev/ttyUSB0")
        
        # Start service
        await service.start(session_id=1)
        assert service.is_running is True
        assert service.session_id == 1
        
        # Stop service
        await service.stop()
        assert service.is_running is False


class TestGPSIntegration:
    """Integration tests for GPS service with sample NMEA data."""
    
    @pytest.fixture
    def sample_nmea_file(self) -> Path:
        """Create a temporary file with sample NMEA data."""
        sample_data = """$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47
$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A
$GPVTG,054.7,T,034.4,M,005.5,N,010.2,K*48
$GPGGA,123520,4807.039,N,01131.001,E,1,08,0.9,545.5,M,46.9,M,,*48
$GPRMC,123520,A,4807.039,N,01131.001,E,022.5,084.5,230394,003.1,W*6B
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.nmea', delete=False) as f:
            f.write(sample_data)
            return Path(f.name)
    
    @patch('backend.app.services.gps_service.websocket_bus')
    async def test_process_sample_nmea_data(self, mock_websocket_bus, sample_nmea_file) -> None:
        """Test processing sample NMEA data from file."""
        service = GPSService()
        service.session_id = 1
        
        # Mock websocket bus
        mock_websocket_bus.broadcast_to_session = AsyncMock()
        
        # Read and process sample data
        with open(sample_nmea_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    await service._process_nmea_sentence(line)
        
        # Check statistics
        assert service.sentences_received == 5
        assert service.sentences_parsed == 5
        
        # Check last known values
        assert "latitude" in service.last_known_values
        assert "longitude" in service.last_known_values
        assert "altitude" in service.last_known_values
        assert "speed_kph" in service.last_known_values
        
        # Check WebSocket broadcasts
        assert mock_websocket_bus.broadcast_to_session.call_count == 5
        
        # Clean up
        sample_nmea_file.unlink()
    
    @patch('backend.app.services.gps_service.websocket_bus')
    async def test_serial_connection_simulation(self, mock_websocket_bus) -> None:
        """Test GPS service with simulated serial connection."""
        # Mock websocket bus
        mock_websocket_bus.broadcast_to_session = AsyncMock()
        
        service = GPSService(port="/dev/ttyUSB0", rate_hz=10.0)
        service.session_id = 1
        
        # Test processing NMEA sentences directly (simulating serial input)
        test_sentences = [
            "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47",
            "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A",
        ]
        
        for sentence in test_sentences:
            await service._process_nmea_sentence(sentence)
        
        # Check that data was processed
        assert service.sentences_received == 2
        assert service.sentences_parsed == 2
        
        # Check WebSocket broadcasts
        assert mock_websocket_bus.broadcast_to_session.call_count == 2


# Pytest configuration for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
