"""GPS service for reading and parsing NMEA data from serial ports."""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import serial
import serial.tools.list_ports

from ..db.crud import signal_crud
from ..services.websocket_bus import websocket_bus
from ..services.db_writer import db_writer, TelemetryData
from ..services.meshtastic_service import meshtastic_service

logger = logging.getLogger(__name__)


class NMEAParser:
    """NMEA sentence parser for GPS data."""
    
    def __init__(self) -> None:
        """Initialize NMEA parser."""
        # More flexible patterns that handle optional/empty fields
        self._gga_pattern = re.compile(
            r'\$GPGGA,([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*)\*([0-9A-F]{2})'
        )
        self._rmc_pattern = re.compile(
            r'\$GPRMC,([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*)\*([0-9A-F]{2})'
        )
        self._vtg_pattern = re.compile(
            r'\$GPVTG,([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*)\*([0-9A-F]{2})'
        )
    
    def parse_gga(self, sentence: str) -> Optional[Dict[str, any]]:
        """Parse GGA (Global Positioning System Fix Data) sentence.
        
        Args:
            sentence: NMEA GGA sentence.
            
        Returns:
            Optional[Dict]: Parsed GGA data or None if invalid.
        """
        match = self._gga_pattern.match(sentence.strip())
        if not match:
            return None
        
        try:
            time_str = match.group(1)
            lat_deg = float(match.group(2)) if match.group(2) else 0.0
            lat_dir = match.group(3)
            lon_deg = float(match.group(4)) if match.group(4) else 0.0
            lon_dir = match.group(5)
            quality = int(match.group(6)) if match.group(6) else 0
            satellites = int(match.group(7)) if match.group(7) else 0
            hdop = float(match.group(8)) if match.group(8) else 0.0
            altitude = float(match.group(9)) if match.group(9) and match.group(9) != 'M' else 0.0
            geoid_height = float(match.group(11)) if match.group(11) and match.group(11) != 'M' else 0.0
            dgps_age = float(match.group(12)) if match.group(12) and match.group(12) != 'M' else 0.0
            dgps_id = match.group(13) if match.group(13) else ""
            
            # Convert to decimal degrees
            latitude = self._ddm_to_dd(lat_deg, lat_dir)
            longitude = self._ddm_to_dd(lon_deg, lon_dir)
            
            return {
                "sentence_type": "GGA",
                "time": time_str,
                "latitude": latitude,
                "longitude": longitude,
                "quality": quality,
                "satellites": satellites,
                "hdop": hdop,
                "altitude": altitude,
                "geoid_height": geoid_height,
                "dgps_age": dgps_age,
                "dgps_id": dgps_id,
            }
        except (ValueError, IndexError) as e:
            logger.warning(f"Error parsing GGA sentence: {e}")
            return None
    
    def parse_rmc(self, sentence: str) -> Optional[Dict[str, any]]:
        """Parse RMC (Recommended Minimum Navigation Information) sentence.
        
        Args:
            sentence: NMEA RMC sentence.
            
        Returns:
            Optional[Dict]: Parsed RMC data or None if invalid.
        """
        match = self._rmc_pattern.match(sentence.strip())
        if not match:
            return None
        
        try:
            time_str = match.group(1)
            status = match.group(2)
            lat_deg = float(match.group(3)) if match.group(3) else 0.0
            lat_dir = match.group(4)
            lon_deg = float(match.group(5)) if match.group(5) else 0.0
            lon_dir = match.group(6)
            speed_knots = float(match.group(7)) if match.group(7) else 0.0
            course = float(match.group(8)) if match.group(8) else 0.0
            date_str = match.group(9)
            magnetic_variation = float(match.group(10)) if match.group(10) else 0.0
            mag_var_dir = match.group(11)
            
            # Convert to decimal degrees
            latitude = self._ddm_to_dd(lat_deg, lat_dir)
            longitude = self._ddm_to_dd(lon_deg, lon_dir)
            
            # Convert speed to km/h
            speed_kph = speed_knots * 1.852
            
            return {
                "sentence_type": "RMC",
                "time": time_str,
                "status": status,
                "latitude": latitude,
                "longitude": longitude,
                "speed_kph": speed_kph,
                "course": course,
                "date": date_str,
                "magnetic_variation": magnetic_variation,
                "mag_var_dir": mag_var_dir,
            }
        except (ValueError, IndexError) as e:
            logger.warning(f"Error parsing RMC sentence: {e}")
            return None
    
    def parse_vtg(self, sentence: str) -> Optional[Dict[str, any]]:
        """Parse VTG (Track Made Good and Ground Speed) sentence.
        
        Args:
            sentence: NMEA VTG sentence.
            
        Returns:
            Optional[Dict]: Parsed VTG data or None if invalid.
        """
        match = self._vtg_pattern.match(sentence.strip())
        if not match:
            return None
        
        try:
            course_true = float(match.group(1)) if match.group(1) and match.group(1) != 'T' else 0.0
            course_magnetic = float(match.group(3)) if match.group(3) and match.group(3) != 'M' else 0.0
            speed_knots = float(match.group(5)) if match.group(5) and match.group(5) != 'N' else 0.0
            speed_kph = float(match.group(7)) if match.group(7) and match.group(7) != 'K' else 0.0
            
            return {
                "sentence_type": "VTG",
                "course_true": course_true,
                "course_magnetic": course_magnetic,
                "speed_knots": speed_knots,
                "speed_kph": speed_kph,
            }
        except (ValueError, IndexError) as e:
            logger.warning(f"Error parsing VTG sentence: {e}")
            return None
    
    def _ddm_to_dd(self, ddm: float, direction: str) -> float:
        """Convert degrees decimal minutes to decimal degrees.
        
        Args:
            ddm: Degrees decimal minutes.
            direction: N/S/E/W direction.
            
        Returns:
            float: Decimal degrees.
        """
        degrees = int(ddm // 100)
        minutes = ddm % 100
        decimal_degrees = degrees + minutes / 60.0
        
        if direction in ['S', 'W']:
            decimal_degrees = -decimal_degrees
        
        return decimal_degrees


class GPSService:
    """GPS service for reading NMEA data from serial ports."""
    
    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 4800,
        timeout: float = 1.0,
        rate_hz: float = 1.0,
        max_reconnect_attempts: int = 10,
        reconnect_delay: float = 5.0,
    ) -> None:
        """Initialize GPS service.
        
        Args:
            port: Serial port path.
            baudrate: Serial baud rate.
            timeout: Serial timeout in seconds.
            rate_hz: Data collection rate in Hz.
            max_reconnect_attempts: Maximum reconnection attempts.
            reconnect_delay: Delay between reconnection attempts in seconds.
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.rate_hz = rate_hz
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        
        self.parser = NMEAParser()
        self.serial_connection: Optional[serial.Serial] = None
        self.is_running = False
        self.last_known_values: Dict[str, any] = {}
        self.session_id: Optional[int] = None
        
        # Statistics
        self.sentences_received = 0
        self.sentences_parsed = 0
        self.reconnect_count = 0
    
    async def start(self, session_id: int) -> None:
        """Start GPS service for a session.
        
        Args:
            session_id: Session ID to collect data for.
        """
        self.session_id = session_id
        self.is_running = True
        
        logger.info(f"Starting GPS service for session {session_id} on port {self.port}")
        
        # Start the main collection loop
        asyncio.create_task(self._collection_loop())
    
    async def stop(self) -> None:
        """Stop GPS service."""
        self.is_running = False
        
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            logger.info("GPS serial connection closed")
        
        logger.info(f"GPS service stopped. Stats: {self.sentences_received} received, {self.sentences_parsed} parsed")
    
    async def _collection_loop(self) -> None:
        """Main data collection loop."""
        while self.is_running:
            try:
                await self._connect_serial()
                await self._read_serial_data()
            except Exception as e:
                logger.error(f"GPS collection loop error: {e}")
                await self._handle_reconnect()
    
    async def _connect_serial(self) -> None:
        """Connect to serial port with retry logic."""
        for attempt in range(self.max_reconnect_attempts):
            try:
                if self.serial_connection and self.serial_connection.is_open:
                    return
                
                self.serial_connection = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                )
                
                logger.info(f"GPS connected to {self.port} at {self.baudrate} baud")
                self.reconnect_count = 0
                return
                
            except Exception as e:
                logger.warning(f"GPS connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_reconnect_attempts - 1:
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    raise
    
    async def _read_serial_data(self) -> None:
        """Read and process serial data."""
        if not self.serial_connection or not self.serial_connection.is_open:
            raise Exception("Serial connection not available")
        
        buffer = ""
        
        while self.is_running:
            try:
                # Read data from serial port
                data = self.serial_connection.readline().decode('utf-8', errors='ignore')
                if not data:
                    await asyncio.sleep(0.1)
                    continue
                
                buffer += data
                
                # Process complete sentences
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    
                    if line and line.startswith('$'):
                        await self._process_nmea_sentence(line)
                
                # Rate limiting
                await asyncio.sleep(1.0 / self.rate_hz)
                
            except Exception as e:
                logger.error(f"Error reading serial data: {e}")
                raise
    
    async def _process_nmea_sentence(self, sentence: str) -> None:
        """Process a single NMEA sentence.
        
        Args:
            sentence: NMEA sentence to process.
        """
        self.sentences_received += 1
        
        # Parse the sentence
        parsed_data = None
        if sentence.startswith('$GPGGA'):
            parsed_data = self.parser.parse_gga(sentence)
        elif sentence.startswith('$GPRMC'):
            parsed_data = self.parser.parse_rmc(sentence)
        elif sentence.startswith('$GPVTG'):
            parsed_data = self.parser.parse_vtg(sentence)
        
        if parsed_data:
            self.sentences_parsed += 1
            await self._handle_parsed_data(parsed_data)
    
    async def _handle_parsed_data(self, data: Dict[str, any]) -> None:
        """Handle parsed GPS data.
        
        Args:
            data: Parsed GPS data.
        """
        if not self.session_id:
            return
        
        # Update last known values
        self.last_known_values.update(data)
        
        # Create timestamp
        now = datetime.now(timezone.utc)
        ts_mono_ns = asyncio.get_event_loop().time() * 1_000_000_000
        
        # Prepare data for database
        db_data = []
        for key, value in data.items():
            if key == "sentence_type":
                continue
            
            db_data.append({
                "session_id": self.session_id,
                "source": "gps",
                "channel": key,
                "ts_utc": now,
                "ts_mono_ns": int(ts_mono_ns),
                "value_num": float(value) if isinstance(value, (int, float)) else None,
                "value_text": str(value) if not isinstance(value, (int, float)) else None,
                "unit": self._get_unit(key),
            })
        
        # Store in database via database writer
        if db_data:
            for signal_data in db_data:
                telemetry_data = TelemetryData(
                    session_id=signal_data["session_id"],
                    source=signal_data["source"],
                    channel=signal_data["channel"],
                    value_num=signal_data["value_num"],
                    value_text=signal_data["value_text"],
                    unit=signal_data["unit"],
                    quality="good",
                    timestamp=signal_data["ts_utc"],
                )
                await db_writer.queue_signal(telemetry_data)
        
        # Update Meshtastic service with GPS data
        meshtastic_service.update_telemetry_data("gps", data)
        
        # Broadcast to WebSocket
        await websocket_bus.broadcast_to_session(self.session_id, {
            "source": "gps",
            "sentence_type": data.get("sentence_type"),
            "data": data,
            "timestamp": now.isoformat(),
        })
    
    def _get_unit(self, channel: str) -> Optional[str]:
        """Get unit for a GPS channel.
        
        Args:
            channel: Channel name.
            
        Returns:
            Optional[str]: Unit string.
        """
        units = {
            "latitude": "degrees",
            "longitude": "degrees",
            "altitude": "meters",
            "speed_kph": "kph",
            "course": "degrees",
            "hdop": "dimensionless",
            "satellites": "count",
        }
        return units.get(channel)
    
    async def _handle_reconnect(self) -> None:
        """Handle reconnection logic."""
        if not self.is_running:
            return
        
        self.reconnect_count += 1
        logger.warning(f"GPS reconnection attempt {self.reconnect_count}")
        
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        
        await asyncio.sleep(self.reconnect_delay)
    
    def get_status(self) -> Dict[str, any]:
        """Get GPS service status.
        
        Returns:
            Dict[str, any]: Service status information.
        """
        return {
            "is_running": self.is_running,
            "port": self.port,
            "baudrate": self.baudrate,
            "rate_hz": self.rate_hz,
            "session_id": self.session_id,
            "sentences_received": self.sentences_received,
            "sentences_parsed": self.sentences_parsed,
            "reconnect_count": self.reconnect_count,
            "last_known_values": self.last_known_values,
            "serial_connected": self.serial_connection is not None and self.serial_connection.is_open,
        }
    
    @staticmethod
    def list_available_ports() -> List[str]:
        """List available serial ports.
        
        Returns:
            List[str]: List of available serial port paths.
        """
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(port.device)
        return ports
