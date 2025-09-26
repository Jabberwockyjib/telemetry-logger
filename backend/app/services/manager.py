"""Service manager for coordinating telemetry data collection services."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Set

from ..db.crud import session_crud, device_profile_crud
from ..db.models import Session, DeviceProfile
from sqlalchemy.ext.asyncio import AsyncSession
from .db_writer import db_writer, TelemetryData
from .meshtastic_service import meshtastic_service
from .gps_service import GPSService
from .obd_service import OBDService

logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages active telemetry data collection services.
    
    This class tracks active sessions and coordinates the start/stop
    of data collection services (OBD-II, GPS, etc.).
    """
    
    def __init__(self) -> None:
        """Initialize the service manager."""
        self._active_sessions: Set[int] = set()
        self._service_tasks: Dict[int, Dict[str, asyncio.Task]] = {}
        self._current_session_id: Optional[int] = None
        self._lock = asyncio.Lock()
        
        # Service instances
        self._gps_service: Optional[GPSService] = None
        self._obd_service: Optional[OBDService] = None
        self._meshtastic_service = meshtastic_service
        
        # Current device profile
        self._current_profile: Optional[DeviceProfile] = None
    
    async def initialize(self, db: AsyncSession) -> bool:
        """Initialize the service manager with default device profile.
        
        Args:
            db: Database session.
            
        Returns:
            bool: True if initialization successful, False otherwise.
        """
        try:
            # Load default device profile
            success = await self.load_device_profile(db, None)
            if success:
                self._create_services_from_profile()
                logger.info("Service manager initialized with device profile")
            else:
                logger.warning("Service manager initialized without device profile, using defaults")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize service manager: {e}")
            return False
    
    async def load_device_profile(self, db: AsyncSession, profile_id: Optional[int] = None) -> bool:
        """Load device profile configuration.
        
        Args:
            db: Database session.
            profile_id: Optional profile ID. If None, loads default profile.
            
        Returns:
            bool: True if profile loaded successfully, False otherwise.
        """
        try:
            if profile_id is None:
                profile = await device_profile_crud.get_default(db)
            else:
                profile = await device_profile_crud.get_by_id(db, profile_id)
            
            if profile is None:
                logger.warning("No device profile found, using default service configurations")
                return False
            
            self._current_profile = profile
            logger.info(f"Loaded device profile: {profile.name} (ID: {profile.id})")
            
            # Log configuration details
            if profile.gps_config:
                import json
                gps_config = json.loads(profile.gps_config) if isinstance(profile.gps_config, str) else (profile.gps_config if isinstance(profile.gps_config, dict) else {})
                logger.info(f"GPS Configuration - Port: {gps_config.get('port', 'default')}, "
                           f"Baud Rate: {gps_config.get('baud_rate', 'default')}, "
                           f"Rate: {gps_config.get('rate_hz', 'default')} Hz")
            
            if profile.obd_config:
                import json
                obd_config = json.loads(profile.obd_config) if isinstance(profile.obd_config, str) else (profile.obd_config if isinstance(profile.obd_config, dict) else {})
                logger.info(f"OBD Configuration - Port: {obd_config.get('port', 'default')}, "
                           f"Baud Rate: {obd_config.get('baud_rate', 'default')}, "
                           f"Rate: {obd_config.get('rate_hz', 'default')} Hz")
            
            if profile.meshtastic_config:
                import json
                mesh_config = json.loads(profile.meshtastic_config) if isinstance(profile.meshtastic_config, str) else (profile.meshtastic_config if isinstance(profile.meshtastic_config, dict) else {})
                logger.info(f"Meshtastic Configuration - Port: {mesh_config.get('port', 'default')}, "
                           f"Baud Rate: {mesh_config.get('baud_rate', 'default')}, "
                           f"Rate: {mesh_config.get('rate_hz', 'default')} Hz")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load device profile: {e}")
            return False
    
    def _create_services_from_profile(self) -> None:
        """Create service instances based on current device profile."""
        if self._current_profile is None:
            logger.warning("No device profile loaded, using default service configurations")
            return
        
        # Create GPS service
        if self._current_profile.gps_config:
            import json
            gps_config = json.loads(self._current_profile.gps_config) if isinstance(self._current_profile.gps_config, str) else (self._current_profile.gps_config if isinstance(self._current_profile.gps_config, dict) else {})
            self._gps_service = GPSService(
                port=gps_config.get('port', '/dev/ttyUSB0'),
                baudrate=gps_config.get('baud_rate', 4800),
                timeout=gps_config.get('timeout', 1.0),
                rate_hz=gps_config.get('rate_hz', 1.0),
                max_reconnect_attempts=gps_config.get('max_reconnect', 10),
                reconnect_delay=gps_config.get('reconnect_delay', 5.0)
            )
            logger.info(f"Created GPS service with port: {self._gps_service.port}, "
                       f"baud rate: {self._gps_service.baudrate}")
        else:
            self._gps_service = GPSService()  # Use defaults
            logger.info("Created GPS service with default configuration")
        
        # Create OBD service
        if self._current_profile.obd_config:
            import json
            obd_config = json.loads(self._current_profile.obd_config) if isinstance(self._current_profile.obd_config, str) else (self._current_profile.obd_config if isinstance(self._current_profile.obd_config, dict) else {})
            self._obd_service = OBDService(
                port=obd_config.get('port', '/dev/ttyUSB1'),
                baudrate=obd_config.get('baud_rate', 38400),
                timeout=obd_config.get('timeout', 5.0),
                max_reconnect_attempts=obd_config.get('max_reconnect', 5),
                reconnect_delay=obd_config.get('reconnect_delay', 10.0)
            )
            logger.info(f"Created OBD service with port: {self._obd_service.port}, "
                       f"baud rate: {self._obd_service.baudrate}")
        else:
            self._obd_service = OBDService()  # Use defaults
            logger.info("Created OBD service with default configuration")
        
        # Configure Meshtastic service
        if self._current_profile.meshtastic_config:
            import json
            mesh_config = json.loads(self._current_profile.meshtastic_config) if isinstance(self._current_profile.meshtastic_config, str) else (self._current_profile.meshtastic_config if isinstance(self._current_profile.meshtastic_config, dict) else {})
            # Update meshtastic service configuration
            self._meshtastic_service.port = mesh_config.get('port', '/dev/ttyUSB2')
            self._meshtastic_service.baudrate = mesh_config.get('baud_rate', 9600)
            self._meshtastic_service.timeout = mesh_config.get('timeout', 1.0)
            self._meshtastic_service.rate_hz = mesh_config.get('rate_hz', 1.0)
            logger.info(f"Configured Meshtastic service with port: {self._meshtastic_service.port}, "
                       f"baud rate: {self._meshtastic_service.baudrate}")
        else:
            logger.info("Using default Meshtastic service configuration")
    
    async def start_session_services(self, session_id: int, db: AsyncSession) -> bool:
        """Start data collection services for a session.
        
        Args:
            session_id: ID of the session to start services for.
            
        Returns:
            bool: True if services started successfully, False otherwise.
        """
        async with self._lock:
            if session_id in self._active_sessions:
                return False  # Session already active
            
            # Verify session exists
            session = await session_crud.get_by_id(db, session_id)
            if session is None:
                return False
            
            try:
                # Start database writer if not already running
                if not db_writer.is_running:
                    await db_writer.start()
                
                # Start data collection services
                tasks = {}
                
                # Start GPS service if configured
                if self._gps_service is not None:
                    tasks["gps_service"] = asyncio.create_task(self._start_gps_service(session_id))
                else:
                    tasks["gps_service"] = asyncio.create_task(self._gps_service_stub(session_id))
                
                # Start OBD service if configured
                if self._obd_service is not None:
                    tasks["obd_service"] = asyncio.create_task(self._start_obd_service(session_id))
                else:
                    tasks["obd_service"] = asyncio.create_task(self._obd_service_stub(session_id))
                
                # Start Meshtastic service
                tasks["meshtastic_service"] = asyncio.create_task(self._start_meshtastic_service(session_id))
                
                self._service_tasks[session_id] = tasks
                self._active_sessions.add(session_id)
                
                return True
                
            except Exception as e:
                # Clean up on error
                await self._cleanup_session_services(session_id)
                raise e
    
    async def stop_session_services(self, session_id: int) -> bool:
        """Stop data collection services for a session.
        
        Args:
            session_id: ID of the session to stop services for.
            
        Returns:
            bool: True if services stopped successfully, False otherwise.
        """
        async with self._lock:
            if session_id not in self._active_sessions:
                return False  # Session not active
            
            try:
                # Stop all services for this session
                await self._cleanup_session_services(session_id)
                self._active_sessions.discard(session_id)
                
                return True
                
            except Exception as e:
                # Log error but don't fail the stop operation
                print(f"Error stopping services for session {session_id}: {e}")
                return False
    
    async def is_session_active(self, session_id: int) -> bool:
        """Check if a session is currently active.
        
        Args:
            session_id: ID of the session to check.
            
        Returns:
            bool: True if session is active, False otherwise.
        """
        async with self._lock:
            return session_id in self._active_sessions
    
    async def get_active_sessions(self) -> Set[int]:
        """Get all currently active session IDs.
        
        Returns:
            Set[int]: Set of active session IDs.
        """
        async with self._lock:
            return self._active_sessions.copy()
    
    def is_running(self) -> bool:
        """Check if telemetry is currently running.
        
        Returns:
            bool: True if telemetry is running, False otherwise.
        """
        return self._current_session_id is not None
    
    def get_current_session_id(self) -> Optional[int]:
        """Get the current active session ID.
        
        Returns:
            Optional[int]: Current session ID if running, None otherwise.
        """
        return self._current_session_id
    
    async def start_session(self, session_id: int, profile_id: Optional[int] = None, db: Optional[AsyncSession] = None) -> bool:
        """Start a new telemetry session.
        
        Args:
            session_id: ID of the session to start.
            profile_id: Optional profile ID for device configuration.
            db: Database session for loading profiles.
            
        Returns:
            bool: True if session started successfully, False otherwise.
        """
        async with self._lock:
            if self._current_session_id is not None:
                return False  # Already running
            
            try:
                # Load device profile if provided
                if profile_id is not None and db is not None:
                    await self.load_device_profile(db, profile_id)
                    self._create_services_from_profile()
                
                # Start services for the session
                success = await self.start_session_services(session_id, db)
                if success:
                    self._current_session_id = session_id
                    return True
                return False
                
            except Exception as e:
                logger.error(f"Error starting session {session_id}: {e}")
                return False
    
    async def stop_session(self) -> bool:
        """Stop the current telemetry session.
        
        Returns:
            bool: True if session stopped successfully, False otherwise.
        """
        async with self._lock:
            if self._current_session_id is None:
                return False  # Not running
            
            try:
                session_id = self._current_session_id
                success = await self.stop_session_services(session_id)
                if success:
                    self._current_session_id = None
                    return True
                return False
                
            except Exception as e:
                print(f"Error stopping session: {e}")
                return False
    
    async def _cleanup_session_services(self, session_id: int) -> None:
        """Clean up service tasks for a session.
        
        Args:
            session_id: ID of the session to clean up.
        """
        if session_id in self._service_tasks:
            tasks = self._service_tasks[session_id]
            
            # Cancel all tasks
            for task_name, task in tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass  # Expected when cancelling
            
            # Remove from tracking
            del self._service_tasks[session_id]
    
    async def _start_gps_service(self, session_id: int) -> None:
        """Start GPS service with configured settings.
        
        Args:
            session_id: ID of the session to collect data for.
        """
        try:
            if self._gps_service is not None:
                logger.info(f"Starting GPS service for session {session_id} on port {self._gps_service.port}")
                await self._gps_service.start(session_id)
                
                # Keep the service running
                while True:
                    await asyncio.sleep(1.0)
                    
        except asyncio.CancelledError:
            logger.info(f"GPS service stopped for session {session_id}")
            if self._gps_service is not None:
                await self._gps_service.stop()
        except Exception as e:
            logger.error(f"GPS service error for session {session_id}: {e}")
    
    async def _start_obd_service(self, session_id: int) -> None:
        """Start OBD service with configured settings.
        
        Args:
            session_id: ID of the session to collect data for.
        """
        try:
            if self._obd_service is not None:
                logger.info(f"Starting OBD service for session {session_id} on port {self._obd_service.port}")
                await self._obd_service.start(session_id)
                
                # Keep the service running
                while True:
                    await asyncio.sleep(1.0)
                    
        except asyncio.CancelledError:
            logger.info(f"OBD service stopped for session {session_id}")
            if self._obd_service is not None:
                await self._obd_service.stop()
        except Exception as e:
            logger.error(f"OBD service error for session {session_id}: {e}")
    
    async def _start_meshtastic_service(self, session_id: int) -> None:
        """Start Meshtastic service with configured settings.
        
        Args:
            session_id: ID of the session to collect data for.
        """
        try:
            logger.info(f"Starting Meshtastic service for session {session_id} on port {self._meshtastic_service.port}")
            await self._meshtastic_service.start(session_id)
            
            # Keep the service running
            while True:
                await asyncio.sleep(1.0)
                
        except asyncio.CancelledError:
            logger.info(f"Meshtastic service stopped for session {session_id}")
            await self._meshtastic_service.stop()
        except Exception as e:
            logger.error(f"Meshtastic service error for session {session_id}: {e}")
    
    async def _obd_service_stub(self, session_id: int) -> None:
        """OBD-II data collection service.
        
        Args:
            session_id: ID of the session to collect data for.
        """
        try:
            from .obd_service import OBDService
            
            # Create and start OBD service
            obd_service = OBDService()
            await obd_service.start(session_id)
            
            # Keep the service running
            while True:
                await asyncio.sleep(1.0)
                
        except asyncio.CancelledError:
            print(f"OBD service stopped for session {session_id}")
            if 'obd_service' in locals():
                await obd_service.stop()
            raise
        except Exception as e:
            print(f"OBD service error for session {session_id}: {e}")
            if 'obd_service' in locals():
                await obd_service.stop()
            raise
    
    async def _gps_service_stub(self, session_id: int) -> None:
        """Stub GPS data collection service.
        
        Args:
            session_id: ID of the session to collect data for.
        """
        try:
            while True:
                # TODO: Implement actual GPS data collection
                print(f"GPS service collecting data for session {session_id}")
                
                # Broadcast stub data via WebSocket
                from .websocket_bus import websocket_bus
                stub_data = {
                    "source": "gps",
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "altitude_m": 10.0,
                    "speed_kph": 65.0,
                    "heading_deg": 45.0,
                }
                await websocket_bus.broadcast_to_session(session_id, stub_data)
                
                await asyncio.sleep(0.1)  # 10 Hz collection rate
                
        except asyncio.CancelledError:
            print(f"GPS service stopped for session {session_id}")
            raise
    
    async def _meshtastic_service_stub(self, session_id: int) -> None:
        """Meshtastic uplink service.
        
        Args:
            session_id: ID of the session to uplink data for.
        """
        try:
            # Start the real Meshtastic service
            await meshtastic_service.start(session_id)
            
            # Keep the service running
            while True:
                await asyncio.sleep(1.0)
                
        except asyncio.CancelledError:
            print(f"Meshtastic service stopped for session {session_id}")
            await meshtastic_service.stop()
            raise
        except Exception as e:
            print(f"Meshtastic service error for session {session_id}: {e}")
            await meshtastic_service.stop()
            raise
    
    async def shutdown(self) -> None:
        """Shutdown all services and clean up resources."""
        async with self._lock:
            # Stop all active sessions
            active_sessions = list(self._active_sessions)
            for session_id in active_sessions:
                await self._cleanup_session_services(session_id)
            
            self._active_sessions.clear()
            self._service_tasks.clear()
            
            # Stop database writer
            if db_writer.is_running:
                await db_writer.stop()


# Global service manager instance
service_manager = ServiceManager()
