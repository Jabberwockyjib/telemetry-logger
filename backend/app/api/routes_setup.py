"""API routes for device setup wizard."""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.base import get_db
from ..db.crud import device_profile_crud, device_setup_crud
from ..db.models import DeviceProfile, DeviceSetup

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setup", tags=["setup"])


# Pydantic models for request/response
class DeviceConfig(BaseModel):
    """Device configuration model."""
    port: Optional[str] = None
    baud_rate: Optional[int] = None
    rate_hz: Optional[float] = None
    timeout: Optional[float] = None
    max_reconnect: Optional[int] = None
    reconnect_delay: Optional[float] = None
    custom_settings: Optional[Dict[str, Any]] = None


class DeviceProfileCreate(BaseModel):
    """Device profile creation model."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    gps_config: Optional[DeviceConfig] = None
    obd_config: Optional[DeviceConfig] = None
    meshtastic_config: Optional[DeviceConfig] = None
    custom_config: Optional[Dict[str, Any]] = None
    is_default: bool = False


class DeviceProfileUpdate(BaseModel):
    """Device profile update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    gps_config: Optional[DeviceConfig] = None
    obd_config: Optional[DeviceConfig] = None
    meshtastic_config: Optional[DeviceConfig] = None
    custom_config: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None


class DeviceSetupCreate(BaseModel):
    """Device setup creation model."""
    setup_type: str = Field(..., regex="^(gps|obd|meshtastic)$")
    device_name: str = Field(..., min_length=1, max_length=255)
    profile_id: Optional[int] = None
    port_path: Optional[str] = None
    baud_rate: Optional[int] = None


class DeviceSetupUpdate(BaseModel):
    """Device setup update model."""
    status: Optional[str] = Field(None, regex="^(pending|testing|success|failed)$")
    error_message: Optional[str] = None
    test_results: Optional[Dict[str, Any]] = None


class DeviceTestRequest(BaseModel):
    """Device test request model."""
    setup_id: int
    test_type: str = Field(..., regex="^(connection|data|full)$")


class DeviceTestResponse(BaseModel):
    """Device test response model."""
    success: bool
    message: str
    test_results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Device Profile Routes
@router.get("/profiles", response_model=List[Dict[str, Any]])
async def get_device_profiles(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get all device profiles.
    
    Args:
        limit: Maximum number of profiles to return.
        offset: Number of profiles to skip.
        db: Database session dependency.
        
    Returns:
        List of device profiles.
    """
    try:
        profiles = await device_profile_crud.get_all(db, limit=limit, offset=offset)
        return [profile.to_dict() for profile in profiles]
    except Exception as e:
        logger.error(f"Error getting device profiles: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device profiles")


@router.get("/profiles/{profile_id}", response_model=Dict[str, Any])
async def get_device_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get device profile by ID.
    
    Args:
        profile_id: Profile ID.
        db: Database session dependency.
        
    Returns:
        Device profile.
        
    Raises:
        HTTPException: If profile not found.
    """
    try:
        profile = await device_profile_crud.get_by_id(db, profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
        return profile.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device profile")


@router.get("/profiles/default", response_model=Dict[str, Any])
async def get_default_device_profile(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get the default device profile.
    
    Args:
        db: Database session dependency.
        
    Returns:
        Default device profile.
        
    Raises:
        HTTPException: If no default profile found.
    """
    try:
        profile = await device_profile_crud.get_default(db)
        if not profile:
            raise HTTPException(status_code=404, detail="No default profile found")
        return profile.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting default device profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to get default profile")


@router.post("/profiles", response_model=Dict[str, Any])
async def create_device_profile(
    profile_data: DeviceProfileCreate,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Create a new device profile.
    
    Args:
        profile_data: Profile creation data.
        db: Database session dependency.
        
    Returns:
        Created device profile.
    """
    try:
        # Convert Pydantic models to dicts
        gps_config = profile_data.gps_config.dict() if profile_data.gps_config else None
        obd_config = profile_data.obd_config.dict() if profile_data.obd_config else None
        meshtastic_config = profile_data.meshtastic_config.dict() if profile_data.meshtastic_config else None
        
        profile = await device_profile_crud.create(
            db=db,
            name=profile_data.name,
            description=profile_data.description,
            gps_config=gps_config,
            obd_config=obd_config,
            meshtastic_config=meshtastic_config,
            custom_config=profile_data.custom_config,
            is_default=profile_data.is_default,
        )
        return profile.to_dict()
    except Exception as e:
        logger.error(f"Error creating device profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to create device profile")


@router.put("/profiles/{profile_id}", response_model=Dict[str, Any])
async def update_device_profile(
    profile_id: int,
    profile_data: DeviceProfileUpdate,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update device profile.
    
    Args:
        profile_id: Profile ID.
        profile_data: Profile update data.
        db: Database session dependency.
        
    Returns:
        Updated device profile.
        
    Raises:
        HTTPException: If profile not found.
    """
    try:
        # Convert Pydantic models to dicts
        update_data = {}
        if profile_data.name is not None:
            update_data['name'] = profile_data.name
        if profile_data.description is not None:
            update_data['description'] = profile_data.description
        if profile_data.gps_config is not None:
            update_data['gps_config'] = profile_data.gps_config.dict()
        if profile_data.obd_config is not None:
            update_data['obd_config'] = profile_data.obd_config.dict()
        if profile_data.meshtastic_config is not None:
            update_data['meshtastic_config'] = profile_data.meshtastic_config.dict()
        if profile_data.custom_config is not None:
            update_data['custom_config'] = profile_data.custom_config
        if profile_data.is_default is not None:
            update_data['is_default'] = profile_data.is_default
        
        profile = await device_profile_crud.update(db, profile_id, **update_data)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
        return profile.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating device profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update device profile")


@router.delete("/profiles/{profile_id}")
async def delete_device_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Delete device profile.
    
    Args:
        profile_id: Profile ID.
        db: Database session dependency.
        
    Returns:
        Success message.
        
    Raises:
        HTTPException: If profile not found.
    """
    try:
        success = await device_profile_crud.delete(db, profile_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
        return {"message": f"Profile {profile_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting device profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete device profile")


# Device Setup Routes
@router.get("/setups", response_model=List[Dict[str, Any]])
async def get_device_setups(
    profile_id: Optional[int] = Query(None),
    setup_type: Optional[str] = Query(None, regex="^(gps|obd|meshtastic)$"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get device setups.
    
    Args:
        profile_id: Optional profile ID filter.
        setup_type: Optional setup type filter.
        limit: Maximum number of setups to return.
        offset: Number of setups to skip.
        db: Database session dependency.
        
    Returns:
        List of device setups.
    """
    try:
        if profile_id:
            setups = await device_setup_crud.get_by_profile(db, profile_id, limit, offset)
        elif setup_type:
            setups = await device_setup_crud.get_by_type(db, setup_type, limit, offset)
        else:
            # Get all setups (would need a new CRUD method)
            setups = []
        return [setup.to_dict() for setup in setups]
    except Exception as e:
        logger.error(f"Error getting device setups: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device setups")


@router.get("/setups/{setup_id}", response_model=Dict[str, Any])
async def get_device_setup(
    setup_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get device setup by ID.
    
    Args:
        setup_id: Setup ID.
        db: Database session dependency.
        
    Returns:
        Device setup.
        
    Raises:
        HTTPException: If setup not found.
    """
    try:
        setup = await device_setup_crud.get_by_id(db, setup_id)
        if not setup:
            raise HTTPException(status_code=404, detail=f"Setup {setup_id} not found")
        return setup.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device setup {setup_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device setup")


@router.post("/setups", response_model=Dict[str, Any])
async def create_device_setup(
    setup_data: DeviceSetupCreate,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Create a new device setup.
    
    Args:
        setup_data: Setup creation data.
        db: Database session dependency.
        
    Returns:
        Created device setup.
    """
    try:
        setup = await device_setup_crud.create(
            db=db,
            setup_type=setup_data.setup_type,
            device_name=setup_data.device_name,
            profile_id=setup_data.profile_id,
            port_path=setup_data.port_path,
            baud_rate=setup_data.baud_rate,
        )
        return setup.to_dict()
    except Exception as e:
        logger.error(f"Error creating device setup: {e}")
        raise HTTPException(status_code=500, detail="Failed to create device setup")


@router.put("/setups/{setup_id}", response_model=Dict[str, Any])
async def update_device_setup(
    setup_id: int,
    setup_data: DeviceSetupUpdate,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update device setup.
    
    Args:
        setup_id: Setup ID.
        setup_data: Setup update data.
        db: Database session dependency.
        
    Returns:
        Updated device setup.
        
    Raises:
        HTTPException: If setup not found.
    """
    try:
        update_data = {}
        if setup_data.status is not None:
            update_data['status'] = setup_data.status
        if setup_data.error_message is not None:
            update_data['error_message'] = setup_data.error_message
        if setup_data.test_results is not None:
            update_data['test_results'] = json.dumps(setup_data.test_results)
        
        setup = await device_setup_crud.update(db, setup_id, **update_data)
        if not setup:
            raise HTTPException(status_code=404, detail=f"Setup {setup_id} not found")
        return setup.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating device setup {setup_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update device setup")


@router.delete("/setups/{setup_id}")
async def delete_device_setup(
    setup_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Delete device setup.
    
    Args:
        setup_id: Setup ID.
        db: Database session dependency.
        
    Returns:
        Success message.
        
    Raises:
        HTTPException: If setup not found.
    """
    try:
        success = await device_setup_crud.delete(db, setup_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Setup {setup_id} not found")
        return {"message": f"Setup {setup_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting device setup {setup_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete device setup")


# Device Testing Routes
@router.post("/test", response_model=DeviceTestResponse)
async def test_device(
    test_request: DeviceTestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> DeviceTestResponse:
    """Test device connection and functionality.
    
    Args:
        test_request: Test request data.
        background_tasks: Background tasks for async operations.
        db: Database session dependency.
        
    Returns:
        Test response.
    """
    try:
        # Get the setup
        setup = await device_setup_crud.get_by_id(db, test_request.setup_id)
        if not setup:
            raise HTTPException(status_code=404, detail=f"Setup {test_request.setup_id} not found")
        
        # Update status to testing
        await device_setup_crud.update(db, test_request.setup_id, status="testing")
        
        # Start background test
        background_tasks.add_task(
            run_device_test,
            db,
            test_request.setup_id,
            test_request.test_type,
            setup.setup_type,
            setup.port_path,
            setup.baud_rate
        )
        
        return DeviceTestResponse(
            success=True,
            message="Device test started",
            test_results={"status": "testing", "test_type": test_request.test_type}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting device test: {e}")
        raise HTTPException(status_code=500, detail="Failed to start device test")


async def run_device_test(
    db: AsyncSession,
    setup_id: int,
    test_type: str,
    setup_type: str,
    port_path: Optional[str],
    baud_rate: Optional[int]
) -> None:
    """Run device test in background.
    
    Args:
        db: Database session.
        setup_id: Setup ID.
        test_type: Type of test to run.
        setup_type: Type of device setup.
        port_path: Port path for the device.
        baud_rate: Baud rate for the device.
    """
    try:
        test_results = {}
        error_message = None
        
        if test_type == "connection":
            # Test basic connection
            if port_path and baud_rate:
                # Simulate connection test
                await asyncio.sleep(2)  # Simulate test time
                test_results = {
                    "connection": "success",
                    "port": port_path,
                    "baud_rate": baud_rate,
                    "response_time": "0.1s"
                }
            else:
                error_message = "Port path and baud rate required for connection test"
                
        elif test_type == "data":
            # Test data reception
            if setup_type == "gps":
                # Simulate GPS data test
                await asyncio.sleep(3)
                test_results = {
                    "data_received": True,
                    "nmea_sentences": ["GGA", "RMC", "VTG"],
                    "fix_quality": "good",
                    "satellites": 8
                }
            elif setup_type == "obd":
                # Simulate OBD data test
                await asyncio.sleep(3)
                test_results = {
                    "data_received": True,
                    "pids_supported": ["SPEED", "RPM", "THROTTLE_POS"],
                    "response_time": "0.2s"
                }
            elif setup_type == "meshtastic":
                # Simulate Meshtastic test
                await asyncio.sleep(3)
                test_results = {
                    "connection": "success",
                    "radio_status": "active",
                    "frequency": "915.0 MHz"
                }
                
        elif test_type == "full":
            # Run comprehensive test
            await asyncio.sleep(5)
            test_results = {
                "connection": "success",
                "data_received": True,
                "performance": "good",
                "stability": "stable"
            }
        
        # Update setup with results
        if error_message:
            await device_setup_crud.update(
                db, setup_id,
                status="failed",
                error_message=error_message,
                test_results=json.dumps(test_results)
            )
        else:
            await device_setup_crud.update(
                db, setup_id,
                status="success",
                test_results=json.dumps(test_results),
                completed_utc=datetime.now(timezone.utc)
            )
            
    except Exception as e:
        logger.error(f"Error in device test: {e}")
        await device_setup_crud.update(
            db, setup_id,
            status="failed",
            error_message=str(e)
        )


# Utility Routes
@router.get("/ports")
async def get_available_ports() -> Dict[str, List[str]]:
    """Get available serial ports.
    
    Returns:
        Dictionary of available ports by platform.
    """
    try:
        import serial.tools.list_ports
        
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                "device": port.device,
                "description": port.description,
                "hwid": port.hwid
            })
        
        return {"ports": ports}
    except ImportError:
        return {"ports": [], "error": "pyserial not available"}
    except Exception as e:
        logger.error(f"Error getting available ports: {e}")
        return {"ports": [], "error": str(e)}


@router.get("/device-types")
async def get_device_types() -> Dict[str, List[Dict[str, Any]]]:
    """Get supported device types and their configurations.
    
    Returns:
        Dictionary of device types and their default configurations.
    """
    return {
        "device_types": [
            {
                "type": "gps",
                "name": "GPS Device",
                "description": "NMEA-compatible GPS device",
                "default_config": {
                    "baud_rate": 4800,
                    "rate_hz": 10.0,
                    "timeout": 1.0,
                    "max_reconnect": 10,
                    "reconnect_delay": 5.0
                },
                "required_fields": ["port", "baud_rate"],
                "optional_fields": ["rate_hz", "timeout", "max_reconnect", "reconnect_delay"]
            },
            {
                "type": "obd",
                "name": "OBD-II Adapter",
                "description": "ELM327-based OBD-II adapter",
                "default_config": {
                    "baud_rate": 38400,
                    "timeout": 5.0,
                    "max_reconnect": 5,
                    "reconnect_delay": 10.0
                },
                "required_fields": ["port", "baud_rate"],
                "optional_fields": ["timeout", "max_reconnect", "reconnect_delay"]
            },
            {
                "type": "meshtastic",
                "name": "Meshtastic Device",
                "description": "Meshtastic-compatible radio device",
                "default_config": {
                    "baud_rate": 38400,
                    "rate_hz": 1.0,
                    "max_payload_size": 64
                },
                "required_fields": ["port", "baud_rate"],
                "optional_fields": ["rate_hz", "max_payload_size"]
            }
        ]
    }
