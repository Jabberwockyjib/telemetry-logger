"""OBD-II service for reading automotive diagnostic data using python-OBD."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

try:
    import obd
    from obd import OBDStatus
    OBD_AVAILABLE = True
except ImportError:
    OBD_AVAILABLE = False
    # Create mock OBD classes for when library is not available
    class OBDStatus:
        CAR_CONNECTED = "CAR_CONNECTED"
        NOT_CONNECTED = "NOT_CONNECTED"
    
    class MockOBD:
        def __init__(self, *args, **kwargs):
            self.status = OBDStatus.NOT_CONNECTED
        
        def query(self, *args, **kwargs):
            return None
        
        def close(self):
            pass
    
    class MockOBDCommand:
        def __init__(self, name):
            self.name = name
    
    class MockOBDResponse:
        def __init__(self, value=None, unit=None):
            self.value = value
            self.unit = unit
    
    # Mock obd module
    class MockOBDModule:
        OBD = MockOBD
        OBDStatus = OBDStatus
        OBDResponse = MockOBDResponse
        OBDCommand = MockOBDCommand
        commands = type('commands', (), {
            'SPEED': MockOBDCommand('SPEED'),
            'RPM': MockOBDCommand('RPM'),
            'THROTTLE_POS': MockOBDCommand('THROTTLE_POS'),
            'ENGINE_LOAD': MockOBDCommand('ENGINE_LOAD'),
            'COOLANT_TEMP': MockOBDCommand('COOLANT_TEMP'),
            'FUEL_LEVEL': MockOBDCommand('FUEL_LEVEL'),
            'INTAKE_TEMP': MockOBDCommand('INTAKE_TEMP'),
            'MAF': MockOBDCommand('MAF'),
            'TIMING_ADVANCE': MockOBDCommand('TIMING_ADVANCE'),
            'FUEL_PRESSURE': MockOBDCommand('FUEL_PRESSURE'),
        })()
    
    obd = MockOBDModule()

from ..services.websocket_bus import websocket_bus
from ..services.db_writer import db_writer, TelemetryData
from ..services.meshtastic_service import meshtastic_service

logger = logging.getLogger(__name__)


class OBDService:
    """OBD-II service for reading automotive diagnostic data.
    
    This service uses python-OBD to communicate with OBD-II compliant vehicles
    and provides configurable PID monitoring with per-PID rates.
    """
    
    # Default PID configuration with common automotive parameters
    DEFAULT_PIDS = {
        "SPEED": {"rate_hz": 10.0, "unit": "kph", "description": "Vehicle speed"},
        "RPM": {"rate_hz": 10.0, "unit": "rpm", "description": "Engine RPM"},
        "THROTTLE_POS": {"rate_hz": 5.0, "unit": "%", "description": "Throttle position"},
        "ENGINE_LOAD": {"rate_hz": 5.0, "unit": "%", "description": "Calculated engine load"},
        "COOLANT_TEMP": {"rate_hz": 2.0, "unit": "°C", "description": "Engine coolant temperature"},
        "FUEL_LEVEL": {"rate_hz": 1.0, "unit": "%", "description": "Fuel tank level"},
        "INTAKE_TEMP": {"rate_hz": 2.0, "unit": "°C", "description": "Intake air temperature"},
        "MAF": {"rate_hz": 5.0, "unit": "g/s", "description": "Mass air flow rate"},
        "TIMING_ADVANCE": {"rate_hz": 5.0, "unit": "°", "description": "Timing advance"},
        "FUEL_PRESSURE": {"rate_hz": 2.0, "unit": "kPa", "description": "Fuel rail pressure"},
    }
    
    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 38400,
        timeout: float = 5.0,
        max_reconnect_attempts: int = 5,
        reconnect_delay: float = 10.0,
        pid_config: Optional[Dict[str, Dict[str, any]]] = None,
    ) -> None:
        """Initialize OBD service.
        
        Args:
            port: Serial port for OBD-II adapter.
            baudrate: Serial baud rate.
            timeout: OBD command timeout in seconds.
            max_reconnect_attempts: Maximum reconnection attempts.
            reconnect_delay: Delay between reconnection attempts in seconds.
            pid_config: Custom PID configuration. If None, uses DEFAULT_PIDS.
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        
        # PID configuration
        self.pid_config = pid_config or self.DEFAULT_PIDS.copy()
        self.supported_pids: Set[str] = set()
        self.unsupported_pids: Set[str] = set()
        
        # OBD connection
        self.obd_connection: Optional[obd.OBD] = None
        self.is_running = False
        self.session_id: Optional[int] = None
        
        # Data tracking
        self.last_known_values: Dict[str, any] = {}
        self.reading_tasks: Dict[str, asyncio.Task] = {}
        
        # Statistics
        self.total_readings = 0
        self.successful_readings = 0
        self.failed_readings = 0
        self.reconnect_count = 0
    
    async def start(self, session_id: int) -> None:
        """Start OBD service for a session.
        
        Args:
            session_id: Session ID to collect data for.
        """
        self.session_id = session_id
        self.is_running = True
        
        logger.info(f"Starting OBD service for session {session_id} on port {self.port}")
        
        # Connect to OBD adapter
        await self._connect_obd()
        
        # Start PID reading tasks
        await self._start_pid_tasks()
    
    async def stop(self) -> None:
        """Stop OBD service."""
        self.is_running = False
        
        # Cancel all reading tasks
        for task in self.reading_tasks.values():
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.reading_tasks:
            await asyncio.gather(*self.reading_tasks.values(), return_exceptions=True)
        
        self.reading_tasks.clear()
        
        # Close OBD connection
        if self.obd_connection:
            self.obd_connection.close()
            self.obd_connection = None
        
        logger.info(f"OBD service stopped. Stats: {self.total_readings} total, {self.successful_readings} successful, {self.failed_readings} failed")
    
    async def _connect_obd(self) -> None:
        """Connect to OBD adapter with retry logic."""
        for attempt in range(self.max_reconnect_attempts):
            try:
                if self.obd_connection and self.obd_connection.status == OBDStatus.CAR_CONNECTED:
                    return
                
                logger.info(f"Connecting to OBD adapter on {self.port} (attempt {attempt + 1})")
                
                # Create OBD connection
                self.obd_connection = obd.OBD(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                )
                
                # Check connection status
                if self.obd_connection.status == OBDStatus.CAR_CONNECTED:
                    logger.info("OBD adapter connected successfully")
                    await self._discover_supported_pids()
                    self.reconnect_count = 0
                    return
                else:
                    logger.warning(f"OBD connection failed with status: {self.obd_connection.status}")
                    self.obd_connection.close()
                    self.obd_connection = None
                
            except Exception as e:
                logger.error(f"OBD connection attempt {attempt + 1} failed: {e}")
                if self.obd_connection:
                    self.obd_connection.close()
                    self.obd_connection = None
            
            if attempt < self.max_reconnect_attempts - 1:
                await asyncio.sleep(self.reconnect_delay)
        
        raise Exception(f"Failed to connect to OBD adapter after {self.max_reconnect_attempts} attempts")
    
    async def _discover_supported_pids(self) -> None:
        """Discover which PIDs are supported by the vehicle."""
        if not self.obd_connection:
            return
        
        logger.info("Discovering supported PIDs...")
        
        for pid_name in self.pid_config.keys():
            try:
                # Get the OBD command for this PID
                cmd = self._get_obd_command(pid_name)
                if cmd is None:
                    logger.warning(f"Unknown PID: {pid_name}")
                    self.unsupported_pids.add(pid_name)
                    continue
                
                # Test if PID is supported
                response = self.obd_connection.query(cmd, force=True)
                if response.value is not None:
                    self.supported_pids.add(pid_name)
                    logger.debug(f"PID {pid_name} is supported")
                else:
                    self.unsupported_pids.add(pid_name)
                    logger.debug(f"PID {pid_name} is not supported")
                
            except Exception as e:
                logger.warning(f"Error testing PID {pid_name}: {e}")
                self.unsupported_pids.add(pid_name)
        
        logger.info(f"Supported PIDs: {len(self.supported_pids)}/{len(self.pid_config)}")
        logger.info(f"Supported: {sorted(self.supported_pids)}")
        if self.unsupported_pids:
            logger.info(f"Unsupported: {sorted(self.unsupported_pids)}")
    
    async def _start_pid_tasks(self) -> None:
        """Start async tasks for reading each supported PID."""
        for pid_name in self.supported_pids:
            if pid_name in self.reading_tasks:
                continue
            
            rate_hz = self.pid_config[pid_name]["rate_hz"]
            task = asyncio.create_task(self._read_pid_loop(pid_name, rate_hz))
            self.reading_tasks[pid_name] = task
            logger.debug(f"Started reading task for PID {pid_name} at {rate_hz} Hz")
    
    async def _read_pid_loop(self, pid_name: str, rate_hz: float) -> None:
        """Read a specific PID at the configured rate.
        
        Args:
            pid_name: Name of the PID to read.
            rate_hz: Reading rate in Hz.
        """
        interval = 1.0 / rate_hz
        
        try:
            while self.is_running:
                await self._read_single_pid(pid_name)
                await asyncio.sleep(interval)
                
        except asyncio.CancelledError:
            logger.debug(f"PID reading task for {pid_name} cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in PID reading loop for {pid_name}: {e}")
            raise
    
    async def _read_single_pid(self, pid_name: str) -> None:
        """Read a single PID value.
        
        Args:
            pid_name: Name of the PID to read.
        """
        if not self.obd_connection or not self.is_running:
            return
        
        try:
            # Get OBD command
            cmd = self._get_obd_command(pid_name)
            if cmd is None:
                return
            
            # Query the PID
            response = self.obd_connection.query(cmd)
            
            self.total_readings += 1
            
            if response.value is not None:
                self.successful_readings += 1
                await self._handle_pid_response(pid_name, response)
            else:
                self.failed_readings += 1
                logger.debug(f"Failed to read PID {pid_name}: {response}")
                
        except Exception as e:
            self.failed_readings += 1
            logger.error(f"Error reading PID {pid_name}: {e}")
            
            # Check if we need to reconnect
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                await self._handle_connection_error()
    
    async def _handle_pid_response(self, pid_name: str, response: obd.OBDResponse) -> None:
        """Handle a successful PID response.
        
        Args:
            pid_name: Name of the PID.
            response: OBD response object.
        """
        if not self.session_id:
            return
        
        # Extract value and unit
        value = response.value
        unit = response.unit
        
        # Get PID configuration
        pid_config = self.pid_config.get(pid_name, {})
        configured_unit = pid_config.get("unit", "")
        
        # Use configured unit if available, otherwise use OBD unit
        final_unit = configured_unit or (unit if unit else "")
        
        # Determine quality based on response
        quality = "good" if response.value is not None else "no_data"
        
        # Update last known values
        self.last_known_values[pid_name] = {
            "value": value,
            "unit": final_unit,
            "quality": quality,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Prepare data for WebSocket broadcast
        ws_data = {
            "source": "obd",
            "pid": pid_name,
            "value": value,
            "unit": final_unit,
            "quality": quality,
            "description": pid_config.get("description", ""),
        }
        
        # Store in database via database writer
        telemetry_data = TelemetryData(
            session_id=self.session_id,
            source="obd",
            channel=pid_name,
            value_num=value,
            unit=final_unit,
            quality=quality,
        )
        await db_writer.queue_signal(telemetry_data)
        
        # Update Meshtastic service with OBD data
        meshtastic_service.update_telemetry_data("obd", {pid_name: {"value": value, "unit": final_unit, "quality": quality}})
        
        # Broadcast to WebSocket
        await websocket_bus.broadcast_to_session(self.session_id, ws_data)
        
        logger.debug(f"OBD {pid_name}: {value} {final_unit} ({quality})")
    
    async def _handle_connection_error(self) -> None:
        """Handle OBD connection errors."""
        logger.warning("OBD connection error detected, attempting reconnection...")
        
        # Cancel current reading tasks
        for task in self.reading_tasks.values():
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.reading_tasks:
            await asyncio.gather(*self.reading_tasks.values(), return_exceptions=True)
        
        self.reading_tasks.clear()
        
        # Attempt reconnection
        try:
            await self._connect_obd()
            await self._start_pid_tasks()
            self.reconnect_count += 1
            logger.info(f"OBD reconnection successful (attempt {self.reconnect_count})")
        except Exception as e:
            logger.error(f"OBD reconnection failed: {e}")
            # Will retry on next reading attempt
    
    def _get_obd_command(self, pid_name: str) -> Optional[obd.OBDCommand]:
        """Get OBD command for a PID name.
        
        Args:
            pid_name: Name of the PID.
            
        Returns:
            OBD command object or None if not found.
        """
        # Map PID names to OBD commands
        pid_commands = {
            "SPEED": obd.commands.SPEED,
            "RPM": obd.commands.RPM,
            "THROTTLE_POS": obd.commands.THROTTLE_POS,
            "ENGINE_LOAD": obd.commands.ENGINE_LOAD,
            "COOLANT_TEMP": obd.commands.COOLANT_TEMP,
            "FUEL_LEVEL": obd.commands.FUEL_LEVEL,
            "INTAKE_TEMP": obd.commands.INTAKE_TEMP,
            "MAF": obd.commands.MAF,
            "TIMING_ADVANCE": obd.commands.TIMING_ADVANCE,
            "FUEL_PRESSURE": obd.commands.FUEL_PRESSURE,
        }
        
        return pid_commands.get(pid_name)
    
    def get_status(self) -> Dict[str, any]:
        """Get OBD service status.
        
        Returns:
            Dict containing service status information.
        """
        return {
            "is_running": self.is_running,
            "port": self.port,
            "baudrate": self.baudrate,
            "session_id": self.session_id,
            "connection_status": self.obd_connection.status if self.obd_connection else "disconnected",
            "supported_pids": sorted(self.supported_pids),
            "unsupported_pids": sorted(self.unsupported_pids),
            "active_tasks": len(self.reading_tasks),
            "total_readings": self.total_readings,
            "successful_readings": self.successful_readings,
            "failed_readings": self.failed_readings,
            "reconnect_count": self.reconnect_count,
            "last_known_values": self.last_known_values,
        }
    
    def get_pid_config(self) -> Dict[str, Dict[str, any]]:
        """Get current PID configuration.
        
        Returns:
            Dict containing PID configuration.
        """
        return self.pid_config.copy()
    
    def update_pid_config(self, pid_config: Dict[str, Dict[str, any]]) -> None:
        """Update PID configuration.
        
        Args:
            pid_config: New PID configuration.
        """
        self.pid_config.update(pid_config)
        logger.info(f"Updated PID configuration: {list(pid_config.keys())}")
    
    @staticmethod
    def get_available_pids() -> List[str]:
        """Get list of available PID names.
        
        Returns:
            List of available PID names.
        """
        return list(OBDService.DEFAULT_PIDS.keys())
