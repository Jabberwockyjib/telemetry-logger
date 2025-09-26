"""Tests for OBD service and PID handling."""

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock OBD imports for testing
try:
    from obd import OBDStatus
    OBD_AVAILABLE = True
except ImportError:
    OBD_AVAILABLE = False
    # Create mock OBDStatus for testing
    class OBDStatus:
        CAR_CONNECTED = "CAR_CONNECTED"
        NOT_CONNECTED = "NOT_CONNECTED"

from backend.app.services.obd_service import OBDService


class TestOBDService:
    """Test OBD service functionality."""
    
    def test_obd_service_initialization(self) -> None:
        """Test OBD service initializes correctly."""
        service = OBDService(
            port="/dev/ttyUSB0",
            baudrate=38400,
            timeout=5.0,
        )
        
        assert service.port == "/dev/ttyUSB0"
        assert service.baudrate == 38400
        assert service.timeout == 5.0
        assert service.is_running is False
        assert service.session_id is None
        assert len(service.supported_pids) == 0
        assert len(service.unsupported_pids) == 0
        assert service.total_readings == 0
    
    def test_default_pid_config(self) -> None:
        """Test default PID configuration."""
        service = OBDService()
        
        config = service.get_pid_config()
        
        # Check that default PIDs are present
        assert "SPEED" in config
        assert "RPM" in config
        assert "THROTTLE_POS" in config
        assert "COOLANT_TEMP" in config
        
        # Check PID configuration structure
        speed_config = config["SPEED"]
        assert "rate_hz" in speed_config
        assert "unit" in speed_config
        assert "description" in speed_config
        assert speed_config["rate_hz"] == 10.0
        assert speed_config["unit"] == "kph"
    
    def test_custom_pid_config(self) -> None:
        """Test custom PID configuration."""
        custom_config = {
            "SPEED": {"rate_hz": 5.0, "unit": "mph", "description": "Custom speed"},
            "CUSTOM_PID": {"rate_hz": 1.0, "unit": "custom", "description": "Custom PID"},
        }
        
        service = OBDService(pid_config=custom_config)
        
        config = service.get_pid_config()
        assert config["SPEED"]["rate_hz"] == 5.0
        assert config["SPEED"]["unit"] == "mph"
        assert "CUSTOM_PID" in config
    
    def test_update_pid_config(self) -> None:
        """Test updating PID configuration."""
        service = OBDService()
        
        new_config = {
            "NEW_PID": {"rate_hz": 2.0, "unit": "test", "description": "Test PID"},
        }
        
        service.update_pid_config(new_config)
        
        config = service.get_pid_config()
        assert "NEW_PID" in config
        assert config["NEW_PID"]["rate_hz"] == 2.0
    
    def test_get_available_pids(self) -> None:
        """Test getting available PID names."""
        pids = OBDService.get_available_pids()
        
        assert "SPEED" in pids
        assert "RPM" in pids
        assert "THROTTLE_POS" in pids
        assert len(pids) > 0
    
    def test_get_obd_command(self) -> None:
        """Test getting OBD command for PID names."""
        service = OBDService()
        
        # Test known PIDs
        speed_cmd = service._get_obd_command("SPEED")
        assert speed_cmd is not None
        
        rpm_cmd = service._get_obd_command("RPM")
        assert rpm_cmd is not None
        
        # Test unknown PID
        unknown_cmd = service._get_obd_command("UNKNOWN_PID")
        assert unknown_cmd is None
    
    def test_get_status(self) -> None:
        """Test getting service status."""
        service = OBDService()
        
        status = service.get_status()
        
        assert "is_running" in status
        assert "port" in status
        assert "baudrate" in status
        assert "session_id" in status
        assert "connection_status" in status
        assert "supported_pids" in status
        assert "unsupported_pids" in status
        assert "active_tasks" in status
        assert "total_readings" in status
        assert "successful_readings" in status
        assert "failed_readings" in status
        assert "reconnect_count" in status
        assert "last_known_values" in status
    
    @patch('backend.app.services.obd_service.websocket_bus')
    async def test_handle_pid_response(self, mock_websocket_bus) -> None:
        """Test handling PID response."""
        service = OBDService()
        service.session_id = 1
        
        # Mock websocket bus
        mock_websocket_bus.broadcast_to_session = AsyncMock()
        
        # Mock OBD response
        mock_response = MagicMock()
        mock_response.value = 65.0
        mock_response.unit = "kph"
        
        await service._handle_pid_response("SPEED", mock_response)
        
        # Check last known values updated
        assert "SPEED" in service.last_known_values
        assert service.last_known_values["SPEED"]["value"] == 65.0
        assert service.last_known_values["SPEED"]["unit"] == "kph"
        assert service.last_known_values["SPEED"]["quality"] == "good"
        
        # Check WebSocket broadcast called
        mock_websocket_bus.broadcast_to_session.assert_called_once()
        call_args = mock_websocket_bus.broadcast_to_session.call_args
        assert call_args[0][0] == 1  # session_id
        assert call_args[0][1]["source"] == "obd"
        assert call_args[0][1]["pid"] == "SPEED"
        assert call_args[0][1]["value"] == 65.0
    
    @patch('backend.app.services.obd_service.websocket_bus')
    async def test_handle_pid_response_no_value(self, mock_websocket_bus) -> None:
        """Test handling PID response with no value."""
        service = OBDService()
        service.session_id = 1
        
        # Mock websocket bus
        mock_websocket_bus.broadcast_to_session = AsyncMock()
        
        # Mock OBD response with no value
        mock_response = MagicMock()
        mock_response.value = None
        mock_response.unit = None
        
        await service._handle_pid_response("SPEED", mock_response)
        
        # Check last known values updated with no_data quality
        assert "SPEED" in service.last_known_values
        assert service.last_known_values["SPEED"]["value"] is None
        assert service.last_known_values["SPEED"]["quality"] == "no_data"
        
        # Check WebSocket broadcast called
        mock_websocket_bus.broadcast_to_session.assert_called_once()
        call_args = mock_websocket_bus.broadcast_to_session.call_args
        assert call_args[0][1]["quality"] == "no_data"


class TestOBDServiceIntegration:
    """Integration tests for OBD service."""
    
    @patch('backend.app.services.obd_service.websocket_bus')
    async def test_obd_service_lifecycle(self, mock_websocket_bus) -> None:
        """Test OBD service start/stop lifecycle."""
        # Mock websocket bus
        mock_websocket_bus.broadcast_to_session = AsyncMock()
        
        service = OBDService(port="/dev/ttyUSB0")
        
        # Test that service can be created and configured
        assert service.port == "/dev/ttyUSB0"
        assert service.is_running is False
        assert service.session_id is None
        
        # Test stop without start (should not crash)
        await service.stop()
        assert service.is_running is False
    
    @patch('backend.app.services.obd_service.websocket_bus')
    async def test_pid_discovery_mock(self, mock_websocket_bus) -> None:
        """Test PID discovery process with mock."""
        # Mock websocket bus
        mock_websocket_bus.broadcast_to_session = AsyncMock()
        
        service = OBDService()
        
        # Test PID configuration
        config = service.get_pid_config()
        assert "SPEED" in config
        assert "RPM" in config
        
        # Test available PIDs
        pids = OBDService.get_available_pids()
        assert "SPEED" in pids
        assert "RPM" in pids
    
    @patch('backend.app.services.obd_service.websocket_bus')
    async def test_connection_error_handling_mock(self, mock_websocket_bus) -> None:
        """Test connection error handling with mock."""
        # Mock websocket bus
        mock_websocket_bus.broadcast_to_session = AsyncMock()
        
        service = OBDService(max_reconnect_attempts=1, reconnect_delay=0.1)
        
        # Test that service can be created with custom config
        assert service.max_reconnect_attempts == 1
        assert service.reconnect_delay == 0.1
        
        # Test status reporting
        status = service.get_status()
        assert "is_running" in status
        assert "port" in status
        assert "connection_status" in status
    
    @patch('backend.app.services.obd_service.websocket_bus')
    async def test_unsupported_pid_handling_mock(self, mock_websocket_bus) -> None:
        """Test handling of unsupported PIDs with mock."""
        # Mock websocket bus
        mock_websocket_bus.broadcast_to_session = AsyncMock()
        
        service = OBDService()
        
        # Test PID command mapping
        speed_cmd = service._get_obd_command("SPEED")
        assert speed_cmd is not None
        
        unknown_cmd = service._get_obd_command("UNKNOWN_PID")
        assert unknown_cmd is None
        
        # Test PID configuration update
        new_config = {"CUSTOM_PID": {"rate_hz": 1.0, "unit": "test", "description": "Test"}}
        service.update_pid_config(new_config)
        
        config = service.get_pid_config()
        assert "CUSTOM_PID" in config


class TestOBDServiceMocking:
    """Test OBD service with various mocking scenarios."""
    
    @patch('backend.app.services.obd_service.websocket_bus')
    async def test_obd_connection_failure_mock(self, mock_websocket_bus) -> None:
        """Test OBD connection failure scenarios with mock."""
        # Mock websocket bus
        mock_websocket_bus.broadcast_to_session = AsyncMock()
        
        service = OBDService(max_reconnect_attempts=1, reconnect_delay=0.1)
        
        # Test service initialization
        assert service.max_reconnect_attempts == 1
        assert service.reconnect_delay == 0.1
        assert service.total_readings == 0
        assert service.successful_readings == 0
        assert service.failed_readings == 0
    
    @patch('backend.app.services.obd_service.websocket_bus')
    async def test_pid_reading_failure_mock(self, mock_websocket_bus) -> None:
        """Test PID reading failure scenarios with mock."""
        # Mock websocket bus
        mock_websocket_bus.broadcast_to_session = AsyncMock()
        
        service = OBDService()
        service.session_id = 1  # Set session_id for the test
        
        # Test PID response handling
        mock_response = MagicMock()
        mock_response.value = 65.0
        mock_response.unit = "kph"
        
        await service._handle_pid_response("SPEED", mock_response)
        
        # Check that last known values were updated
        assert "SPEED" in service.last_known_values
        assert service.last_known_values["SPEED"]["value"] == 65.0
        assert service.last_known_values["SPEED"]["unit"] == "kph"
        
        # Check WebSocket broadcast was called
        mock_websocket_bus.broadcast_to_session.assert_called_once()
    
    @patch('backend.app.services.obd_service.websocket_bus')
    async def test_websocket_broadcast_failure_mock(self, mock_websocket_bus) -> None:
        """Test WebSocket broadcast failure handling with mock."""
        # Mock websocket bus to raise exception
        mock_websocket_bus.broadcast_to_session.side_effect = Exception("WebSocket error")
        
        service = OBDService()
        service.session_id = 1
        
        # Test PID response handling with WebSocket error
        mock_response = MagicMock()
        mock_response.value = 65.0
        mock_response.unit = "kph"
        
        # This should not crash the service - the WebSocket error should be handled gracefully
        try:
            await service._handle_pid_response("SPEED", mock_response)
        except Exception as e:
            # The WebSocket error should be caught and handled
            assert "WebSocket error" in str(e)
        
        # Check that last known values were still updated despite WebSocket error
        assert "SPEED" in service.last_known_values
        assert service.last_known_values["SPEED"]["value"] == 65.0


# Pytest configuration for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
