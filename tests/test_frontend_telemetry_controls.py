"""Tests for frontend telemetry controls."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


class TestFrontendTelemetryControls:
    """Test frontend telemetry controls functionality."""
    
    def test_dashboard_has_telemetry_controls(self, client: TestClient):
        """Test that dashboard has telemetry control buttons."""
        response = client.get("/index.html")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for telemetry control buttons
        assert 'id="start-telemetry-btn"' in content
        assert 'id="stop-telemetry-btn"' in content
        assert 'Start Telemetry' in content
        assert 'Stop Telemetry' in content
        
        # Check for telemetry status display
        assert 'id="session-id-display"' in content
        assert 'id="elapsed-time-display"' in content
        assert 'telemetry-controls' in content
    
    def test_telemetry_api_endpoints_accessible(self, client: TestClient):
        """Test that telemetry API endpoints are accessible."""
        # Test status endpoint
        response = client.get("/api/v1/telemetry/status")
        assert response.status_code == 200
        
        # Test start endpoint (should fail without proper setup)
        response = client.post("/api/v1/telemetry/start", json={})
        assert response.status_code in [400, 500]  # Expected to fail in test environment
        
        # Test stop endpoint (should fail when not running)
        response = client.post("/api/v1/telemetry/stop")
        assert response.status_code == 400  # Expected to fail when not running
    
    def test_app_js_includes_telemetry_functionality(self, client: TestClient):
        """Test that app.js includes telemetry control functionality."""
        response = client.get("/js/app.js")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for telemetry-related methods
        assert 'startTelemetry' in content
        assert 'stopTelemetry' in content
        assert 'checkTelemetryStatus' in content
        assert 'updateTelemetryUI' in content
        assert 'startElapsedTimer' in content
        assert 'stopElapsedTimer' in content
        
        # Check for API calls
        assert '/api/v1/telemetry/start' in content
        assert '/api/v1/telemetry/stop' in content
        assert '/api/v1/telemetry/status' in content
        
        # Check for event binding
        assert 'start-telemetry-btn' in content
        assert 'stop-telemetry-btn' in content
    
    def test_telemetry_controls_have_loading_states(self, client: TestClient):
        """Test that telemetry controls have loading states."""
        response = client.get("/js/app.js")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for loading state management
        assert 'Starting...' in content
        assert 'Stopping...' in content
        assert 'loading.style.display' in content
        assert 'disabled = true' in content
        assert 'disabled = false' in content
    
    def test_telemetry_status_display_logic(self, client: TestClient):
        """Test telemetry status display logic."""
        response = client.get("/js/app.js")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for status display logic
        assert 'is_running' in content
        assert 'session_id' in content
        assert 'session_name' in content
        assert 'start_time' in content
        assert 'elapsed' in content
    
    def test_elapsed_time_calculation(self, client: TestClient):
        """Test elapsed time calculation functionality."""
        response = client.get("/js/app.js")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for elapsed time calculation
        assert 'elapsed' in content
        assert 'hours' in content
        assert 'minutes' in content
        assert 'seconds' in content
        assert 'padStart' in content
        assert 'setInterval' in content
        assert 'clearInterval' in content
    
    def test_telemetry_error_handling(self, client: TestClient):
        """Test telemetry error handling."""
        response = client.get("/js/app.js")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for error handling
        assert 'catch (error)' in content
        assert 'showError' in content
        assert 'showSuccess' in content
        assert 'Failed to start telemetry' in content
        assert 'Failed to stop telemetry' in content
    
    def test_telemetry_ui_state_management(self, client: TestClient):
        """Test telemetry UI state management."""
        response = client.get("/js/app.js")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for UI state management
        assert 'telemetryRunning' in content
        assert 'currentSessionId' in content
        assert 'sessionStartTime' in content
        assert 'elapsedInterval' in content
        
        # Check for UI updates
        assert 'style.display' in content
        assert 'textContent' in content
        assert 'style.color' in content
    
    def test_telemetry_session_refresh(self, client: TestClient):
        """Test that telemetry actions refresh session list."""
        response = client.get("/js/app.js")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for session list refresh
        assert 'loadSessions()' in content
        assert 'refresh' in content.lower() or 'reload' in content.lower()
    
    def test_telemetry_controls_css_styling(self, client: TestClient):
        """Test that telemetry controls have proper CSS styling."""
        response = client.get("/css/styles.css")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for telemetry control styles
        assert '.telemetry-controls' in content
        assert '.telemetry-status' in content
        assert '#session-id-display' in content
        assert '#elapsed-time-display' in content
        
        # Check for button styles
        assert '.btn-success' in content
        assert '.btn-danger' in content
        assert '.loading' in content


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)
