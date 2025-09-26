"""Tests for device scanning API endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app


class TestDeviceScanning:
    """Test device scanning functionality."""
    
    def test_scan_devices_success(self, client: TestClient):
        """Test successful device scanning."""
        # Mock serial ports
        mock_port = MagicMock()
        mock_port.device = "/dev/ttyUSB0"
        mock_port.vid = 0x1234
        mock_port.pid = 0x5678
        mock_port.description = "USB Serial Device"
        mock_port.hwid = "USB VID:PID=1234:5678"
        
        with patch('serial.tools.list_ports.comports', return_value=[mock_port]):
            with patch('cv2.VideoCapture') as mock_cv2:
                # Mock camera detection - only first camera works
                def mock_camera_constructor(index):
                    mock_cap = MagicMock()
                    if index == 0:  # Only first camera works
                        mock_cap.isOpened.return_value = True
                        mock_cap.read.return_value = (True, None)
                    else:  # Others don't work
                        mock_cap.isOpened.return_value = False
                    return mock_cap
                
                mock_cv2.side_effect = mock_camera_constructor
                
                response = client.get("/api/v1/devices/scan")
                
                assert response.status_code == 200
                data = response.json()
                
                assert "serial_ports" in data
                assert "cameras" in data
                assert "scan_time" in data
                
                # Check serial port data
                assert len(data["serial_ports"]) == 1
                port = data["serial_ports"][0]
                assert port["path"] == "/dev/ttyUSB0"
                assert port["vid"] == 0x1234
                assert port["pid"] == 0x5678
                assert port["desc"] == "USB Serial Device"
                assert port["hwid"] == "USB VID:PID=1234:5678"
                
                # Check camera data
                assert len(data["cameras"]) == 1
                camera = data["cameras"][0]
                assert camera["path"] == "/dev/video0"
                assert camera["name"] == "Camera 0"
                assert camera["index"] == 0
    
    def test_scan_devices_no_serial_ports(self, client: TestClient):
        """Test device scanning with no serial ports."""
        with patch('serial.tools.list_ports.comports', return_value=[]):
            with patch('cv2.VideoCapture') as mock_cv2:
                # Mock no cameras
                mock_cap = MagicMock()
                mock_cap.isOpened.return_value = False
                mock_cv2.return_value = mock_cap
                
                response = client.get("/api/v1/devices/scan")
                
                assert response.status_code == 200
                data = response.json()
                
                assert len(data["serial_ports"]) == 0
                assert len(data["cameras"]) == 0
    
    def test_scan_devices_pyserial_not_available(self, client: TestClient):
        """Test device scanning when pyserial is not available."""
        with patch('serial.tools.list_ports.comports', side_effect=ImportError):
            response = client.get("/api/v1/devices/scan")
            
            assert response.status_code == 200
            data = response.json()
            
            assert len(data["serial_ports"]) == 0
            assert "scan_time" in data
    
    def test_scan_devices_opencv_not_available(self, client: TestClient):
        """Test device scanning when OpenCV is not available."""
        with patch('serial.tools.list_ports.comports', return_value=[]):
            with patch('cv2.VideoCapture', side_effect=ImportError):
                response = client.get("/api/v1/devices/scan")
                
                assert response.status_code == 200
                data = response.json()
                
                assert len(data["cameras"]) == 0
                assert "scan_time" in data
    
    def test_scan_devices_serial_error(self, client: TestClient):
        """Test device scanning with serial port error."""
        with patch('serial.tools.list_ports.comports', side_effect=Exception("Serial error")):
            response = client.get("/api/v1/devices/scan")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should return empty list on error
            assert len(data["serial_ports"]) == 0
    
    def test_scan_devices_camera_error(self, client: TestClient):
        """Test device scanning with camera error."""
        with patch('serial.tools.list_ports.comports', return_value=[]):
            with patch('cv2.VideoCapture', side_effect=Exception("Camera error")):
                response = client.get("/api/v1/devices/scan")
                
                assert response.status_code == 200
                data = response.json()
                
                # Should return empty list on error
                assert len(data["cameras"]) == 0
    
    def test_scan_devices_multiple_ports(self, client: TestClient):
        """Test device scanning with multiple serial ports."""
        # Mock multiple ports
        mock_ports = []
        for i in range(3):
            mock_port = MagicMock()
            mock_port.device = f"/dev/ttyUSB{i}"
            mock_port.vid = 0x1234 + i
            mock_port.pid = 0x5678 + i
            mock_port.description = f"USB Device {i}"
            mock_port.hwid = f"USB VID:PID={0x1234 + i:04x}:{0x5678 + i:04x}"
            mock_ports.append(mock_port)
        
        with patch('serial.tools.list_ports.comports', return_value=mock_ports):
            with patch('cv2.VideoCapture') as mock_cv2:
                # Mock no cameras
                mock_cap = MagicMock()
                mock_cap.isOpened.return_value = False
                mock_cv2.return_value = mock_cap
                
                response = client.get("/api/v1/devices/scan")
                
                assert response.status_code == 200
                data = response.json()
                
                assert len(data["serial_ports"]) == 3
                
                # Check each port
                for i, port in enumerate(data["serial_ports"]):
                    assert port["path"] == f"/dev/ttyUSB{i}"
                    assert port["vid"] == 0x1234 + i
                    assert port["pid"] == 0x5678 + i
                    assert port["desc"] == f"USB Device {i}"
    
    def test_scan_devices_multiple_cameras(self, client: TestClient):
        """Test device scanning with multiple cameras."""
        with patch('serial.tools.list_ports.comports', return_value=[]):
            with patch('cv2.VideoCapture') as mock_cv2:
                # Mock multiple cameras
                def mock_camera_constructor(index):
                    mock_cap = MagicMock()
                    if index < 2:  # First 2 cameras work
                        mock_cap.isOpened.return_value = True
                        mock_cap.read.return_value = (True, None)
                    else:  # Others don't work
                        mock_cap.isOpened.return_value = False
                    return mock_cap
                
                mock_cv2.side_effect = mock_camera_constructor
                
                response = client.get("/api/v1/devices/scan")
                
                assert response.status_code == 200
                data = response.json()
                
                assert len(data["cameras"]) == 2
                
                # Check each camera
                for i, camera in enumerate(data["cameras"]):
                    assert camera["path"] == f"/dev/video{i}"
                    assert camera["name"] == f"Camera {i}"
                    assert camera["index"] == i


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)
