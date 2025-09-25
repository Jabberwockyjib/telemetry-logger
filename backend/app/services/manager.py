"""Service manager for coordinating telemetry data collection services."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional, Set

from ..db.crud import session_crud
from ..db.models import Session
from sqlalchemy.ext.asyncio import AsyncSession


class ServiceManager:
    """Manages active telemetry data collection services.
    
    This class tracks active sessions and coordinates the start/stop
    of data collection services (OBD-II, GPS, etc.).
    """
    
    def __init__(self) -> None:
        """Initialize the service manager."""
        self._active_sessions: Set[int] = set()
        self._service_tasks: Dict[int, Dict[str, asyncio.Task]] = {}
        self._lock = asyncio.Lock()
    
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
                # Start data collection services (stubs for now)
                tasks = {
                    "obd_service": asyncio.create_task(self._obd_service_stub(session_id)),
                    "gps_service": asyncio.create_task(self._gps_service_stub(session_id)),
                    "meshtastic_service": asyncio.create_task(self._meshtastic_service_stub(session_id)),
                }
                
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
        """Stub Meshtastic uplink service.
        
        Args:
            session_id: ID of the session to uplink data for.
        """
        try:
            while True:
                # TODO: Implement actual Meshtastic uplink
                print(f"Meshtastic service uplinking data for session {session_id}")
                
                # Broadcast uplink status via WebSocket
                from .websocket_bus import websocket_bus
                uplink_data = {
                    "source": "meshtastic",
                    "status": "uplinked",
                    "packet_size_bytes": 64,
                    "signal_strength": -85,
                }
                await websocket_bus.broadcast_to_session(session_id, uplink_data)
                
                await asyncio.sleep(1.0)  # 1 Hz uplink rate
                
        except asyncio.CancelledError:
            print(f"Meshtastic service stopped for session {session_id}")
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


# Global service manager instance
service_manager = ServiceManager()
