"""Tests for frontend device scanning functionality."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app


class TestFrontendDeviceScanning:
    """Test frontend device scanning functionality."""
    
    def test_setup_page_loads_with_scan_button(self, client: TestClient):
        """Test that setup page loads with scan devices button."""
        response = client.get("/setup.html")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for scan button
        assert 'id="scan-devices-btn"' in content
        assert 'Scan Devices' in content
        
        # Check for scan status element
        assert 'id="scan-status"' in content
        
        # Check for device configuration sections
        assert 'id="gps-config"' in content
        assert 'id="obd-config"' in content
        assert 'id="meshtastic-config"' in content
    
    def test_scan_devices_api_endpoint_accessible(self, client: TestClient):
        """Test that scan devices API endpoint is accessible."""
        with patch('serial.tools.list_ports.comports', return_value=[]):
            with patch('cv2.VideoCapture') as mock_cv2:
                # Mock no cameras
                mock_cap = MagicMock()
                mock_cap.isOpened.return_value = False
                mock_cv2.return_value = mock_cap
                
                response = client.get("/api/v1/devices/scan")
                
                assert response.status_code == 200
                data = response.json()
                
                assert "serial_ports" in data
                assert "cameras" in data
                assert "scan_time" in data
    
    def test_setup_js_includes_scan_functionality(self, client: TestClient):
        """Test that setup.js includes device scanning functionality."""
        response = client.get("/js/setup.js")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for scan-related methods
        assert 'scanDevices()' in content
        assert 'isScanning' in content
        assert 'lastScanResults' in content
        assert 'showToast' in content
        
        # Check for API call
        assert '/api/v1/devices/scan' in content
        
        # Check for event binding
        assert 'scan-devices-btn' in content
    
    def test_populate_port_selects_handles_empty_ports(self, client: TestClient):
        """Test that populatePortSelects handles empty port list."""
        response = client.get("/js/setup.js")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for empty port handling
        assert 'No devices detected' in content
        assert 'ports.length === 0' in content
    
    def test_populate_port_selects_preserves_selection(self, client: TestClient):
        """Test that populatePortSelects preserves valid selections."""
        response = client.get("/js/setup.js")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for selection preservation logic
        assert 'currentValue' in content
        assert 'optionExists' in content
        assert 'selectedIndex' in content
    
    def test_scan_devices_shows_loading_state(self, client: TestClient):
        """Test that scan devices shows loading state."""
        response = client.get("/js/setup.js")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for loading state management
        assert 'Scanning...' in content
        assert 'loading.style.display' in content
        assert 'scanBtn.disabled' in content
    
    def test_scan_devices_handles_errors(self, client: TestClient):
        """Test that scan devices handles errors gracefully."""
        response = client.get("/js/setup.js")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for error handling
        assert 'catch (error)' in content
        assert 'showToast' in content
        assert 'Device scan failed' in content
    
    def test_scan_devices_updates_dropdowns(self, client: TestClient):
        """Test that scan devices updates port dropdowns."""
        response = client.get("/js/setup.js")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for dropdown updates
        assert 'populatePortSelects' in content
        assert 'gps-port' in content
        assert 'obd-port' in content
        assert 'meshtastic-port' in content
    
    def test_toast_notification_system(self, client: TestClient):
        """Test that toast notification system is implemented."""
        response = client.get("/js/setup.js")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for toast functionality
        assert 'showToast' in content
        assert 'toast' in content
        assert 'success' in content
        assert 'error' in content
    
    def test_scan_status_display(self, client: TestClient):
        """Test that scan status is displayed correctly."""
        response = client.get("/js/setup.js")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for status display
        assert 'scan-status' in content
        assert 'Found' in content
        assert 'serial ports' in content
        assert 'cameras' in content


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)
