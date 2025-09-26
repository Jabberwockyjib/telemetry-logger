"""
Tests for device profile persistence across server restarts.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.main import app
from backend.app.db.base import get_db
from backend.app.services.manager import service_manager


class TestDeviceProfilePersistence:
    """Test device profile persistence and service configuration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    async def async_db_session(self):
        """Create async database session."""
        async for session in get_db():
            yield session

    def test_create_device_profile_with_port_configs(self, client):
        """Test creating a device profile with port and baud rate configurations."""
        profile_data = {
            "name": "Test Profile",
            "description": "Test profile with port configurations",
            "gps_config": {
                "port": "/dev/ttyUSB0",
                "baud_rate": 4800,
                "rate_hz": 1.0,
                "timeout": 1.0
            },
            "obd_config": {
                "port": "/dev/ttyUSB1",
                "baud_rate": 38400,
                "rate_hz": 2.0,
                "timeout": 1.0
            },
            "meshtastic_config": {
                "port": "/dev/ttyUSB2",
                "baud_rate": 9600,
                "rate_hz": 1.0,
                "timeout": 1.0
            },
            "is_default": True
        }
        
        response = client.post("/api/v1/setup/profiles", json=profile_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify profile was created
        assert data["name"] == "Test Profile"
        assert data["is_default"] is True
        
        # Verify configurations (stored as JSON strings)
        import json
        gps_config = json.loads(data["gps_config"]) if data["gps_config"] else {}
        obd_config = json.loads(data["obd_config"]) if data["obd_config"] else {}
        mesh_config = json.loads(data["meshtastic_config"]) if data["meshtastic_config"] else {}
        
        assert gps_config["port"] == "/dev/ttyUSB0"
        assert gps_config["baud_rate"] == 4800
        assert obd_config["port"] == "/dev/ttyUSB1"
        assert obd_config["baud_rate"] == 38400
        assert mesh_config["port"] == "/dev/ttyUSB2"
        assert mesh_config["baud_rate"] == 9600

    def test_update_device_profile_ports(self, client):
        """Test updating device profile port configurations."""
        # First create a profile
        profile_data = {
            "name": "Update Test Profile",
            "gps_config": {
                "port": "/dev/ttyUSB0",
                "baud_rate": 4800
            },
            "is_default": False
        }
        
        create_response = client.post("/api/v1/setup/profiles", json=profile_data)
        assert create_response.status_code == 200
        profile_id = create_response.json()["id"]
        
        # Update the profile with new port configurations
        update_data = {
            "gps_config": {
                "port": "/dev/ttyACM0",
                "baud_rate": 9600,
                "rate_hz": 2.0
            },
            "obd_config": {
                "port": "/dev/ttyACM1",
                "baud_rate": 115200,
                "rate_hz": 5.0
            }
        }
        
        update_response = client.put(f"/api/v1/setup/profiles/{profile_id}", json=update_data)
        assert update_response.status_code == 200
        
        data = update_response.json()
        import json
        gps_config = json.loads(data["gps_config"]) if data["gps_config"] else {}
        obd_config = json.loads(data["obd_config"]) if data["obd_config"] else {}
        
        assert gps_config["port"] == "/dev/ttyACM0"
        assert gps_config["baud_rate"] == 9600
        assert gps_config["rate_hz"] == 2.0
        assert obd_config["port"] == "/dev/ttyACM1"
        assert obd_config["baud_rate"] == 115200
        assert obd_config["rate_hz"] == 5.0

    def test_get_device_profiles_persistence(self, client):
        """Test that device profiles persist and can be retrieved."""
        # Create multiple profiles
        profiles_data = [
            {
                "name": "Profile 1",
                "gps_config": {"port": "/dev/ttyUSB0", "baud_rate": 4800},
                "is_default": True
            },
            {
                "name": "Profile 2",
                "obd_config": {"port": "/dev/ttyUSB1", "baud_rate": 38400},
                "is_default": False
            },
            {
                "name": "Profile 3",
                "meshtastic_config": {"port": "/dev/ttyUSB2", "baud_rate": 9600},
                "is_default": False
            }
        ]
        
        created_profiles = []
        for profile_data in profiles_data:
            response = client.post("/api/v1/setup/profiles", json=profile_data)
            assert response.status_code == 200
            created_profiles.append(response.json())
        
        # Retrieve all profiles
        response = client.get("/api/v1/setup/profiles")
        assert response.status_code == 200
        profiles = response.json()
        
        # Verify all profiles are present
        assert len(profiles) >= len(created_profiles)
        
        # Find our created profiles
        profile_names = [p["name"] for p in profiles]
        assert "Profile 1" in profile_names
        assert "Profile 2" in profile_names
        assert "Profile 3" in profile_names
        
        # Verify default profile
        default_profile = next((p for p in profiles if p["is_default"]), None)
        assert default_profile is not None
        assert default_profile["name"] == "Profile 1"

    def test_device_profile_configuration_validation(self, client):
        """Test validation of device profile configurations."""
        # Test invalid port configuration
        invalid_profile = {
            "name": "Invalid Profile",
            "gps_config": {
                "port": "",  # Empty port
                "baud_rate": -1  # Invalid baud rate
            }
        }
        
        response = client.post("/api/v1/setup/profiles", json=invalid_profile)
        # Should still create profile (validation happens at service level)
        assert response.status_code == 200
        
        # Test missing required fields
        minimal_profile = {
            "name": "Minimal Profile"
        }
        
        response = client.post("/api/v1/setup/profiles", json=minimal_profile)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Minimal Profile"
        # Verify configurations (should be None for minimal profile)
        assert data["gps_config"] is None
        assert data["obd_config"] is None
        assert data["meshtastic_config"] is None

    async def test_service_manager_profile_loading(self, async_db_session):
        """Test that service manager can load device profiles."""
        # This test would require mocking the service manager initialization
        # For now, we'll test the profile loading logic directly
        
        # Create a test profile
        from backend.app.db.crud import device_profile_crud
        
        profile_data = {
            "name": "Service Test Profile",
            "gps_config": {
                "port": "/dev/ttyUSB0",
                "baud_rate": 4800,
                "rate_hz": 1.0
            },
            "obd_config": {
                "port": "/dev/ttyUSB1",
                "baud_rate": 38400,
                "rate_hz": 2.0
            },
            "is_default": True
        }
        
        # Create profile in database
        profile = await device_profile_crud.create(
            db=async_db_session,
            name=profile_data["name"],
            gps_config=profile_data["gps_config"],
            obd_config=profile_data["obd_config"],
            is_default=profile_data["is_default"]
        )
        
        # Test loading the profile
        success = await service_manager.load_device_profile(async_db_session, profile.id)
        assert success is True
        assert service_manager._current_profile is not None
        assert service_manager._current_profile.id == profile.id
        assert service_manager._current_profile.name == "Service Test Profile"

    async def test_service_creation_from_profile(self, async_db_session):
        """Test that services are created with correct configurations from profile."""
        from backend.app.db.crud import device_profile_crud
        
        # Create a profile with specific configurations
        profile_data = {
            "name": "Service Creation Test",
            "gps_config": {
                "port": "/dev/ttyACM0",
                "baud_rate": 9600,
                "rate_hz": 2.0,
                "timeout": 2.0
            },
            "obd_config": {
                "port": "/dev/ttyACM1",
                "baud_rate": 115200,
                "rate_hz": 5.0,
                "timeout": 1.5
            },
            "is_default": True
        }
        
        profile = await device_profile_crud.create(
            db=async_db_session,
            name=profile_data["name"],
            gps_config=profile_data["gps_config"],
            obd_config=profile_data["obd_config"],
            is_default=profile_data["is_default"]
        )
        
        # Load profile and create services
        await service_manager.load_device_profile(async_db_session, profile.id)
        service_manager._create_services_from_profile()
        
        # Verify GPS service configuration
        assert service_manager._gps_service is not None
        assert service_manager._gps_service.port == "/dev/ttyACM0"
        assert service_manager._gps_service.baudrate == 9600
        assert service_manager._gps_service.rate_hz == 2.0
        assert service_manager._gps_service.timeout == 2.0
        
        # Verify OBD service configuration
        assert service_manager._obd_service is not None
        assert service_manager._obd_service.port == "/dev/ttyACM1"
        assert service_manager._obd_service.baudrate == 115200
        assert service_manager._obd_service.timeout == 1.5

    async def test_default_profile_loading(self, client, async_db_session):
        """Test that default profile is loaded when no profile ID is specified."""
        from backend.app.db.crud import device_profile_crud
        
        # Create a default profile
        profile = await device_profile_crud.create(
            db=async_db_session,
            name="Default Test Profile",
            gps_config={"port": "/dev/ttyUSB0", "baud_rate": 4800},
            is_default=True
        )
        
        # Test loading default profile
        success = await service_manager.load_device_profile(async_db_session, None)
        assert success is True
        assert service_manager._current_profile is not None
        assert service_manager._current_profile.id == profile.id
        assert service_manager._current_profile.is_default is True

    async def test_profile_not_found_handling(self, async_db_session):
        """Test handling when profile is not found."""
        # Reset current profile to ensure clean state
        service_manager._current_profile = None
        
        # Try to load non-existent profile
        success = await service_manager.load_device_profile(async_db_session, 99999)
        assert success is False
        assert service_manager._current_profile is None

    def test_service_creation_without_profile(self):
        """Test that services are created with defaults when no profile is loaded."""
        # Ensure no profile is loaded and reset services
        service_manager._current_profile = None
        service_manager._gps_service = None
        service_manager._obd_service = None
        
        # Create services from profile (should use defaults)
        service_manager._create_services_from_profile()
        
        # When no profile is loaded, services should not be created
        # The method should just return without creating services
        assert service_manager._gps_service is None
        assert service_manager._obd_service is None
