"""Tests for telemetry start/stop controls."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from backend.app.main import app


class TestTelemetryControls:
    """Test telemetry start/stop functionality."""
    
    def test_start_telemetry_success(self, client: TestClient):
        """Test successful telemetry start."""
        with patch('backend.app.api.routes_telemetry.get_service_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.is_running.return_value = False
            mock_manager.start_session = AsyncMock(return_value=True)
            mock_get_manager.return_value = mock_manager
            
            with patch('backend.app.api.routes_telemetry.device_profile_crud.get_default') as mock_get_profile:
                mock_profile = MagicMock()
                mock_profile.id = 1
                mock_get_profile.return_value = mock_profile
                
                with patch('backend.app.api.routes_telemetry.session_crud.create') as mock_create_session:
                    mock_session = MagicMock()
                    mock_session.id = 123
                    mock_session.name = "Test Session"
                    mock_create_session.return_value = mock_session
                    
                    response = client.post("/api/v1/telemetry/start", json={
                        "session_name": "Test Session"
                    })
                    
                    assert response.status_code == 200
                    data = response.json()
                    
                    assert data["success"] is True
                    assert data["session_id"] == 123
                    assert data["session_name"] == "Test Session"
                    assert data["profile_id"] == 1
                    assert "successfully" in data["message"]
    
    def test_start_telemetry_already_running(self, client: TestClient):
        """Test starting telemetry when already running."""
        with patch('backend.app.api.routes_telemetry.get_service_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.is_running.return_value = True
            mock_get_manager.return_value = mock_manager
            
            response = client.post("/api/v1/telemetry/start", json={
                "session_name": "Test Session"
            })
            
            assert response.status_code == 400
            data = response.json()
            assert "already running" in data["detail"]
    
    def test_start_telemetry_no_profile(self, client: TestClient):
        """Test starting telemetry with no profile available."""
        with patch('backend.app.api.routes_telemetry.get_service_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.is_running.return_value = False
            mock_get_manager.return_value = mock_manager
            
            with patch('backend.app.api.routes_telemetry.device_profile_crud.get_default') as mock_get_profile:
                mock_get_profile.return_value = None
                
                response = client.post("/api/v1/telemetry/start", json={
                    "session_name": "Test Session"
                })
                
                assert response.status_code == 400
                data = response.json()
                assert "No profile specified" in data["detail"]
    
    def test_stop_telemetry_success(self, client: TestClient):
        """Test successful telemetry stop."""
        with patch('backend.app.api.routes_telemetry.get_service_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.is_running.return_value = True
            mock_manager.get_current_session_id.return_value = 123
            mock_manager.stop_session = AsyncMock(return_value=True)
            mock_get_manager.return_value = mock_manager
            
            response = client.post("/api/v1/telemetry/stop")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["session_id"] == 123
            assert "successfully" in data["message"]
    
    def test_stop_telemetry_not_running(self, client: TestClient):
        """Test stopping telemetry when not running."""
        with patch('backend.app.api.routes_telemetry.get_service_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.is_running.return_value = False
            mock_get_manager.return_value = mock_manager
            
            response = client.post("/api/v1/telemetry/stop")
            
            assert response.status_code == 400
            data = response.json()
            assert "not currently running" in data["detail"]
    
    def test_get_telemetry_status_running(self, client: TestClient):
        """Test getting telemetry status when running."""
        with patch('backend.app.api.routes_telemetry.get_service_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.is_running.return_value = True
            mock_manager.get_current_session_id.return_value = 123
            mock_get_manager.return_value = mock_manager
            
            with patch('backend.app.api.routes_telemetry.session_crud.get_by_id') as mock_get_session:
                mock_session = MagicMock()
                mock_session.id = 123
                mock_session.name = "Test Session"
                mock_session.profile_id = 1
                mock_session.created_at = datetime.now(timezone.utc)
                mock_get_session.return_value = mock_session
                
                response = client.get("/api/v1/telemetry/status")
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["is_running"] is True
                assert data["session_id"] == 123
                assert data["session_name"] == "Test Session"
                assert data["profile_id"] == 1
                assert data["start_time"] is not None
                assert data["elapsed_seconds"] is not None
    
    def test_get_telemetry_status_not_running(self, client: TestClient):
        """Test getting telemetry status when not running."""
        with patch('backend.app.api.routes_telemetry.get_service_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.is_running.return_value = False
            mock_manager.get_current_session_id.return_value = None
            mock_get_manager.return_value = mock_manager
            
            response = client.get("/api/v1/telemetry/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["is_running"] is False
            assert data["session_id"] is None
            assert data["session_name"] is None
            assert data["profile_id"] is None
            assert data["start_time"] is None
            assert data["elapsed_seconds"] is None
    
    def test_start_telemetry_service_error(self, client: TestClient):
        """Test telemetry start with service error."""
        with patch('backend.app.api.routes_telemetry.get_service_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.is_running.return_value = False
            mock_manager.start_session = AsyncMock(side_effect=Exception("Service error"))
            mock_get_manager.return_value = mock_manager
            
            with patch('backend.app.api.routes_telemetry.device_profile_crud.get_default') as mock_get_profile:
                mock_profile = MagicMock()
                mock_profile.id = 1
                mock_get_profile.return_value = mock_profile
                
                with patch('backend.app.api.routes_telemetry.session_crud.create') as mock_create_session:
                    mock_session = MagicMock()
                    mock_session.id = 123
                    mock_session.name = "Test Session"
                    mock_create_session.return_value = mock_session
                    
                    response = client.post("/api/v1/telemetry/start", json={
                        "session_name": "Test Session"
                    })
                    
                    assert response.status_code == 500
                    data = response.json()
                    assert "Failed to start telemetry" in data["detail"]
    
    def test_stop_telemetry_service_error(self, client: TestClient):
        """Test telemetry stop with service error."""
        with patch('backend.app.api.routes_telemetry.get_service_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.is_running.return_value = True
            mock_manager.get_current_session_id.return_value = 123
            mock_manager.stop_session = AsyncMock(side_effect=Exception("Service error"))
            mock_get_manager.return_value = mock_manager
            
            response = client.post("/api/v1/telemetry/stop")
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to stop telemetry" in data["detail"]


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)
