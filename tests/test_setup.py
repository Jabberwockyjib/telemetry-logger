"""Tests for device setup wizard functionality."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, List
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.db.crud import device_profile_crud, device_setup_crud
from backend.app.db.models import DeviceProfile, DeviceSetup
from backend.app.main import app


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


@pytest.fixture
def client() -> TestClient:
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
async def test_profile(async_db_session: AsyncSession) -> DeviceProfile:
    """Create a test device profile."""
    profile = await device_profile_crud.create(
        db=async_db_session,
        name="Test Profile",
        description="Test device profile",
        gps_config={"port": "/dev/ttyUSB0", "baud_rate": 4800},
        obd_config={"port": "/dev/ttyUSB1", "baud_rate": 38400},
        is_default=True
    )
    return profile


@pytest.fixture
async def test_setup(async_db_session: AsyncSession, test_profile: DeviceProfile) -> DeviceSetup:
    """Create a test device setup."""
    setup = await device_setup_crud.create(
        db=async_db_session,
        setup_type="gps",
        device_name="Test GPS Device",
        profile_id=test_profile.id,
        port_path="/dev/ttyUSB0",
        baud_rate=4800
    )
    return setup


class TestDeviceProfileCRUD:
    """Test device profile CRUD operations."""
    
    async def test_create_device_profile(self, async_db_session: AsyncSession) -> None:
        """Test creating a device profile."""
        profile = await device_profile_crud.create(
            db=async_db_session,
            name="Test Profile",
            description="Test description",
            gps_config={"port": "/dev/ttyUSB0", "baud_rate": 4800},
            is_default=True
        )
        
        assert profile.id is not None
        assert profile.name == "Test Profile"
        assert profile.description == "Test description"
        assert profile.is_default is True
        assert profile.gps_config == '{"port": "/dev/ttyUSB0", "baud_rate": 4800}'
    
    async def test_get_device_profile_by_id(self, async_db_session: AsyncSession, test_profile: DeviceProfile) -> None:
        """Test getting a device profile by ID."""
        profile = await device_profile_crud.get_by_id(async_db_session, test_profile.id)
        
        assert profile is not None
        assert profile.id == test_profile.id
        assert profile.name == "Test Profile"
    
    async def test_get_all_device_profiles(self, async_db_session: AsyncSession) -> None:
        """Test getting all device profiles."""
        # Create multiple profiles
        await device_profile_crud.create(
            db=async_db_session,
            name="Profile 1",
            is_default=True
        )
        await device_profile_crud.create(
            db=async_db_session,
            name="Profile 2",
            is_default=False
        )
        
        profiles = await device_profile_crud.get_all(async_db_session)
        
        assert len(profiles) == 2
        assert profiles[0].is_default is True  # Default profile should be first
    
    async def test_get_default_device_profile(self, async_db_session: AsyncSession, test_profile: DeviceProfile) -> None:
        """Test getting the default device profile."""
        profile = await device_profile_crud.get_default(async_db_session)
        
        assert profile is not None
        assert profile.id == test_profile.id
        assert profile.is_default is True
    
    async def test_update_device_profile(self, async_db_session: AsyncSession, test_profile: DeviceProfile) -> None:
        """Test updating a device profile."""
        updated_profile = await device_profile_crud.update(
            db=async_db_session,
            profile_id=test_profile.id,
            name="Updated Profile",
            description="Updated description"
        )
        
        assert updated_profile is not None
        assert updated_profile.name == "Updated Profile"
        assert updated_profile.description == "Updated description"
    
    async def test_delete_device_profile(self, async_db_session: AsyncSession, test_profile: DeviceProfile) -> None:
        """Test deleting a device profile."""
        success = await device_profile_crud.delete(async_db_session, test_profile.id)
        
        assert success is True
        
        # Verify profile is deleted
        profile = await device_profile_crud.get_by_id(async_db_session, test_profile.id)
        assert profile is None


class TestDeviceSetupCRUD:
    """Test device setup CRUD operations."""
    
    async def test_create_device_setup(self, async_db_session: AsyncSession, test_profile: DeviceProfile) -> None:
        """Test creating a device setup."""
        setup = await device_setup_crud.create(
            db=async_db_session,
            setup_type="gps",
            device_name="Test GPS Device",
            profile_id=test_profile.id,
            port_path="/dev/ttyUSB0",
            baud_rate=4800
        )
        
        assert setup.id is not None
        assert setup.setup_type == "gps"
        assert setup.device_name == "Test GPS Device"
        assert setup.profile_id == test_profile.id
        assert setup.port_path == "/dev/ttyUSB0"
        assert setup.baud_rate == 4800
        assert setup.status == "pending"
    
    async def test_get_device_setup_by_id(self, async_db_session: AsyncSession, test_setup: DeviceSetup) -> None:
        """Test getting a device setup by ID."""
        setup = await device_setup_crud.get_by_id(async_db_session, test_setup.id)
        
        assert setup is not None
        assert setup.id == test_setup.id
        assert setup.setup_type == "gps"
    
    async def test_get_device_setups_by_profile(self, async_db_session: AsyncSession, test_profile: DeviceProfile) -> None:
        """Test getting device setups by profile ID."""
        # Create multiple setups for the same profile
        await device_setup_crud.create(
            db=async_db_session,
            setup_type="gps",
            device_name="GPS Device",
            profile_id=test_profile.id
        )
        await device_setup_crud.create(
            db=async_db_session,
            setup_type="obd",
            device_name="OBD Device",
            profile_id=test_profile.id
        )
        
        setups = await device_setup_crud.get_by_profile(async_db_session, test_profile.id)
        
        assert len(setups) == 2
        assert all(setup.profile_id == test_profile.id for setup in setups)
    
    async def test_get_device_setups_by_type(self, async_db_session: AsyncSession) -> None:
        """Test getting device setups by type."""
        # Create setups of different types
        await device_setup_crud.create(
            db=async_db_session,
            setup_type="gps",
            device_name="GPS Device 1"
        )
        await device_setup_crud.create(
            db=async_db_session,
            setup_type="gps",
            device_name="GPS Device 2"
        )
        await device_setup_crud.create(
            db=async_db_session,
            setup_type="obd",
            device_name="OBD Device"
        )
        
        gps_setups = await device_setup_crud.get_by_type(async_db_session, "gps")
        obd_setups = await device_setup_crud.get_by_type(async_db_session, "obd")
        
        assert len(gps_setups) == 2
        assert len(obd_setups) == 1
        assert all(setup.setup_type == "gps" for setup in gps_setups)
        assert all(setup.setup_type == "obd" for setup in obd_setups)
    
    async def test_update_device_setup(self, async_db_session: AsyncSession, test_setup: DeviceSetup) -> None:
        """Test updating a device setup."""
        updated_setup = await device_setup_crud.update(
            db=async_db_session,
            setup_id=test_setup.id,
            status="success",
            test_results='{"connection": "success", "data_received": true}'
        )
        
        assert updated_setup is not None
        assert updated_setup.status == "success"
        assert updated_setup.test_results == '{"connection": "success", "data_received": true}'
    
    async def test_delete_device_setup(self, async_db_session: AsyncSession, test_setup: DeviceSetup) -> None:
        """Test deleting a device setup."""
        success = await device_setup_crud.delete(async_db_session, test_setup.id)
        
        assert success is True
        
        # Verify setup is deleted
        setup = await device_setup_crud.get_by_id(async_db_session, test_setup.id)
        assert setup is None


class TestSetupAPI:
    """Test setup API endpoints."""
    
    def test_get_device_profiles(self, client: TestClient) -> None:
        """Test getting device profiles via API."""
        response = client.get("/api/v1/setup/profiles")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_device_profile_by_id(self, client: TestClient) -> None:
        """Test getting a device profile by ID via API."""
        # First create a profile
        profile_data = {
            "name": "Test Profile",
            "description": "Test description",
            "gps_config": {"port": "/dev/ttyUSB0", "baud_rate": 4800}
        }
        
        create_response = client.post("/api/v1/setup/profiles", json=profile_data)
        assert create_response.status_code == 200
        profile = create_response.json()
        
        # Then get it by ID
        response = client.get(f"/api/v1/setup/profiles/{profile['id']}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == profile["id"]
        assert data["name"] == "Test Profile"
    
    def test_create_device_profile(self, client: TestClient) -> None:
        """Test creating a device profile via API."""
        profile_data = {
            "name": "New Profile",
            "description": "New description",
            "gps_config": {
                "port": "/dev/ttyUSB0",
                "baud_rate": 4800,
                "rate_hz": 10.0
            },
            "obd_config": {
                "port": "/dev/ttyUSB1",
                "baud_rate": 38400,
                "timeout": 5.0
            },
            "is_default": True
        }
        
        response = client.post("/api/v1/setup/profiles", json=profile_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Profile"
        assert data["description"] == "New description"
        assert data["is_default"] is True
        assert data["gps_config"] is not None
        assert data["obd_config"] is not None
    
    def test_update_device_profile(self, client: TestClient) -> None:
        """Test updating a device profile via API."""
        # First create a profile
        profile_data = {
            "name": "Original Profile",
            "description": "Original description"
        }
        
        create_response = client.post("/api/v1/setup/profiles", json=profile_data)
        assert create_response.status_code == 200
        profile = create_response.json()
        
        # Then update it
        update_data = {
            "name": "Updated Profile",
            "description": "Updated description",
            "gps_config": {"port": "/dev/ttyUSB0", "baud_rate": 4800}
        }
        
        response = client.put(f"/api/v1/setup/profiles/{profile['id']}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Profile"
        assert data["description"] == "Updated description"
        assert data["gps_config"] is not None
    
    def test_delete_device_profile(self, client: TestClient) -> None:
        """Test deleting a device profile via API."""
        # First create a profile
        profile_data = {
            "name": "To Delete Profile",
            "description": "This will be deleted"
        }
        
        create_response = client.post("/api/v1/setup/profiles", json=profile_data)
        assert create_response.status_code == 200
        profile = create_response.json()
        
        # Then delete it
        response = client.delete(f"/api/v1/setup/profiles/{profile['id']}")
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
    
    def test_get_device_setups(self, client: TestClient) -> None:
        """Test getting device setups via API."""
        response = client.get("/api/v1/setup/setups")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_device_setup(self, client: TestClient) -> None:
        """Test creating a device setup via API."""
        setup_data = {
            "setup_type": "gps",
            "device_name": "Test GPS Device",
            "port_path": "/dev/ttyUSB0",
            "baud_rate": 4800
        }
        
        response = client.post("/api/v1/setup/setups", json=setup_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["setup_type"] == "gps"
        assert data["device_name"] == "Test GPS Device"
        assert data["port_path"] == "/dev/ttyUSB0"
        assert data["baud_rate"] == 4800
        assert data["status"] == "pending"
    
    def test_update_device_setup(self, client: TestClient) -> None:
        """Test updating a device setup via API."""
        # First create a setup
        setup_data = {
            "setup_type": "gps",
            "device_name": "Test GPS Device"
        }
        
        create_response = client.post("/api/v1/setup/setups", json=setup_data)
        assert create_response.status_code == 200
        setup = create_response.json()
        
        # Then update it
        update_data = {
            "status": "success",
            "test_results": {"connection": "success", "data_received": True}
        }
        
        response = client.put(f"/api/v1/setup/setups/{setup['id']}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["test_results"] is not None
    
    def test_delete_device_setup(self, client: TestClient) -> None:
        """Test deleting a device setup via API."""
        # First create a setup
        setup_data = {
            "setup_type": "gps",
            "device_name": "To Delete Device"
        }
        
        create_response = client.post("/api/v1/setup/setups", json=setup_data)
        assert create_response.status_code == 200
        setup = create_response.json()
        
        # Then delete it
        response = client.delete(f"/api/v1/setup/setups/{setup['id']}")
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
    
    def test_get_available_ports(self, client: TestClient) -> None:
        """Test getting available serial ports via API."""
        response = client.get("/api/v1/setup/ports")
        
        assert response.status_code == 200
        data = response.json()
        assert "ports" in data
        assert isinstance(data["ports"], list)
    
    def test_get_device_types(self, client: TestClient) -> None:
        """Test getting supported device types via API."""
        response = client.get("/api/v1/setup/device-types")
        
        assert response.status_code == 200
        data = response.json()
        assert "device_types" in data
        assert isinstance(data["device_types"], list)
        
        # Check that expected device types are present
        device_types = [dt["type"] for dt in data["device_types"]]
        assert "gps" in device_types
        assert "obd" in device_types
        assert "meshtastic" in device_types
    
    @patch('backend.app.api.routes_setup.run_device_test')
    def test_device_test(self, mock_run_device_test: AsyncMock, client: TestClient) -> None:
        """Test device testing via API."""
        # First create a setup
        setup_data = {
            "setup_type": "gps",
            "device_name": "Test GPS Device",
            "port_path": "/dev/ttyUSB0",
            "baud_rate": 4800
        }
        
        create_response = client.post("/api/v1/setup/setups", json=setup_data)
        assert create_response.status_code == 200
        setup = create_response.json()
        
        # Then test it
        test_data = {
            "setup_id": setup["id"],
            "test_type": "connection"
        }
        
        response = client.post("/api/v1/setup/test", json=test_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "started" in data["message"]
        assert data["test_results"]["status"] == "testing"
    
    def test_get_nonexistent_profile(self, client: TestClient) -> None:
        """Test getting a non-existent device profile."""
        response = client.get("/api/v1/setup/profiles/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_get_nonexistent_setup(self, client: TestClient) -> None:
        """Test getting a non-existent device setup."""
        response = client.get("/api/v1/setup/setups/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_invalid_setup_type(self, client: TestClient) -> None:
        """Test creating a setup with invalid type."""
        setup_data = {
            "setup_type": "invalid",
            "device_name": "Test Device"
        }
        
        response = client.post("/api/v1/setup/setups", json=setup_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_test_type(self, client: TestClient) -> None:
        """Test device testing with invalid test type."""
        # First create a setup
        setup_data = {
            "setup_type": "gps",
            "device_name": "Test GPS Device"
        }
        
        create_response = client.post("/api/v1/setup/setups", json=setup_data)
        assert create_response.status_code == 200
        setup = create_response.json()
        
        # Then test with invalid type
        test_data = {
            "setup_id": setup["id"],
            "test_type": "invalid"
        }
        
        response = client.post("/api/v1/setup/test", json=test_data)
        
        assert response.status_code == 422  # Validation error


class TestSetupIntegration:
    """Integration tests for the setup wizard."""
    
    def test_complete_setup_workflow(self, client: TestClient) -> None:
        """Test the complete setup workflow from profile creation to device testing."""
        # Step 1: Create a device profile
        profile_data = {
            "name": "Integration Test Profile",
            "description": "Profile for integration testing",
            "gps_config": {
                "port": "/dev/ttyUSB0",
                "baud_rate": 4800,
                "rate_hz": 10.0
            },
            "obd_config": {
                "port": "/dev/ttyUSB1",
                "baud_rate": 38400,
                "timeout": 5.0
            },
            "is_default": True
        }
        
        profile_response = client.post("/api/v1/setup/profiles", json=profile_data)
        assert profile_response.status_code == 200
        profile = profile_response.json()
        
        # Step 2: Create device setups
        gps_setup_data = {
            "setup_type": "gps",
            "device_name": "GPS Device",
            "profile_id": profile["id"],
            "port_path": "/dev/ttyUSB0",
            "baud_rate": 4800
        }
        
        obd_setup_data = {
            "setup_type": "obd",
            "device_name": "OBD Device",
            "profile_id": profile["id"],
            "port_path": "/dev/ttyUSB1",
            "baud_rate": 38400
        }
        
        gps_setup_response = client.post("/api/v1/setup/setups", json=gps_setup_data)
        assert gps_setup_response.status_code == 200
        gps_setup = gps_setup_response.json()
        
        obd_setup_response = client.post("/api/v1/setup/setups", json=obd_setup_data)
        assert obd_setup_response.status_code == 200
        obd_setup = obd_setup_response.json()
        
        # Step 3: Test devices
        gps_test_data = {
            "setup_id": gps_setup["id"],
            "test_type": "connection"
        }
        
        obd_test_data = {
            "setup_id": obd_setup["id"],
            "test_type": "data"
        }
        
        gps_test_response = client.post("/api/v1/setup/test", json=gps_test_data)
        assert gps_test_response.status_code == 200
        
        obd_test_response = client.post("/api/v1/setup/test", json=obd_test_data)
        assert obd_test_response.status_code == 200
        
        # Step 4: Verify profile and setups exist
        profile_verify_response = client.get(f"/api/v1/setup/profiles/{profile['id']}")
        assert profile_verify_response.status_code == 200
        
        setups_response = client.get(f"/api/v1/setup/setups?profile_id={profile['id']}")
        assert setups_response.status_code == 200
        setups = setups_response.json()
        assert len(setups) == 2
        
        # Step 5: Clean up
        client.delete(f"/api/v1/setup/setups/{gps_setup['id']}")
        client.delete(f"/api/v1/setup/setups/{obd_setup['id']}")
        client.delete(f"/api/v1/setup/profiles/{profile['id']}")
    
    def test_default_profile_management(self, client: TestClient) -> None:
        """Test default profile management."""
        # Create first profile as default
        profile1_data = {
            "name": "First Profile",
            "is_default": True
        }
        
        profile1_response = client.post("/api/v1/setup/profiles", json=profile1_data)
        assert profile1_response.status_code == 200
        profile1 = profile1_response.json()
        assert profile1["is_default"] is True
        
        # Create second profile as default (should unset first)
        profile2_data = {
            "name": "Second Profile",
            "is_default": True
        }
        
        profile2_response = client.post("/api/v1/setup/profiles", json=profile2_data)
        assert profile2_response.status_code == 200
        profile2 = profile2_response.json()
        assert profile2["is_default"] is True
        
        # Verify first profile is no longer default
        profile1_verify_response = client.get(f"/api/v1/setup/profiles/{profile1['id']}")
        assert profile1_verify_response.status_code == 200
        profile1_updated = profile1_verify_response.json()
        assert profile1_updated["is_default"] is False
        
        # Get default profile
        default_response = client.get("/api/v1/setup/profiles/default")
        assert default_response.status_code == 200
        default_profile = default_response.json()
        assert default_profile["id"] == profile2["id"]
        
        # Clean up
        client.delete(f"/api/v1/setup/profiles/{profile1['id']}")
        client.delete(f"/api/v1/setup/profiles/{profile2['id']}")
