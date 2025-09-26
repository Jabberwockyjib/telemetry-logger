"""API routes for device scanning and detection."""

import logging
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/devices", tags=["devices"])


class SerialPort(BaseModel):
    """Serial port information model."""
    path: str
    vid: Optional[int] = None
    pid: Optional[int] = None
    desc: Optional[str] = None
    hwid: Optional[str] = None


class Camera(BaseModel):
    """Camera device information model."""
    path: str
    name: str
    index: int


class DeviceScanResponse(BaseModel):
    """Device scan response model."""
    serial_ports: List[SerialPort]
    cameras: List[Camera]
    scan_time: str


@router.get("/scan", response_model=DeviceScanResponse)
async def scan_devices() -> DeviceScanResponse:
    """Scan for available serial ports and cameras.
    
    Returns:
        DeviceScanResponse: List of available serial ports and cameras.
    """
    try:
        logger.info("Starting device scan...")
        
        # Scan serial ports
        serial_ports = await _scan_serial_ports()
        
        # Scan cameras
        cameras = await _scan_cameras()
        
        logger.info(f"Device scan completed: {len(serial_ports)} serial ports, {len(cameras)} cameras")
        
        return DeviceScanResponse(
            serial_ports=serial_ports,
            cameras=cameras,
            scan_time=_get_current_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Error during device scan: {e}")
        raise HTTPException(status_code=500, detail=f"Device scan failed: {str(e)}")


async def _scan_serial_ports() -> List[SerialPort]:
    """Scan for available serial ports.
    
    Returns:
        List[SerialPort]: Available serial ports.
    """
    try:
        import serial.tools.list_ports
        
        ports = []
        for port in serial.tools.list_ports.comports():
            # Extract VID/PID from hwid if available
            vid = None
            pid = None
            if port.vid is not None:
                vid = port.vid
            if port.pid is not None:
                pid = port.pid
            
            ports.append(SerialPort(
                path=port.device,
                vid=vid,
                pid=pid,
                desc=port.description,
                hwid=port.hwid
            ))
        
        logger.info(f"Found {len(ports)} serial ports")
        return ports
        
    except ImportError:
        logger.warning("pyserial not available, returning empty port list")
        return []
    except Exception as e:
        logger.error(f"Error scanning serial ports: {e}")
        return []


async def _scan_cameras() -> List[Camera]:
    """Scan for available cameras.
    
    Returns:
        List[Camera]: Available cameras.
    """
    try:
        import cv2
        
        cameras = []
        # Try to detect cameras by attempting to open them
        for i in range(10):  # Check first 10 camera indices
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # Try to read a frame to verify the camera works
                    ret, _ = cap.read()
                    if ret:
                        cameras.append(Camera(
                            path=f"/dev/video{i}",
                            name=f"Camera {i}",
                            index=i
                        ))
                    cap.release()
            except Exception:
                continue
        
        logger.info(f"Found {len(cameras)} cameras")
        return cameras
        
    except ImportError:
        logger.warning("OpenCV not available, returning empty camera list")
        return []
    except Exception as e:
        logger.error(f"Error scanning cameras: {e}")
        return []


def _get_current_timestamp() -> str:
    """Get current timestamp as ISO string.
    
    Returns:
        str: Current timestamp in ISO format.
    """
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
