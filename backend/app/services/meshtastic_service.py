"""Meshtastic service for publishing telemetry data via radio uplink."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from ..utils.packing import telemetry_packer
from ..services.websocket_bus import websocket_bus
from ..services.db_writer import db_writer, TelemetryData

logger = logging.getLogger(__name__)


class MeshtasticService:
    """Meshtastic service for publishing telemetry data via radio uplink.
    
    This service aggregates last-known values from GPS and OBD services
    and publishes them as compact binary payloads at 1 Hz rate.
    """
    
    def __init__(
        self,
        publish_rate_hz: float = 1.0,
        max_payload_size: int = 64,
        device_path: Optional[str] = None,
        baudrate: int = 38400,
    ) -> None:
        """Initialize Meshtastic service.
        
        Args:
            publish_rate_hz: Rate of frame publishing in Hz.
            max_payload_size: Maximum payload size in bytes.
            device_path: Path to Meshtastic device (e.g., '/dev/ttyUSB0').
            baudrate: Serial baud rate for device communication.
        """
        self.publish_rate_hz = publish_rate_hz
        self.max_payload_size = max_payload_size
        self.device_path = device_path
        self.baudrate = baudrate
        
        # State
        self.is_running = False
        self.session_id: Optional[int] = None
        self.last_known_values: Dict[str, any] = {}
        
        # Statistics
        self.frames_published = 0
        self.bytes_transmitted = 0
        self.publish_errors = 0
        self.start_time: Optional[datetime] = None
    
    async def start(self, session_id: int) -> None:
        """Start Meshtastic service for a session.
        
        Args:
            session_id: Session ID to publish data for.
        """
        self.session_id = session_id
        self.is_running = True
        self.start_time = datetime.now(timezone.utc)
        
        logger.info(f"Starting Meshtastic service for session {session_id} at {self.publish_rate_hz} Hz")
        
        # Start the publishing loop
        asyncio.create_task(self._publishing_loop())
    
    async def stop(self) -> None:
        """Stop Meshtastic service."""
        self.is_running = False
        
        logger.info(f"Meshtastic service stopped. Stats: {self.frames_published} frames, {self.bytes_transmitted} bytes")
    
    async def _publishing_loop(self) -> None:
        """Main publishing loop for Meshtastic frames."""
        interval = 1.0 / self.publish_rate_hz
        
        try:
            while self.is_running:
                await self._publish_frame()
                await asyncio.sleep(interval)
                
        except asyncio.CancelledError:
            logger.debug("Meshtastic publishing loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in Meshtastic publishing loop: {e}")
            raise
    
    async def _publish_frame(self) -> None:
        """Publish a single frame with current telemetry data."""
        if not self.session_id:
            return
        
        try:
            # Collect current telemetry data
            telemetry_data = await self._collect_telemetry_data()
            
            if not telemetry_data:
                logger.debug("No telemetry data available for publishing")
                return
            
            # Pack the data into binary payload
            payload = telemetry_packer.pack_telemetry_data(telemetry_data)
            
            if not payload:
                logger.debug("Failed to pack telemetry data")
                return
            
            # Check payload size
            if len(payload) > self.max_payload_size:
                logger.warning(f"Payload size {len(payload)} exceeds maximum {self.max_payload_size}")
                # Try to reduce payload size by removing less critical fields
                payload = await self._create_reduced_payload(telemetry_data)
            
            if not payload:
                logger.warning("Failed to create reduced payload")
                return
            
            # Publish the frame
            await self._transmit_frame(payload)
            
            # Update statistics
            self.frames_published += 1
            self.bytes_transmitted += len(payload)
            
            # Broadcast status via WebSocket
            await self._broadcast_status(payload)
            
            logger.debug(f"Published frame: {len(payload)} bytes, {len(telemetry_data)} fields")
            
        except Exception as e:
            self.publish_errors += 1
            logger.error(f"Error publishing frame: {e}")
    
    async def _collect_telemetry_data(self) -> Dict[str, float]:
        """Collect current telemetry data from all sources.
        
        Returns:
            Dictionary of current telemetry values.
        """
        # This would typically collect from GPS and OBD services
        # For now, we'll use the last known values stored in this service
        telemetry_data = {}
        
        for field_name, value_info in self.last_known_values.items():
            if isinstance(value_info, dict) and "value" in value_info:
                value = value_info["value"]
                if isinstance(value, (int, float)):
                    telemetry_data[field_name] = value
        
        return telemetry_data
    
    async def _create_reduced_payload(self, telemetry_data: Dict[str, float]) -> bytes:
        """Create a reduced payload by removing less critical fields.
        
        Args:
            telemetry_data: Full telemetry data dictionary.
            
        Returns:
            Reduced binary payload.
        """
        # Priority order: GPS position > OBD critical > OBD secondary
        priority_fields = [
            "latitude", "longitude", "altitude",  # GPS position (highest priority)
            "SPEED", "RPM", "THROTTLE_POS",      # OBD critical
            "ENGINE_LOAD", "COOLANT_TEMP",       # OBD secondary
            "FUEL_LEVEL", "INTAKE_TEMP",         # OBD tertiary
        ]
        
        reduced_data = {}
        for field in priority_fields:
            if field in telemetry_data:
                reduced_data[field] = telemetry_data[field]
                
                # Check if we're within size limit
                payload = telemetry_packer.pack_telemetry_data(reduced_data)
                if len(payload) <= self.max_payload_size:
                    continue
                else:
                    # Remove the last added field and return
                    del reduced_data[field]
                    break
        
        return telemetry_packer.pack_telemetry_data(reduced_data)
    
    async def _transmit_frame(self, payload: bytes) -> None:
        """Transmit frame via Meshtastic device.
        
        Args:
            payload: Binary payload to transmit.
        """
        if self.device_path:
            # In a real implementation, this would send data to the Meshtastic device
            # For now, we'll simulate the transmission
            logger.debug(f"Transmitting {len(payload)} bytes to {self.device_path}")
            
            # Simulate transmission delay
            await asyncio.sleep(0.01)
            
            # Store frame in database
            await self._store_frame(payload)
        else:
            logger.debug(f"Simulating transmission of {len(payload)} bytes")
            await self._store_frame(payload)
    
    async def _store_frame(self, payload: bytes) -> None:
        """Store frame data in database.
        
        Args:
            payload: Binary payload data.
        """
        if not self.session_id:
            return
        
        try:
            # Create frame data
            frame_data = {
                "payload_size": len(payload),
                "payload_hex": payload.hex(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            # Queue frame for database storage
            await db_writer.queue_frame(self.session_id, frame_data)
            
        except Exception as e:
            logger.error(f"Error storing frame: {e}")
    
    async def _broadcast_status(self, payload: bytes) -> None:
        """Broadcast Meshtastic status via WebSocket.
        
        Args:
            payload: Binary payload that was transmitted.
        """
        if not self.session_id:
            return
        
        try:
            status_data = {
                "source": "meshtastic",
                "status": "transmitted",
                "payload_size": len(payload),
                "frames_published": self.frames_published,
                "bytes_transmitted": self.bytes_transmitted,
                "publish_errors": self.publish_errors,
            }
            
            await websocket_bus.broadcast_to_session(self.session_id, status_data)
            
        except Exception as e:
            logger.error(f"Error broadcasting Meshtastic status: {e}")
    
    def update_telemetry_data(self, source: str, data: Dict[str, any]) -> None:
        """Update last known telemetry data from a source.
        
        Args:
            source: Data source (e.g., 'gps', 'obd').
            data: Telemetry data from the source.
        """
        for field_name, value in data.items():
            if isinstance(value, dict) and "value" in value:
                # Handle structured value (from OBD service)
                self.last_known_values[field_name] = value
            elif isinstance(value, (int, float)):
                # Handle direct numeric value (from GPS service)
                self.last_known_values[field_name] = {
                    "value": value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
    
    def get_status(self) -> Dict[str, any]:
        """Get Meshtastic service status.
        
        Returns:
            Dict containing service status information.
        """
        runtime = 0
        if self.start_time:
            runtime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        frames_per_minute = 0
        if runtime > 0:
            frames_per_minute = (self.frames_published / runtime) * 60
        
        return {
            "is_running": self.is_running,
            "session_id": self.session_id,
            "publish_rate_hz": self.publish_rate_hz,
            "max_payload_size": self.max_payload_size,
            "device_path": self.device_path,
            "frames_published": self.frames_published,
            "bytes_transmitted": self.bytes_transmitted,
            "publish_errors": self.publish_errors,
            "runtime_seconds": runtime,
            "frames_per_minute": frames_per_minute,
            "last_known_values_count": len(self.last_known_values),
        }
    
    def get_last_known_values(self) -> Dict[str, any]:
        """Get current last known telemetry values.
        
        Returns:
            Dictionary of last known values.
        """
        return self.last_known_values.copy()
    
    def clear_telemetry_data(self) -> None:
        """Clear all last known telemetry data."""
        self.last_known_values.clear()
        logger.info("Cleared all telemetry data")


# Global Meshtastic service instance
meshtastic_service = MeshtasticService()
