"""
Integration tests for session creation functionality.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


class TestSessionCreationIntegration:
    """Test session creation integration with full API flow."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_create_session_with_all_fields(self, client):
        """Test creating a session with all fields populated."""
        session_data = {
            "name": "Test Track Day",
            "car_id": "CAR001",
            "driver": "John Doe",
            "track": "Laguna Seca",
            "notes": "First track day of the season"
        }
        
        response = client.post("/api/v1/sessions", json=session_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert data["name"] == "Test Track Day"
        assert data["car_id"] == "CAR001"
        assert data["driver"] == "John Doe"
        assert data["track"] == "Laguna Seca"
        assert data["notes"] == "First track day of the season"
        assert "created_utc" in data
        assert "is_active" in data
        assert data["is_active"] is False  # New sessions should not be active

    def test_create_session_with_required_fields_only(self, client):
        """Test creating a session with only required fields."""
        session_data = {
            "name": "Minimal Session"
        }
        
        response = client.post("/api/v1/sessions", json=session_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert data["name"] == "Minimal Session"
        assert data["car_id"] is None
        assert data["driver"] is None
        assert data["track"] is None
        assert data["notes"] is None
        assert "created_utc" in data
        assert "is_active" in data

    def test_create_session_validation_errors(self, client):
        """Test session creation validation errors."""
        # Test missing required name
        response = client.post("/api/v1/sessions", json={})
        assert response.status_code == 422
        
        # Test empty name
        response = client.post("/api/v1/sessions", json={"name": ""})
        assert response.status_code == 422
        
        # Test name too long
        long_name = "x" * 256
        response = client.post("/api/v1/sessions", json={"name": long_name})
        assert response.status_code == 422

    def test_create_session_field_length_limits(self, client):
        """Test field length limits are enforced."""
        # Test car_id too long
        session_data = {
            "name": "Test Session",
            "car_id": "x" * 101  # Exceeds 100 char limit
        }
        response = client.post("/api/v1/sessions", json=session_data)
        assert response.status_code == 422
        
        # Test driver too long
        session_data = {
            "name": "Test Session",
            "driver": "x" * 101  # Exceeds 100 char limit
        }
        response = client.post("/api/v1/sessions", json=session_data)
        assert response.status_code == 422
        
        # Test track too long
        session_data = {
            "name": "Test Session",
            "track": "x" * 101  # Exceeds 100 char limit
        }
        response = client.post("/api/v1/sessions", json=session_data)
        assert response.status_code == 422

    def test_create_session_with_optional_fields(self, client):
        """Test creating a session with various combinations of optional fields."""
        # Test with car_id only
        session_data = {
            "name": "Car ID Session",
            "car_id": "CAR002"
        }
        response = client.post("/api/v1/sessions", json=session_data)
        assert response.status_code == 201
        data = response.json()
        assert data["car_id"] == "CAR002"
        assert data["driver"] is None
        assert data["track"] is None
        assert data["notes"] is None
        
        # Test with driver only
        session_data = {
            "name": "Driver Session",
            "driver": "Jane Smith"
        }
        response = client.post("/api/v1/sessions", json=session_data)
        assert response.status_code == 201
        data = response.json()
        assert data["car_id"] is None
        assert data["driver"] == "Jane Smith"
        assert data["track"] is None
        assert data["notes"] is None
        
        # Test with track only
        session_data = {
            "name": "Track Session",
            "track": "Monaco GP"
        }
        response = client.post("/api/v1/sessions", json=session_data)
        assert response.status_code == 201
        data = response.json()
        assert data["car_id"] is None
        assert data["driver"] is None
        assert data["track"] == "Monaco GP"
        assert data["notes"] is None
        
        # Test with notes only
        session_data = {
            "name": "Notes Session",
            "notes": "Important test session"
        }
        response = client.post("/api/v1/sessions", json=session_data)
        assert response.status_code == 201
        data = response.json()
        assert data["car_id"] is None
        assert data["driver"] is None
        assert data["track"] is None
        assert data["notes"] == "Important test session"

    def test_create_session_persistence(self, client):
        """Test that created sessions persist and can be retrieved."""
        # Create a session
        session_data = {
            "name": "Persistent Session",
            "car_id": "CAR003",
            "driver": "Test Driver",
            "track": "Test Track",
            "notes": "This session should persist"
        }
        
        create_response = client.post("/api/v1/sessions", json=session_data)
        assert create_response.status_code == 201
        created_session = create_response.json()
        session_id = created_session["id"]
        
        # Retrieve the session list to verify it was saved
        list_response = client.get("/api/v1/sessions")
        assert list_response.status_code == 200
        sessions_data = list_response.json()
        
        # Find our created session in the list
        found_session = None
        for session in sessions_data["sessions"]:
            if session["id"] == session_id:
                found_session = session
                break
        
        assert found_session is not None
        assert found_session["name"] == "Persistent Session"
        assert found_session["car_id"] == "CAR003"
        assert found_session["driver"] == "Test Driver"
        assert found_session["track"] == "Test Track"
        assert found_session["notes"] == "This session should persist"

    def test_create_multiple_sessions(self, client):
        """Test creating multiple sessions."""
        sessions_data = [
            {
                "name": "Session 1",
                "car_id": "CAR001",
                "driver": "Driver 1"
            },
            {
                "name": "Session 2",
                "car_id": "CAR002",
                "driver": "Driver 2"
            },
            {
                "name": "Session 3",
                "car_id": "CAR003",
                "driver": "Driver 3"
            }
        ]
        
        created_sessions = []
        for session_data in sessions_data:
            response = client.post("/api/v1/sessions", json=session_data)
            assert response.status_code == 201
            created_sessions.append(response.json())
        
        # Verify all sessions were created with unique IDs
        session_ids = [session["id"] for session in created_sessions]
        assert len(set(session_ids)) == len(session_ids)  # All IDs should be unique
        
        # Verify session names match
        for i, session in enumerate(created_sessions):
            assert session["name"] == f"Session {i + 1}"
            assert session["car_id"] == f"CAR00{i + 1}"
            assert session["driver"] == f"Driver {i + 1}"
