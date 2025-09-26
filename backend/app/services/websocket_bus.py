"""WebSocket bus for real-time telemetry data streaming.

This module implements a pub/sub pattern for broadcasting telemetry data
to connected WebSocket clients in real-time.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketBus:
    """WebSocket bus for managing real-time data streaming.
    
    This class manages WebSocket connections and provides a pub/sub
    interface for broadcasting telemetry data to connected clients.
    """
    
    def __init__(self) -> None:
        """Initialize the WebSocket bus."""
        self._connections: Dict[int, Set[WebSocket]] = {}  # session_id -> set of websockets
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, session_id: int) -> None:
        """Connect a WebSocket client to a session.
        
        Args:
            websocket: WebSocket connection to add.
            session_id: Session ID to connect to.
        """
        async with self._lock:
            if session_id not in self._connections:
                self._connections[session_id] = set()
            
            self._connections[session_id].add(websocket)
            logger.info(f"WebSocket connected to session {session_id}. Total connections: {len(self._connections[session_id])}")
            
            # Start heartbeat if this is the first connection
            if len(self._connections[session_id]) == 1 and self._heartbeat_task is None:
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def disconnect(self, websocket: WebSocket, session_id: int) -> None:
        """Disconnect a WebSocket client from a session.
        
        Args:
            websocket: WebSocket connection to remove.
            session_id: Session ID to disconnect from.
        """
        async with self._lock:
            if session_id in self._connections:
                self._connections[session_id].discard(websocket)
                logger.info(f"WebSocket disconnected from session {session_id}. Remaining connections: {len(self._connections[session_id])}")
                
                # Clean up empty session
                if not self._connections[session_id]:
                    del self._connections[session_id]
                    logger.info(f"Session {session_id} has no more WebSocket connections")
                
                # Stop heartbeat if no connections remain
                if not self._connections and self._heartbeat_task:
                    self._heartbeat_task.cancel()
                    self._heartbeat_task = None
    
    async def broadcast_to_session(self, session_id: int, data: Dict[str, Any]) -> None:
        """Broadcast data to all WebSocket clients connected to a session.
        
        Args:
            session_id: Session ID to broadcast to.
            data: Data to broadcast (will be JSON serialized).
        """
        if session_id not in self._connections:
            return
        
        # Create a copy of connections to avoid modification during iteration
        connections = self._connections[session_id].copy()
        
        if not connections:
            return
        
        # Prepare the message
        message = {
            "type": "telemetry_data",
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        
        message_json = json.dumps(message)
        
        # Broadcast to all connections
        disconnected = set()
        for websocket in connections:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected WebSockets
        if disconnected:
            async with self._lock:
                self._connections[session_id] -= disconnected
                if not self._connections[session_id]:
                    del self._connections[session_id]
    
    async def broadcast_heartbeat(self) -> None:
        """Broadcast heartbeat to all connected WebSocket clients."""
        if not self._connections:
            return
        
        heartbeat_message = {
            "type": "heartbeat",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "WebSocket connection active",
        }
        
        heartbeat_json = json.dumps(heartbeat_message)
        
        # Broadcast to all sessions
        for session_id in list(self._connections.keys()):
            connections = self._connections[session_id].copy()
            disconnected = set()
            
            for websocket in connections:
                try:
                    await websocket.send_text(heartbeat_json)
                except Exception as e:
                    logger.warning(f"Failed to send heartbeat to WebSocket: {e}")
                    disconnected.add(websocket)
            
            # Remove disconnected WebSockets
            if disconnected:
                async with self._lock:
                    self._connections[session_id] -= disconnected
                    if not self._connections[session_id]:
                        del self._connections[session_id]
    
    async def get_connection_count(self, session_id: Optional[int] = None) -> int:
        """Get the number of active WebSocket connections.
        
        Args:
            session_id: Optional session ID to count connections for.
                       If None, returns total connections across all sessions.
        
        Returns:
            int: Number of active connections.
        """
        async with self._lock:
            if session_id is not None:
                return len(self._connections.get(session_id, set()))
            else:
                return sum(len(connections) for connections in self._connections.values())
    
    async def get_active_sessions(self) -> List[int]:
        """Get list of session IDs with active WebSocket connections.
        
        Returns:
            List[int]: List of session IDs with active connections.
        """
        async with self._lock:
            return list(self._connections.keys())
    
    async def _heartbeat_loop(self) -> None:
        """Background task to send periodic heartbeats."""
        try:
            while True:
                await asyncio.sleep(5.0)  # Send heartbeat every 5 seconds
                await self.broadcast_heartbeat()
        except asyncio.CancelledError:
            logger.info("Heartbeat loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the WebSocket bus and clean up resources."""
        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
        
        # Close all connections
        async with self._lock:
            for session_id, connections in self._connections.items():
                for websocket in connections:
                    try:
                        await websocket.close()
                    except Exception as e:
                        logger.warning(f"Error closing WebSocket: {e}")
            
            self._connections.clear()
        
        logger.info("WebSocket bus shutdown complete")


# Global WebSocket bus instance
websocket_bus = WebSocketBus()
